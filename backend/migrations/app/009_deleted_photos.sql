CREATE TABLE deleted_photos (
    id uuid PRIMARY KEY,
    trip_id uuid NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    pallet_id uuid NOT NULL REFERENCES pallets(id) ON DELETE CASCADE,
    deleted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX deleted_photos_trip ON deleted_photos(trip_id);
CREATE INDEX deleted_photos_pallet ON deleted_photos(pallet_id);
