"""
Department Risk Service — calculates complaint density risk per department.
Returns GREEN / AMBER / RED indicator.
"""
from utils.logger import app_logger


class DepartmentRiskService:
    def evaluate(self):
        """
        Calculates risk score per department.
        Returns list of {department, risk_score, risk_level, open_tickets,
        sla_breaches, critical_tickets}
        """
        from database.models import Ticket, Department

        try:
            results = []
            departments = Department.query.all()

            for dept in departments:
                open_t     = Ticket.query.filter_by(
                    department_id=dept.id
                ).filter(Ticket.status.in_(['Open','In Progress','Escalated'])).count()

                sla_b      = Ticket.query.filter_by(
                    department_id=dept.id, escalation_flag=True
                ).count()

                critical   = Ticket.query.filter_by(
                    department_id=dept.id, severity='Critical'
                ).filter(Ticket.status.in_(['Open','In Progress','Escalated'])).count()

                risk_score = open_t * 3 + sla_b * 5 + critical * 8

                if risk_score >= 50:
                    level = 'RED'
                elif risk_score >= 20:
                    level = 'AMBER'
                else:
                    level = 'GREEN'

                results.append({
                    'department':       dept.name,
                    'risk_score':       risk_score,
                    'risk_level':       level,
                    'open_tickets':     open_t,
                    'sla_breaches':     sla_b,
                    'critical_tickets': critical,
                })

            results.sort(key=lambda d: d['risk_score'], reverse=True)
            app_logger.info(f"Department risk evaluated: {len(results)} depts")
            return results

        except Exception as e:
            app_logger.error(f"DepartmentRiskService error: {e}")
            return []


department_risk_service = DepartmentRiskService()
