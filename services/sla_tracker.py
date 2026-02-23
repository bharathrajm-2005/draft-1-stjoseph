from datetime import datetime, timedelta
from database.models import db, Ticket, Feedback, EscalationLog
from utils.logger import app_logger
from .notification_service import NotificationService
import json

class SLATracker:
    def __init__(self):
        self.notifier = NotificationService()

    def check_breaches(self):
        """ Checks for active tickets that have breached their SLA or need escalation """
        now = datetime.utcnow()
        
        # 1. Standard SLA Breaches (Any status, past deadline)
        breached_tickets = Ticket.query.filter(
            Ticket.status.in_(['Open', 'In Progress']),
            Ticket.sla_deadline < now,
            Ticket.escalation_level < 1 # Not already escalated to high level
        ).all()
        
        for ticket in breached_tickets:
            self.escalate_ticket(ticket, 1, "SLA Deadline Breached", now)

        # 2. Critical Escalation Level 1 (Critical + Not assigned in 10 mins)
        ten_mins_ago = now - timedelta(minutes=10)
        critical_unassigned = Ticket.query.join(Feedback).filter(
            Ticket.severity == 'Critical',
            Ticket.assigned_user_id == None,
            Ticket.status == 'Open',
            Feedback.created_at < ten_mins_ago,
            Ticket.escalation_level < 1
        ).all()

        for ticket in critical_unassigned:
            self.escalate_ticket(ticket, 1, "Critical ticket not assigned within 10 minutes", now)

        # 3. Critical Escalation Level 2 (Critical + Not resolved in 30 mins)
        thirty_mins_ago = now - timedelta(minutes=30)
        critical_unresolved = Ticket.query.join(Feedback).filter(
            Ticket.severity == 'Critical',
            Ticket.status.in_(['Open', 'In Progress', 'Escalated']),
            Feedback.created_at < thirty_mins_ago,
            Ticket.escalation_level < 2
        ).all()

        for ticket in critical_unresolved:
            self.escalate_ticket(ticket, 2, "Critical ticket not resolved within 30 minutes", now)

        db.session.commit()
        return "Check Completed"

    def escalate_ticket(self, ticket, target_level, reason, timestamp):
        app_logger.warning(f"ESCALATION: Ticket {ticket.id} to Level {target_level}. Reason: {reason}")
        
        prev_level = ticket.escalation_level
        ticket.escalation_level = target_level
        ticket.escalation_flag = True
        ticket.status = 'Escalated'

        # Log to Escalation table
        log = EscalationLog(ticket_id=ticket.id, level=target_level, reason=reason)
        db.session.add(log)

        # Update status history
        history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
        target_name = "Senior Department Head" if target_level == 1 else "Hospital Operations Director"
        
        history.append({
            "status": "Escalated",
            "timestamp": timestamp.isoformat() + "Z",
            "action": f"🚨 Automated Escalation to {target_name}",
            "reason": reason
        })
        ticket.status_history_log = json.dumps(history)

        # Alerts
        sms_alert = f"SMS ALERT: Ticket {ticket.id} escalated to {target_name}. Reason: {reason}"
        email_alert = f"EMAIL ALERT: Senior Management attention required for Ticket {ticket.id}."
        
        self.notifier.send_notification("Management", f"{sms_alert} | {email_alert}")
