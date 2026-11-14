# Image database

`001_initial.sql` creates immutable photo_blobs containing JPEG BYTEA and checksum.
Image metadata lives in the business database. A blob commits before its reference; interrupted uploads can leave unreferenced blobs, not ready references without a committed upload.
The archive maintenance job removes unreferenced blobs older than two days after verifying that the business database has no reference.
