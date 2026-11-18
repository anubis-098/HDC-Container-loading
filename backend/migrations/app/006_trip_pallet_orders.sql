ALTER TABLE trips ADD COLUMN structure_version integer NOT NULL DEFAULT 1 CHECK(structure_version IN (1,2));
ALTER TABLE pallets ADD COLUMN trip_id uuid REFERENCES trips(id);
ALTER TABLE pallets ADD COLUMN store_code varchar(40) REFERENCES stores(code);
ALTER TABLE pallets ADD COLUMN store_name varchar(160);
UPDATE pallets p SET trip_id=s.trip_id,store_code=s.store_code,store_name=s.store_name FROM shipments s WHERE s.id=p.shipment_id;
ALTER TABLE pallets ALTER COLUMN trip_id SET NOT NULL;
ALTER TABLE pallets ALTER COLUMN store_code SET NOT NULL;
ALTER TABLE pallets ALTER COLUMN store_name SET NOT NULL;
ALTER TABLE pallets ALTER COLUMN shipment_id DROP NOT NULL;
CREATE INDEX pallets_trip ON pallets(trip_id,number,id);
CREATE UNIQUE INDEX pallets_new_trip_number ON pallets(trip_id,number) WHERE shipment_id IS NULL;
CREATE TABLE pallet_orders (
 pallet_id uuid NOT NULL REFERENCES pallets(id) ON DELETE CASCADE,
 order_number varchar(80) NOT NULL CHECK(length(btrim(order_number))>0),
 position integer NOT NULL CHECK(position>=0),
 PRIMARY KEY(pallet_id,order_number)
);
CREATE INDEX pallet_orders_number ON pallet_orders(order_number);
