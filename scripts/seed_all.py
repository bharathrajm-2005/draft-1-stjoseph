from app import create_app
from database.models import db, Department, Staff
import random

def seed_everything():
    app = create_app()
    with app.app_context():
        # 1. Reset Database
        db.drop_all()
        db.create_all()
        print("Database schema recreated.")

        # 2. Departments
        dept_names = [
            "Emergency", "Cardiology", "Neurology", "Orthopedics", "Billing",
            "Pharmacy", "General Medicine", "Radiology", "ICU", "Administration"
        ]
        
        departments = {}
        for name in dept_names:
            dept = Department(name=name)
            db.session.add(dept)
            departments[name] = dept
        
        db.session.commit() # Get IDs

        # 3. Staff (10 per department)
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

        for dept_name, dept in departments.items():
            used_names = set()
            for i in range(10):
                while True:
                    name = f"Dr. {random.choice(first_names)} {random.choice(last_names)}"
                    if name not in used_names:
                        used_names.add(name)
                        break
                
                staff = Staff(
                    name=name,
                    designation=random.choice(designations[dept_name]),
                    department_id=dept.id,
                    active_ticket_count=0,
                    avg_resolution_time=random.randint(20, 180),
                    performance_rating=round(random.uniform(3.5, 5.0), 1)
                )
                db.session.add(staff)
        
        db.session.commit()
        print("Staff members seeded.")

if __name__ == "__main__":
    seed_everything()
