# 🏥 Patient Experience AI Platform

**AI-Driven Patient Experience Analytics & Automated Service Recovery System**

A scalable hospital feedback intelligence platform that analyzes patient feedback using NLP, classifies issues, assigns severity levels, tracks SLAs, and enables automated service recovery workflows.

---

## 🚀 Core Features

### 🧠 AI & NLP Engine
* **Sentiment Analysis** powered by VADER.
* **Issue Classification** using TF-IDF + Logistic Regression.
* Automatically categorizes feedback into: Billing, Wait Time, Staff Behavior, Cleanliness, Infrastructure, and others.

### ⚠️ Severity Scoring Engine
* Rule-based scoring mechanism.
* Keyword-based escalation logic.
* Combines sentiment + classification + urgency terms to determine priority level.

### 🔄 Automated Service Recovery
* Generates recovery tasks for negative or high-severity feedback.
* Assigns workflows based on issue category.
* Enables structured complaint resolution.

### ⏳ SLA Monitoring System
* Tracks resolution deadlines.
* Detects SLA breaches with escalation-ready logic.

### 📊 Real-Time Admin Dashboard
* **Native HTML/JS Dashboard**: High-performance, flicker-free interface served by Flask.
* **AJAX Polling**: Updates data smoothly every 10 seconds without page reloads.
* **Priority Sorting**: Intelligent sorting by Status (Open > In Progress), Sentiment (Neg > Neu > Pos), and Recency.
* **Dynamic Filtering**: Real-time filtering by Department, Sentiment, and Status.

---

## 🛠 Installation & Setup

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Train AI Models
```bash
python scripts/train_model.py
```
This generates trained models stored inside the `data/` directory.

### 3️⃣ Start the Integrated Platform
```bash
python app.py
```
Both the Patient Website and Admin Dashboard are now unified under one command.

*   **Patient Website**: [http://localhost:5000/](http://localhost:5000/)
*   **Admin Dashboard**: [http://localhost:5000/admin](http://localhost:5000/admin)

---

## 📁 Project Structure

```
patient-experience-ai/
│
├── app.py                     # Flask application entry point
├── templates/                 # HTML Templates (Patient & Admin)
├── static/                    # CSS/JS Assets (Smooth UI logic)
├── backend/                   # API routes and controllers
├── models/                    # NLP, classification, severity logic
├── services/                  # Business logic & SLA workflows
├── database/                  # SQLAlchemy models & DB initialization
├── data/                      # Trained models & sample datasets
├── scripts/                   # Model training scripts
├── utils/                     # Logging and helper utilities
├── tests/                     # Unit & integration tests
└── requirements.txt
```

---

## 📡 Key API Endpoints

### Submit Feedback
`POST /api/submit-feedback`

### Get Feedback List
`GET /api/get-feedback`

### Manage Recovery Tasks
`GET /api/tasks`
`PATCH /api/tasks/<id>` (Status Updates)

### Manual SLA Breach Check
`POST /api/sla/check`

---

## 🧱 Technology Stack
* **Backend**: Flask (Unified API & Web Server)
* **Database**: SQLAlchemy (SQLite)
* **NLP & ML**: VADER, Scikit-learn
* **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+)
* **Architecture**: RESTful API + AJAX Polling

---

## 🎯 System Architecture
Patient Website → Flask API → AI Processing → Database → Admin Dashboard (Unified Flask App)

---

## 📌 Future Enhancements
* Role-based admin authentication.
* Email/SMS notification for SLA breaches.
* Advanced deep learning sentiment models.
* Real-time WebSocket integration.
* Deployment via Docker & CI/CD.