CREATE TABLE IF NOT EXISTS dietary_recalls (
    participant_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    timepoint INTEGER NOT NULL,
    recall_number INTEGER NOT NULL DEFAULT 1,
    attempt_number INTEGER NOT NULL,
    completed_at TIMESTAMPTZ,
    recall_json TEXT,
    nutrient_totals TEXT,
    PRIMARY KEY (
        participant_id,
        study_id,
        timepoint,
        recall_number,
        attempt_number
    ),
    CHECK (attempt_number >= 1),
    CHECK (recall_number >= 1)
);
