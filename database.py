import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "./weathergpt.db"))

def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()
    return salt, digest

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL,
          salt TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user',
          language TEXT NOT NULL DEFAULT 'en',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          expires_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS alert_subscriptions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER,
          lat REAL NOT NULL,
          lon REAL NOT NULL,
          radius_km REAL NOT NULL DEFAULT 100,
          min_severity TEXT NOT NULL DEFAULT 'moderate',
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS weather_cache(
          cache_key TEXT PRIMARY KEY,
          payload TEXT NOT NULL,
          fetched_at TEXT NOT NULL
        );
        """)
        row = con.execute("SELECT id FROM users WHERE email=?", ("admin@weathergpt.local",)).fetchone()
        if not row:
            salt, digest = hash_password("admin123")
            con.execute(
                "INSERT INTO users(name,email,salt,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                ("WeatherGPT Admin", "admin@weathergpt.local", salt, digest, "admin", datetime.now(timezone.utc).isoformat()),
            )

def create_user(name: str, email: str, password: str):
    salt, digest = hash_password(password)
    try:
        with connect() as con:
            cur = con.execute(
                "INSERT INTO users(name,email,salt,password_hash,created_at) VALUES(?,?,?,?,?)",
                (name, email.lower().strip(), salt, digest, datetime.now(timezone.utc).isoformat()),
            )
            return dict(con.execute("SELECT id,name,email,role,language,created_at FROM users WHERE id=?", (cur.lastrowid,)).fetchone())
    except sqlite3.IntegrityError:
        return None

def authenticate(email: str, password: str):
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
        if not row:
            return None
        _, digest = hash_password(password, row["salt"])
        if not secrets.compare_digest(digest, row["password_hash"]):
            return None
        return dict(row)

def create_session(user_id: int, hours: int = 72):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    with connect() as con:
        con.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)", (token, user_id, expires.isoformat()))
    return token

def get_user_by_token(token: str | None):
    if not token:
        return None
    now = datetime.now(timezone.utc)
    with connect() as con:
        row = con.execute("""
            SELECT u.id,u.name,u.email,u.role,u.language,u.created_at,s.expires_at
            FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?
        """, (token,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < now:
            con.execute("DELETE FROM sessions WHERE token=?", (token,))
            return None
        return dict(row)

def delete_session(token: str):
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE token=?", (token,))

def stats():
    with connect() as con:
        users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        subs = con.execute("SELECT COUNT(*) c FROM alert_subscriptions WHERE active=1").fetchone()["c"]
    return {"users": users, "active_alert_subscriptions": subs}
