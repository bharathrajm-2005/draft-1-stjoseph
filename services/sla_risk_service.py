"""
SLA Breach Risk Scorer — predicts breach probability for all open tickets.
"""
from datetime import datetime, timezone
from utils.logger import app_logger

HIGH_RISK_THRESHOLD = 0.7


class SLARiskService:
    def evaluate_all(self):
        """
        Scores every open/in-progress ticket for SLA breach probability (0–1).
        Persists score to Ticket.sla_risk_score.
        Returns all tickets with risk score > 0.
        """
        from database.models import db, Ticket, User

        try:
            now = datetime.utcnow()

            open_tickets = Ticket.query.filter(
                Ticket.status.in_(['Open', 'In Progress', 'Escalated'])
            ).all()

            results = []
            for t in open_tickets:
                # Factor 1: time remaining (0 = overdue, 1 = plenty of time)
                total_sla_secs  = (t.sla_deadline - t.feedback.created_at).total_seconds() \
                                  if t.feedback and t.feedback.created_at else 3600
                remaining_secs  = (t.sla_deadline - now).total_seconds()
                time_factor     = max(0, min(1, remaining_secs / max(total_sla_secs, 1)))

                # Factor 2: staff load (0 = no load, 1 = fully loaded)
                staff_load = 0.5
                if t.assigned_user_id:
                    staff = User.query.get(t.assigned_user_id)
                    if staff:
                        staff_load = min(1, staff.active_tasks / 10)

                # Factor 3: severity weight
                sev_map = {'Critical': 1.0, 'High': 0.75, 'Medium': 0.5, 'Low': 0.25}
                sev_w   = sev_map.get(t.severity, 0.5)

                # Composite risk
                risk = (
                    (1 - time_factor) * 0.50 +
                    staff_load        * 0.30 +
                    sev_w             * 0.20
                )
                risk = round(min(1.0, risk), 3)

                t.sla_risk_score = risk
                results.append({
                    'ticket_id':        t.id,
                    'severity':         t.severity,
                    'status':           t.status,
                    'sla_risk_score':   risk,
                    'sla_deadline':     t.sla_deadline.isoformat() + 'Z',
                    'remaining_mins':   round(remaining_secs / 60, 1),
                    'high_risk':        risk >= HIGH_RISK_THRESHOLD,
                    'department':       t.department_rel.name if t.department_rel else '—',
                    'assigned_to':      t.assigned_to_user.name if t.assigned_to_user else 'Unassigned',
                })

            db.session.commit()
            results.sort(key=lambda r: r['sla_risk_score'], reverse=True)
            app_logger.info(f"SLA risk evaluated for {len(results)} tickets")
            return results

        except Exception as e:
            app_logger.error(f"SLARiskService error: {e}")
            db.session.rollback()
            return []


sla_risk_service = SLARiskService()
