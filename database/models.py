CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id  INTEGER UNIQUE NOT NULL,
    name         TEXT,
    language     TEXT DEFAULT 'ru',
    current_level   INTEGER DEFAULT 1,
    current_lesson  INTEGER DEFAULT 1,
    notify_time  TEXT DEFAULT '07:00',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);"""

CREATE_PROGRESS = """
CREATE TABLE IF NOT EXISTS progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(id),
    lesson_id    INTEGER NOT NULL,
    score        INTEGER DEFAULT 0,
    completed    BOOLEAN DEFAULT FALSE,
    completed_at DATETIME,
    lesson_sent  BOOLEAN DEFAULT FALSE
);"""

CREATE_STATISTICS = """
CREATE TABLE IF NOT EXISTS statistics (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER UNIQUE REFERENCES users(id),
    words_learned     INTEGER DEFAULT 0,
    lessons_completed INTEGER DEFAULT 0,
    current_streak    INTEGER DEFAULT 0,
    average_score     REAL DEFAULT 0.0,
    last_activity     DATETIME
);"""

CREATE_REMINDERS = """
CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER UNIQUE REFERENCES users(id),
    hourly_enabled  BOOLEAN DEFAULT TRUE,
    morning_time    TEXT DEFAULT '07:00',
    evening_time    TEXT DEFAULT '20:00'
);"""
