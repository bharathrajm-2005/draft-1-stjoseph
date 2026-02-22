from datetime import datetime
from database.models import db, RecoveryTask
from utils.logger import app_logger
from .notification_service import NotificationService

class SLATracker:
    def __init__(self):
        self.notifier = NotificationService()

    def check_breaches(self):
        """ Checks for active tasks that have breached their SLA """
        now = datetime.utcnow()
        breached_tasks = RecoveryTask.query.filter(
            RecoveryTask.status != 'Resolved',
            RecoveryTask.sla_deadline < now,
            RecoveryTask.escalation_flag == False
        ).all()
        
        for task in breached_tasks:
            app_logger.warning(f"SLA BREACH: Task ID {task.id} (Dept: {task.department}) has exceeded deadline.")
            task.escalation_flag = True
            
            # Notify management
            self.notifier.send_notification(
                "Management", 
                f"SLA BREACH ALERT: Task {task.id} in {task.department} is overdue!"
            )
            
        db.session.commit()
        return len(breached_tasks)
