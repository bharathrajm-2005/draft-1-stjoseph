import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from models.preprocessing import Preprocessor
from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH, MODEL_DIR

def train_basic_model():
    # Sample training data
    data = {
        'text': [
            'The bill was much higher than expected.',
            'I waited for three hours to see a doctor.',
            'Wait times are absolutely ridiculous here.',
            'The nurse was very rude to my family.',
            'Staff behavior was unprofessional.',
            'The doctor explained everything clearly but wait was long.',
            'Incorrect billing for the laboratory tests.',
            'The facility was not clean.',
            'The room was very dirty and smelled bad.',
            'Medical quality was excellent, but administrative staff was poor.',
            'Excellent surgery, very professional clinical team.',
            'The receptionist refused to help me with the form.'
        ],
        'category': [
            'Billing', 'Waiting Time', 'Waiting Time', 'Staff Behavior',
            'Staff Behavior', 'Waiting Time', 'Billing', 'Facility',
            'Facility', 'Clinical Quality', 'Clinical Quality', 'Staff Behavior'
        ]
    }
    
    df = pd.DataFrame(data)
    preprocessor = Preprocessor()
    
    app_logger_print("Preprocessing training data...")
    df['cleaned'] = df['text'].apply(preprocessor.clean_text)
    
    # Vectorization
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df['cleaned'])
    y = df['category']
    
    # Model training
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    
    # Create directory if not exists
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save models
    joblib.dump(model, CLASSIFIER_MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    
    # Save sample CSV for demo
    sample_csv_path = MODEL_DIR / "sample_feedback.csv"
    df.to_csv(sample_csv_path, index=False)
    
    print(f"Models trained and saved to {MODEL_DIR}")

def app_logger_print(msg):
    print(f"TRAINING: {msg}")

if __name__ == "__main__":
    train_basic_model()
