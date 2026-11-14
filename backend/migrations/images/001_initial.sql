CREATE TABLE photo_blobs (id uuid PRIMARY KEY, content bytea NOT NULL, sha256 char(64) NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
