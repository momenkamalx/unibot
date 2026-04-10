import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "university_bot.db")

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                file_type TEXT,
                title TEXT,
                telegram_file_id TEXT,
                content_type TEXT,
                uploader_id INTEGER,
                uploader_name TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );
            CREATE TABLE IF NOT EXISTS pending (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                file_type TEXT,
                title TEXT,
                telegram_file_id TEXT,
                content_type TEXT,
                uploader_id INTEGER,
                uploader_name TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def add_user(self, user_id, name, username):
        self.conn.execute(
            "INSERT OR IGNORE INTO users (id, name, username) VALUES (?, ?, ?)",
            (user_id, name, username)
        )
        self.conn.commit()

    def add_subject(self, name):
        self.conn.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
        self.conn.commit()

    def get_subjects(self):
        return self.conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()

    def get_subject(self, subject_id):
        return self.conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()

    def get_files(self, subject_id, file_type):
        return self.conn.execute(
            "SELECT * FROM files WHERE subject_id = ? AND file_type = ? ORDER BY uploaded_at DESC",
            (subject_id, file_type)
        ).fetchall()

    def get_file_by_id(self, file_id):
        return self.conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()

    def add_pending(self, subject_id, file_type, title, telegram_file_id, content_type, uploader_id, uploader_name):
        cur = self.conn.execute(
            "INSERT INTO pending (subject_id, file_type, title, telegram_file_id, content_type, uploader_id, uploader_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (subject_id, file_type, title, telegram_file_id, content_type, uploader_id, uploader_name)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_pending(self):
        return self.conn.execute("SELECT * FROM pending WHERE status = 'pending'").fetchall()

    def count_pending(self):
        return self.conn.execute("SELECT COUNT(*) FROM pending WHERE status = 'pending'").fetchone()[0]

    def approve_pending(self, pending_id):
        p = self.conn.execute("SELECT * FROM pending WHERE id = ?", (pending_id,)).fetchone()
        if p:
            self.conn.execute(
                "INSERT INTO files (subject_id, file_type, title, telegram_file_id, content_type, uploader_id, uploader_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["subject_id"], p["file_type"], p["title"], p["telegram_file_id"], p["content_type"], p["uploader_id"], p["uploader_name"])
            )
            self.conn.execute("UPDATE pending SET status = 'approved' WHERE id = ?", (pending_id,))
            self.conn.commit()

    def reject_pending(self, pending_id):
        self.conn.execute("UPDATE pending SET status = 'rejected' WHERE id = ?", (pending_id,))
        self.conn.commit()

    def count_users(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def count_files(self):
        return self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    def search_files(self, keyword):
        return self.conn.execute(
            "SELECT * FROM files WHERE title LIKE ? ORDER BY uploaded_at DESC LIMIT 20",
            (f"%{keyword}%",)
        ).fetchall()

    def delete_subject(self, subject_id):
        self.conn.execute("DELETE FROM files WHERE subject_id = ?", (subject_id,))
        self.conn.execute("DELETE FROM subjects
