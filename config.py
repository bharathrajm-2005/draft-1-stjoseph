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

# SLA Settings (in hours)
SLA_LEVELS = {
    'Critical': 4,
    'High': 24,
    'Medium': 48,
    'Low': 72
}

# Department assignments
ISSUE_DEPARTMENTS = {
    'Billing': 'Finance',
    'Waiting Time': 'Front Desk',
    'Staff Behavior': 'HR',
    'Clinical Quality': 'Medical',
    'Facility': 'Maintenance',
    'Other': 'General Services'
}
