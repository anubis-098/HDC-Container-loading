# Archive worker

Set ARCHIVE_ENABLED=true after preparing durable archive storage.
The scheduler checks every 24 hours. It archives photos older than PHOTO_RETENTION_DAYS from completed trips only, in batches of 100.
Each ZIP contains images and a manifest. Readback and SHA-256 verification precede metadata update and source deletion.
Incomplete jobs retry safely: a source is deleted only if a verified archive already exists and metadata is committed.
Open trips are retained. Business records and audit events are not purged. Archive retention itself is not automated.
Administrator can open an archived photo via /api/admin/archived-photos/{photo_id}.
