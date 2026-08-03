/**
 * Database helpers for the Ameer system using Cloudflare D1.
 *
 * Use `getDB()` in API routes and server actions.
 * Use `getAI()` in server-side chat logic.
 *
 * Run with `pnpm preview` (wrangler dev) to have the CF bindings available.
 */

import { getCloudflareContext } from '@opennextjs/cloudflare';
import { hashPassword } from './auth';

/** Returns the D1 database binding from the Cloudflare context. */
export async function getDB(): Promise<D1Database> {
  const { env } = await getCloudflareContext();
  return env.DB;
}

/** Returns the Workers AI binding from the Cloudflare context. */
export async function getAI(): Promise<Ai> {
  const { env } = await getCloudflareContext();
  return (env as CloudflareEnv).AI;
}

/**
 * Creates all tables and seeds default users.
 * Safe to call multiple times (uses IF NOT EXISTS / INSERT OR IGNORE).
 */
export async function initializeDatabase(): Promise<{ success: boolean; message: string; error?: unknown }> {
  try {
    const db = await getDB();

    // --- Schema ---
    await db.batch([
      db.prepare(`
        CREATE TABLE IF NOT EXISTS users (
          id         INTEGER PRIMARY KEY AUTOINCREMENT,
          username   TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          role       TEXT NOT NULL CHECK(role IN ('admin','assistant','user')),
          display_name TEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `),
      db.prepare(`
        CREATE TABLE IF NOT EXISTS conversations (
          id         INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title      TEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `),
      db.prepare(`
        CREATE TABLE IF NOT EXISTS messages (
          id               INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id  INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
          role             TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
          content          TEXT NOT NULL,
          created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `),
      db.prepare(`
        CREATE TABLE IF NOT EXISTS memory (
          id            INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_type   TEXT NOT NULL CHECK(memory_type IN ('temporary','project','founder','core')),
          key           TEXT NOT NULL,
          value         TEXT NOT NULL,
          source        TEXT,
          confidence    REAL DEFAULT 1.0,
          approved      INTEGER NOT NULL DEFAULT 0,
          approved_by   INTEGER REFERENCES users(id),
          approved_at   DATETIME,
          superseded_by INTEGER REFERENCES memory(id),
          created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `),
      db.prepare(`
        CREATE TABLE IF NOT EXISTS audit_log (
          id            INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id       INTEGER REFERENCES users(id),
          action        TEXT NOT NULL,
          resource_type TEXT,
          resource_id   INTEGER,
          details       TEXT,
          created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `),
      db.prepare(`CREATE INDEX IF NOT EXISTS idx_messages_conv  ON messages(conversation_id)`),
      db.prepare(`CREATE INDEX IF NOT EXISTS idx_conv_user      ON conversations(user_id)`),
      db.prepare(`CREATE INDEX IF NOT EXISTS idx_memory_type    ON memory(memory_type)`),
      db.prepare(`CREATE INDEX IF NOT EXISTS idx_memory_key     ON memory(key)`),
    ]);

    // --- Seed default users (skip if already present) ---
    const existing = await db.prepare('SELECT id FROM users WHERE username IN (?,?)').bind('naseem','amir').all<{ id: number }>();
    if (existing.results.length === 0) {
      const [naseemHash, amirHash] = await Promise.all([
        hashPassword('admin123'),
        hashPassword('assistant123'),
      ]);
      await db.batch([
        db.prepare('INSERT OR IGNORE INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)').bind('naseem', naseemHash, 'admin', 'نسيم'),
        db.prepare('INSERT OR IGNORE INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)').bind('amir',   amirHash,  'assistant', 'أمير'),
      ]);
    }

    return { success: true, message: 'تم تهيئة قاعدة البيانات بنجاح' };
  } catch (error) {
    console.error('خطأ في تهيئة قاعدة البيانات:', error);
    return { success: false, message: 'حدث خطأ أثناء تهيئة قاعدة البيانات', error };
  }
}
