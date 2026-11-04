CREATE TABLE setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE category (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    color       TEXT NOT NULL,
    is_system   INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1))
);

INSERT INTO category (id, name, color, is_system) VALUES (1, 'None', '#9e9e9e', 1);

CREATE TABLE scenario (
    id                  INTEGER PRIMARY KEY,
    name                TEXT NOT NULL UNIQUE COLLATE NOCASE,
    repeat_count        INTEGER NOT NULL CHECK (repeat_count >= 1),
    work_minutes        INTEGER,
    short_break_minutes INTEGER,
    long_break_minutes  INTEGER,
    long_break_every    INTEGER
);

CREATE TABLE scenario_row (
    id          INTEGER PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES scenario (id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    category_id INTEGER NOT NULL REFERENCES category (id),
    count       INTEGER NOT NULL CHECK (count >= 1),
    UNIQUE (scenario_id, position)
);

CREATE TABLE session (
    id                INTEGER PRIMARY KEY,
    kind              TEXT NOT NULL CHECK (kind IN ('flow', 'scenario')),
    status            TEXT NOT NULL
                      CHECK (status IN ('running', 'completed', 'stopped', 'interrupted')),
    started_at        TEXT NOT NULL,
    ended_at          TEXT,
    scenario_name     TEXT,
    scenario_snapshot TEXT,
    CHECK (
        (kind = 'flow' AND scenario_name IS NULL AND scenario_snapshot IS NULL)
        OR (kind = 'scenario' AND scenario_name IS NOT NULL AND scenario_snapshot IS NOT NULL)
    )
);

CREATE TABLE interval (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES session (id),
    position        INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('work', 'short_break', 'long_break')),
    category_id     INTEGER REFERENCES category (id),
    planned_seconds INTEGER NOT NULL,
    actual_seconds  INTEGER,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT CHECK (status IN ('completed', 'skipped', 'stopped', 'interrupted')),
    UNIQUE (session_id, position),
    CHECK ((kind = 'work') = (category_id IS NOT NULL))
);

CREATE VIEW interval_details AS
SELECT i.*,
       c.name          AS category_name,
       c.color         AS category_color,
       s.kind          AS session_kind,
       s.scenario_name AS scenario_name
FROM interval i
JOIN session s ON s.id = i.session_id
LEFT JOIN category c ON c.id = i.category_id;
