"""
Driver Efficiency Scoring Service — rates drivers on response time, 
completion rate, and reassignment frequency (0–100).
"""
from utils.logger import app_logger


class DriverScoringService:
    def score_all(self):
        """
        Computes efficiency score for every driver user.
        Persists score to User.driver_efficiency_score.
        Returns ranked list.
        """
        from database.models import db, User, EmergencyRequest

        try:
            drivers = [u for u in User.query.filter_by(role='staff').all()
                       if (u.designation or '').lower().startswith('driver')]

            results = []
            for driver in drivers:
                missions = EmergencyRequest.query.filter_by(
                    assigned_driver_id=driver.id
                ).all()

                total = len(missions)
                if total == 0:
                    score = 50.0  # neutral default
                    results.append({
                        'id': driver.id, 'name': driver.name,
                        'department': driver.department or '—',
                        'score': score,
                        'total_missions': 0,
                        'avg_response_mins': None,
                        'completion_rate': None,
                    })
                    driver.driver_efficiency_score = score
                    continue

                # Avg response time (dispatch → accept)
                response_times = []
                for m in missions:
                    if m.driver_response_time is not None:
                        response_times.append(m.driver_response_time / 60)  # to minutes
                    elif m.accepted_at and m.created_at:
                        secs = (m.accepted_at - m.created_at).total_seconds()
                        response_times.append(secs / 60)

                avg_resp = (sum(response_times) / len(response_times)
                            if response_times else 10)

                # Completion rate
                completed   = [m for m in missions if m.status == 'Completed']
                comp_rate   = (len(completed) / total) * 100

                # Reassignment penalty (assume 0 for now — no reassignment field)
                reassign_rate = 0.0

                # Normalise response time: 0 min = 100, 30 min = 0
                resp_score  = max(0, min(100, (30 - avg_resp) / 0.30))

                composite = (
                    resp_score    * 0.40 +
                    comp_rate     * 0.40 +
                    (100 - reassign_rate) * 0.20
                )
                composite = round(composite, 1)
                driver.driver_efficiency_score = composite

                results.append({
                    'id':                driver.id,
                    'name':              driver.name,
                    'department':        driver.department or '—',
                    'score':             composite,
                    'total_missions':    total,
                    'avg_response_mins': round(avg_resp, 1),
                    'completion_rate':   round(comp_rate, 1),
                })

            db.session.commit()
            results.sort(key=lambda d: d['score'], reverse=True)
            app_logger.info(f"Driver scores computed: {len(results)} drivers")
            return results

        except Exception as e:
            app_logger.error(f"DriverScoringService error: {e}")
            db.session.rollback()
            return []


driver_scoring_service = DriverScoringService()
