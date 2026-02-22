-- Database Schema for Patient Experience AI Platform

-- Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(50) NOT NULL,
    feedback_text TEXT NOT NULL,
    sentiment VARCHAR(20),
    sentiment_score FLOAT,
    issue_type VARCHAR(50),
    severity VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Recovery Task Table
CREATE TABLE IF NOT EXISTS recovery_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    department VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'Open',
    sla_deadline DATETIME NOT NULL,
    resolved_at DATETIME,
    escalation_flag BOOLEAN DEFAULT 0,
    FOREIGN KEY (feedback_id) REFERENCES feedback(id)
);
