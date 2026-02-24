"""
Doctor Performance Intelligence Service — scores doctors on 4 dimensions (0–100).
"""
from utils.logger import app_logger


class DoctorPerformanceService:
    def score_all(self):
        """
        Computes AI performance score for every staff doctor.
        Persists score to User.doctor_performance_score.
        Returns sorted list of doctor dicts.
        """
        from database.models import db, User, Appointment, Ticket, Feedback

        try:
            doctors = User.query.filter_by(role='staff').all()
            results = []

            for doc in doctors:
                # Skip drivers
                if (doc.designation or '').lower().startswith('driver'):
                    continue

                # 1. Completion speed (inverted — faster = higher sub-score)
                completed = Appointment.query.filter_by(
                    doctor_id=doc.id, status='Completed'
                ).all()
                if completed:
                    durations = []
                    for a in completed:
                        if a.completed_at and a.created_at:
                            mins = (a.completed_at - a.created_at).total_seconds() / 60
                            durations.append(mins)
                    avg_mins = sum(durations) / len(durations) if durations else 60
                else:
                    avg_mins = 60  # assume 60 mins if no data

                # Normalise: 10 min = 100, 120 min = 0
                speed_score = max(0, min(100, (120 - avg_mins) / 1.1))

                # 2. Verified patient satisfaction (avg rating from verified feedback)
                appt_ids = [a.id for a in completed]
                verified_fb = (Feedback.query
                               .filter(Feedback.appointment_id.in_(appt_ids),
                                       Feedback.is_verified == True)
                               .all()) if appt_ids else []
                if verified_fb:
                    avg_rating   = sum(f.rating or 3 for f in verified_fb) / len(verified_fb)
                    satisfaction = (avg_rating / 5) * 100
                else:
                    satisfaction = 50.0  # neutral default

                # 3. SLA compliance (tickets resolved before deadline)
                my_tickets = Ticket.query.filter_by(assigned_user_id=doc.id).all()
                if my_tickets:
                    compliant   = [t for t in my_tickets
                                   if t.resolved_at and t.sla_deadline
                                   and t.resolved_at <= t.sla_deadline]
                    sla_score   = (len(compliant) / len(my_tickets)) * 100
                else:
                    sla_score = 75.0

                # 4. Emergency contribution (normalised 0–100 for display)
                emergency_count = Appointment.query.filter_by(
                    doctor_id=doc.id, appointment_type='Emergency'
                ).count()
                emergency_score = min(100, emergency_count * 10)

                # Weighted composite
                composite = (
                    speed_score    * 0.25 +
                    satisfaction   * 0.35 +
                    sla_score      * 0.25 +
                    emergency_score * 0.15
                )
                composite = round(composite, 1)

                doc.doctor_performance_score = composite
                results.append({
                    'id':          doc.id,
                    'name':        doc.name,
                    'department':  doc.department or '—',
                    'designation': doc.designation or 'Doctor',
                    'score':       composite,
                    'speed':       round(speed_score, 1),
                    'satisfaction': round(satisfaction, 1),
                    'sla_compliance': round(sla_score, 1),
                    'emergency_contribution': round(emergency_score, 1),
                    'appointments_completed': len(completed),
                })

            db.session.commit()
            results.sort(key=lambda d: d['score'], reverse=True)
            app_logger.info(f"Doctor performance scored: {len(results)} doctors")
            return results

        except Exception as e:
            app_logger.error(f"DoctorPerformanceService error: {e}")
            db.session.rollback()
            return []


doctor_performance_service = DoctorPerformanceService()
