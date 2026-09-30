-- Optional bootstrap after SQLAlchemy has created the portable tables.
-- Requires a PostgreSQL server with PostGIS installed and extension privileges.
CREATE EXTENSION IF NOT EXISTS postgis;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS location_geom geography(Point,4326)
    GENERATED ALWAYS AS (
        CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography ELSE NULL END
    ) STORED;
CREATE INDEX IF NOT EXISTS incidents_location_gist ON incidents USING GIST(location_geom);
-- This release uses portable Python distance checks; these indices support future SQL spatial querying.
