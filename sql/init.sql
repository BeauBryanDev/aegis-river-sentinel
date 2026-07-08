--|Database Init tables 

CREATE TABLE IF NOT EXISTS rivers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    length_km   FLOAT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS locations (
    id              SERIAL PRIMARY KEY,
    river_id        INTEGER NOT NULL REFERENCES rivers(id) ON DELETE CASCADE,
    river_segment   VARCHAR(150) NOT NULL,
    region          VARCHAR(100) NOT NULL,
    latitude        FLOAT NOT NULL,
    longitude       FLOAT NOT NULL,
    avg_width_m     FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
    
);


CREATE TABLE IF NOT EXISTS videos (
    id            SERIAL PRIMARY KEY,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    filename      VARCHAR(255) NOT NULL,
    filepath      VARCHAR(512) NOT NULL,
    fps           FLOAT,
    duration_s    FLOAT,
    width         INTEGER,
    height        INTEGER,
    total_frames  INTEGER,
    status        VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_msg     TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    processed_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS analyses (
    id            SERIAL PRIMARY KEY,
    video_id      INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_start   INTEGER NOT NULL,
    frame_end     INTEGER NOT NULL,
    water_ratio   FLOAT NOT NULL,
    vel_mean      FLOAT NOT NULL,
    vel_std       FLOAT NOT NULL,
    vel_max       FLOAT NOT NULL,
    anomaly_score FLOAT NOT NULL DEFAULT 0.0,
    anomaly_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id               SERIAL PRIMARY KEY,
    video_id         INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    analysis_id      INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    frame_num        INTEGER NOT NULL,
    alert_type       VARCHAR(100) NOT NULL,
    severity         VARCHAR(50) NOT NULL,
    description      TEXT,
    acknowledged     BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at  TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_videos_location_id    ON videos(location_id);
CREATE INDEX IF NOT EXISTS idx_videos_status         ON videos(status);
CREATE INDEX IF NOT EXISTS idx_analyses_video_id     ON analyses(video_id);
CREATE INDEX IF NOT EXISTS idx_alerts_video_id       ON alerts(video_id);
CREATE INDEX IF NOT EXISTS idx_alerts_analysis_id    ON alerts(analysis_id);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged   ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_locations_river_id    ON locations(river_id);
