"""
Appointment Load Forecast Service — predicts next-N-days appointment volume
per department using linear regression on historical data.
"""
from datetime import datetime, timedelta
from utils.logger import app_logger


class ForecastService:
    def forecast_next_days(self, horizon_days=7):
        """
        Predicts appointment counts for the next `horizon_days` days.
        Stores results in AppointmentForecast table.
        Returns list of forecast dicts.
        """
        from database.models import db, Appointment, Department, AppointmentForecast

        try:
            # Pull historical appointments grouped by date + department
            all_appts = Appointment.query.all()
            if not all_appts:
                return []

            from collections import defaultdict
            dept_daily = defaultdict(lambda: defaultdict(int))
            dept_hours = defaultdict(list)

            for a in all_appts:
                date_str = a.appointment_date[:10] if a.appointment_date else None
                if not date_str:
                    continue
                dept_daily[a.department.name][date_str] += 1
                # Extract hour from time_slot like "10:00 AM"
                try:
                    ts = a.time_slot.strip()
                    if ':' in ts:
                        h = int(ts.split(':')[0])
                        if 'PM' in ts.upper() and h != 12:
                            h += 12
                        elif 'AM' in ts.upper() and h == 12:
                            h = 0
                        dept_hours[a.department.name].append(h)
                except Exception:
                    pass

            results = []
            today   = datetime.utcnow().date()

            for dept in Department.query.all():
                dname    = dept.name
                day_map  = dept_daily.get(dname, {})

                if not day_map:
                    # No history — use conservative estimate
                    predicted = 2
                    peak_hour = 10
                else:
                    # Simple linear regression on sorted daily counts
                    sorted_counts = sorted(day_map.values())
                    n = len(sorted_counts)
                    if n >= 3:
                        try:
                            import numpy as np
                            x = np.arange(n).reshape(-1, 1)
                            y = np.array(sorted_counts)
                            m = np.polyfit(x.flatten(), y, 1)
                            predicted = max(0, int(m[0] * n + m[1]))
                        except Exception:
                            predicted = int(sum(sorted_counts) / n)
                    else:
                        predicted = int(sum(sorted_counts) / n)

                    # Peak hour = mode
                    hours = dept_hours.get(dname, [])
                    if hours:
                        from collections import Counter
                        peak_hour = Counter(hours).most_common(1)[0][0]
                    else:
                        peak_hour = 10

                # Risk level
                if predicted >= 15:
                    risk = 'HIGH'
                elif predicted >= 8:
                    risk = 'MODERATE'
                else:
                    risk = 'LOW'

                for day_offset in range(1, horizon_days + 1):
                    fdate = (today + timedelta(days=day_offset)).strftime('%Y-%m-%d')

                    # Upsert
                    existing = AppointmentForecast.query.filter_by(
                        forecast_date=fdate, department=dname
                    ).first()
                    if existing:
                        existing.predicted_count = predicted
                        existing.peak_hour       = peak_hour
                        existing.risk_level      = risk
                    else:
                        db.session.add(AppointmentForecast(
                            forecast_date   = fdate,
                            department      = dname,
                            predicted_count = predicted,
                            peak_hour       = peak_hour,
                            risk_level      = risk,
                        ))

                    results.append({
                        'date':      fdate,
                        'department': dname,
                        'predicted': predicted,
                        'peak_hour': peak_hour,
                        'risk':      risk,
                    })

            db.session.commit()
            app_logger.info(f"Forecast generated: {len(results)} dept-day entries")
            return results

        except Exception as e:
            app_logger.error(f"ForecastService error: {e}")
            db.session.rollback()
            return []


forecast_service = ForecastService()
