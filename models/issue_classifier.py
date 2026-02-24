import joblib
import os
import re
from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH
from utils.logger import app_logger

class IssueClassifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.load_model()
        
        # Keyword mappings for hybrid fallback
        self.category_keywords = {
            "Clinical Issue": ["pain", "diagnosis", "treatment", "wrong medicine", "prescription", "doctor", "nurse", "surgery", "medication"],
            "Billing": ["invoice", "charge", "bill", "payment", "excess", "refund", "insurance", "cost", "price"],
            "Infrastructure": ["cleanliness", "room", "equipment", "maintenance", "broken", "ac", "bed", "toilet", "wifi"],
            "Staff Behavior": ["rude", "unprofessional", "ignored", "attitude", "disrespect", "receptionist", "waiting"],
            "Emergency Care": ["ambulance", "emergency", "sos", "response time", "critical", "delay", "trauma", "accident"]
        }

    def load_model(self):
        try:
            if os.path.exists(CLASSIFIER_MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
                self.model = joblib.load(CLASSIFIER_MODEL_PATH)
                self.vectorizer = joblib.load(VECTORIZER_PATH)
                app_logger.info("Issue classification models loaded successfully. (Phase 2 Hybrid)")
            else:
                app_logger.warning("Issue classification models not found. Falling back to keyword-based hybrid logic.")
        except Exception as e:
            app_logger.error(f"Error loading models: {e}")

    def predict(self, cleaned_text):
        """Standard ML prediction with keyword-boost fallback"""
        if self.model and self.vectorizer:
            try:
                vect_text = self.vectorizer.transform([cleaned_text])
                prediction = self.model.predict(vect_text)[0]
                return prediction
            except Exception:
                pass
        
        # Fallback to simple keyword logic
        text_lower = cleaned_text.lower()
        for category, keywords in self.category_keywords.items():
            if any(k in text_lower for k in keywords):
                return category
                
        return "General"

    def categorize(self, text):
        """Phase 2 Hybrid Categorization: Always returns one of the 5 key categories if possible."""
        text_lower = text.lower()
        
        # 1. Direct Keyword Scan (High Precision)
        for category, keywords in self.category_keywords.items():
            if any(re.search(r'\b' + re.escape(k) + r'\b', text_lower) for k in keywords):
                return category
        
        # 2. ML Prediction (Contextual)
        if self.model and self.vectorizer:
            try:
                vect_text = self.vectorizer.transform([text])
                prediction = self.model.predict(vect_text)[0]
                # Map generic ML output to one of the target categories if possible
                if prediction in self.category_keywords:
                    return prediction
            except Exception:
                pass
        
        # 3. Default
        return "General Hospital Operations"
