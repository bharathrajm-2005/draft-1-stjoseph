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

    # 1. Clean up existing tables (in dependency order)
    tables = [
        'ai_response_logs', 'escalation_logs', 'tickets', 'feedback', 
        'appointments', 'users', 'departments', 'ambulances', 'emergency_dispatches', 'emergency_requests'
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # 2. Create Tables
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
    CREATE TABLE appointments (
        id INTEGER PRIMARY KEY,
        patient_name VARCHAR(100) NOT NULL,
        patient_email VARCHAR(100) NOT NULL,
        patient_phone VARCHAR(20),
        department_id INTEGER NOT NULL,
        doctor_id INTEGER,
        appointment_date VARCHAR(20) NOT NULL,
        time_slot VARCHAR(20) NOT NULL,
        status VARCHAR(20) DEFAULT 'Scheduled',
        appointment_type VARCHAR(20) DEFAULT 'Normal',
        ambulance_id INTEGER,
        completed_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(department_id) REFERENCES departments(id),
        FOREIGN KEY(doctor_id) REFERENCES users(id),
        FOREIGN KEY(ambulance_id) REFERENCES ambulances(id)
    )""")

    cursor.execute("""
    CREATE TABLE ambulances (
        id INTEGER PRIMARY KEY,
        driver_id INTEGER,
        vehicle_number VARCHAR(20) UNIQUE NOT NULL,
        driver_name VARCHAR(100) NOT NULL,
        status VARCHAR(20) DEFAULT 'Available',
        current_lat FLOAT,
        current_lng FLOAT,
        target_lat FLOAT,
        target_lng FLOAT,
        last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(driver_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE emergency_dispatches (
        id INTEGER PRIMARY KEY,
        appointment_id INTEGER NOT NULL,
        dispatch_status VARCHAR(20) DEFAULT 'Pending',
        primary_driver_id INTEGER,
        secondary_driver_id INTEGER,
        assigned_driver_id INTEGER,
        first_alert_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        second_alert_time DATETIME,
        accepted_at DATETIME,
        FOREIGN KEY(appointment_id) REFERENCES appointments(id),
        FOREIGN KEY(primary_driver_id) REFERENCES users(id),
        FOREIGN KEY(secondary_driver_id) REFERENCES users(id),
        FOREIGN KEY(assigned_driver_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE emergency_requests (
        id INTEGER PRIMARY KEY,
        patient_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        address TEXT,
        latitude FLOAT,
        longitude FLOAT,
        status TEXT DEFAULT 'Pending',
        assigned_driver_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        accepted_at DATETIME,
        completed_at DATETIME,
        FOREIGN KEY(assigned_driver_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE feedback (
        id INTEGER PRIMARY KEY,
        patient_id VARCHAR(50) NOT NULL,
        patient_name VARCHAR(100),
        patient_email VARCHAR(100),
        feedback_text TEXT NOT NULL,
        sentiment VARCHAR(20),
        sentiment_score FLOAT,
        rating INTEGER,
        issue_type VARCHAR(50),
        severity VARCHAR(20),
        is_verified BOOLEAN DEFAULT 0,
        appointment_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
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

    # 3. Seed Admin
    print("Seeding Admin...")
    cursor.execute("""
        INSERT INTO users (name, email, password, role, designation)
        VALUES ('CareAxis Admin', 'admin@careaxis.com', 'admin123', 'admin', 'Chief Operations Officer')
    """)

    # 4. Seed Drivers & Ambulances
    print("Seeding drivers and ambulances...")
    drivers_data = [
        ("Karan Sharma", "karan@careaxis.com", "AMB-001", 12.9716, 77.5946),
        ("Sumeet Vyas",  "sumeet@careaxis.com", "AMB-002", 12.9345, 77.6101),
        ("Rahul Bose",   "rahul@careaxis.com", "AMB-003", 12.9562, 77.7019),
        ("Vikas Khanna", "vikas@careaxis.com", "AMB-004", 13.0358, 77.5970),
        ("Aditya Roy",   "aditya@careaxis.com", "AMB-005", 12.9141, 77.6413)
    ]
    
    for name, email, v_num, lat, lng in drivers_data:
        # Create user
        cursor.execute("""
            INSERT INTO users (name, email, password, role, designation)
            VALUES (?, ?, 'driver123', 'staff', 'Ambulance Driver')
        """, (name, email))
        driver_id = cursor.lastrowid
        
        # Create ambulance linked to user
        cursor.execute("""
            INSERT INTO ambulances (driver_id, vehicle_number, driver_name, current_lat, current_lng, status)
            VALUES (?, ?, ?, ?, ?, 'Available')
        """, (driver_id, v_num, name, lat, lng))

    # 5. Seed Departments & Staff
    print("Seeding departments and staff...")
    departments = [
        "Emergency", "Cardiology", "Neurology", "Orthopedics", "Billing",
        "Pharmacy", "General Medicine", "Radiology", "ICU", "Administration"
    ]

    first_names = ["Arjun", "Rajesh", "Priya", "Vikram", "Anjali", "Suresh", "Meena", "Vijay", "Anita", "Sunil", "Kavita", "Rohan", "Sonal", "Deepak", "Pooja", "Amit", "Rahul", "Neha", "Manish", "Swati"]
    last_names  = ["Menon", "Kumar", "Sharma", "Singh", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Verma", "Joshi", "Das", "Bose", "Misra", "Malhotra"]

    designations = {
        "Emergency":        ["ER Specialist", "Trauma Surgeon", "Chief ER Physician"],
        "Cardiology":       ["Senior Cardiologist", "Interventional Cardiologist", "Cardiac Surgeon"],
        "Neurology":        ["Neurosurgeon", "Neurology Consultant", "Senior Neurologist"],
        "Orthopedics":      ["Orthopedic Surgeon", "Joint Specialist", "Senior Orthopedician"],
        "Billing":          ["Billing Manager", "Financial Counselor", "Accounts Supervisor"],
        "Pharmacy":         ["Chief Pharmacist", "Clinical Pharmacist", "Pharmacy Supervisor"],
        "General Medicine": ["Internal Medicine Specialist", "Senior General Physician"],
        "Radiology":        ["Senior Radiologist", "Interventional Radiologist"],
        "ICU":              ["Intensivist", "ICU Specialist", "Critical Care Consultant"],
        "Administration":   ["Operations Manager", "Patient Experience Head"]
    }

    for dept_name in departments:
        cursor.execute("INSERT INTO departments (name) VALUES (?)", (dept_name,))
        for i in range(5):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            name  = f"Dr. {fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1,99)}@careaxis.com"
            designation = random.choice(designations[dept_name])
            avg_res = random.randint(20, 180)
            rating  = round(random.uniform(3.5, 5.0), 1)
            cursor.execute("""
                INSERT INTO users (name, email, password, role, department, designation, active_tasks, avg_resolution_time, performance_rating)
                VALUES (?, ?, ?, 'staff', ?, ?, 0, ?, ?)
            """, (name, email, "password123", dept_name, designation, avg_res, rating))

    # 5. Seed Sample Appointments
    print("Seeding sample appointments...")
    sample_appointments = [
        # (name, email, dept, date, slot, status, type)
        ("Ravi Shankar",  "ravi.shankar@example.com",  "Cardiology",  "2026-02-20", "09:00 AM", "Completed",   "Normal"),
        ("Priya Mehta",   "priya.mehta@example.com",   "Neurology",   "2026-02-21", "10:30 AM", "In Progress", "Urgent"),
        ("Amol Patil",    "amol.patil@example.com",    "Orthopedics", "2026-02-21", "02:00 PM", "Scheduled",   "Normal"),
        ("Sunita Rao",    "sunita.rao@example.com",    "Emergency",   "2026-02-22", "08:00 AM", "Scheduled",   "Emergency"),
        ("Vikram Bhatia", "vikram.bhatia@example.com", "Radiology",   "2026-02-22", "11:00 AM", "Scheduled",   "Normal"),
    ]
    completed_now = datetime.utcnow().isoformat()
    for pname, pemail, dept_name, appt_date, slot, status, appt_type in sample_appointments:
        cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
        row = cursor.fetchone()
        if not row:
            continue
        dept_id = row[0]
        cursor.execute("SELECT id FROM users WHERE department = ? AND role = 'staff' LIMIT 1", (dept_name,))
        doc_row = cursor.fetchone()
        doc_id = doc_row[0] if doc_row else None
        comp_at = completed_now if status == 'Completed' else None
        cursor.execute("""
            INSERT INTO appointments (patient_name, patient_email, department_id, doctor_id, appointment_date, time_slot, status, completed_at, appointment_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pname, pemail, dept_id, doc_id, appt_date, slot, status, comp_at, appt_type))

    # 6. Seed Sample Feedback (including one verified)
    print("Seeding sample feedback & tickets...")
    sample_feedbacks = [
        ("P-1001", "",                         "The waiting time in the emergency room was unacceptable. Over 4 hours!", "Negative", -0.8, 1, "Waiting Time", "High",     "Emergency"),
        ("P-1002", "",                         "Dr. Sharma was very helpful and explained everything clearly.",           "Positive",  0.9, 5, "Clinical Quality", "Normal", "Cardiology"),
        ("P-1003", "",                         "The billing department made a mistake in my insurance claim.",            "Negative", -0.5, 2, "Billing",           "Medium",  "Billing"),
        ("P-1004", "",                         "EQUIPMENT FAILURE: The MRI machine broke down during my scan.",          "Negative", -0.9, 1, "Facility",          "Critical","Radiology"),
        ("P-1005", "ravi.shankar@example.com", "The cardiologist was rude and did not explain my test results at all.",  "Negative", -0.7, 2, "Staff Behavior",    "High",    "Cardiology"),
    ]

    appointment_id_map = {}
    cursor.execute("SELECT id, patient_email FROM appointments")
    for aid, aemail in cursor.fetchall():
        appointment_id_map[aemail.lower()] = aid

    for pid, pemail, text, sent, score, rat, itype, sev, dept_name in sample_feedbacks:
        is_verified = 0
        appt_id = None
        if pemail and pemail.lower() in appointment_id_map:
            # Only Completed appointments produce verified feedback
            cursor.execute("SELECT status FROM appointments WHERE id = ?", (appointment_id_map[pemail.lower()],))
            appt_status_row = cursor.fetchone()
            if appt_status_row and appt_status_row[0] == 'Completed':
                is_verified = 1
                appt_id = appointment_id_map[pemail.lower()]

        cursor.execute("""
            INSERT INTO feedback (patient_id, patient_email, feedback_text, sentiment, sentiment_score, rating, issue_type, severity, is_verified, appointment_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, pemail, text, sent, score, rat, itype, sev, is_verified, appt_id))
        fid = cursor.lastrowid

        cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
        dept_id = cursor.fetchone()[0]

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
    print("✅ Database recreated and seeded: Departments, Staff, Appointments & Tickets.")
    conn.close()

if __name__ == "__main__":
    seed_database()
