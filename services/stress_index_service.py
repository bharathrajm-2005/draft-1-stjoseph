"""
Hospital Stress Index Service — Computes real-time operational stress score.
"""
from datetime import datetime
from utils.logger import app_logger

# Weight constants
W_EMERGENCY    = 20.0
W_SLA_BREACH   = 15.0
W_OPEN_TICKETS =  2.0
W_APPOINTMENTS =  1.0
W_DOCTOR_LOAD  =  0.3

LEVELS = [
    (85, 'CRITICAL'),
    (60, 'HIGH'),
    (30, 'MODERATE'),
    ( 0, 'LOW'),
]


class StressIndexService:
    def compute(self):
        """
        Calculates the Hospital Stress Index and persists a snapshot.
        Returns dict: {score, level, factors, history}
        """
        from database.models import (
            db, Ticket, Appointment, EmergencyRequest,
            StressIndexSnapshot, User
        )

        try:
            active_emerg  = EmergencyRequest.query.filter(
                EmergencyRequest.status.in_(['Pending', 'Dispatched', 'In Transit'])
            ).count()

            active_appts  = Appointment.query.filter(
                Appointment.status.in_(['Scheduled', 'In Progress'])
            ).count()

            open_tickets  = Ticket.query.filter(
                Ticket.status.in_(['Open', 'In Progress', 'Escalated'])
            ).count()

            sla_breaches  = Ticket.query.filter_by(escalation_flag=True).count()

            doctors       = User.query.filter_by(role='staff').all()
            avg_load = 0.0
            if doctors:
                loads    = [min(100, (d.active_appointments / 10) * 100) for d in doctors]
                avg_load = sum(loads) / len(loads)

            score = (
                active_emerg  * W_EMERGENCY    +
                sla_breaches  * W_SLA_BREACH   +
                open_tickets  * W_OPEN_TICKETS +
                active_appts  * W_APPOINTMENTS +
                avg_load      * W_DOCTOR_LOAD
            )
            score = round(min(score, 100), 1)

            level = 'LOW'
            for threshold, lbl in LEVELS:
                if score >= threshold:
                    level = lbl
                    break

            # Persist snapshot (keep only latest 48)
            snap = StressIndexSnapshot(
                stress_score        = score,
                stress_level        = level,
                active_emergencies  = active_emerg,
                active_appointments = active_appts,
                open_tickets        = open_tickets,
                sla_breaches        = sla_breaches,
                avg_doctor_load     = round(avg_load, 1),
            )
            db.session.add(snap)

            count = StressIndexSnapshot.query.count()
            if count > 48:
                old = (StressIndexSnapshot.query
                       .order_by(StressIndexSnapshot.timestamp.asc())
                       .limit(count - 48).all())
                for o in old:
                    db.session.delete(o)

            db.session.commit()

            history = [
                {'time': s.timestamp.strftime('%H:%M'), 'score': s.stress_score}
                for s in StressIndexSnapshot.query
                          .order_by(StressIndexSnapshot.timestamp.asc())
                          .limit(24).all()
            ]

            app_logger.info(f"Stress Index: {score} ({level})")
            return {
                'score':  score,
                'level':  level,
                'factors': {
                    'active_emergencies':  active_emerg,
                    'active_appointments': active_appts,
                    'open_tickets':        open_tickets,
                    'sla_breaches':        sla_breaches,
                    'avg_doctor_load':     round(avg_load, 1),
                },
                'history': history,
            }
        except Exception as e:
            app_logger.error(f"StressIndexService error: {e}")
            return {'score': 0, 'level': 'LOW', 'factors': {}, 'history': []}


stress_index_service = StressIndexService()
