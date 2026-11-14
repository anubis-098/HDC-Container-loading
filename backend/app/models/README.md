# Data model

The executable schema is in backend/migrations/app and backend/migrations/images.
Trip → Shipment → Pallet → Photo; each photo has one of front/back/left/right.
Shipment numbers are globally unique; pallet numbers are unique within a Shipment.
The business database stores references and timestamps; the image database stores binary JPEG data.
A Trip must have at least one Shipment, each Shipment at least one Pallet, and each Pallet four committed images to complete.
Writes lock the Trip row and reject changes after completion. UUID request identifiers allow creation retries.
