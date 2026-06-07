CREATE TABLE IF NOT EXISTS videos (
    id          SERIAL PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL,
    filepath    VARCHAR(512) NOT NULL,
    fps         FLOAT,
    duration_s  FLOAT,
    width       INTEGER,
    height      INTEGER,
    status      VARCHAR(50) DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyses (
    id              SERIAL PRIMARY KEY,
    video_id        INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    frame_start     INTEGER,
    frame_end       INTEGER,
    water_px_ratio  FLOAT,
    mean_velocity   FLOAT,
    max_velocity    FLOAT,
    anomaly_score   FLOAT,
    anomaly_flag    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id          SERIAL PRIMARY KEY,
    video_id    INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    frame_num   INTEGER,
    alert_type  VARCHAR(100),
    severity    VARCHAR(50),
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_video_id ON analyses(video_id);
CREATE INDEX IF NOT EXISTS idx_alerts_video_id   ON alerts(video_id);