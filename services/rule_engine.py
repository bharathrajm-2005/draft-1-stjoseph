from config import SLA_LEVELS, ISSUE_DEPARTMENTS

class RuleEngine:
    def __init__(self):
        pass

    def determine_sla_and_dept(self, issue_type, severity):
        department = ISSUE_DEPARTMENTS.get(issue_type, 'General Services')
        
        # Mapping severity to SLA hours
        sla_hours = SLA_LEVELS.get(severity, 72)
        
        return department, sla_hours
