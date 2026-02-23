from datetime import datetime
import json
from database.models import db, Feedback, Ticket, Department, Staff
from models.preprocessing import Preprocessor
from models.sentiment_model import SentimentModel
from models.issue_classifier import IssueClassifier
from models.severity_engine import SeverityEngine
from .rule_engine import RuleEngine
from .notification_service import NotificationService
from .ai_response_service import AIResponseService
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

    def process_new_feedback(self, patient_id, feedback_text, rating=None):
        try:
            app_logger.info(f"Processing feedback for patient: {patient_id}")
            
            # 1. Preprocessing
            cleaned_text = self.preprocessor.clean_text(feedback_text)
            
            # 2. Sentiment Analysis
            sentiment, score = self.sentiment_model.analyze(feedback_text)
            
            # 3. Issue Classification
            issue_type = self.classifier.predict(cleaned_text)
            
            # 4. Severity Prediction (Enhanced)
            # If sentiment is very negative or keywords like "emergency", "danger", "death", "wrong" are present
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
                severity=severity
            )
            db.session.add(new_feedback)
            db.session.commit()
            
            # 6. Trigger Recovery Workflow if not Positive/Low (all actionable feedback)
            if sentiment != "Positive" or severity != "Low":
                self.trigger_recovery_workflow(new_feedback)
            elif rating and rating <= 3: # Also trigger if rating is low regardless of sentiment
                self.trigger_recovery_workflow(new_feedback)
            
            return new_feedback
            
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error in RecoveryService: {e}")
            raise e

    def trigger_recovery_workflow(self, feedback):
        dept_name, sla_mins = self.rule_engine.determine_sla_and_dept(feedback.issue_type, feedback.severity)
        deadline = calculate_deadline(sla_mins / 60)
        
        # Find department ID
        department = Department.query.filter_by(name=dept_name).first()
        if not department:
            department = Department.query.filter_by(name='Administration').first()
        
        if not department:
            # Last resort fallback if even Administration is missing
            app_logger.error("Critical: 'Administration' department not found in database.")
            raise Exception("Department configuration missing")

        # FULLY AUTOMATED SMART STAFF ASSIGNMENT (Optimized Formula)
        # score = (activeTasks * 4) + (avgResolutionTime / 10) - (performanceRating * 2)
        all_staff = Staff.query.filter_by(department_id=department.id).all()
        best_staff = None
        min_score = float('inf')
        
        for s in all_staff:
            # Applying new optimized formula
            score = (s.active_ticket_count * 4) + (s.avg_resolution_time / 10) - (s.performance_rating * 2)
            if score < min_score:
                min_score = score
                best_staff = s

        assigned_staff_id = None
        if best_staff:
            assigned_staff_id = best_staff.id
            best_staff.active_ticket_count += 1

        ticket = Ticket(
            feedback_id=feedback.id,
            department_id=department.id,
            severity=feedback.severity,
            sla_deadline=deadline,
            status='In Progress' if assigned_staff_id else 'Open',
            assigned_staff_id=assigned_staff_id,
            status_history_log=json.dumps([{
                "status": "In Progress" if assigned_staff_id else "Open",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": f"🤖 AI Suggestion: {best_staff.name} (Score: {round(min_score, 1)})" if assigned_staff_id else "Ticket Created",
                "reason": f"Hybrid Score: Workload={best_staff.active_ticket_count}, Speed={round(best_staff.avg_resolution_time)}m, Rating={best_staff.performance_rating}" if best_staff else ""
            }])
        )

        # 7. Generate AI Response Suggestion
        suggestion_data = self.ai_responder.generate_suggestion(ticket, feedback)
        ticket.ai_suggested_response = suggestion_data['response']
        ticket.internal_notes = suggestion_data['escalation_note']

        db.session.add(ticket)
        db.session.commit()
        
        # 8. Notify Department
        self.notifier.send_notification(dept_name, f"New {feedback.severity} ticket {ticket.id} assigned to {best_staff.name if best_staff else 'Queue'}")
        
        return ticket
