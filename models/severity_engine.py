class SeverityEngine:
    def __init__(self):
        # Keywords that indicate high severity
        self.critical_keywords = ['malpractice', 'lawsuit', 'legal', 'injury', 'severe case', 'emergency', 'heart attack', 'bleeding']
        self.high_keywords = ['angry', 'refused', 'unacceptable', 'terrible', 'wrong medication', 'infection']

    def calculate_severity(self, feedback_text, sentiment_score):
        text_lower = feedback_text.lower()
        
        # Check for critical keywords
        if any(keyword in text_lower for keyword in self.critical_keywords):
            return "Critical"
        
        # Check for high severity indicators
        if any(keyword in text_lower for keyword in self.high_keywords) or sentiment_score < -0.6:
            return "High"
        
        if sentiment_score < -0.3:
            return "Medium"
        
        return "Low"
