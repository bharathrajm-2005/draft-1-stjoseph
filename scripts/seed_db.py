import sqlite3
import os
import random
from datetime import datetime

def seed_database():
    db_path = os.path.join('database', 'patient_experience.db')
    
    # Remove old DB to ensure clean schema
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Create Tables (Manual Schema to avoid SQLAlchemy mismatch in seed)
    cursor.execute("""
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY,
        name VARCHAR(50) UNIQUE NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE staff (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        designation VARCHAR(100),
        department_id INTEGER NOT NULL,
        active_ticket_count INTEGER DEFAULT 0,
        avg_resolution_time FLOAT DEFAULT 30.0,
        performance_rating FLOAT DEFAULT 5.0,
        FOREIGN KEY(department_id) REFERENCES departments(id)
    )""")

    cursor.execute("""
    CREATE TABLE feedback (
        id INTEGER PRIMARY KEY,
        patient_id VARCHAR(50) NOT NULL,
        feedback_text TEXT NOT NULL,
        sentiment VARCHAR(20),
        sentiment_score FLOAT,
        rating INTEGER,
        issue_type VARCHAR(50),
        severity VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY,
        feedback_id INTEGER NOT NULL,
        department_id INTEGER NOT NULL,
        status VARCHAR(20) DEFAULT 'Open',
        severity VARCHAR(20),
        sla_deadline DATETIME NOT NULL,
        resolved_at DATETIME,
        resolution_time INTEGER,
        escalation_flag BOOLEAN DEFAULT 0,
        escalation_level INTEGER DEFAULT 0,
        assigned_staff_id INTEGER,
        internal_notes TEXT,
        ai_suggested_response TEXT,
        status_history_log TEXT,
        FOREIGN KEY(feedback_id) REFERENCES feedback(id),
        FOREIGN KEY(department_id) REFERENCES departments(id),
        FOREIGN KEY(assigned_staff_id) REFERENCES staff(id)
    )""")

    # 2. Seed Data
    departments = [
        "Emergency", "Cardiology", "Neurology", "Orthopedics", "Billing",
        "Pharmacy", "General Medicine", "Radiology", "ICU", "Administration"
    ]

    for dept_name in departments:
        cursor.execute("INSERT INTO departments (name) VALUES (?)", (dept_name,))
        dept_id = cursor.lastrowid

        first_names = ["Arjun", "Rajesh", "Priya", "Vikram", "Anjali", "Suresh", "Meena", "Vijay", "Anita", "Sunil", "Kavita", "Rohan", "Sonal", "Deepak", "Pooja", "Amit", "Rahul", "Neha", "Manish", "Swati"]
        last_names = ["Menon", "Kumar", "Sharma", "Singh", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Verma", "Joshi", "Das", "Bose", "Misra", "Malhotra"]

        designations = {
            "Emergency": ["ER Specialist", "Trauma Surgeon", "Chief ER Physician", "Emergency Resident", "Triage Specialist"],
            "Cardiology": ["Senior Cardiologist", "Interventional Cardiologist", "Cardiac Surgeon", "Consultant Cardiologist", "Cardiology Fellow"],
            "Neurology": ["Neurosurgeon", "Neurology Consultant", "Senior Neurologist", "Clinical Neurologist", "Neuro Resident"],
            "Orthopedics": ["Orthopedic Surgeon", "Joint Specialist", "Senior Orthopedician", "Sports Medicine Specialist", "Ortho Consultant"],
            "Billing": ["Billing Manager", "Financial Counselor", "Accounts Supervisor", "Patient Billing Rep", "Senior Billing Officer"],
            "Pharmacy": ["Chief Pharmacist", "Clinical Pharmacist", "Pharmacy Supervisor", "Senior Pharmacist", "Pharmacy Specialist"],
            "General Medicine": ["Internal Medicine Specialist", "Senior General Physician", "Family Medicine Doc", "Medicine Consultant", "MD Physician"],
            "Radiology": ["Senior Radiologist", "Interventional Radiologist", "Radiology Consultant", "Chief Radiologist", "Medical Imaging Specialist"],
            "ICU": ["Intensivist", "ICU Specialist", "Critical Care Consultant", "Intensive Care Lead", "Senior Intensivist"],
            "Administration": ["Operations Manager", "Patient Experience Head", "Admin Supervisor", "Quality Assurance Lead", "Hospital Administrator"]
        }

        used_names = set()
        for i in range(10):
            while True:
                name = f"Dr. {random.choice(first_names)} {random.choice(last_names)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            
            designation = random.choice(designations[dept_name])
            avg_res = random.randint(20, 180)
            rating = round(random.uniform(3.5, 5.0), 1)
            
            cursor.execute("""
                INSERT INTO staff (name, designation, department_id, active_ticket_count, avg_resolution_time, performance_rating)
                VALUES (?, ?, ?, 0, ?, ?)
            """, (name, designation, dept_id, avg_res, rating))

    conn.commit()
    print("Database recreated and seeded via SQLite3 successfully.")
    conn.close()

if __name__ == "__main__":
    seed_database()
