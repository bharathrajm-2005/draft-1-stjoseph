from flask import request, jsonify
from datetime import datetime
from services.recovery_service import RecoveryService
from services.sla_tracker import SLATracker
from database.models import Feedback, RecoveryTask, db
from utils.helpers import format_response
from utils.logger import app_logger

recovery_service = RecoveryService()
sla_tracker = SLATracker()

def submit_feedback():
    data = request.get_json()
    if not data or 'patient_id' not in data or 'feedback_text' not in data:
        return jsonify(format_response("error", message="Missing required fields")), 400
    
    try:
        feedback = recovery_service.process_new_feedback(
            data['patient_id'], 
            data['feedback_text']
        )
        return jsonify(format_response("success", data={
            "id": feedback.id,
            "sentiment": feedback.sentiment,
            "sentiment_score": feedback.sentiment_score,
            "issue_type": feedback.issue_type,
            "severity": feedback.severity
        })), 201
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_feedback_list():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    result = [{
        "id": f.id,
        "patient_id": f.patient_id,
        "feedback_text": f.feedback_text,
        "sentiment": f.sentiment,
        "sentiment_score": f.sentiment_score,
        "issue_type": f.issue_type,
        "severity": f.severity,
        "created_at": f.created_at.isoformat()
    } for f in feedbacks]
    return jsonify(format_response("success", data=result))

def get_recovery_tasks():
    tasks = RecoveryTask.query.all()
    result = [{
        "id": t.id,
        "feedback_id": t.feedback_id,
        "department": t.department,
        "status": t.status,
        "sla_deadline": t.sla_deadline.isoformat(),
        "escalation_flag": t.escalation_flag
    } for t in tasks]
    return jsonify(format_response("success", data=result))

def check_sla():
    breaches = sla_tracker.check_breaches()
    return jsonify(format_response("success", data={"breaches_found": breaches}))

def update_task_status(id):
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify(format_response("error", message="Missing status field")), 400
    
    task = RecoveryTask.query.get(id)
    if not task:
        return jsonify(format_response("error", message="Task not found")), 404
    
    try:
        task.status = data['status']
        if data['status'] == 'Resolved':
            task.resolved_at = datetime.utcnow()
        
        db.session.commit()
        app_logger.info(f"Task ID {id} status updated to {data['status']}")
        return jsonify(format_response("success", data={
            "id": task.id,
            "status": task.status,
            "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None
        }))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500
