from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic
from threading import Lock
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from psycopg.errors import UniqueViolation
from app.api.schemas import WorkerInput, LoginInput, TripInput, ShipmentInput, PalletInput, StoreInput
from app.core.security import worker, admin, actor, create_session, password_matches, password_hash, trip_access
from app.db.connection import connect
from app.services.images import normalize_image

router = APIRouter()
_login_attempts = defaultdict(deque)
_login_lock = Lock()
_dummy_password = password_hash('timing-only-not-an-account')

def audit(conn, who, event, target=None):
    conn.execute('INSERT INTO audit_log(actor_id,event,target_id) VALUES (%s,%s,%s)', (who['id'], event, target))

def detail(conn, trip_id, who):
    trip = trip_access(conn, trip_id, who)
    trip['worker_name'] = conn.execute('SELECT name FROM workers WHERE id=%s', (trip['worker_id'],)).fetchone()['name']
    trip['shipments'] = conn.execute('SELECT * FROM shipments WHERE trip_id=%s ORDER BY number', (trip_id,)).fetchall()
    for shipment in trip['shipments']:
        shipment['pallets'] = conn.execute('SELECT * FROM pallets WHERE shipment_id=%s ORDER BY number', (shipment['id'],)).fetchall()
        for pallet in shipment['pallets']:
            pallet['photos'] = conn.execute('SELECT id,side,byte_size,uploaded_at,archived_at FROM photos WHERE pallet_id=%s ORDER BY side', (pallet['id'],)).fetchall()
    trip['photos'] = conn.execute('SELECT id,side,byte_size,uploaded_at,archived_at FROM photos WHERE trip_id=%s ORDER BY uploaded_at,id', (trip_id,)).fetchall()
    return trip

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.get('/ready')
def ready():
    for images in (False, True):
        with connect(images) as conn:
            conn.execute('SELECT 1')
    return {'status': 'ready'}

@router.post('/worker/session')
def worker_login(body: WorkerInput, request: Request, response: Response):
    try:
        current = worker(request)
    except HTTPException:
        current = None
    with connect() as conn:
        if current and current['name'] == body.name:
            return current
        if current and conn.execute("SELECT 1 FROM trips WHERE worker_id=%s AND status='OPEN' LIMIT 1", (current['id'],)).fetchone():
            raise HTTPException(409, 'มีเที่ยวรถค้างในชื่อเดิม กรุณาทำงานเดิมให้เสร็จก่อนเปลี่ยนชื่อ')
        worker_id = uuid4()
        conn.execute('INSERT INTO workers(id,name) VALUES (%s,%s)', (worker_id, body.name))
        create_session(conn, response, worker_id, 'worker')
        return {'id': worker_id, 'name': body.name, 'role': 'worker'}

@router.get('/worker/me')
def worker_me(who=Depends(worker)):
    return who

@router.post('/admin/login')
def login(body: LoginInput, request: Request, response: Response):
    now = monotonic()
    # Single API process; attempts expire after 15 minutes. Proxy overwrites this header.
    ip = request.headers.get('x-real-ip', request.client.host if request.client else 'unknown')
    with _login_lock:
        for key in list(_login_attempts):
            if not _login_attempts[key] or now - _login_attempts[key][-1] > 900:
                del _login_attempts[key]
        attempts = _login_attempts[ip]
        while attempts and now-attempts[0]>900:
            attempts.popleft()
        if len(attempts)>=10:
            raise HTTPException(429, 'ลองเข้าสู่ระบบบ่อยเกินไป กรุณารอ 15 นาที')
        attempts.append(now)
    with connect() as conn:
        account = conn.execute('SELECT * FROM admins WHERE username=%s', (body.username.strip().lower(),)).fetchone()
        valid = password_matches(body.password, account['password_hash'] if account else _dummy_password)
        if not account or not valid:
            raise HTTPException(401, 'ชื่อบัญชีหรือรหัสผ่านไม่ถูกต้อง')
        create_session(conn, response, account['id'], 'admin')
        audit(conn, {'id': account['id']}, 'admin.login')
        return {'name': account['username'], 'role': 'admin'}

@router.get('/admin/me')
def admin_me(who=Depends(admin)):
    return who

@router.post('/admin/logout')
def logout(request: Request, response: Response):
    import hashlib
    with connect() as conn:
        conn.execute('DELETE FROM sessions WHERE token_hash=%s', (hashlib.sha256(request.cookies.get('admin_session','').encode()).hexdigest(),))
    response.delete_cookie('admin_session', path='/')
    return {'ok': True}

@router.get('/stores')
def stores(who=Depends(actor)):
    with connect() as conn:
        return conn.execute('SELECT * FROM stores WHERE active=true ORDER BY code').fetchall()

@router.get('/provinces')
def provinces(who=Depends(actor)):
    with connect() as conn:
        return conn.execute('SELECT name FROM provinces ORDER BY name').fetchall()

@router.get('/admin/stores')
def admin_stores(who=Depends(admin)):
    with connect() as conn:
        return conn.execute('SELECT * FROM stores ORDER BY code').fetchall()

@router.put('/admin/stores/{code}')
def save_store(code: str, body: StoreInput, who=Depends(admin)):
    if code != body.code:
        raise HTTPException(422, 'รหัส Store ไม่ตรงกัน')
    with connect() as conn:
        conn.execute('INSERT INTO stores(code,name,active) VALUES (%s,%s,%s) ON CONFLICT(code) DO UPDATE SET name=excluded.name,active=excluded.active', (body.code,body.name,body.active))
        audit(conn, who, 'store.update')
    return body

@router.get('/trips')
def trips(who=Depends(worker)):
    with connect() as conn:
        return conn.execute('SELECT * FROM trips WHERE worker_id=%s ORDER BY created_at DESC LIMIT 100', (who['id'],)).fetchall()

@router.post('/trips')
def create_trip(body: TripInput, who=Depends(worker)):
    try:
        with connect() as conn:
            if body.truck_province is not None and not conn.execute('SELECT 1 FROM provinces WHERE name=%s', (body.truck_province,)).fetchone():
                raise HTTPException(422, 'กรุณาเลือกจังหวัดป้ายทะเบียนจากรายการ')
            conn.execute('INSERT INTO trips(id,worker_id,truck_id,truck_type,truck_province) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING', (body.id,who['id'],body.truck_id,body.truck_type,body.truck_province))
            result = trip_access(conn, body.id, who)
            conn.execute('SELECT id FROM trips WHERE id=%s FOR UPDATE', (body.id,))
            if result['truck_id'] != body.truck_id or result['truck_type'] != body.truck_type or result['truck_province'] != body.truck_province:
                raise HTTPException(409, 'คำขอเดิมมีข้อมูลรถไม่ตรงกัน')
            existing = conn.execute('SELECT * FROM shipments WHERE trip_id=%s', (body.id,)).fetchall()
            if existing:
                if len(existing)!=1 or existing[0]['number']!=body.shipment_number.upper() or existing[0]['store_code']!=body.store_code:
                    raise HTTPException(409, 'คำขอเดิมมี Shipment หรือ Store ไม่ตรงกัน')
            else:
                store = conn.execute('SELECT * FROM stores WHERE code=%s AND active=true', (body.store_code,)).fetchone()
                if not store:
                    raise HTTPException(422, 'กรุณาเลือก Store ที่เปิดใช้งาน')
                conn.execute('INSERT INTO shipments VALUES (%s,%s,%s,%s,%s)', (body.id,body.id,body.shipment_number.upper(),body.store_code,store['name']))
                audit(conn, who, 'trip.create', body.id)
            return detail(conn, body.id, who)
    except UniqueViolation:
        raise HTTPException(409, 'เลข Shipment นี้มีในระบบแล้ว กรุณาตรวจสอบงานค้าง')

@router.get('/trips/{trip_id}')
def get_trip(trip_id: UUID, who=Depends(actor)):
    with connect() as conn:
        return detail(conn, trip_id, who)

@router.post('/trips/{trip_id}/shipments')
def add_shipment(trip_id: UUID, body: ShipmentInput, who=Depends(worker)):
    try:
        with connect() as conn:
            trip_access(conn, trip_id, who, True)
            existing = conn.execute('SELECT * FROM shipments WHERE id=%s', (body.id,)).fetchone()
            if existing:
                if existing['trip_id'] != trip_id or existing['number'] != body.number.upper() or existing['store_code'] != body.store_code:
                    raise HTTPException(409, 'คำขอ Shipment ซ้ำแต่ข้อมูลไม่ตรงกัน')
                return detail(conn, trip_id, who)
            if conn.execute('SELECT 1 FROM shipments WHERE trip_id=%s', (trip_id,)).fetchone():
                raise HTTPException(409, 'หนึ่ง Trip มีได้เพียงหนึ่ง Shipment และหนึ่ง Store')
            store = conn.execute('SELECT * FROM stores WHERE code=%s AND active=true', (body.store_code,)).fetchone()
            if not store:
                raise HTTPException(422, 'กรุณาเลือก Store ที่เปิดใช้งาน')
            conn.execute('INSERT INTO shipments VALUES (%s,%s,%s,%s,%s)', (body.id,trip_id,body.number.upper(),body.store_code,store['name']))
            audit(conn, who, 'shipment.create', body.id)
            return detail(conn, trip_id, who)
    except UniqueViolation:
        raise HTTPException(409, 'เลข Shipment นี้มีในระบบแล้ว กรุณาตรวจสอบงานค้าง')

@router.post('/trips/{trip_id}/shipments/{shipment_id}/pallets')
def add_pallet(trip_id: UUID, shipment_id: UUID, body: PalletInput, who=Depends(worker)):
    with connect() as conn:
        trip_access(conn, trip_id, who, True)
        if not conn.execute('SELECT 1 FROM shipments WHERE id=%s AND trip_id=%s', (shipment_id,trip_id)).fetchone():
            raise HTTPException(404, 'ไม่พบ Shipment')
        existing = conn.execute('SELECT * FROM pallets WHERE id=%s', (body.id,)).fetchone()
        if existing:
            if existing['shipment_id'] != shipment_id:
                raise HTTPException(409, 'Pallet ID ซ้ำ')
        else:
            number = conn.execute('SELECT COALESCE(MAX(number),0)+1 AS n FROM pallets WHERE shipment_id=%s', (shipment_id,)).fetchone()['n']
            conn.execute('INSERT INTO pallets VALUES (%s,%s,%s)', (body.id,shipment_id,number))
        return detail(conn, trip_id, who)

@router.put('/trips/{trip_id}/pallets/{pallet_id}/photos/{side}')
def upload(trip_id: UUID, pallet_id: UUID, side: str, file: UploadFile = File(...), who=Depends(worker)):
    if side not in ('front','back','left','right'):
        raise HTTPException(422, 'ด้านภาพไม่ถูกต้อง')
    content = file.file.read(8 * 1024 * 1024 + 1)
    if len(content)>8 * 1024 * 1024:
        raise HTTPException(413, 'ไฟล์ภาพต้องไม่เกิน 8 MB')
    data, digest = normalize_image(content)
    with connect() as conn:
        trip_access(conn, trip_id, who, True)
        if not conn.execute('SELECT 1 FROM pallets p JOIN shipments s ON s.id=p.shipment_id WHERE p.id=%s AND s.trip_id=%s', (pallet_id,trip_id)).fetchone():
            raise HTTPException(404, 'ไม่พบ Pallet')
        previous = conn.execute('SELECT * FROM photos WHERE pallet_id=%s AND side=%s', (pallet_id,side)).fetchone()
        if previous and previous['sha256'] == digest and not previous['archived_at']:
            with connect(True) as images:
                existing_blob = images.execute('SELECT sha256 FROM photo_blobs WHERE id=%s', (previous['id'],)).fetchone()
            if existing_blob and existing_blob['sha256'] == digest:
                return {'id': previous['id'], 'side': side}
        if not previous and conn.execute('SELECT count(*) AS n FROM photos WHERE trip_id=%s', (trip_id,)).fetchone()['n'] >= 120:
            raise HTTPException(409, 'เที่ยวรถนี้มีภาพครบ 120 ภาพแล้ว')
        photo_id = uuid4()
        # Blob is committed first. Unreferenced blobs after a crash are cleaned by archive maintenance.
        with connect(True) as images:
            images.execute('INSERT INTO photo_blobs(id,content,sha256) VALUES (%s,%s,%s)', (photo_id,data,digest))
        conn.execute('INSERT INTO photos(id,pallet_id,side,sha256,byte_size,trip_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(pallet_id,side) DO UPDATE SET id=excluded.id,sha256=excluded.sha256,byte_size=excluded.byte_size,uploaded_at=now(),archived_at=NULL,archive_file=NULL', (photo_id,pallet_id,side,digest,len(data),trip_id))
        audit(conn, who, 'photo.replace' if previous else 'photo.upload', photo_id)
    return {'id': photo_id, 'side': side}

@router.get('/photos/{photo_id}')
def photo(photo_id: UUID, who=Depends(actor)):
    with connect() as conn:
        row = conn.execute('SELECT f.* FROM photos f WHERE f.id=%s', (photo_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'ไม่พบภาพ')
        trip_access(conn, row['trip_id'], who)
        if row['archived_at']:
            raise HTTPException(410, 'ภาพถูก Archive แล้ว')
    with connect(True) as images:
        blob = images.execute('SELECT content FROM photo_blobs WHERE id=%s', (photo_id,)).fetchone()
        if not blob:
            raise HTTPException(503, 'ไม่พบข้อมูลภาพ กรุณาติดต่อผู้ดูแล')
        return Response(bytes(blob['content']), media_type='image/jpeg', headers={'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})

@router.post('/trips/{trip_id}/complete')
def complete(trip_id: UUID, who=Depends(worker)):
    with connect() as conn:
        trip_access(conn, trip_id, who)
        conn.execute('SELECT id FROM trips WHERE id=%s FOR UPDATE', (trip_id,))
        trip = trip_access(conn, trip_id, who)
        if trip['status'] == 'DONE':
            return detail(conn, trip_id, who)
        trip_access(conn, trip_id, who, True)
        current = detail(conn, trip_id, who)
        if len(current['shipments']) != 1 or not current['photos']:
            raise HTTPException(409, 'ต้องมี Shipment เดียวและภาพอย่างน้อย 1 ภาพก่อนปิดเที่ยวรถ')
        ids = [photo['id'] for photo in current['photos']]
        with connect(True) as images:
            count = images.execute('SELECT count(*) AS n FROM photo_blobs WHERE id=ANY(%s)', (ids,)).fetchone()['n']
        if count != len(ids):
            raise HTTPException(409, 'ภาพยังไม่ครบในฐานข้อมูล กรุณาลองส่งใหม่')
        conn.execute("UPDATE trips SET status='DONE',completed_at=now() WHERE id=%s", (trip_id,))
        audit(conn, who, 'trip.complete', trip_id)
        return detail(conn, trip_id, who)

@router.get('/admin/trips')
def admin_trips(q: str = '', offset: int = 0, who=Depends(admin)):
    if len(q)>100 or offset<0:
        raise HTTPException(422, 'เงื่อนไขค้นหาไม่ถูกต้อง')
    with connect() as conn:
        return conn.execute('''SELECT t.*,w.name AS worker_name,
          (SELECT count(*) FROM shipments s WHERE s.trip_id=t.id) AS shipment_count,
          (SELECT count(*) FROM photos f WHERE f.trip_id=t.id) AS photo_count
          FROM trips t JOIN workers w ON w.id=t.worker_id
          WHERE t.truck_id ILIKE %s OR t.truck_province ILIKE %s OR EXISTS(SELECT 1 FROM shipments s WHERE s.trip_id=t.id AND (s.number ILIKE %s OR s.store_name ILIKE %s OR s.store_code ILIKE %s))
          ORDER BY t.created_at DESC,t.id DESC LIMIT 50 OFFSET %s''', (f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',offset)).fetchall()

@router.get('/admin/summary')
def summary(who=Depends(admin)):
    with connect() as conn:
        return conn.execute("SELECT count(*) AS trips, count(*) FILTER(WHERE status='OPEN') AS open, count(*) FILTER(WHERE status='DONE') AS done, (SELECT count(*) FROM shipments) AS shipments, (SELECT count(*) FROM photos) AS photos FROM trips").fetchone()


@router.get('/admin/storage')
def storage_status(who=Depends(admin)):
    import shutil
    from app.core.config import settings
    cfg = settings()
    try:
        usage = shutil.disk_usage(cfg.archive_directory)
        free_bytes = usage.free
    except OSError:
        free_bytes = None
    with connect() as conn:
        totals = conn.execute('SELECT count(*) FILTER(WHERE archived_at IS NULL) AS online_photos, count(*) FILTER(WHERE archived_at IS NOT NULL) AS archived_photos, COALESCE(sum(byte_size) FILTER(WHERE archived_at IS NULL),0) AS online_bytes FROM photos').fetchone()
    return {**totals, 'retention_days':cfg.photo_retention_days, 'archive_enabled':cfg.archive_enabled, 'archive_free_bytes':free_bytes}



@router.get('/admin/archived-photos/{photo_id}')
def archived_photo(photo_id: UUID, who=Depends(admin)):
    import hashlib
    from pathlib import Path
    from zipfile import ZipFile, BadZipFile
    from app.core.config import settings
    with connect() as conn:
        row = conn.execute('SELECT archive_file,sha256 FROM photos WHERE id=%s AND archived_at IS NOT NULL', (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'ไม่พบภาพใน Archive')
    try:
        path = Path(settings().archive_directory) / Path(row['archive_file']).name
        with ZipFile(path) as archive:
            data = archive.read(f'{photo_id}.jpg')
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Checksum mismatch')
    except (OSError, KeyError, BadZipFile, ValueError):
        raise HTTPException(503, 'Archive ไม่พร้อมหรือไม่ผ่านการตรวจสอบ กรุณาติดต่อ IT')
    return Response(data, media_type='image/jpeg', headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@router.post('/ocr/plate')
def plate_ocr(file: UploadFile = File(...), who=Depends(worker)):
    from app.services.plate_ocr import recognize_plate
    content = file.file.read(8 * 1024 * 1024 + 1)
    if len(content)>8 * 1024 * 1024:
        raise HTTPException(413, 'ไฟล์ภาพต้องไม่เกิน 8 MB')
    return recognize_plate(content)

@router.put('/trips/{trip_id}/photos/{photo_id}')
def upload_trip_photo(trip_id: UUID, photo_id: UUID, file: UploadFile = File(...), who=Depends(worker)):
    content = file.file.read(8 * 1024 * 1024 + 1)
    if len(content)>8 * 1024 * 1024:
        raise HTTPException(413, 'ไฟล์ภาพต้องไม่เกิน 8 MB')
    data, digest = normalize_image(content)
    with connect() as conn:
        trip_access(conn, trip_id, who, True)
        previous = conn.execute('SELECT * FROM photos WHERE id=%s', (photo_id,)).fetchone()
        if previous and (previous['trip_id'] != trip_id or previous['sha256'] != digest):
            raise HTTPException(409, 'Photo ID ซ้ำกับภาพอื่น กรุณาโหลดหน้าจอใหม่')
        if not previous and conn.execute('SELECT count(*) AS n FROM photos WHERE trip_id=%s', (trip_id,)).fetchone()['n'] >= 120:
            raise HTTPException(409, 'เที่ยวรถนี้มีภาพครบ 120 ภาพแล้ว')
        with connect(True) as images:
            images.execute('INSERT INTO photo_blobs(id,content,sha256) VALUES (%s,%s,%s) ON CONFLICT(id) DO NOTHING', (photo_id,data,digest))
            blob = images.execute('SELECT sha256 FROM photo_blobs WHERE id=%s', (photo_id,)).fetchone()
            if blob['sha256'] != digest:
                raise HTTPException(409, 'Photo ID มีข้อมูลภาพต่างกัน')
        conn.execute('INSERT INTO photos(id,trip_id,sha256,byte_size) VALUES (%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING', (photo_id,trip_id,digest,len(data)))
        stored = conn.execute('SELECT trip_id FROM photos WHERE id=%s', (photo_id,)).fetchone()
        if stored['trip_id'] != trip_id:
            raise HTTPException(409, 'Photo ID ถูกใช้กับเที่ยวรถอื่นแล้ว')
        if not previous:
            audit(conn, who, 'photo.upload', photo_id)
    return {'id':photo_id}
