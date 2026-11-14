import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
from app.core.config import settings
from app.db.connection import connect

def run():
    root = Path(settings().archive_directory)
    root.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        if not conn.execute('SELECT pg_try_advisory_xact_lock(913021) AS locked').fetchone()['locked']:
            raise SystemExit('Another archive job is running')
        rows = conn.execute("""SELECT f.* FROM photos f JOIN trips t ON t.id=f.trip_id WHERE t.status='DONE' AND f.archived_at IS NULL AND f.uploaded_at < now() - (%s * interval '1 day') ORDER BY f.uploaded_at LIMIT 100""", (settings().photo_retention_days,)).fetchall()
        if rows:
            name = f'{uuid4()}.zip'
            temp = root / (name + '.partial')
            final = root / name
            manifest = []
            with ZipFile(temp, 'w', ZIP_DEFLATED) as archive:
                with connect(True) as images:
                    for row in rows:
                        blob = images.execute('SELECT content FROM photo_blobs WHERE id=%s', (row['id'],)).fetchone()
                        if not blob or hashlib.sha256(bytes(blob['content'])).hexdigest() != row['sha256']:
                            raise RuntimeError('Missing or corrupt source image; no data deleted')
                        archive.writestr(f"{row['id']}.jpg", bytes(blob['content']))
                        manifest.append({'id':str(row['id']), 'sha256':row['sha256']})
                archive.writestr('manifest.json', json.dumps(manifest))
            with open(temp, 'rb') as stream:
                os.fsync(stream.fileno())
            with ZipFile(temp) as archive:
                for item in manifest:
                    if hashlib.sha256(archive.read(item['id']+'.jpg')).hexdigest() != item['sha256']:
                        raise RuntimeError('Archive verification failed; no data deleted')
            os.replace(temp, final)
            for row in rows:
                conn.execute('UPDATE photos SET archived_at=now(),archive_file=%s WHERE id=%s', (name,row['id']))
    # Re-read and verify durable archive before deleting each archived blob. Retriable after interruption.
    with connect() as conn, connect(True) as images:
        archived = conn.execute('SELECT id,sha256,archive_file FROM photos WHERE archived_at IS NOT NULL').fetchall()
        for row in archived:
            if not images.execute('SELECT 1 FROM photo_blobs WHERE id=%s', (row['id'],)).fetchone():
                continue
            with ZipFile(root / row['archive_file']) as archive:
                if hashlib.sha256(archive.read(f"{row['id']}.jpg")).hexdigest() != row['sha256']:
                    raise RuntimeError('Archived image verification failed; deletion stopped')
            images.execute('DELETE FROM photo_blobs WHERE id=%s', (row['id'],))
        # Old unreferenced blobs come from replaced photos or interrupted cross-database writes.
        orphan_candidates = images.execute("SELECT id FROM photo_blobs WHERE created_at < now() - interval '2 days' LIMIT 1000").fetchall()
        for row in orphan_candidates:
            if not conn.execute('SELECT 1 FROM photos WHERE id=%s', (row['id'],)).fetchone():
                images.execute('DELETE FROM photo_blobs WHERE id=%s', (row['id'],))
    print(f'Archived {len(rows)} images', flush=True)
    return len(rows)

if __name__ == '__main__':
    run()

