import hashlib
import json
from pathlib import Path
from tempfile import TemporaryFile
from uuid import UUID
from zipfile import ZipFile, ZIP_STORED, BadZipFile
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from app.core.config import settings
from app.core.security import admin, trip_access
from app.db.connection import connect

router = APIRouter(prefix='/admin/trips', tags=['downloads'])

def pallet_manifest(conn, trip, photos):
    pallets = conn.execute('SELECT id,number,store_code,store_name FROM pallets WHERE trip_id=%s ORDER BY number,id', (trip['id'],)).fetchall()
    orders = conn.execute('SELECT o.* FROM pallet_orders o JOIN pallets p ON p.id=o.pallet_id WHERE p.trip_id=%s ORDER BY o.position', (trip['id'],)).fetchall()
    return {'trip_id':str(trip['id']), 'truck_id':trip['truck_id'], 'pallets':[
        {**p,'id':str(p['id']),'orders':[o['order_number'] for o in orders if o['pallet_id']==p['id']]} for p in pallets],
        'photos':[{'id':str(p['id']),'pallet_id':str(p['pallet_id']) if p['pallet_id'] else None} for p in photos]}

def scoped_photo_path(manifest, row, index):
    pallet = next((p for p in manifest['pallets'] if p['id']==str(row['pallet_id'])), None)
    folder = f"Pallet-{pallet['number']:03d}-{pallet['id'][:8]}" if pallet else 'Trip-overview'
    return f"{folder}/{index:03d}-{row['id']}.jpg"

@router.post('/photos.zip')
def download_selected_photos(ids: list[UUID], who=Depends(admin)):
    import re
    from zoneinfo import ZoneInfo
    if not ids or len(ids) > 50:
        raise HTTPException(422, 'Select 1-50 trips')
    def safe(value):
        return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '-', str(value)).strip(' .')[:100] or 'unknown'
    output = TemporaryFile()
    try:
        with connect() as conn, ZipFile(output, 'w', ZIP_STORED) as archive:
            count = 0
            for trip_id in sorted(set(ids)):
                trip = trip_access(conn, trip_id, who)
                conn.execute('SELECT id FROM trips WHERE id=%s FOR SHARE', (trip_id,))
                shipments = conn.execute('SELECT number FROM shipments WHERE trip_id=%s ORDER BY number', (trip_id,)).fetchall()
                rows = conn.execute('SELECT * FROM photos WHERE trip_id=%s ORDER BY uploaded_at,id FOR SHARE', (trip_id,)).fetchall()
                if trip['structure_version']==2:
                    manifest = pallet_manifest(conn, trip, rows)
                    base = f"Trip-{safe(trip['truck_id'])}-{trip_id}"
                    archive.writestr(base+'/manifest.json',json.dumps(manifest,ensure_ascii=False))
                    for index,row in enumerate(rows,1):
                        archive.writestr(base+'/'+scoped_photo_path(manifest,row,index), image_bytes(row))
                        count += 1
                    continue
                for row in rows:
                    numbers = []
                    if row.get('pallet_id'):
                        shipment = conn.execute('SELECT s.number FROM shipments s JOIN pallets p ON p.shipment_id=s.id WHERE p.id=%s', (row['pallet_id'],)).fetchone()
                        if shipment: numbers = [shipment['number']]
                    if not numbers: numbers = [s['number'] for s in shipments] or ['NO-SHIPMENT']
                    day = row['uploaded_at'].astimezone(ZoneInfo('Asia/Bangkok')).strftime('%Y%m%d')
                    # Trip-level images belong to every Shipment on the trip.
                    content = image_bytes(row)
                    for number in numbers:
                        base = f"{safe(number)}_{safe(trip['truck_id'])}_{day}"
                        archive.writestr(f"{base}/{base}_{row['id']}.jpg", content)
                        count += 1
            if not count: raise HTTPException(404, 'No photos in selected trips')
        size = output.tell()
        output.seek(0)
    except BaseException:
        output.close()
        raise
    def chunks():
        try:
            while chunk := output.read(64*1024): yield chunk
        finally: output.close()
    return StreamingResponse(chunks(), media_type='application/zip', headers={'Content-Disposition':'attachment; filename="container-loading-photos.zip"','Content-Length':str(size),'Cache-Control':'no-store'}, background=BackgroundTask(output.close))

def image_bytes(row):
    if row['archived_at']:
        try:
            with ZipFile(Path(settings().archive_directory) / Path(row['archive_file']).name) as archive:
                data = archive.read(f"{row['id']}.jpg")
        except (OSError, KeyError, BadZipFile):
            raise HTTPException(503, 'อ่านภาพจาก Archive ไม่สำเร็จ กรุณาติดต่อ IT')
    else:
        with connect(True) as images:
            blob = images.execute('SELECT content FROM photo_blobs WHERE id=%s', (row['id'],)).fetchone()
            if not blob:
                raise HTTPException(503, 'ข้อมูลภาพไม่ครบ กรุณาติดต่อ IT')
            data = bytes(blob['content'])
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise HTTPException(503, 'ภาพไม่ผ่านการตรวจสอบความสมบูรณ์ กรุณาติดต่อ IT')
    return data

@router.get('/{trip_id}/photos/{photo_id}/download')
def download_photo(trip_id: UUID, photo_id: UUID, who=Depends(admin)):
    with connect() as conn:
        trip_access(conn, trip_id, who)
        row=conn.execute('SELECT * FROM photos WHERE id=%s AND trip_id=%s FOR SHARE', (photo_id,trip_id)).fetchone()
        if not row:
            raise HTTPException(404, 'ไม่พบภาพในเที่ยวรถนี้')
        data=image_bytes(row)
    return Response(data, media_type='image/jpeg', headers={'Content-Disposition':f'attachment; filename="trip-{trip_id}-{photo_id}.jpg"','Cache-Control':'no-store'})

@router.get('/{trip_id}/photos.zip')
def download_trip(trip_id: UUID, who=Depends(admin)):
    output=TemporaryFile()
    try:
        with connect() as conn:
            trip_access(conn, trip_id, who)
            conn.execute('SELECT id FROM trips WHERE id=%s FOR SHARE', (trip_id,))
            rows=conn.execute('SELECT * FROM photos WHERE trip_id=%s ORDER BY uploaded_at,id FOR SHARE', (trip_id,)).fetchall()
            if not rows:
                raise HTTPException(404, 'เที่ยวรถนี้ยังไม่มีภาพ')
            # Verify all images before sending any ZIP bytes. Never silently omit failures.
            with ZipFile(output, 'w', ZIP_STORED) as archive:
                manifest = pallet_manifest(conn, trip_access(conn, trip_id, who), rows) if trip_access(conn, trip_id, who)['structure_version']==2 else None
                if manifest:
                    archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
                for index,row in enumerate(rows,1):
                    archive.writestr(scoped_photo_path(manifest,row,index) if manifest else f"{index:03d}-{row['id']}.jpg", image_bytes(row))
        size=output.tell()
        output.seek(0)
    except BaseException:
        output.close()
        raise
    def chunks():
        try:
            while chunk:=output.read(64*1024):
                yield chunk
        finally:
            output.close()
    return StreamingResponse(chunks(), media_type='application/zip', headers={'Content-Disposition':f'attachment; filename="trip-{trip_id}.zip"','Content-Length':str(size),'Cache-Control':'no-store'}, background=BackgroundTask(output.close))

@router.get('/{trip_id}/report.pdf')
def download_pdf(trip_id: UUID, who=Depends(admin)):
    from app.services.trip_pdf import render_trip_pdf
    output=TemporaryFile()
    try:
        with connect() as conn:
            trip=trip_access(conn,trip_id,who)
            conn.execute('SELECT id FROM trips WHERE id=%s FOR SHARE',(trip_id,))
            trip['worker_name']=conn.execute('SELECT name FROM workers WHERE id=%s',(trip['worker_id'],)).fetchone()['name']
            trip['shipments']=conn.execute('SELECT * FROM shipments WHERE trip_id=%s ORDER BY number',(trip_id,)).fetchall()
            trip['pallets']=conn.execute('SELECT * FROM pallets WHERE trip_id=%s ORDER BY number,id',(trip_id,)).fetchall()
            for pallet in trip['pallets']:
                pallet['orders']=[row['order_number'] for row in conn.execute('SELECT order_number FROM pallet_orders WHERE pallet_id=%s ORDER BY position',(pallet['id'],)).fetchall()]
            rows=conn.execute('SELECT * FROM photos WHERE trip_id=%s ORDER BY uploaded_at,id FOR SHARE',(trip_id,)).fetchall()
            if not rows:
                raise HTTPException(404,'เที่ยวรถนี้ยังไม่มีภาพ')
            render_trip_pdf(output,trip,rows,image_bytes)
        size=output.tell();output.seek(0)
    except BaseException:
        output.close()
        raise
    def chunks():
        try:
            while chunk:=output.read(64*1024):
                yield chunk
        finally:
            output.close()
    return StreamingResponse(chunks(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="trip-{trip_id}.pdf"','Content-Length':str(size),'Cache-Control':'no-store'},background=BackgroundTask(output.close))

@router.delete('/{trip_id}')
def delete_trip(trip_id: UUID, who=Depends(admin)):
    with connect() as conn:
        trip_access(conn, trip_id, who)
        conn.execute('SELECT id FROM trips WHERE id=%s FOR UPDATE', (trip_id,))
        conn.execute('DELETE FROM photos WHERE trip_id=%s OR pallet_id IN (SELECT p.id FROM pallets p JOIN shipments s ON s.id=p.shipment_id WHERE s.trip_id=%s)', (trip_id,trip_id))
        conn.execute('DELETE FROM pallets WHERE trip_id=%s', (trip_id,))
        conn.execute('DELETE FROM shipments WHERE trip_id=%s', (trip_id,))
        conn.execute('DELETE FROM trips WHERE id=%s', (trip_id,))
        conn.execute("INSERT INTO audit_log(actor_id,event,target_id) VALUES (%s,'DELETE_TRIP',%s)", (who['id'],trip_id))
    return {'ok': True}
