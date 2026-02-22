import joblib
import os
from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH
from utils.logger import app_logger

class IssueClassifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.load_model()

    def load_model(self):
        try:
            if os.path.exists(CLASSIFIER_MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
                self.model = joblib.load(CLASSIFIER_MODEL_PATH)
                self.vectorizer = joblib.load(VECTORIZER_PATH)
                app_logger.info("Issue classification models loaded successfully.")
            else:
                app_logger.warning("Issue classification models not found. Please run training script.")
        except Exception as e:
            app_logger.error(f"Error loading models: {e}")

    def predict(self, cleaned_text):
        if self.model and self.vectorizer:
            vect_text = self.vectorizer.transform([cleaned_text])
            prediction = self.model.predict(vect_text)[0]
            return prediction
        return "Other"
