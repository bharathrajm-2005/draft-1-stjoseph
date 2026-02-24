"""
Phase 2 AI Intelligence Layer — Database Migration Script
Run once: python scripts/migrate_phase2_ai.py
"""
import sqlite3, os, sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'patient_experience.db')

ALTERATIONS = [
    # User — Phase 2 AI
    "ALTER TABLE users ADD COLUMN doctor_performance_score REAL DEFAULT 0.0",
    "ALTER TABLE users ADD COLUMN driver_efficiency_score REAL DEFAULT 0.0",
    "ALTER TABLE users ADD COLUMN complaint_count INTEGER DEFAULT 0",
    # EmergencyRequest — ETA + timing
    "ALTER TABLE emergency_requests ADD COLUMN eta_minutes REAL",
    "ALTER TABLE emergency_requests ADD COLUMN driver_response_time REAL",
    "ALTER TABLE emergency_requests ADD COLUMN completed_duration REAL",
    # Feedback — category
    "ALTER TABLE feedback ADD COLUMN feedback_category TEXT",
    # Ticket — SLA risk
    "ALTER TABLE tickets ADD COLUMN sla_risk_score REAL DEFAULT 0.0",
]

CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS stress_index_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        stress_score REAL NOT NULL,
        stress_level TEXT NOT NULL,
        active_emergencies INTEGER DEFAULT 0,
        active_appointments INTEGER DEFAULT 0,
        open_tickets INTEGER DEFAULT 0,
        sla_breaches INTEGER DEFAULT 0,
        avg_doctor_load REAL DEFAULT 0.0
    )""",
    """
    CREATE TABLE IF NOT EXISTS appointment_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forecast_date TEXT NOT NULL,
        department TEXT NOT NULL,
        predicted_count INTEGER DEFAULT 0,
        peak_hour INTEGER,
        risk_level TEXT DEFAULT 'LOW',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
]

def run():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    print("=== Phase 2 AI Migration ===")
    for sql in ALTERATIONS:
        col = sql.split("ADD COLUMN")[1].strip().split()[0]
        try:
            cur.execute(sql)
            print(f"  [+] Added column: {col}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  [~] Already exists: {col}")
            else:
                print(f"  [!] Error on {col}: {e}")

    for sql in CREATE_TABLES:
        table = sql.strip().split("TABLE IF NOT EXISTS")[1].strip().split()[0]
        cur.execute(sql)
        print(f"  [+] Created table (if new): {table}")

    # Indexes
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sis_timestamp ON stress_index_snapshots(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_af_date ON appointment_forecasts(forecast_date)")
        print("  [+] Indexes created.")
    except Exception as e:
        print(f"  [!] Index error: {e}")

    conn.commit()
    conn.close()
    print("=== Migration complete ===")

if __name__ == '__main__':
    run()
