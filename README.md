# 🏥 Patient Experience AI Platform

**AI-Driven Patient Experience Analytics & Automated Service Recovery System**

A scalable hospital feedback intelligence platform that analyzes patient feedback using NLP, classifies issues, assigns severity levels, tracks SLAs, and enables automated service recovery workflows.

---

## 🚀 Core Features

### 🧠 AI & NLP Engine

* **Sentiment Analysis** powered by VADER
* **Issue Classification** using TF-IDF + Logistic Regression
* Automatically categorizes feedback into:

  * Billing
  * Wait Time
  * Staff Behavior
  * Cleanliness
  * Infrastructure
  * Others

---

### ⚠️ Severity Scoring Engine

* Rule-based scoring mechanism
* Keyword-based escalation logic
* Combines sentiment + classification + urgency terms
* Automatically determines priority level

---

### 🔄 Automated Service Recovery

* Generates recovery tasks for negative or high-severity feedback
* Assigns workflows based on issue category
* Enables structured complaint resolution

---

### ⏳ SLA Monitoring System

* Tracks resolution deadlines
* Detects SLA breaches
* Escalation-ready logic

---

### 📊 Real-Time Admin Dashboard

* Built with Streamlit
* Interactive visualizations using Plotly
* Displays:

  * Sentiment distribution
  * Department-level insights
  * Severity breakdown
  * Recovery task tracking

---

## 🛠 Installation & Setup

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 2️⃣ Train AI Models

```bash
python scripts/train_model.py
```

This generates trained models stored inside the `data/` directory.

---

### 3️⃣ Run Flask Backend

```bash
python app.py
```

Backend will start on:

```
http://localhost:5000
```

---

### 4️⃣ Run Admin Dashboard (Streamlit)

```bash
streamlit run dashboard/dashboard.py
```

Dashboard will be available at:

```
http://localhost:8501
```

---

## 📁 Project Structure

```
patient-experience-ai/
│
├── app.py                     # Flask application entry point
│
├── backend/                   # API routes and controllers
├── models/                    # NLP, classification, severity logic
├── services/                  # Business logic & SLA workflows
├── database/                  # SQLAlchemy models & DB initialization
├── dashboard/                 # Streamlit admin dashboard
├── data/                      # Trained models & sample datasets
├── scripts/                   # Model training scripts
├── utils/                     # Logging and helper utilities
├── tests/                     # Unit & integration tests
│
└── requirements.txt
```

---

## 📡 API Endpoints

### Submit Feedback

```
POST /api/feedback
```

### List All Feedback

```
GET /api/feedback
```

### List Recovery Tasks

```
GET /api/tasks
```

### Manual SLA Breach Check

```
POST /api/sla/check
```

---

## 🧱 Technology Stack

* **Backend**: Flask
* **Database**: SQLAlchemy (SQLite/PostgreSQL compatible)
* **NLP & ML**: VADER, Scikit-learn
* **Frontend (Admin)**: Streamlit
* **Visualization**: Plotly
* **Model Storage**: Joblib

---

## 🎯 System Architecture

Patient Website → Flask API → AI Processing → Database → Admin Dashboard

---

## 📌 Future Enhancements

* Role-based admin authentication
* Email/SMS notification for SLA breaches
* Advanced deep learning sentiment model
* React-based production admin dashboard
* Deployment via Docker & CI/CD