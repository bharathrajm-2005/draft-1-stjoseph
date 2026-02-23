from app import create_app
from database.models import db, Ticket, Feedback, Department, User
from sqlalchemy import func

app = create_app()
with app.app_context():
    print("--- Detailed Diagnostic ---")
    tickets = Ticket.query.all()
    print(f"Total Ticket Count: {len(tickets)}")
    for t in tickets:
        print(f"ID: {t.id} | Status: {t.status} | Dept: {t.department_id} | User: {t.assigned_user_id}")
    
    active_count = Ticket.query.filter(Ticket.status.in_(['Open', 'In Progress', 'Escalated'])).count()
    print(f"Active Tickets Count (Backend Logic): {active_count}")
    
    # Check if we can join
    try:
        results = db.session.query(Ticket).join(Feedback).join(Department).all()
        print(f"Join Results Count: {len(results)}")
    except Exception as e:
        print(f"Join Error: {e}")

    # Check Departments
    depts = Department.query.all()
    print(f"Departments: {[d.name for d in depts]}")
