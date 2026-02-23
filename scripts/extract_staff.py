import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.models import User
import pandas as pd

app = create_app()
with app.app_context():
    staff_members = User.query.filter_by(role='staff').all()
    
    data = []
    for s in staff_members:
        data.append({
            "Name": s.name,
            "Email": s.email,
            "Department": s.department,
            "Designation": s.designation,
            "Password": "password123" # All seeded staff use this default
        })
    
    df = pd.DataFrame(data)
    print("\n--- SEEDED STAFF DETAILS ---")
    print(df.to_string(index=False))
    print("\n----------------------------")
