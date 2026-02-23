import sqlite3
import os
import random
from datetime import datetime, timedelta

def seed_database():
    db_path = os.path.join('database', 'patient_experience.db')
    
    # Remove old DB to ensure clean schema
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Clean up existing tables
    tables = ['ai_response_logs', 'escalation_logs', 'tickets', 'feedback', 'users', 'departments']
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # 1. Create Tables
    cursor.execute("""
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY,
        name VARCHAR(50) UNIQUE NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'staff',
        department VARCHAR(100),
        designation VARCHAR(100),
        active_tasks INTEGER DEFAULT 0,
        avg_resolution_time FLOAT DEFAULT 30.0,
        performance_rating FLOAT DEFAULT 5.0
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
        assigned_user_id INTEGER,
        resolution_notes TEXT,
        ai_suggested_response TEXT,
        status_history_log TEXT,
        FOREIGN KEY(feedback_id) REFERENCES feedback(id),
        FOREIGN KEY(department_id) REFERENCES departments(id),
        FOREIGN KEY(assigned_user_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE escalation_logs (
        id INTEGER PRIMARY KEY,
        ticket_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        reason VARCHAR(200),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ticket_id) REFERENCES tickets(id)
    )""")

    cursor.execute("""
    CREATE TABLE ai_response_logs (
        id INTEGER PRIMARY KEY,
        ticket_id INTEGER NOT NULL,
        draft_content TEXT,
        action_taken VARCHAR(50),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ticket_id) REFERENCES tickets(id)
    )""")

    # 2. Seed Admin
    cursor.execute("""
        INSERT INTO users (name, email, password, role, designation)
        VALUES ('Aurevia Admin', 'admin@aurevia.com', 'admin123', 'admin', 'Chief Operations Officer')
    """)

    # 3. Seed Departments & Staff
    departments = [
        "Emergency", "Cardiology", "Neurology", "Orthopedics", "Billing",
        "Pharmacy", "General Medicine", "Radiology", "ICU", "Administration"
    ]

    for dept_name in departments:
        cursor.execute("INSERT INTO departments (name) VALUES (?)", (dept_name,))
        
        first_names = ["Arjun", "Rajesh", "Priya", "Vikram", "Anjali", "Suresh", "Meena", "Vijay", "Anita", "Sunil", "Kavita", "Rohan", "Sonal", "Deepak", "Pooja", "Amit", "Rahul", "Neha", "Manish", "Swati"]
        last_names = ["Menon", "Kumar", "Sharma", "Singh", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Verma", "Joshi", "Das", "Bose", "Misra", "Malhotra"]

        designations = {
            "Emergency": ["ER Specialist", "Trauma Surgeon", "Chief ER Physician"],
            "Cardiology": ["Senior Cardiologist", "Interventional Cardiologist", "Cardiac Surgeon"],
            "Neurology": ["Neurosurgeon", "Neurology Consultant", "Senior Neurologist"],
            "Orthopedics": ["Orthopedic Surgeon", "Joint Specialist", "Senior Orthopedician"],
            "Billing": ["Billing Manager", "Financial Counselor", "Accounts Supervisor"],
            "Pharmacy": ["Chief Pharmacist", "Clinical Pharmacist", "Pharmacy Supervisor"],
            "General Medicine": ["Internal Medicine Specialist", "Senior General Physician"],
            "Radiology": ["Senior Radiologist", "Interventional Radiologist"],
            "ICU": ["Intensivist", "ICU Specialist", "Critical Care Consultant"],
            "Administration": ["Operations Manager", "Patient Experience Head"]
        }

        for i in range(5): # 5 staff per dept
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            name = f"Dr. {fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1,99)}@aurevia.com"
            password = "password123"
            designation = random.choice(designations[dept_name])
            avg_res = random.randint(20, 180)
            rating = round(random.uniform(3.5, 5.0), 1)
            
            cursor.execute("""
                INSERT INTO users (name, email, password, role, department, designation, active_tasks, avg_resolution_time, performance_rating)
                VALUES (?, ?, ?, 'staff', ?, ?, 0, ?, ?)
            """, (name, email, password, dept_name, designation, avg_res, rating))

    # 4. Seed Sample Tickets
    print("Seeding sample tickets...")
    sample_feedbacks = [
        ("P-1001", "The waiting time in the emergency room was unacceptable. Over 4 hours!", "Negative", -0.8, 1, "Waiting Time", "High", "Emergency"),
        ("P-1002", "Dr. Sharma was very helpful and explained everything clearly.", "Positive", 0.9, 5, "Clinical Quality", "Normal", "Cardiology"),
        ("P-1003", "The billing department made a mistake in my insurance claim.", "Negative", -0.5, 2, "Billing", "Medium", "Billing"),
        ("P-1004", "EQUIPMENT FAILURE: The MRI machine broke down during my scan. Very scary.", "Negative", -0.9, 1, "Facility", "Critical", "Radiology")
    ]

    for pid, text, sent, score, rat, itype, sev, dept_name in sample_feedbacks:
        cursor.execute("""
            INSERT INTO feedback (patient_id, feedback_text, sentiment, sentiment_score, rating, issue_type, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pid, text, sent, score, rat, itype, sev))
        fid = cursor.lastrowid
        
        cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
        dept_id = cursor.fetchone()[0]
        
        # Get a staff from that dept
        cursor.execute("SELECT id FROM users WHERE department = ? AND role = 'staff' LIMIT 1", (dept_name,))
        assigned_user = cursor.fetchone()
        uid = assigned_user[0] if assigned_user else None
        
        deadline = (datetime.utcnow() + timedelta(hours=6)).isoformat()
        
        cursor.execute("""
            INSERT INTO tickets (feedback_id, department_id, status, severity, sla_deadline, assigned_user_id)
            VALUES (?, ?, 'In Progress', ?, ?, ?)
        """, (fid, dept_id, sev, deadline, uid))
        
        if uid:
            cursor.execute("UPDATE users SET active_tasks = active_tasks + 1 WHERE id = ?", (uid,))

    conn.commit()
    print("Database recreated and seeded with Users, Departments & Sample Tickets successfully.")
    conn.close()

if __name__ == "__main__":
    seed_database()
