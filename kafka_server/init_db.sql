-- init_db.sql

CREATE TABLE IF NOT EXISTS health_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    details TEXT,
    location VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
