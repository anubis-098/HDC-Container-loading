ALTER TABLE trips DROP CONSTRAINT trips_status_check;
ALTER TABLE trips ADD CONSTRAINT trips_status_check CHECK (status IN ('OPEN','DONE','CANCELLED'));
ALTER TABLE trips ADD COLUMN cancelled_at timestamptz;
ALTER TABLE trips ADD COLUMN cancelled_by uuid REFERENCES admins(id);
