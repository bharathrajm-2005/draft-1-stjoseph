from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    staff = db.relationship('Staff', backref='department', lazy=True)
    tickets = db.relationship('Ticket', backref='department_rel', lazy=True)

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    active_ticket_count = db.Column(db.Integer, default=0)
    avg_resolution_time = db.Column(db.Float, default=30.0) # in minutes
    performance_rating = db.Column(db.Float, default=5.0) # 1.0 - 5.0
    tickets = db.relationship('Ticket', backref='assigned_staff', lazy=True)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(20))
    sentiment_score = db.Column(db.Float)
    rating = db.Column(db.Integer)
    issue_type = db.Column(db.String(50))
    severity = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tickets = db.relationship('Ticket', backref='feedback', lazy=True)

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    status = db.Column(db.String(20), default='Open')
    severity = db.Column(db.String(20))
    sla_deadline = db.Column(db.DateTime, nullable=False)
    resolved_at = db.Column(db.DateTime)
    resolution_time = db.Column(db.Integer)
    escalation_flag = db.Column(db.Boolean, default=False)
    escalation_level = db.Column(db.Integer, default=0) # 0: None, 1: Dept Head, 2: Director
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    internal_notes = db.Column(db.Text)
    ai_suggested_response = db.Column(db.Text)
    status_history_log = db.Column(db.Text)

class EscalationLog(db.Model):
    __tablename__ = 'escalation_logs'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIResponseLog(db.Model):
    __tablename__ = 'ai_response_logs'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    draft_content = db.Column(db.Text)
    action_taken = db.Column(db.String(50)) # Suggested, Editted, Approved, Regenerated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Ticket, self).__init__(**kwargs)
