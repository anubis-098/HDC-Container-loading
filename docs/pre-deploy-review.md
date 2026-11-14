# Pre-deployment review

## Changes from the review

- Client blocks data entry when initial server data fails to load, with a retry action.
- Trip operations have an immediate lock against duplicate clicks; photo queues update after each saved image when selecting multiple files.
- Client describes required fields, optional province, automatic photo upload and completion requirements.
- Editing a disabled Store preserves its status; the Store code cannot be changed while editing. Cancel restores the create form.
- Admin authentication distinguishes an unavailable server from an expired session.
- Settings stops showing a perpetual loading message after an error.
- Province options support touch scrolling; gallery text remains readable on its light background.
- Dashboard searches province and Store code, with stable ordering for equal timestamps.

## Validation status

Frontend formatting and CSS parsing were checked; nginx encoding is UTF-8 without BOM.
The partial TypeScript check reports missing installed packages. It is not a successful build.
Docker, Python and Tesseract are unavailable in the review environment, so backend integration tests,
PDF rendering, database migrations and device/camera behavior must still be verified on the deployment machine.

## Acceptance sequence before release

1. Build all services; run the isolated integration suite using `docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests`.
2. Create Admin, add Store, edit a disabled Store and verify it remains disabled.
3. On TC22 over trusted HTTPS: enter worker name, create Trip, optional province, required truck/Shipment, scanner Tab and Enter, camera permission and OCR.
4. Upload multiple images; interrupt connectivity, retry and verify image counts. Do not clear site data with pending photos. Reloading while offline is not supported as a complete offline application.
5. Verify 0 images cannot complete, 1 image can complete, maximum 120 and rejection above 120; completion waits for the queue to drain.
6. Verify another worker cannot access the Trip; worker cannot access Admin downloads.
7. Verify single image, ZIP and landscape PDF, including archived images and Thai metadata.
8. Back up both databases and Archive; test restore before enabling scheduled archive. Confirm mounts and free space on HDD.

Storage switching through the Admin UI remains unimplemented. Settings reports this limitation explicitly.
