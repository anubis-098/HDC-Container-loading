# Photo ZIP folders

Single-Trip downloads contain `Pallet-001/<Order number>/<photo>_DDMMYYYY.jpg`. A Pallet with several Orders has the same original photos in each Order folder. The suffix uses the photo upload date in Asia/Bangkok and the Gregorian year (for example `_18112026.jpg`). Image checksums remain verified before export.

Batch downloads add a separate Trip folder above the Pallet folders to distinguish Pallets with the same number across different Trips. Both download types retain `manifest.json`.

Trip-level photos are kept in `Trip-overview`. Legacy Pallets without Orders use `No-Order`; duplicate legacy Pallet numbers include their identifier to keep them separate. Order names unsafe on Windows are sanitized and suffixed with a short hash; case-insensitive collisions are also disambiguated. Original Order values remain available in the manifest.
