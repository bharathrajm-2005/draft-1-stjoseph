# 🏥 CareAxis Medical - Patient Experience AI Platform

**AI-Driven Patient Experience Analytics & Automated Service Recovery System**

A scalable hospital feedback intelligence platform that analyzes patient feedback using NLP, classifies issues, assigns severity levels, tracks SLAs, and enables automated service recovery workflows.

---

## 🚀 Core Features

### 🧠 AI & NLP Engine
*   **Sentiment Analysis**: Powered by **VADER** (Valence Aware Dictionary and sEntiment Reasoner). Analyzes text for Positive, Negative, and Neutral tones.
*   **Issue Classification**: Employs a **Hybrid Classifier** (TF-IDF Vectorization + Logistic Regression) for robust categorization.
*   **Triage System**: Uses keyword-based logic (RegEx) for high-precision emergency detection in appointment descriptions.
*   **Dynamic Response Generation**: AI-assisted response templates based on feedback severity and issue type.

### 🆘 Emergency SOS System (Premium Redesign)
*   **One-Click Dispatch**: High-visibility, primary action button for instant medical assistance.
*   **GPS Precision**: Real-time geolocation tracking with fallback to manual address entry.
*   **Live Feedback**: Visual confirmation and "locating" animations to build trust during emergencies.
*   **Admin Integration**: Direct routing of SOS alerts to the dispatch control center.

### 🔄 Automated Service Recovery (Phases 1-3)
*   **Task Generation**: Automatically creates recovery tasks for all negative or high-severity feedback.
*   **Escalation Logic**: Multi-tier escalation based on severity (Critical, High, Medium, Normal).
*   **SLA Tracking**: Dynamic SLA calculation based on priority and patient verification status.

### 📊 Real-Time Operations Dashboard
*   **Unified Monitoring**: View feedback, SOS alerts, and recovery tasks in a single premium interface.
*   **AJAX Polling**: Real-time updates every 15 seconds without flickering.
*   **Priority Sorting**: Intelligent sorting by urgency (SOS > Critical Feedback > High Priority).

---

## 🧠 AI Models & Processing Logic

| Component | Model / Technology | Purpose |
| :--- | :--- | :--- |
| **Sentiment Analysis** | VADER (NLTK) | Scoring compound emotion in text |
| **Issue Classifier** | Logistic Regression (Scikit-learn) | Categorizing feedback (Staff, Billing, Infrastructure, etc.) |
| **Vectorization** | TF-IDF (Term Frequency-Inverse Document Frequency) | Converting text to numerical features for the ML model |
| **Text Preprocessing** | NLTK (WordNet Lemmatizer + Stopwords) | Tokenization, cleaning, and normalizing text |
| **Emergency Triage** | Regex-based Keyword matching | Identifying life-threatening conditions (Stroke, Trauma, etc.) |

---

## 🛠 Technology Stack & Versions

The platform is built on a modern Python-based micro-architecture:

*   **Core Language**: Python 3.10.11 (AMD64)
*   **Web Framework**: Flask 3.1.3 (Unified Web & API Engine)
*   **Database**: SQLAlchemy 2.0.46 (SQLite)
*   **Data Processing**: Pandas 2.3.3, NumPy 2.2.6
*   **AI/ML Stack**: 
    *   Scikit-learn 1.7.2
    *   NLTK 3.9.2
    *   VaderSentiment (Integrated via NLTK)
*   **Frontend**: Vanilla HTML5, CSS3 (Premium Glassmorphism), ES6+ JavaScript

---

## 📁 Project Structure

```bash
patient-experience-ai/
├── app.py                     # Entry point (Flask App Factory)
├── config.py                  # Environment & Model configurations
├── requirements.txt           # Dependency management
├── database/
│   ├── db.py                  # Database initialization logic
│   └── models.py              # SQLAlchemy Database models (User, Feedback, SOS, Tasks)
├── backend/
│   └── routes.py              # Central API Blueprint
├── models/
│   ├── sentiment_model.py     # VADER Sentiment logic
│   ├── issue_classifier.py    # Hybrid ML Classifier logic
│   └── preprocessing.py       # NLTK-based text cleaning
├── services/
│   ├── recovery_service.py    # AI Pipeline orchestration
│   ├── triage_service.py      # Keyword-based urgency matching
│   └── ai_response_service.py # Smart response template logic
├── static/
│   ├── css/                   # Premium styles (hospital.css, admin.css)
│   └── js/                    # Core logic (hospital.js, admin.js)
├── templates/                 # Glassmorphic UI templates (Patient, Admin, Staff)
├── data/                      # Persistent stores for .pkl models
└── logs/                      # Comprehensive system audit logs
```

---

## � Getting Started

1.  **Environment Setup**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```

2.  **Machine Learning Setup**:
    ```bash
    # Ensure NLTK data is downloaded (handled automatically on first run)
    python scripts/train_model.py  # Optional: Re-train classifier
    ```

3.  **Run Application**:
    ```bash
    python app.py
    ```
    *   Patient Terminal: [http://localhost:5000](http://localhost:5000)
    *   Admin HQ: [http://localhost:5000/admin](http://localhost:5000/admin)

---

## �️ Administrative Access
*   **Admin Dashboard**: `/admin` (SLA tracking, AI analytics, SOS Monitoring)
*   **Staff Dashboard**: `/staff` (Task management, recovery workflows)
*   **Auth**: Role-based access control (RBAC) implemented via Flask-Login.

---
*Created for CareAxis Medical Institute - Aiming for Clinical Excellence through AI Intelligence.*