from utils.logger import app_logger
import re

class TriageService:
    def __init__(self):
        # High impact keywords for Emergency
        self.emergency_keywords = [
            'chest pain', 'bleeding', 'unconscious', 'accident', 
            'stroke', 'heart attack', 'respiratory', 'trauma',
            'poisoning', 'seizure', 'burning'
        ]
        
        # Urgent keywords
        self.urgent_keywords = [
            'fever', 'fracture', 'severe pain', 'dehydration',
            'infection', 'deep cut', 'blurred vision'
        ]

    def classify_appointment(self, patient_description):
        if not patient_description:
            return "Normal"
            
        text = patient_description.lower()
        
        # 1. Check for Emergency keywords
        for kw in self.emergency_keywords:
            if re.search(r'\b' + kw + r'\b', text):
                app_logger.info(f"Triage: Emergency detected via keyword '{kw}'")
                return "Emergency"
                
        # 2. Check for Urgent keywords
        for kw in self.urgent_keywords:
            if re.search(r'\b' + kw + r'\b', text):
                app_logger.info(f"Triage: Urgent detected via keyword '{kw}'")
                return "Urgent"
                
        # 3. Default to Normal
        return "Normal"

    def calculate_dynamic_sla(self, appt_type, is_verified=False, is_anonymous=False):
        # Base SLA in minutes
        # Low: 4h (240m), Medium: 2h (120m), High: 1h (60m), Emergency: 30m
        base_sla_map = {
            "Emergency": 30,
            "Urgent": 60,
            "Urgent-M": 120, # Placeholder for "Medium"
            "Normal": 240
        }
        
        # Map our types to the requested SLA levels
        # Normal -> Low (4h)
        # Urgent -> High (1h)
        # Emergency -> Emergency (30m)
        
        base_sla = 240 # Default to 4h
        if appt_type == "Emergency":
            base_sla = 30
        elif appt_type == "Urgent":
            base_sla = 60
        elif appt_type == "Normal":
            base_sla = 240
            
        # Adjustments
        if is_verified:
            # Boost priority (20% reduction in time)
            base_sla = int(base_sla * 0.8)
        elif is_anonymous:
            # Anonymous penalty (20% increase in time)
            base_sla = int(base_sla * 1.2)
            
        return base_sla
