from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff') # 'admin' or 'staff'
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    
    # Metrics fields moved here for simplicity and requested structure
    active_tasks = db.Column(db.Integer, default=0)
    avg_resolution_time = db.Column(db.Float, default=30.0)
    performance_rating = db.Column(db.Float, default=5.0)

    assigned_tickets = db.relationship('Ticket', backref='assigned_to_user', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    tickets = db.relationship('Ticket', backref='department_rel', lazy=True)

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    appointment_date = db.Column(db.String(20), nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    # Allowed: Scheduled | In Progress | Completed | Cancelled
    status = db.Column(db.String(20), default='Scheduled')
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship('Department', backref='appointments', lazy=True)
    doctor = db.relationship('User', backref='appointments', lazy=True)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False)
    patient_name = db.Column(db.String(100))
    patient_email = db.Column(db.String(100))
    feedback_text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(20))
    sentiment_score = db.Column(db.Float)
    rating = db.Column(db.Integer)
    issue_type = db.Column(db.String(50))
    severity = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tickets = db.relationship('Ticket', backref='feedback', lazy=True)
    appointment = db.relationship('Appointment', backref='feedbacks', lazy=True)

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
    escalation_level = db.Column(db.Integer, default=0)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolution_notes = db.Column(db.Text)
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
    action_taken = db.Column(db.String(50)) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
