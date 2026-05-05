"""User model + authentication helpers (Flask-Login + SQLite)."""
import sqlite3
from datetime import datetime
from pathlib import Path

import bcrypt
from flask_login import UserMixin

DB_PATH = Path(__file__).parent / "app.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Idempotent."""
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            school_name   TEXT,
            role          TEXT NOT NULL DEFAULT 'client',
            plan          TEXT NOT NULL DEFAULT 'starter',
            quota_leads   INTEGER NOT NULL DEFAULT 500,
            status        TEXT NOT NULL DEFAULT 'pending',
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS leads_consumption (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            lead_class  TEXT NOT NULL,
            nb_downloaded INTEGER NOT NULL,
            exported_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS access_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            action     TEXT NOT NULL,
            ip         TEXT,
            user_agent TEXT,
            timestamp  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contact_requests (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL,
            school     TEXT,
            message    TEXT,
            status     TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS articles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            slug         TEXT UNIQUE NOT NULL,
            title        TEXT NOT NULL,
            excerpt      TEXT,
            body         TEXT,
            author       TEXT,
            category     TEXT,
            published_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


class User(UserMixin):
    def __init__(self, row: sqlite3.Row):
        self.id = row["id"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.school_name = row["school_name"]
        self.role = row["role"]
        self.plan = row["plan"]
        self.quota_leads = row["quota_leads"]
        self.status = row["status"]
        self.created_at = row["created_at"]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def plan_label(self) -> str:
        return {
            "starter": "Baromètre Starter",
            "growth": "Baromètre Growth",
            "premium": "Baromètre Premium",
            "leads_only": "Leads CPL",
            "premium_leads": "Premium + Leads",
            "admin": "Administrateur",
        }.get(self.plan, self.plan)

    @classmethod
    def get(cls, user_id):
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return cls(row) if row else None

    @classmethod
    def by_email(cls, email):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return cls(row) if row else None

    @classmethod
    def create(cls, email, password, school_name, role="client", plan="starter",
               quota_leads=500, status="pending"):
        conn = get_db()
        try:
            cur = conn.execute(
                """
                INSERT INTO users (email, password_hash, school_name, role, plan,
                                   quota_leads, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email.lower().strip(),
                    hash_password(password),
                    school_name,
                    role,
                    plan,
                    quota_leads,
                    status,
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
            return cls.get(cur.lastrowid)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def update_password(self, new_password: str):
        conn = get_db()
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), self.id),
        )
        conn.commit()
        conn.close()
        self.password_hash = hash_password(new_password)

    def update_profile(self, school_name: str):
        conn = get_db()
        conn.execute(
            "UPDATE users SET school_name = ? WHERE id = ?", (school_name, self.id)
        )
        conn.commit()
        conn.close()
        self.school_name = school_name


def log_access(user_id, action, ip=None, user_agent=None):
    conn = get_db()
    conn.execute(
        """INSERT INTO access_log (user_id, action, ip, user_agent, timestamp)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, action, ip, user_agent, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def recent_access_logs(user_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM access_log WHERE user_id = ?
           ORDER BY timestamp DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_export(user_id, lead_class_counts: dict):
    """lead_class_counts: {'A': 12, 'B': 5, 'C': 0}"""
    conn = get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    for cls, n in lead_class_counts.items():
        if n > 0:
            conn.execute(
                """INSERT INTO leads_consumption (user_id, lead_class, nb_downloaded, exported_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, cls, n, now),
            )
    conn.commit()
    conn.close()


def consumption_summary(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT lead_class, SUM(nb_downloaded) AS total
           FROM leads_consumption WHERE user_id = ? GROUP BY lead_class""",
        (user_id,),
    ).fetchall()
    conn.close()
    return {r["lead_class"]: r["total"] for r in rows}


def consumption_history(user_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        """SELECT lead_class, nb_downloaded, exported_at
           FROM leads_consumption WHERE user_id = ?
           ORDER BY exported_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_contact(name, email, school, message):
    conn = get_db()
    conn.execute(
        """INSERT INTO contact_requests (name, email, school, message, status, created_at)
           VALUES (?, ?, ?, ?, 'new', ?)""",
        (name, email, school, message, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
