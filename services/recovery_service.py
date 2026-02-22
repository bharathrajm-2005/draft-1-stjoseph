from datetime import datetime
from database.models import db, Feedback, RecoveryTask
from models.preprocessing import Preprocessor
from models.sentiment_model import SentimentModel
from models.issue_classifier import IssueClassifier
from models.severity_engine import SeverityEngine
from .rule_engine import RuleEngine
from .notification_service import NotificationService
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

    def process_new_feedback(self, patient_id, feedback_text):
        try:
            app_logger.info(f"Processing feedback for patient: {patient_id}")
            
            # 1. Preprocessing
            cleaned_text = self.preprocessor.clean_text(feedback_text)
            
            # 2. Sentiment Analysis
            sentiment, score = self.sentiment_model.analyze(feedback_text)
            
            # 3. Issue Classification
            issue_type = self.classifier.predict(cleaned_text)
            
            # 4. Severity Scoring
            severity = self.severity_engine.calculate_severity(feedback_text, score)
            
            # 5. Store Feedback
            new_feedback = Feedback(
                patient_id=patient_id,
                feedback_text=feedback_text,
                sentiment=sentiment,
                sentiment_score=score,
                issue_type=issue_type,
                severity=severity
            )
            db.session.add(new_feedback)
            db.session.commit()
            
            # 6. Trigger Recovery Workflow if negative
            if sentiment == "Negative":
                self.trigger_recovery_workflow(new_feedback)
            
            return new_feedback
            
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Error in RecoveryService: {e}")
            raise e

    def trigger_recovery_workflow(self, feedback):
        dept, sla_hours = self.rule_engine.determine_sla_and_dept(feedback.issue_type, feedback.severity)
        deadline = calculate_deadline(sla_hours)
        
        recovery_task = RecoveryTask(
            feedback_id=feedback.id,
            department=dept,
            sla_deadline=deadline
        )
        db.session.add(recovery_task)
        db.session.commit()
        
        # 7. Notify Department
        self.notifier.send_notification(dept, f"New {feedback.severity} recovery task assigned for patient {feedback.patient_id}")
        
        return recovery_task
