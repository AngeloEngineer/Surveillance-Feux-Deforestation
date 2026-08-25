CREATE TABLE IF NOT EXISTS fire_detections (
    id BIGSERIAL PRIMARY KEY,
    geom GEOMETRY(Point, 4326) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    bright_ti4 DOUBLE PRECISION,
    scan DOUBLE PRECISION,
    track DOUBLE PRECISION,
    acq_date DATE NOT NULL,
    acq_time TEXT NOT NULL,
    satellite TEXT,
    instrument TEXT,
    confidence TEXT,
    version TEXT,
    bright_ti5 DOUBLE PRECISION,
    frp DOUBLE PRECISION,
    daynight CHAR(1),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (latitude, longitude, acq_date, acq_time, satellite)
);

CREATE INDEX IF NOT EXISTS idx_fire_detections_geom ON fire_detections USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_fire_detections_acq_date ON fire_detections (acq_date) ;

PGPASSWORD=$(grep POSTGRES_PASSWORD .env | cut -d '=' -f2) docker exec -i surveillance_postgres psql -U surveillance -d surveillance < storage/sql/001_create_fire_detections.sql
PGPASSWORD=$(grep POSTGRES_PASSWORD .env | cut -d '=' -f2) docker exec -i surveillance_postgres psql -U surveillance -d surveillance -c "\d fire_detections"