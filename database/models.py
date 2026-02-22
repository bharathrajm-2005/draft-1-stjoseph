from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(20))
    sentiment_score = db.Column(db.Float)
    issue_type = db.Column(db.String(50))
    severity = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with recovery tasks
    recovery_tasks = db.relationship('RecoveryTask', backref='feedback', lazy=True)

class RecoveryTask(db.Model):
    __tablename__ = 'recovery_task'
    
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Open') # Open, In Progress, Resolved
    sla_deadline = db.Column(db.DateTime, nullable=False)
    resolved_at = db.Column(db.DateTime)
    escalation_flag = db.Column(db.Boolean, default=False)
    
    def __init__(self, **kwargs):
        super(RecoveryTask, self).__init__(**kwargs)
