# Trip photo upgrade

Current workflow: Trip → Photos (1–120 per Trip), with Shipment/Store records under Trip for destinations.
No new pallet selection or four-side requirement. Existing pallet links remain only for migration/history and pending uploads from older browser tabs.

## Deploy

Back up both PostgreSQL databases before upgrading. Finish pending uploads on older clients when possible.
Run `docker compose up -d --build` (not frontend-only): API includes Tesseract Thai/English and SQL migration 002; archive worker must also be rebuilt.
Migration 002 adds and backfills photos.trip_id; it preserves photo UUIDs, blobs, archive locations and legacy pallet references. It does not delete existing data or relabel old truck types.
Existing Trips exceeding 120 photos are preserved; no additional photos can be added to those trips. Do not use `down -v`.
Refresh every client after deployment. IndexedDB v1 pending records remain supported through the legacy upload endpoint; new records use one immutable UUID per image.

## OCR

Camera/file capture → local compression → authenticated server OCR → review/edit candidate → explicit Use button.
OCR images are not stored in the Trip gallery and do not count toward 120. Recognition requires connectivity. Plate parsing is heuristic and may fail with blur, glare, unusual plates or background text; manual correction remains available.
Tesseract runs inside the API container with Thai + English models, 20-second timeout and two concurrent jobs. No third-party OCR service receives images.
Command reference: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html

## Checks

`docker compose -p loading-tests -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests`
Tests cover 120 cap, retries, one-photo completion, allowed truck types and OCR parsing/mocked process response in addition to existing auth/archive checks.
Real OCR accuracy and TC22 camera behavior still require device tests. Tests have not been run in the editing environment (Python/Docker unavailable).

## Single Shipment per Trip (migration 003)

The creation form now includes Truck ID, Truck Type, Store and Shipment together. POST /api/trips requires shipment_number and store_code and writes Trip + Shipment atomically.
A database trigger and API checks prevent assigning a second Shipment to a Trip. Shipment numbers remain globally unique.
Legacy Trips with zero Shipments can fill in their destination through the compatibility form. Legacy multi-Shipment records are retained, shown read-only as history; open multi-Shipment Trips cannot complete under the new rule and require IT-assisted reconciliation. No historical destinations or photos are deleted by migration 003.
Rebuild all services and refresh browser tabs. Back up databases before deployment. Do not use down -v.
