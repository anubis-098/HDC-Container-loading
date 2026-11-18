from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile
import json
from PIL import Image, ImageDraw
from pypdf import PdfReader
from test_workflow import isolated_database, worker
from app.db.connection import connect


def new_trip(client, **extra):
    body={'id':str(uuid4()),'truck_id':'70-1234','truck_type':'10 ล้อ',**extra}
    response=client.post('/api/trips',json=body)
    assert response.status_code==200, response.text
    return response.json(),body


def photo(client,trip,pallet=None,photo_id=None):
    content=BytesIO();Image.new('RGB',(640,480),'#006da8').save(content,'JPEG')
    photo_id=photo_id or str(uuid4())
    return client.put(f'/api/trips/{trip}/photos/{photo_id}',params={'pallet_id':pallet} if pallet else {},files={'file':('image.jpg',content.getvalue(),'image/jpeg')})


def test_admin_can_cancel_only_open_trips_and_preserve_data():
    client=worker();trip,_=new_trip(client);tid=trip['id']
    payload={'id':str(uuid4()),'store_code':'1001','orders':['KEEP-ORDER']}
    assert client.post(f'/api/trips/{tid}/pallets',json=payload).status_code==200
    assert photo(client,tid,payload['id']).status_code==200
    assert client.post(f'/api/admin/trips/{tid}/cancel').status_code==401
    from fastapi.testclient import TestClient
    from app.main import app
    administrator=TestClient(app)
    assert administrator.post('/api/admin/login',json={'username':'admin','password':' test-password-123 '}).status_code==200
    response=administrator.post(f'/api/admin/trips/{tid}/cancel')
    assert response.status_code==200,response.text
    cancelled=response.json()
    assert cancelled['status']=='CANCELLED' and cancelled['cancelled_at'] and cancelled['cancelled_by']
    assert cancelled['completed_at'] is None
    assert cancelled['pallets'][0]['orders']==['KEEP-ORDER'] and len(cancelled['photos'])==1
    assert administrator.post(f'/api/admin/trips/{tid}/cancel').status_code==200
    assert client.get(f'/api/trips/{tid}').json()['status']=='CANCELLED'
    assert client.post(f'/api/trips/{tid}/complete').status_code==409
    assert photo(client,tid,payload['id']).status_code==409
    assert client.put(f'/api/trips/{tid}/pallets/{payload["id"]}',json=payload).status_code==409
    stats=administrator.get('/api/admin/summary').json()
    assert stats['cancelled']==1 and stats['open']==0 and stats['done']==0
    with connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM audit_log WHERE event='trip.cancel' AND target_id=%s",(tid,)).fetchone()['n']==1
    completed,_=new_trip(client)
    with connect() as conn:conn.execute("UPDATE trips SET status='DONE' WHERE id=%s",(completed['id'],))
    assert administrator.post(f'/api/admin/trips/{completed["id"]}/cancel').status_code==409


def test_multi_store_pallets_orders_and_both_photo_scopes(tmp_path, monkeypatch):
    client=worker();trip,body=new_trip(client)
    assert trip['structure_version']==2 and trip['shipments']==[] and trip['pallets']==[]
    assert client.post('/api/trips',json=body).status_code==200
    tid=trip['id']
    assert photo(client,tid).status_code==200
    assert client.post(f'/api/trips/{tid}/complete').status_code==409
    with connect() as conn:conn.execute("INSERT INTO stores(code,name) VALUES('2002','Second Store')")
    first={'id':str(uuid4()),'store_code':'1001','orders':['ORDER-A','ORDER-B']}
    second={'id':str(uuid4()),'store_code':'2002','orders':['ORDER-A','ORDER-C']}
    for payload in [first,second]:
        result=client.post(f'/api/trips/{tid}/pallets',json=payload)
        assert result.status_code==200,result.text
        assert client.post(f'/api/trips/{tid}/pallets',json=payload).status_code==200
    assert client.post(f'/api/trips/{tid}/pallets',json={**first,'orders':['DIFFERENT']}).status_code==409
    pid=str(uuid4());assert photo(client,tid,first['id'],pid).status_code==200
    assert photo(client,tid,first['id'],pid).status_code==200
    assert photo(client,tid,second['id'],pid).status_code==409
    assert photo(client,tid,second['id']).status_code==200
    state=client.get(f'/api/trips/{tid}').json()
    assert len(state['pallets'])==2 and len(state['photos'])==3
    assert len([p for p in state['photos'] if p['pallet_id'] is None])==1
    assert state['pallets'][0]['orders']==['ORDER-A','ORDER-B']
    assert len(state['pallets'][0]['photos'])==1
    stranger=worker()
    assert stranger.put(f'/api/trips/{tid}/pallets/{first["id"]}',json=first).status_code==404
    assert client.post(f'/api/trips/{tid}/complete').json()['status']=='DONE'
    assert client.post(f'/api/trips/{tid}/complete').status_code==200
    assert client.put(f'/api/trips/{tid}/pallets/{first["id"]}',json=first).status_code==409
    assert photo(client,tid,first['id']).status_code==409
    assert client.post('/api/admin/login',json={'username':'admin','password':' test-password-123 '}).status_code==200
    assert client.get('/api/admin/trips',params={'q':'ORDER-C'}).json()[0]['id']==tid
    assert client.get('/api/admin/summary').json()['pallets']==2
    zipped=client.get(f'/api/admin/trips/{tid}/photos.zip');assert zipped.status_code==200
    with ZipFile(BytesIO(zipped.content)) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert len(manifest['pallets'])==2 and manifest['pallets'][0]['orders']==first['orders']
        photos = [name for name in archive.namelist() if name.endswith('.jpg')]
        assert len(photos)==5
        assert any(name.startswith('Trip-overview/') for name in archive.namelist())
        assert any(name.startswith('Pallet-001/ORDER-A/') for name in photos)
        assert any(name.startswith('Pallet-001/ORDER-B/') for name in photos)
        assert any(name.startswith('Pallet-002/ORDER-C/') for name in photos)
        assert len(photos)==len(set(photos))
        first_copies = [archive.read(name) for name in photos if name.startswith('Pallet-001/')]
        assert first_copies[0] == first_copies[1]
    labels=[]
    original_text=ImageDraw.ImageDraw.text
    def capture_text(self,xy,text,*args,**kwargs):
        labels.append(str(text))
        return original_text(self,xy,text,*args,**kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw,'text',capture_text)
    report=client.get(f'/api/admin/trips/{tid}/report.pdf');assert report.status_code==200,report.text
    assert len(PdfReader(BytesIO(report.content)).pages)==2
    assert any('Order No.:' in label and 'ORDER-A' in label for label in labels)
    for order in ['ORDER-A','ORDER-B','ORDER-C']:
        assert any('Order No.' in label and order in label for label in labels)
    from pathlib import Path
    Path('/tmp/pallet-uat.pdf').write_bytes(report.content)
    selected=client.post('/api/admin/trips/photos.zip',json=[tid]);assert selected.status_code==200
    with ZipFile(BytesIO(selected.content)) as archive:
        assert any(name.endswith('manifest.json') for name in archive.namelist())
        assert len([name for name in archive.namelist() if name.endswith('.jpg')])==5
        assert any('/Pallet-001/ORDER-B/' in name for name in archive.namelist())
    with connect() as conn:conn.execute("UPDATE photos SET uploaded_at=now()-interval '31 days' WHERE trip_id=%s",(tid,))
    from app.workers.archive import run
    assert run()==3
    assert client.get(f'/api/admin/trips/{tid}/photos.zip').status_code==200
    assert client.get(f'/api/admin/trips/{tid}/report.pdf').status_code==200
    assert client.delete(f'/api/admin/trips/{tid}').status_code==200
    with connect() as conn:assert conn.execute('SELECT count(*) AS n FROM pallet_orders').fetchone()['n']==0


def test_pallet_validation_edits_and_cross_trip_photos():
    client=worker();one,_=new_trip(client);two,_=new_trip(client)
    tid=one['id'];payload={'id':str(uuid4()),'store_code':'1001','orders':['ORDER-1']}
    for changes in [{'store_code':'missing'},{'orders':[]},{'orders':None},{'orders':['DUP','DUP']},{'orders':[' ']},{'orders':['x'*81]},{'orders':['x']*101}]:
        assert client.post(f'/api/trips/{tid}/pallets',json={**payload,**changes}).status_code==422
    assert client.get(f'/api/trips/{tid}').json()['pallets']==[]
    assert client.post(f'/api/trips/{tid}/pallets',json=payload).status_code==200
    assert photo(client,two['id'],payload['id']).status_code==404
    assert client.post(f'/api/trips/{two["id"]}/pallets',json=payload).status_code==409
    edited={**payload,'orders':['000123','ORDER-B']}
    assert client.put(f'/api/trips/{tid}/pallets/{payload["id"]}',json=edited).status_code==200
    assert client.get(f'/api/trips/{tid}').json()['pallets'][0]['orders']==edited['orders']
    assert client.put(f'/api/trips/{tid}/pallets/{payload["id"]}',json={**edited,'orders':[]}).status_code==422
    assert photo(client,tid,payload['id']).status_code==200
    with connect() as conn:conn.execute('DELETE FROM pallet_orders WHERE pallet_id=%s',(payload['id'],))
    response=client.post(f'/api/trips/{tid}/complete')
    assert response.status_code==409 and 'Order' in response.json()['detail']
    assert client.put(f'/api/trips/{tid}/pallets/{payload["id"]}',json=edited).status_code==200
    assert client.post(f'/api/trips/{tid}/complete').status_code==200
