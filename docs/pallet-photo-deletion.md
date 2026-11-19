# Pallet photo deletion

The loading page shows a red **ลบรูป** button below each uploaded Pallet photo while the Trip is OPEN. Deletion requires confirmation and an online connection. Offline photo capture continues to work.

Only the owning worker can delete a photo through `DELETE /api/trips/{trip_id}/pallets/{pallet_id}/photos/{photo_id}`. The server locks the Trip, checks the Pallet/photo relationship, removes the photo record, records `photo.delete` in the audit log and returns updated Trip counts. DONE and CANCELLED Trips remain read-only. If all photos are removed, completion is blocked until another photo is uploaded.

Migration 009 records deleted image identifiers so stale uploads cannot resurrect them. Such retries return HTTP 410; the loading page discards those stale queue entries. Repeating a successful DELETE is safe. The business deletion commits before image blob cleanup so a business transaction failure cannot destroy a referenced image. Image cleanup can be retried with the same DELETE if the image database was temporarily unavailable.

Rebuild the API with the existing Data Center Compose overlay so migration 009 runs before serving requests; rebuild the frontend to show the buttons. Keep the existing database volumes.
