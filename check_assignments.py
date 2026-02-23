"""
Quick diagnostic to verify the complete_staff_task logic works.
Simulates resolving a ticket as a staff user.
"""
import sqlite3
import os

db_path = os.path.join('database', 'patient_experience.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== TICKET ASSIGNMENTS ===")
cursor.execute("""
    SELECT t.id, t.status, t.assigned_user_id, u.name, u.email, d.name as dept
    FROM tickets t
    LEFT JOIN users u ON t.assigned_user_id = u.id
    LEFT JOIN departments d ON t.department_id = d.id
""")
rows = cursor.fetchall()
print(f"{'TKT':<5} | {'STATUS':<15} | {'UID':<4} | {'ASSIGNED TO':<25} | {'EMAIL':<35} | {'DEPT'}")
print("-" * 100)
for row in rows:
    uid = str(row[2]) if row[2] else 'NULL'
    name = row[3] if row[3] else '(unassigned)'
    email = row[4] if row[4] else '-'
    print(f"{row[0]:<5} | {row[1]:<15} | {uid:<4} | {name:<25} | {email:<35} | {row[5]}")

print("\n=== STAFF USERS ===")
cursor.execute("SELECT id, name, email, department FROM users WHERE role='staff' LIMIT 5")
staff = cursor.fetchall()
for s in staff:
    print(f"ID: {s[0]} | {s[1]} | {s[2]} | Dept: {s[3]}")

conn.close()
