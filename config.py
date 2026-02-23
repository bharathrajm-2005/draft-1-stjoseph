import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Flask configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR / "database" / "patient_experience.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Model paths
MODEL_DIR = BASE_DIR / "data"
SENTIMENT_MODEL_PATH = MODEL_DIR / "sentiment_vader.pkl"
CLASSIFIER_MODEL_PATH = MODEL_DIR / "trained_classifier.pkl"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.pkl"

# SLA Settings (in minutes)
SLA_LEVELS = {
    'Critical': 360,  # 6h
    'High': 360,      # 6h
    'Medium': 720,    # 12h
    'Normal': 4320    # 72h
}

# Department assignments
ISSUE_DEPARTMENTS = {
    'Billing': 'Billing',
    'Waiting Time': 'Administration',
    'Staff Behavior': 'Administration',
    'Clinical Quality': 'General Medicine',
    'Facility': 'General Medicine',
    'Emergency': 'Emergency',
    'Other': 'Administration'
}
