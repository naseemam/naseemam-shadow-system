-- Ameer System — Initial Schema
-- Migration: 0001
-- Drops the placeholder tables and creates the full Ameer schema.

DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS memory;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS counters;
DROP TABLE IF EXISTS access_logs;

-- Users
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK(role IN ('admin','assistant','user')),
  display_name  TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Messages (persistent chat history)
CREATE TABLE IF NOT EXISTS messages (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id  INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role             TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
  content          TEXT NOT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Memory (Ameer's layered persistent memory)
CREATE TABLE IF NOT EXISTS memory (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_type   TEXT NOT NULL CHECK(memory_type IN ('temporary','project','founder','core')),
  key           TEXT NOT NULL,
  value         TEXT NOT NULL,
  source        TEXT,
  confidence    REAL DEFAULT 1.0,
  approved      INTEGER NOT NULL DEFAULT 0, -- 0=pending, 1=approved, -1=rejected
  approved_by   INTEGER REFERENCES users(id),
  approved_at   DATETIME,
  superseded_by INTEGER REFERENCES memory(id),
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Audit log (every significant action is recorded)
CREATE TABLE IF NOT EXISTS audit_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER REFERENCES users(id),
  action        TEXT NOT NULL,
  resource_type TEXT,
  resource_id   INTEGER,
  details       TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_user     ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_type   ON memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_key    ON memory(key);
CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit_log(user_id);

