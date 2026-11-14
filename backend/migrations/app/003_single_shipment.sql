CREATE FUNCTION enforce_one_shipment_per_trip() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM id FROM trips WHERE id=NEW.trip_id FOR UPDATE;
  IF EXISTS(SELECT 1 FROM shipments WHERE trip_id=NEW.trip_id AND id<>NEW.id) THEN
    RAISE EXCEPTION 'A trip can have only one shipment' USING ERRCODE='23505';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER one_shipment_per_trip BEFORE INSERT OR UPDATE OF trip_id ON shipments
FOR EACH ROW EXECUTE FUNCTION enforce_one_shipment_per_trip();
-- Existing multi-shipment history is preserved; new assignments are constrained.
