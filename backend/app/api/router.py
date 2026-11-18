from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic
from threading import Lock
from uuid import UUID, uuid4
from fastapi import Form, APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from psycopg.errors import UniqueViolation
from app.api.schemas import WorkerInput, LoginInput, TripInput, ShipmentInput, PalletInput, StoreInput, TripPalletInput
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
    trip['photos'] = conn.execute('SELECT id,pallet_id,side,byte_size,uploaded_at,archived_at FROM photos WHERE trip_id=%s ORDER BY uploaded_at,id', (trip_id,)).fetchall()
    trip['pallets'] = conn.execute('SELECT * FROM pallets WHERE trip_id=%s ORDER BY number,id', (trip_id,)).fetchall()
    order_rows = conn.execute('SELECT o.* FROM pallet_orders o JOIN pallets p ON p.id=o.pallet_id WHERE p.trip_id=%s ORDER BY o.position', (trip_id,)).fetchall()
    for pallet in trip['pallets']:
        pallet['orders'] = [o['order_number'] for o in order_rows if o['pallet_id']==pallet['id']]
        pallet['photos'] = [photo for photo in trip['photos'] if photo['pallet_id']==pallet['id']]
    for shipment in trip['shipments']:
        shipment['pallets'] = [p for p in trip['pallets'] if p['shipment_id']==shipment['id']]
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
        conn.execute('DELETE FROM sessions WHERE token_hash=%s', (hashlib.sha256(request.cookies.get('hdc_container_admin_session','').encode()).hexdigest(),))
    response.delete_cookie('hdc_container_admin_session', path='/')
    return {'ok': True}

@router.get('/stores')
def stores(who=Depends(actor)):
    with connect() as conn:
        return conn.execute('SELECT * FROM stores WHERE active=true AND deleted_at IS NULL ORDER BY code').fetchall()

@router.get('/provinces')
def provinces(who=Depends(actor)):
    with connect() as conn:
        return conn.execute('SELECT name FROM provinces ORDER BY name').fetchall()

@router.get('/admin/stores')
def admin_stores(who=Depends(admin)):
    with connect() as conn:
        return conn.execute('SELECT * FROM stores WHERE deleted_at IS NULL ORDER BY code').fetchall()

@router.put('/admin/stores/{code}')
def save_store(code: str, body: StoreInput, who=Depends(admin)):
    if code != body.code:
        raise HTTPException(422, 'รหัส Store ไม่ตรงกัน')
    with connect() as conn:
        conn.execute('INSERT INTO stores(code,name,active) VALUES (%s,%s,%s) ON CONFLICT(code) DO UPDATE SET name=excluded.name,active=excluded.active,deleted_at=NULL', (body.code,body.name,body.active))
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
            if body.shipment_number is None:
                conn.execute('INSERT INTO trips(id,worker_id,truck_id,truck_type,truck_province,structure_version) VALUES(%s,%s,%s,%s,%s,2) ON CONFLICT(id) DO NOTHING', (body.id,who['id'],body.truck_id,body.truck_type,body.truck_province))
                current = trip_access(conn, body.id, who)
                if current['structure_version']!=2 or (current['truck_id'],current['truck_type'],current['truck_province'])!=(body.truck_id,body.truck_type,body.truck_province):
                    raise HTTPException(409, 'Trip request does not match existing vehicle data')
                if not conn.execute("SELECT 1 FROM audit_log WHERE event='trip.create' AND target_id=%s", (body.id,)).fetchone():
                    audit(conn, who, 'trip.create', body.id)
                return detail(conn, body.id, who)
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
                store = conn.execute('SELECT * FROM stores WHERE code=%s AND active=true AND deleted_at IS NULL', (body.store_code,)).fetchone()
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
            store = conn.execute('SELECT * FROM stores WHERE code=%s AND active=true AND deleted_at IS NULL', (body.store_code,)).fetchone()
            if not store:
                raise HTTPException(422, 'กรุณาเลือก Store ที่เปิดใช้งาน')
            conn.execute('INSERT INTO shipments VALUES (%s,%s,%s,%s,%s)', (body.id,trip_id,body.number.upper(),body.store_code,store['name']))
            audit(conn, who, 'shipment.create', body.id)
            return detail(conn, trip_id, who)
    except UniqueViolation:
        raise HTTPException(409, 'เลข Shipment นี้มีในระบบแล้ว กรุณาตรวจสอบงานค้าง')

def save_trip_pallet(conn, trip_id, body, who, editing=False):
    trip_access(conn, trip_id, who, True)
    existing = conn.execute('SELECT * FROM pallets WHERE id=%s', (body.id,)).fetchone()
    if existing and existing['trip_id'] != trip_id:
        raise HTTPException(409, 'Pallet ID is already used by another Trip')
    if editing and not existing:
        raise HTTPException(404, 'Pallet not found')
    current_orders = [o['order_number'] for o in conn.execute('SELECT order_number FROM pallet_orders WHERE pallet_id=%s ORDER BY position', (body.id,)).fetchall()]
    if existing and not editing:
        if existing['store_code'] != body.store_code or current_orders != body.orders:
            raise HTTPException(409, 'Pallet request does not match existing data')
        return detail(conn, trip_id, who)
    if existing and existing['store_code']==body.store_code:
        store_name = existing['store_name']
    else:
        store = conn.execute('SELECT * FROM stores WHERE code=%s AND active=true AND deleted_at IS NULL FOR SHARE', (body.store_code,)).fetchone()
        if not store:
            raise HTTPException(422, 'กรุณาเลือก Store ที่เปิดใช้งาน')
        store_name = store['name']
    if existing:
        conn.execute('UPDATE pallets SET store_code=%s,store_name=%s WHERE id=%s', (body.store_code,store_name,body.id))
    else:
        number = conn.execute('SELECT COALESCE(MAX(number),0)+1 AS n FROM pallets WHERE trip_id=%s', (trip_id,)).fetchone()['n']
        conn.execute('INSERT INTO pallets(id,trip_id,number,store_code,store_name) VALUES(%s,%s,%s,%s,%s)', (body.id,trip_id,number,body.store_code,store_name))
    conn.execute('DELETE FROM pallet_orders WHERE pallet_id=%s', (body.id,))
    for position, order in enumerate(body.orders):
        conn.execute('INSERT INTO pallet_orders(pallet_id,order_number,position) VALUES(%s,%s,%s)', (body.id,order,position))
    conn.execute('UPDATE trips SET structure_version=2 WHERE id=%s', (trip_id,))
    audit(conn, who, 'pallet.update' if existing else 'pallet.create', body.id)
    return detail(conn, trip_id, who)

@router.post('/trips/{trip_id}/pallets')
def create_trip_pallet(trip_id: UUID, body: TripPalletInput, who=Depends(worker)):
    with connect() as conn:
        return save_trip_pallet(conn, trip_id, body, who)

@router.put('/trips/{trip_id}/pallets/{pallet_id}')
def update_trip_pallet(trip_id: UUID, pallet_id: UUID, body: TripPalletInput, who=Depends(worker)):
    if pallet_id != body.id:
        raise HTTPException(422, 'Pallet ID does not match')
    with connect() as conn:
        return save_trip_pallet(conn, trip_id, body, who, editing=True)

@router.post('/trips/{trip_id}/shipments/{shipment_id}/pallets')
def add_pallet(trip_id: UUID, shipment_id: UUID, body: PalletInput, who=Depends(worker)):
    with connect() as conn:
        trip_access(conn, trip_id, who, True)
        shipment = conn.execute('SELECT * FROM shipments WHERE id=%s AND trip_id=%s', (shipment_id,trip_id)).fetchone()
        if not shipment:
            raise HTTPException(404, 'ไม่พบ Shipment')
        existing = conn.execute('SELECT * FROM pallets WHERE id=%s', (body.id,)).fetchone()
        if existing:
            if existing['shipment_id'] != shipment_id:
                raise HTTPException(409, 'Pallet ID ซ้ำ')
        else:
            number = conn.execute('SELECT COALESCE(MAX(number),0)+1 AS n FROM pallets WHERE shipment_id=%s', (shipment_id,)).fetchone()['n']
            conn.execute('INSERT INTO pallets(id,shipment_id,number,trip_id,store_code,store_name) VALUES (%s,%s,%s,%s,%s,%s)', (body.id,shipment_id,number,trip_id,shipment['store_code'],shipment['store_name']))
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
        if current['structure_version']==2 and (not current['pallets'] or not current['photos']):
            raise HTTPException(409, 'Add at least one Pallet with a Store and upload at least one photo before completing the Trip')
        if current['structure_version']==2 and any(not pallet['orders'] for pallet in current['pallets']):
            raise HTTPException(409, 'กรุณาระบุเลข Order ให้ทุก Pallet ก่อนปิดเที่ยวรถ')
        if current['structure_version']==1 and (len(current['shipments']) != 1 or not current['photos']):
            raise HTTPException(409, 'ต้องมี Shipment เดียวและภาพอย่างน้อย 1 ภาพก่อนปิดเที่ยวรถ')
        ids = [photo['id'] for photo in current['photos']]
        with connect(True) as images:
            count = images.execute('SELECT count(*) AS n FROM photo_blobs WHERE id=ANY(%s)', (ids,)).fetchone()['n']
        if count != len(ids):
            raise HTTPException(409, 'ภาพยังไม่ครบในฐานข้อมูล กรุณาลองส่งใหม่')
        conn.execute("UPDATE trips SET status='DONE',completed_at=now() WHERE id=%s", (trip_id,))
        audit(conn, who, 'trip.complete', trip_id)
        return detail(conn, trip_id, who)

@router.post('/admin/trips/{trip_id}/cancel')
def cancel_trip(trip_id: UUID, who=Depends(admin)):
    with connect() as conn:
        trip = trip_access(conn, trip_id, who)
        trip = conn.execute('SELECT * FROM trips WHERE id=%s FOR UPDATE', (trip_id,)).fetchone()
        if trip['status'] == 'CANCELLED':
            return detail(conn, trip_id, who)
        if trip['status'] != 'OPEN':
            raise HTTPException(409, 'ยกเลิกได้เฉพาะงานค้างเท่านั้น')
        conn.execute("UPDATE trips SET status='CANCELLED',cancelled_at=now(),cancelled_by=%s WHERE id=%s", (who['id'],trip_id))
        audit(conn, who, 'trip.cancel', trip_id)
        return detail(conn, trip_id, who)

@router.get('/admin/trips')
def admin_trips(q: str = '', offset: int = 0, who=Depends(admin)):
    if len(q)>100 or offset<0:
        raise HTTPException(422, 'เงื่อนไขค้นหาไม่ถูกต้อง')
    with connect() as conn:
        return conn.execute('''SELECT t.*,w.name AS worker_name,
          (SELECT count(*) FROM shipments s WHERE s.trip_id=t.id) AS shipment_count,
          (SELECT count(*) FROM photos f WHERE f.trip_id=t.id) AS photo_count, (SELECT count(*) FROM pallets p WHERE p.trip_id=t.id) AS pallet_count
          FROM trips t JOIN workers w ON w.id=t.worker_id
          WHERE t.truck_id ILIKE %s OR t.truck_province ILIKE %s OR EXISTS(SELECT 1 FROM shipments s WHERE s.trip_id=t.id AND (s.number ILIKE %s OR s.store_name ILIKE %s OR s.store_code ILIKE %s))
          OR EXISTS(SELECT 1 FROM pallets p LEFT JOIN pallet_orders o ON o.pallet_id=p.id WHERE p.trip_id=t.id AND (p.store_name ILIKE %s OR p.store_code ILIKE %s OR o.order_number ILIKE %s))
          ORDER BY t.created_at DESC,t.id DESC LIMIT 50 OFFSET %s''', (f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%',offset)).fetchall()

@router.get('/admin/summary')
def summary(who=Depends(admin)):
    with connect() as conn:
        return conn.execute("SELECT count(*) AS trips, count(*) FILTER(WHERE status='OPEN') AS open, count(*) FILTER(WHERE status='DONE') AS done, count(*) FILTER(WHERE status='CANCELLED') AS cancelled, (SELECT count(*) FROM shipments) AS shipments, (SELECT count(*) FROM pallets) AS pallets, (SELECT count(*) FROM photos) AS photos FROM trips").fetchone()


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
def upload_trip_photo(trip_id: UUID, photo_id: UUID, file: UploadFile = File(...), pallet_id: UUID | None = None, who=Depends(worker)):
    content = file.file.read(8 * 1024 * 1024 + 1)
    if len(content)>8 * 1024 * 1024:
        raise HTTPException(413, 'ไฟล์ภาพต้องไม่เกิน 8 MB')
    data, digest = normalize_image(content)
    with connect() as conn:
        trip_access(conn, trip_id, who, True)
        if pallet_id is not None and not conn.execute('SELECT 1 FROM pallets WHERE id=%s AND trip_id=%s', (pallet_id,trip_id)).fetchone():
            raise HTTPException(404, 'Pallet does not belong to this Trip')
        previous = conn.execute('SELECT * FROM photos WHERE id=%s', (photo_id,)).fetchone()
        if previous and (previous['trip_id'] != trip_id or previous['sha256'] != digest or previous['pallet_id'] != pallet_id):
            raise HTTPException(409, 'Photo ID ซ้ำกับภาพอื่น กรุณาโหลดหน้าจอใหม่')
        if not previous and conn.execute('SELECT count(*) AS n FROM photos WHERE trip_id=%s', (trip_id,)).fetchone()['n'] >= 120:
            raise HTTPException(409, 'เที่ยวรถนี้มีภาพครบ 120 ภาพแล้ว')
        with connect(True) as images:
            images.execute('INSERT INTO photo_blobs(id,content,sha256) VALUES (%s,%s,%s) ON CONFLICT(id) DO NOTHING', (photo_id,data,digest))
            blob = images.execute('SELECT sha256 FROM photo_blobs WHERE id=%s', (photo_id,)).fetchone()
            if blob['sha256'] != digest:
                raise HTTPException(409, 'Photo ID มีข้อมูลภาพต่างกัน')
        conn.execute('INSERT INTO photos(id,trip_id,sha256,byte_size,pallet_id) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING', (photo_id,trip_id,digest,len(data),pallet_id))
        stored = conn.execute('SELECT trip_id FROM photos WHERE id=%s', (photo_id,)).fetchone()
        if stored['trip_id'] != trip_id:
            raise HTTPException(409, 'Photo ID ถูกใช้กับเที่ยวรถอื่นแล้ว')
        if not previous:
            audit(conn, who, 'photo.upload', photo_id)
    return {'id':photo_id}

@router.post('/admin/stores/import')
def import_stores(file: UploadFile = File(...), sheet: str = Form(''), who=Depends(admin)):
    try:
        from app.services.store_import import parse_stores
    except ModuleNotFoundError:
        raise HTTPException(503, "Excel support is missing. Rebuild the api image: docker compose up -d --build api")
    if not (file.filename or '').lower().endswith('.xlsx'):
        raise HTTPException(422, 'Please upload an XLSX file')
    data = file.file.read(5_000_001)
    file.file.close()
    if len(data)>5_000_000:
        raise HTTPException(413, 'Maximum file size is 5 MB')
    records = parse_stores(data, sheet.strip())
    with connect() as conn:
        for code,name in records.items():
            conn.execute('INSERT INTO stores(code,name,active) VALUES (%s,%s,true) ON CONFLICT(code) DO UPDATE SET name=excluded.name,active=CASE WHEN stores.deleted_at IS NOT NULL THEN true ELSE stores.active END,deleted_at=NULL', (code,name))
    return {'imported': len(records)}

@router.post('/admin/stores/excel-sheets')
def store_excel_sheets(file: UploadFile = File(...), who=Depends(admin)):
    try:
        from app.services.store_import import workbook_sheets
    except ModuleNotFoundError:
        raise HTTPException(503, 'Excel support is missing. Rebuild the api image: docker compose up -d --build api')
    data = file.file.read(5_000_001)
    file.file.close()
    if len(data)>5_000_000:
        raise HTTPException(413, 'Maximum file size is 5 MB')
    return {'sheets': workbook_sheets(data)}

@router.post('/admin/stores/delete-all')
def delete_all_stores(body: dict, who=Depends(admin)):
    if body.get('confirmation') != 'DELETE ALL STORES':
        raise HTTPException(422, 'Type DELETE ALL STORES to confirm')
    with connect() as conn:
        result = conn.execute('UPDATE stores SET active=false,deleted_at=now() WHERE deleted_at IS NULL')
        count = result.rowcount
    return {'deleted': count}
