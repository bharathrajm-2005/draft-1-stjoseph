class AIResponseService:
    def __init__(self):
        pass

    def generate_suggestion(self, ticket, feedback):
        priority = ticket.severity
        issue_type = feedback.issue_type
        patient_name = feedback.patient_id # Fallback if name not present

        base_apology = f"Dear Patient, we sincerely apologize for the experience you had with our {issue_type} services."
        
        if priority == 'Critical':
            return {
                "response": f"{base_apology} This matter has been escalated to our Hospital Operations Director for immediate review. We are treating this with the highest priority and will contact you within the hour.",
                "escalation_note": "CRITICAL: Immediate intervention required. Senior management notified."
            }
        elif priority == 'High':
            return {
                "response": f"{base_apology} We understand your frustration and have assigned a senior consultant to resolve this issue immediately. Expect a follow-up shortly.",
                "escalation_note": "HIGH: Assignment to Department Head recommended if unresolved in 6 hours."
            }
        elif priority == 'Medium':
            return {
                "response": f"{base_apology} Thank you for bringing this to our attention. Our team is investigating the matter and will get back to you with a resolution timeline soon.",
                "escalation_note": "MEDIUM: Standard follow-up scheduled."
            }
        else:
            return {
                "response": f"Dear Patient, thank you for your feedback regarding {issue_type}. We appreciate your input as it helps us improve our services.",
                "escalation_note": "NORMAL: Logged for quality improvement."
            }
