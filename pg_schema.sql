-- Users table
CREATE TABLE IF NOT EXISTS users (
    tg_id        BIGINT PRIMARY KEY,
    tg_username  TEXT    UNIQUE NOT NULL,
    name        TEXT    NOT NULL,
    role        TEXT    NOT NULL
);

-- Tasks table with relative dates
CREATE TABLE IF NOT EXISTS task (
    task_id      SERIAL PRIMARY KEY,
    title        TEXT    NOT NULL UNIQUE,  -- добавьте UNIQUE
    description  TEXT,
    start_day    INTEGER NOT NULL,   -- День мероприятия (1-based)
    start_time   TEXT    NOT NULL,   -- Время в формате HH:MM
    end_day      INTEGER NOT NULL,   -- День мероприятия (1-based)
    end_time     TEXT    NOT NULL,   -- Время в формате HH:MM
    created_at   TIMESTAMP NOT NULL,
    updated_at   TIMESTAMP,
    completed_at TIMESTAMP
);

-- Assignments table with relative dates
CREATE TABLE IF NOT EXISTS assignment (
    assign_id    SERIAL PRIMARY KEY,
    task_id      INTEGER NOT NULL REFERENCES task(task_id),
    tg_id        BIGINT NOT NULL REFERENCES users(tg_id),
    assigned_by  BIGINT NOT NULL REFERENCES users(tg_id),
    assigned_at  TIMESTAMP NOT NULL,
    start_day    INTEGER NOT NULL,
    start_time   TEXT NOT NULL,
    end_day      INTEGER NOT NULL,
    end_time     TEXT NOT NULL,
    status       TEXT NOT NULL,
    notification_scheduled BOOLEAN DEFAULT FALSE,
    UNIQUE (task_id, tg_id)  -- Prevent duplicate assignments for the same task
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      SERIAL PRIMARY KEY,
    table_name  TEXT NOT NULL,
    operation   TEXT NOT NULL,
    record_id   INTEGER,
    timestamp   TIMESTAMP NOT NULL,
    details     TEXT
);

-- Pending Users table
CREATE TABLE IF NOT EXISTS pending_users (
    tg_username  TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    role        TEXT    NOT NULL
);

-- Spot Tasks table
CREATE TABLE IF NOT EXISTS spot_task (
    spot_task_id   SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMP NOT NULL
);

-- Spot Task Responses table
CREATE TABLE IF NOT EXISTS spot_task_response (
    response_id    SERIAL PRIMARY KEY,
    spot_task_id   INTEGER NOT NULL REFERENCES spot_task(spot_task_id) ON DELETE CASCADE,
    volunteer_id   BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    response       VARCHAR(16) NOT NULL CHECK (response IN ('accepted', 'declined', 'none')),
    responded_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    message_id     INTEGER NOT NULL,  -- Optional message ID for response
    UNIQUE (spot_task_id, volunteer_id)  -- Prevent duplicate responses
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);
CREATE INDEX IF NOT EXISTS idx_assignment_status ON assignment(status);
CREATE INDEX IF NOT EXISTS idx_assignment_tg_id ON assignment(tg_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);