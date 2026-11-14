from io import BytesIO
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.db.connection import connect
from app.core.config import settings
from app.core.security import password_hash
from app.api.router import _login_attempts
from app.workers.archive import run as archive

@pytest.fixture(autouse=True)
def isolated_database():
    # Never truncate a deployment database when tests are invoked accidentally.
    assert settings().app_database_url.endswith('/loading_app_test')
    assert settings().image_database_url.endswith('/loading_images_test')
    with connect() as conn:
        conn.execute('TRUNCATE workers,admins,sessions,stores,trips,shipments,pallets,photos,audit_log CASCADE')
        conn.execute('INSERT INTO admins(id,username,password_hash) VALUES (%s,%s,%s)', (uuid4(),'admin',password_hash(' test-password-123 ')))
        conn.execute("INSERT INTO stores VALUES ('1001','Test Store',true)")
    with connect(True) as conn:
        conn.execute('TRUNCATE photo_blobs')
    _login_attempts.clear()

def worker():
    client = TestClient(app)
    assert client.post('/api/worker/session',json={'name':'Test Worker'}).status_code == 200
    return client

def build_trip(client):
    trip = str(uuid4())
    payload = {'id':trip,'truck_id':'70-1234','truck_type':'6 ล้อ','shipment_number':'SHP-001','store_code':'1001'}
    assert client.post('/api/trips',json=payload).status_code == 200
    assert client.post('/api/trips',json=payload).status_code == 200
    shipment = trip
    body = {'id':shipment,'number':'SHP-001','store_code':'1001'}
    assert client.post(f'/api/trips/{trip}/shipments',json=body).status_code == 200
    assert client.post(f'/api/trips/{trip}/shipments',json=body).status_code == 200
    pallet = str(uuid4())
    path = f'/api/trips/{trip}/shipments/{shipment}/pallets'
    assert client.post(path,json={'id':pallet}).status_code == 200
    assert client.post(path,json={'id':pallet}).status_code == 200
    return trip, shipment, pallet

def upload(client,trip,pallet,side,color='red'):
    out = BytesIO()
    Image.new('RGB',(32,32),color).save(out,format='JPEG')
    return client.put(f'/api/trips/{trip}/pallets/{pallet}/photos/{side}',files={'file':('image.jpg',out.getvalue(),'image/jpeg')})

def test_full_workflow_and_authorization():
    client = worker()
    trip, shipment, pallet = build_trip(client)
    stranger = worker()
    assert stranger.get(f'/api/trips/{trip}').status_code == 404
    assert stranger.post(f'/api/trips/{trip}/complete').status_code == 404
    assert client.post(f'/api/trips/{trip}/complete').status_code == 409
    photo = upload(client,trip,pallet,'front').json()['id']
    assert upload(client,trip,pallet,'front').json()['id'] == photo
    assert stranger.get(f'/api/photos/{photo}').status_code == 404
    for side in ['back','left','right']:
        assert upload(client,trip,pallet,side).status_code == 200
    assert client.post(f'/api/trips/{trip}/complete').json()['status'] == 'DONE'
    assert client.post(f'/api/trips/{trip}/complete').status_code == 200
    assert upload(client,trip,pallet,'front').status_code == 409
    assert client.get(f'/api/photos/{photo}').headers['content-type'] == 'image/jpeg'
    assert client.get('/api/admin/trips').status_code == 401
    assert client.post('/api/admin/login',json={'username':'admin','password':'wrong'}).status_code == 401
    assert client.post('/api/admin/login',json={'username':'admin','password':' test-password-123 '}).status_code == 200
    assert client.get('/api/admin/summary').json()['shipments'] == 1
    assert client.get('/api/admin/summary').json()['photos'] == 4
    assert client.post('/api/admin/logout').status_code == 200
    assert client.get('/api/admin/me').status_code == 401

def test_duplicate_and_invalid_image():
    client = worker()
    trip, shipment, pallet = build_trip(client)
    assert client.post(f'/api/trips/{trip}/shipments',json={'id':str(uuid4()),'number':'shp-001','store_code':'1001'}).status_code == 409
    path=f'/api/trips/{trip}/pallets/{pallet}/photos/front'
    assert client.put(path,files={'file':('bad.jpg',b'not a photo','image/jpeg')}).status_code == 422
    assert upload(client,trip,pallet,'roof').status_code == 422
    assert client.post('/api/worker/session',json={'name':'Another Worker'}).status_code == 409
    assert client.post('/api/trips',json={'id':str(uuid4()),'truck_id':' ','truck_type':'6'}).status_code == 422

def test_missing_blob_prevents_completion():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    for side in ['front','back','left','right']:
        upload(client,trip,pallet,side)
    with connect(True) as conn:
        conn.execute('DELETE FROM photo_blobs')
    assert client.post(f'/api/trips/{trip}/complete').status_code == 409
    for side in ['front','back','left','right']:
        assert upload(client,trip,pallet,side).status_code == 200
    assert client.post(f'/api/trips/{trip}/complete').status_code == 200

def test_csrf_and_rate_limit():
    client=TestClient(app)
    assert client.post('/api/worker/session',json={'name':'Test Worker'},headers={'Origin':'https://other.example'}).status_code == 403
    for _ in range(10):
        assert client.post('/api/admin/login',json={'username':'admin','password':'wrong'}).status_code == 401
    assert client.post('/api/admin/login',json={'username':'admin','password':'wrong'}).status_code == 429

def test_archive_retains_business_data_and_verifies_readback():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    for side in ['front','back','left','right']:
        upload(client,trip,pallet,side)
    assert client.post(f'/api/trips/{trip}/complete').status_code == 200
    with connect() as conn:
        conn.execute("UPDATE photos SET uploaded_at=now()-interval '31 days'")
    assert archive() == 4
    assert archive() == 0
    with connect() as conn:
        assert conn.execute('SELECT count(*) AS n FROM photos WHERE archived_at IS NOT NULL').fetchone()['n'] == 4
        assert conn.execute('SELECT count(*) AS n FROM trips').fetchone()['n'] == 1
    with connect(True) as conn:
        assert conn.execute('SELECT count(*) AS n FROM photo_blobs').fetchone()['n'] == 0


def test_archive_corruption_never_deletes_source(tmp_path):
    from pathlib import Path
    from zipfile import BadZipFile
    client=worker()
    trip,shipment,pallet=build_trip(client)
    for side in ['front','back','left','right']:
        upload(client,trip,pallet,side)
    assert client.post(f'/api/trips/{trip}/complete').status_code == 200
    root=Path(settings().archive_directory)
    root.mkdir(parents=True,exist_ok=True)
    name=f'{uuid4()}.zip'
    (root/name).write_bytes(b'broken archive')
    with connect() as conn:
        conn.execute('UPDATE photos SET archived_at=now(),archive_file=%s', (name,))
    with pytest.raises(BadZipFile):
        archive()
    with connect(True) as conn:
        assert conn.execute('SELECT count(*) AS n FROM photo_blobs').fetchone()['n'] == 4

def test_open_trip_is_not_archived():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    for side in ['front','back','left','right']:
        upload(client,trip,pallet,side)
    with connect() as conn:
        conn.execute("UPDATE photos SET uploaded_at=now()-interval '31 days'")
    assert archive() == 0
    with connect(True) as conn:
        assert conn.execute('SELECT count(*) AS n FROM photo_blobs').fetchone()['n'] == 4

def test_trip_photos_cap_and_retry():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    out=BytesIO()
    Image.new('RGB',(32,32),'red').save(out,format='JPEG')
    photo_id=str(uuid4())
    def send(identifier):
        return client.put(f'/api/trips/{trip}/photos/{identifier}',files={'file':('image.jpg',out.getvalue(),'image/jpeg')})
    assert send(photo_id).status_code == 200
    assert send(photo_id).status_code == 200
    with connect() as conn:
        original=conn.execute('SELECT * FROM photos WHERE id=%s',(photo_id,)).fetchone()
        for _ in range(119):
            conn.execute('INSERT INTO photos(id,trip_id,sha256,byte_size) VALUES (%s,%s,%s,%s)',(uuid4(),trip,original['sha256'],original['byte_size']))
    assert send(str(uuid4())).status_code == 409
    assert send(photo_id).status_code == 200
    assert len(client.get(f'/api/trips/{trip}').json()['photos']) == 120

def test_one_trip_photo_is_enough():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    assert client.post(f'/api/trips/{trip}/complete').status_code == 409
    out=BytesIO()
    Image.new('RGB',(32,32),'blue').save(out,format='JPEG')
    photo_id=str(uuid4())
    assert client.put(f'/api/trips/{trip}/photos/{photo_id}',files={'file':('image.jpg',out.getvalue(),'image/jpeg')}).status_code == 200
    assert client.post(f'/api/trips/{trip}/complete').status_code == 200

def test_truck_type_is_validated():
    client=worker()
    assert client.post('/api/trips',json={'id':str(uuid4()),'truck_id':'70-1234','truck_type':'other'}).status_code == 422

def test_plate_candidates_and_ocr(monkeypatch):
    from types import SimpleNamespace
    from app.services.plate_ocr import plate_candidates
    assert '63-3512' in plate_candidates('THAILAND\n63-3512\nกรุงเทพมหานคร')
    assert '1กข-1234' in plate_candidates('1กข 1234')
    assert '9กข-3463' in plate_candidates('9 ก ข 3463\nกรุงเทพมหานคร')
    assert '9กข-3463' in plate_candidates('๙กข ๓๔๖๓')
    assert plate_candidates('nothing readable') == []
    monkeypatch.setattr('app.services.plate_ocr.subprocess.run',lambda *args,**kwargs:SimpleNamespace(stdout='63-3512'.encode()))
    client=worker()
    out=BytesIO()
    Image.new('RGB',(32,32),'white').save(out,format='JPEG')
    assert client.post('/api/ocr/plate',files={'file':('plate.jpg',out.getvalue(),'image/jpeg')}).json()['candidates'] == ['63-3512']

def test_migration_preserves_legacy_photo_reference():
    from pathlib import Path
    schema='migration_' + uuid4().hex
    worker_id,trip_id,shipment_id,pallet_id,photo_id=[uuid4() for _ in range(5)]
    with connect() as conn:
        try:
            conn.execute(f'CREATE SCHEMA {schema}')
            conn.execute(f'SET LOCAL search_path TO {schema}')
            migrations=Path(__file__).resolve().parent.parent/'migrations'/'app'
            conn.execute((migrations/'001_initial.sql').read_text(encoding='utf-8-sig'))
            conn.execute('INSERT INTO workers(id,name) VALUES (%s,%s)',(worker_id,'Legacy Worker'))
            conn.execute("INSERT INTO stores VALUES ('S1','Legacy Store',true)")
            conn.execute('INSERT INTO trips(id,worker_id,truck_id,truck_type) VALUES (%s,%s,%s,%s)',(trip_id,worker_id,'70-1234','old custom type'))
            conn.execute("INSERT INTO shipments VALUES (%s,%s,'OLD-SHIP','S1','Legacy Store')",(shipment_id,trip_id))
            conn.execute('INSERT INTO pallets VALUES (%s,%s,1)',(pallet_id,shipment_id))
            conn.execute("INSERT INTO photos(id,pallet_id,side,sha256,byte_size) VALUES (%s,%s,'front',%s,123)",(photo_id,pallet_id,'a'*64))
            conn.execute((migrations/'002_trip_photos.sql').read_text(encoding='utf-8-sig'))
            photo=conn.execute('SELECT * FROM photos WHERE id=%s',(photo_id,)).fetchone()
            assert photo['trip_id']==trip_id
            assert photo['pallet_id']==pallet_id
            assert photo['sha256']=='a'*64
            assert conn.execute('SELECT truck_type FROM trips').fetchone()['truck_type']=='old custom type'
        finally:
            conn.rollback()

def test_trip_creation_is_atomic_and_single_shipment():
    client=worker()
    trip,shipment,pallet=build_trip(client)
    assert client.post(f'/api/trips/{trip}/shipments',json={'id':str(uuid4()),'number':'SECOND','store_code':'1001'}).status_code == 409
    duplicate_id=str(uuid4())
    assert client.post('/api/trips',json={'id':duplicate_id,'truck_id':'70-9999','truck_type':'4 ล้อ','shipment_number':'SHP-001','store_code':'1001'}).status_code == 409
    assert client.get(f'/api/trips/{duplicate_id}').status_code == 404
    unknown_store_id=str(uuid4())
    assert client.post('/api/trips',json={'id':unknown_store_id,'truck_id':'70-9999','truck_type':'4 ล้อ','shipment_number':'NEW','store_code':'missing'}).status_code == 422
    assert client.get(f'/api/trips/{unknown_store_id}').status_code == 404
    assert len(client.get(f'/api/trips/{trip}').json()['shipments']) == 1

def test_trip_province_catalog_and_validation():
    assert TestClient(app).get('/api/provinces').status_code == 401
    client = worker()
    names = [row['name'] for row in client.get('/api/provinces').json()]
    assert len(names) == len(set(names)) == 77
    assert {'กรุงเทพมหานคร', 'บึงกาฬ', 'เชียงใหม่'} <= set(names)
    payload = {'id': str(uuid4()), 'truck_id': '70-1234', 'truck_type': '6 ล้อ',
               'truck_province': 'ไม่มีจังหวัดนี้', 'shipment_number': 'PROVINCE-001', 'store_code': '1001'}
    assert client.post('/api/trips', json=payload).status_code == 422
    payload['truck_province'] = 'เชียงใหม่'
    created = client.post('/api/trips', json=payload)
    assert created.status_code == 200
    assert created.json()['truck_province'] == 'เชียงใหม่'
    assert client.post('/api/trips', json=payload).status_code == 200
    assert client.get(f"/api/trips/{payload['id']}").json()['truck_province'] == 'เชียงใหม่'
    payload['truck_province'] = 'เชียงราย'
    assert client.post('/api/trips', json=payload).status_code == 409


def test_admin_image_download_zip_and_pdf():
    from zipfile import ZipFile
    from pypdf import PdfReader
    client=worker()
    trip,shipment,pallet=build_trip(client)
    out=BytesIO()
    Image.new('RGB',(800,1200),'blue').save(out,format='JPEG')
    ids=[]
    for _ in range(7):
        identifier=str(uuid4());ids.append(identifier)
        assert client.put(f'/api/trips/{trip}/photos/{identifier}',files={'file':('image.jpg',out.getvalue(),'image/jpeg')}).status_code==200
    paths=[f'/api/admin/trips/{trip}/photos/{ids[0]}/download',f'/api/admin/trips/{trip}/photos.zip',f'/api/admin/trips/{trip}/report.pdf']
    for path in paths:
        assert client.get(path).status_code==401
    assert client.post(f'/api/trips/{trip}/complete').status_code==200
    with connect() as conn:
        conn.execute("UPDATE photos SET uploaded_at=now()-interval '31 days' WHERE id=%s",(ids[0],))
    assert archive()==1
    assert client.post('/api/admin/login',json={'username':'admin','password':' test-password-123 '}).status_code==200
    image=client.get(paths[0]);assert image.status_code==200
    assert image.headers['content-disposition'].startswith('attachment;')
    assert image.content[:2]==b'\xff\xd8'
    zipped=client.get(paths[1]);assert zipped.status_code==200
    with ZipFile(BytesIO(zipped.content)) as bundle:
        assert len(bundle.namelist())==7
        assert bundle.testzip() is None
    pdf=client.get(paths[2]);assert pdf.status_code==200
    report=PdfReader(BytesIO(pdf.content));assert len(report.pages)==2
    for page in report.pages:
        assert abs(float(page.mediabox.width)-841.89)<1
        assert abs(float(page.mediabox.height)-595.28)<1
    assert 'PHOTO 007' in report.pages[1].extract_text()
    assert client.get(f'/api/admin/trips/{trip}/photos/{uuid4()}/download').status_code==404
    with connect(True) as conn:
        conn.execute('DELETE FROM photo_blobs WHERE id=%s',(ids[1],))
    assert client.get(paths[1]).status_code==503
    assert client.get(paths[2]).status_code==503
