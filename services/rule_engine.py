from config import SLA_LEVELS, ISSUE_DEPARTMENTS

class RuleEngine:
    def __init__(self):
        pass

    def determine_sla_and_dept(self, issue_type, severity):
        department = ISSUE_DEPARTMENTS.get(issue_type, 'Administration')
        
        # Mapping severity to SLA minutes
        sla_mins = SLA_LEVELS.get(severity, 4320) # Default to 4320 mins (72h)
        
        return department, sla_mins
