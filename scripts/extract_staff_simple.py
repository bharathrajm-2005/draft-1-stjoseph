import sqlite3
import os

db_path = os.path.join('database', 'patient_experience.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name, email, department, designation FROM users WHERE role='staff'")
rows = cursor.fetchall()

print(f"{'NAME':<25} | {'EMAIL':<35} | {'DEPARTMENT':<15} | {'DESIGNATION'}")
print("-" * 100)
for row in rows:
    print(f"{row[0]:<25} | {row[1]:<35} | {row[2]:<15} | {row[3]}")

conn.close()
