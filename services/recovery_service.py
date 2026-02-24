from datetime import datetime
import json
from database.models import db, Feedback, Ticket, Department, User
from models.preprocessing import Preprocessor
from models.sentiment_model import SentimentModel
from models.issue_classifier import IssueClassifier
from models.severity_engine import SeverityEngine
from .rule_engine import RuleEngine
from .notification_service import NotificationService
from .ai_response_service import AIResponseService
from .triage_service import TriageService
from utils.helpers import calculate_deadline
from utils.logger import app_logger

class RecoveryService:
    def __init__(self):
        self.preprocessor = Preprocessor()
        self.sentiment_model = SentimentModel()
        self.classifier = IssueClassifier()
        self.severity_engine = SeverityEngine()
        self.rule_engine = RuleEngine()
        self.notifier = NotificationService()
        self.ai_responder = AIResponseService()
        self.triage_service = TriageService()

    def process_new_feedback(self, patient_id, feedback_text, rating=None):
        try:
            app_logger.info(f"Processing feedback for patient: {patient_id}")
            
            # 1. Preprocessing
            cleaned_text = self.preprocessor.clean_text(feedback_text)
            
            # 2. Sentiment Analysis
            sentiment, score = self.sentiment_model.analyze(feedback_text)
            
            # 3. Issue Classification
            issue_type = self.classifier.predict(cleaned_text)
            feedback_category = self.classifier.categorize(feedback_text)
            
            # 4. Severity Prediction (Enhanced)
            severity = self.severity_engine.calculate_severity(feedback_text, score)
            
            critical_keywords = ['emergency', 'danger', 'death', 'wrong medicine', 'bleeding', 'unconscious']
            if any(word in feedback_text.lower() for word in critical_keywords) or score < -0.8:
                severity = "High"
            
            # 5. Store Feedback
            new_feedback = Feedback(
                patient_id=patient_id,
                feedback_text=feedback_text,
                sentiment=sentiment,
                sentiment_score=score,
                rating=rating,
                issue_type=issue_type,
                feedback_category=feedback_category,
                severity=severity
            )
            db.session.add(new_feedback)
            db.session.commit()
            
            # 6. Trigger Recovery Workflow if not Positive/Low
            if sentiment != "Positive" or severity != "Low":
                self.trigger_recovery_workflow(new_feedback)
            elif rating and rating <= 3:
                self.trigger_recovery_workflow(new_feedback)
            
            return new_feedback
            
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error in RecoveryService: {e}")
            raise e

    def trigger_recovery_workflow(self, feedback):
        dept_name, _ = self.rule_engine.determine_sla_and_dept(feedback.issue_type, feedback.severity)
        
        # Calculate Dynamic SLA
        is_verified = getattr(feedback, 'is_verified', False)
        # Note: at this point is_verified might be False because it's set in controllers after process_new_feedback
        # But we can check if there's an appointment link if we re-query later or pass it in.
        # For now, use a base based on severity.
        
        severity_map = {
            "Critical": "Emergency",
            "High": "Urgent",
            "Medium": "Normal", # We'll treat Medium as Normal baseline
            "Low": "Normal"
        }
        
        sla_mins = self.triage_service.calculate_dynamic_sla(
            severity_map.get(feedback.severity, "Normal"),
            is_verified=is_verified
        )
        
        deadline = calculate_deadline(sla_mins / 60)
        
        # Find department 
        department = Department.query.filter_by(name=dept_name).first()
        if not department:
            department = Department.query.filter_by(name='Administration').first()
        
        if not department:
            app_logger.error("Critical: 'Administration' department not found in database.")
            raise Exception("Department configuration missing")

        # FULLY AUTOMATED SMART STAFF ASSIGNMENT (Optimized Formula)
        # score = (activeTasks * 4) + (avgResolutionTime / 10) - (performanceRating * 2)
        all_staff = User.query.filter_by(department=department.name, role='staff').all()
        best_staff = None
        min_score = float('inf')
        
        for s in all_staff:
            score = (s.active_tasks * 4) + (s.avg_resolution_time / 10) - (s.performance_rating * 2)
            if score < min_score:
                min_score = score
                best_staff = s

        assigned_user_id = None
        if best_staff:
            assigned_user_id = best_staff.id
            best_staff.active_tasks += 1

        ticket = Ticket(
            feedback_id=feedback.id,
            department_id=department.id,
            severity=feedback.severity,
            sla_deadline=deadline,
            status='In Progress' if assigned_user_id else 'Open',
            assigned_user_id=assigned_user_id,
            status_history_log=json.dumps([{
                "status": "In Progress" if assigned_user_id else "Open",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": f"🤖 AI Suggestion: {best_staff.name} (Score: {round(min_score, 1)})" if assigned_user_id else "Ticket Created",
                "reason": f"Hybrid Score: Workload={best_staff.active_tasks}, Speed={round(best_staff.avg_resolution_time)}m, Rating={best_staff.performance_rating}" if best_staff else ""
            }])
        )

        suggestion_data = self.ai_responder.generate_suggestion(ticket, feedback)
        ticket.ai_suggested_response = suggestion_data['response']
        # ticket.internal_notes = suggestion_data['escalation_note'] # Combined into suggestion

        db.session.add(ticket)
        db.session.commit()
        
        self.notifier.send_notification(dept_name, f"New {feedback.severity} ticket {ticket.id} assigned to {best_staff.name if best_staff else 'Queue'}")
        
        return ticket
