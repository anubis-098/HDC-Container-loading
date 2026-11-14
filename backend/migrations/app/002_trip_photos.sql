ALTER TABLE photos ADD COLUMN trip_id uuid REFERENCES trips(id);
UPDATE photos f SET trip_id=s.trip_id FROM pallets p JOIN shipments s ON s.id=p.shipment_id WHERE f.pallet_id=p.id;
ALTER TABLE photos ALTER COLUMN trip_id SET NOT NULL;
ALTER TABLE photos ALTER COLUMN pallet_id DROP NOT NULL;
ALTER TABLE photos ALTER COLUMN side DROP NOT NULL;
CREATE INDEX photos_trip ON photos(trip_id,uploaded_at,id);
-- Preserve legacy pallet references and IDs for existing images and pending clients.
