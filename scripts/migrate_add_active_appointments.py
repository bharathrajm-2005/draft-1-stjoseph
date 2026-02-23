"""
Migration: Add active_appointments column to users table.
SQLite does not support automatic column additions via SQLAlchemy create_all,
so this script does it explicitly for all known databases.
"""
import sqlite3
import os

DB_PATHS = [
    "database.db",
    "database/patient_experience.db",
    "hospital.db",
]

for db_path in DB_PATHS:
    if not os.path.exists(db_path):
        print(f"[SKIP] {db_path} not found")
        continue

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if users table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        print(f"[SKIP] {db_path} has no 'users' table")
        conn.close()
        continue

    cols = [row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()]
    print(f"[INFO] {db_path} — current users columns: {cols}")

    if "active_appointments" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN active_appointments INTEGER DEFAULT 0")
        conn.commit()
        print(f"[OK]   {db_path} — 'active_appointments' column ADDED")
    else:
        print(f"[OK]   {db_path} — column already exists, no change needed")

    conn.close()

print("\nMigration complete. Restart the server.")
