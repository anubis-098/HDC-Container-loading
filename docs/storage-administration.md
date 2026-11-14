# Storage administration — Windows 11 Pro

## Deployment target
Windows 11 Pro with Docker Desktop / WSL 2 and Linux containers.
Development defaults to one SSD. Additional storage is optional.

## Production HDD configuration

Use `compose.storage-hdd.yaml` for the requested server layout:

- `D:\HDC-Data\HDC-Contrainer-Loading-data\postgres-images`: PostgreSQL image database files (photos are stored as BYTEA, not loose JPG files).
- `D:\HDC-Data\HDC-Contrainer-Loading-data\archives`: archived ZIP files and manifests.
- Application images, containers and business database remain in Docker Desktop's disk image. Configure its disk image location on C: (SSD) in Docker Desktop before production installation; the repository path alone does not determine physical storage placement.

Create both directories on the server before starting. Mounts deliberately fail if directories do not exist, so an absent HDD does not silently create a new empty location.

```powershell
New-Item -ItemType Directory -Force -Path 'D:\HDC-Data\HDC-Contrainer-Loading-data\postgres-images', 'D:\HDC-Data\HDC-Contrainer-Loading-data\archives'
docker compose -f compose.yaml -f compose.https.yaml -f compose.storage-hdd.yaml config --quiet
docker compose -f compose.yaml -f compose.https.yaml -f compose.storage-hdd.yaml up -d --build
```

Always use the same three Compose files for subsequent production operations. Verify image database health and upload/download behavior on this Windows Docker installation; PostgreSQL filesystem permissions on host bind mounts must work before accepting live data.

For an existing deployment, do not run the new mount configuration immediately: stop uploads/archive work, dump the image database and copy existing archives, restore into the new image database, verify counts/checksums and reads, then resume. An empty HDD path creates an empty database and does not move the current Docker volume. Retain the old volume and archive source for rollback.

The Archive scheduler remains controlled by `ARCHIVE_ENABLED`; enable only after verifying the HDD mounts and backups. It moves eligible images into ZIP after 30 days by default and retains business metadata.

## Administrator workflow (planned)
Settings → Storage → choose a server-provisioned profile → validate → review migration → schedule → activate.
Profiles describe image database connections and archive destinations, not arbitrary browser-selected folders.
The browser cannot reconfigure Docker mounts. Provision Linux-backed database storage and any additional database service during deployment before enabling its profile.
A missing HDD must not prevent the default development deployment from starting.

## Profiles
- dev-default: current image database on Docker default storage; available in the initial deployment.
- production-hdd: image database on provisioned HDD-backed Linux storage; unavailable until configured and verified.
- Archive destinations are configured separately from image database profiles.
- Keep credentials in server-side secrets. Return only IDs, labels, readiness, capacity and health to the UI.

## Activation and migration
Only authenticated Administrator users may read sensitive storage status or request changes. Enforce roles in the API, not just navigation.
Persist active profile in the business database; environment configuration provides bootstrap defaults and an allowlist.
For existing images: enter maintenance mode and drain uploads, back up, copy, verify counts/checksums and references, atomically switch the active profile, smoke-test reads and uploads, then resume.
Keep the source until verification and rollback retention have passed. Never delete source data merely because a profile was selected.
Store job state and audit events durably. Resume or roll back safely after interruption. Reject concurrent migrations.
Do not expose Docker socket to the web application or accept raw host paths from users.

## Current implementation boundary
Administrator authentication and server-side role checks are implemented. The Settings page reads live photo counts, total online image bytes, archive free space and retention status from /api/admin/storage.
Archive has a scheduler, checksum verification, readback and safe retry. Enable ARCHIVE_ENABLED after provisioning durable storage.
Database storage paths remain deployment configuration. Profile persistence, online migration and live storage switching are still planned, so no misleading drive-selector action is enabled.
