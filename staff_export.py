import sqlite3
import os

def export_staff():
    db_path = os.path.join('database', 'patient_experience.db')
    if not os.path.exists(db_path):
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name, email, department, designation FROM users WHERE role='staff'")
    staff = cursor.fetchall()

    print(f"{'#':<3} | {'NAME':<25} | {'EMAIL':<35} | {'DEPARTMENT'}")
    print("-" * 80)
    for i, s in enumerate(staff, 1):
        print(f"{i:<3} | {s[0]:<25} | {s[1]:<35} | {s[2]}")

    conn.close()

if __name__ == "__main__":
    export_staff()
