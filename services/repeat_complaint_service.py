"""
Repeat Complaint Detection Service — flags high-risk patients and auto-escalates.
"""
from utils.logger import app_logger

REPEAT_THRESHOLD = 2   # negative feedbacks to trigger flag


class RepeatComplaintService:
    def evaluate(self, patient_id):
        """
        Called after each new feedback submission.
        If patient_id has >= REPEAT_THRESHOLD negative feedbacks, escalates
        the latest open ticket immediately and updates complaint_count.

        Returns dict: {flagged, complaint_count, ticket_id_escalated}
        """
        from database.models import db, Feedback, Ticket, EscalationLog
        from datetime import datetime

        try:
            negative = (Feedback.query
                        .filter_by(patient_id=patient_id, sentiment='Negative')
                        .all())
            count = len(negative)

            if count < REPEAT_THRESHOLD:
                return {'flagged': False, 'complaint_count': count,
                        'ticket_id_escalated': None}

            # Find latest open ticket for this patient
            latest_fb = (Feedback.query
                         .filter_by(patient_id=patient_id)
                         .order_by(Feedback.id.desc())
                         .first())
            escalated_id = None
            if latest_fb:
                ticket = (Ticket.query
                          .filter_by(feedback_id=latest_fb.id)
                          .first())
                if ticket and ticket.status not in ('Resolved', 'Closed'):
                    ticket.severity       = 'Critical'
                    ticket.escalation_flag = True
                    ticket.escalation_level = max(ticket.escalation_level, 2)
                    escalated_id = ticket.id

                    log = EscalationLog(
                        ticket_id = ticket.id,
                        level     = ticket.escalation_level,
                        reason    = f"🤖 AI: Repeat complaint — patient has {count} negative feedbacks.",
                    )
                    db.session.add(log)

            db.session.commit()
            app_logger.warning(
                f"High-Risk Patient flagged: {patient_id} "
                f"({count} complaints, ticket #{escalated_id} escalated)"
            )
            return {
                'flagged':              True,
                'complaint_count':      count,
                'ticket_id_escalated':  escalated_id,
            }

        except Exception as e:
            app_logger.error(f"RepeatComplaintService error: {e}")
            db.session.rollback()
            return {'flagged': False, 'complaint_count': 0, 'ticket_id_escalated': None}


repeat_complaint_service = RepeatComplaintService()
