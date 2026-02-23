from flask import request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, case
from flask_login import current_user
from services.recovery_service import RecoveryService
from services.sla_tracker import SLATracker
from services.ai_response_service import AIResponseService
from database.models import Feedback, Ticket, Department, User, db, EscalationLog, AIResponseLog
from utils.helpers import format_response
from utils.logger import app_logger
import json

recovery_service = RecoveryService()
sla_tracker = SLATracker()
ai_responder = AIResponseService()

def submit_feedback():
    data = request.get_json()
    if not data or 'patient_id' not in data or 'feedback_text' not in data:
        return jsonify(format_response("error", message="Missing required fields")), 400
    
    try:
        feedback = recovery_service.process_new_feedback(
            data['patient_id'], 
            data['feedback_text'],
            rating=data.get('rating')
        )
        return jsonify(format_response("success", data={
            "id": feedback.id,
            "sentiment": feedback.sentiment,
            "sentiment_score": feedback.sentiment_score,
            "issue_type": feedback.issue_type,
            "severity": feedback.severity
        })), 201
    except Exception as e:
        app_logger.error(f"Error in submit_feedback: {e}")
        return jsonify(format_response("error", message=str(e))), 500

def get_dashboard_stats():
    try:
        active_tickets = Ticket.query.filter(Ticket.status.in_(['Open', 'In Progress', 'Escalated'])).count()
        avg_rating = db.session.query(func.avg(Feedback.rating)).scalar() or 0
        critical_cases = Ticket.query.filter(Ticket.severity == 'Critical').count()
        in_progress_count = Ticket.query.filter(Ticket.status == 'In Progress').count()
        
        dept_counts = db.session.query(Department.name, func.count(Ticket.id)).join(Ticket).filter(Ticket.status != 'Resolved').group_by(Department.name).all()
        
        return jsonify(format_response("success", data={
            "activeTickets": active_tickets,
            "averageRating": round(float(avg_rating), 1),
            "criticalCases": critical_cases,
            "waitTimeAlert": in_progress_count,
            "deptCounts": {d: c for d, c in dept_counts}
        }))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_tickets():
    try:
        query = db.session.query(Ticket).join(Feedback).join(Department)
        status_filter = request.args.get('status')
        if status_filter == 'active':
            query = query.filter(Ticket.status.in_(['Open', 'In Progress', 'Escalated']))
        elif status_filter and status_filter != 'all':
            query = query.filter(Ticket.status == status_filter)
            
        dept_filter = request.args.get('department')
        if dept_filter and dept_filter != 'all':
            query = query.filter(Department.name == dept_filter)

        tickets = query.order_by(
            case((Ticket.status == 'Escalated', 0), else_=1).asc(),
            case((Ticket.severity == 'Critical', 0), (Ticket.severity == 'High', 1), (Ticket.severity == 'Medium', 2), (Ticket.severity == 'Normal', 3), else_=4).asc(),
            Ticket.id.desc()
        ).all()
        
        result = []
        for t in tickets:
            result.append({
                "id": t.id,
                "patient_id": t.feedback.patient_id,
                "department": t.department_rel.name,
                "severity": t.severity,
                "sentiment": t.feedback.sentiment,
                "status": t.status,
                "sla_deadline": t.sla_deadline.isoformat() + "Z",
                "escalation_level": t.escalation_level,
                "created_at": t.feedback.created_at.isoformat() + "Z"
            })
        return jsonify(format_response("success", data=result))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_ticket_details(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404
    
    return jsonify(format_response("success", data={
        "id": ticket.id,
        "patient_id": ticket.feedback.patient_id,
        "department": ticket.department_rel.name,
        "sentiment": ticket.feedback.sentiment,
        "severity": ticket.severity,
        "feedback_text": ticket.feedback.feedback_text,
        "created_at": ticket.feedback.created_at.isoformat() + "Z",
        "status": ticket.status,
        "assigned_staff": ticket.assigned_to_user.name if ticket.assigned_to_user else "Unassigned",
        "assigned_staff_id": ticket.assigned_user_id,
        "internal_notes": ticket.ai_suggested_response, # AI response is internal note now
        "ai_suggested_response": ticket.ai_suggested_response,
        "sla_deadline": ticket.sla_deadline.isoformat() + "Z",
        "escalation_level": ticket.escalation_level,
        "status_history": json.loads(ticket.status_history_log) if ticket.status_history_log else []
    }))

def get_staff_per_dept(dept_name):
    staff_list = User.query.filter_by(department=dept_name, role='staff').all()
    result = []
    for s in staff_list:
        max_tickets = 10
        load_pct = min(100, (s.active_tasks / max_tickets) * 100)
        score = (s.active_tasks * 4) + (s.avg_resolution_time / 10) - (s.performance_rating * 2)
        
        result.append({
            "id": s.id,
            "name": s.name,
            "designation": s.designation,
            "active_tickets": s.active_tasks,
            "avg_res_time": round(s.avg_resolution_time),
            "performance_rating": s.performance_rating,
            "load_pct": round(load_pct),
            "ai_score": round(score, 1)
        })
    result.sort(key=lambda x: x['ai_score'])
    return jsonify(format_response("success", data=result))

def assign_staff(id):
    data = request.get_json()
    user_id = data.get('staff_id')
    
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404

    if ticket.assigned_user_id and ticket.assigned_user_id != user_id:
        old_user = User.query.get(ticket.assigned_user_id)
        if old_user:
            old_user.active_tasks = max(0, old_user.active_tasks - 1)

    user = User.query.get(user_id)
    if not user:
        return jsonify(format_response("error", message="User not found")), 404
    
    try:
        history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
        history.append({
            "status": "In Progress",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": f"Assigned to {user.name}"
        })
        
        ticket.assigned_user_id = user.id
        ticket.status = "In Progress"
        ticket.status_history_log = json.dumps(history)
        user.active_tasks += 1
        
        db.session.commit()
        return jsonify(format_response("success", message="Staff assigned successfully"))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500

def regenerate_response(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404
    
    suggestion = ai_responder.generate_suggestion(ticket, ticket.feedback)
    ticket.ai_suggested_response = suggestion['response']
    
    log = AIResponseLog(ticket_id=ticket.id, draft_content=suggestion['response'], action_taken="Regenerated")
    db.session.add(log)
    db.session.commit()
    
    return jsonify(format_response("success", data={"suggestion": suggestion['response']}))

def approve_response(id):
    data = request.get_json()
    final_content = data.get('response_content')
    
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404
        
    log = AIResponseLog(ticket_id=ticket.id, draft_content=final_content, action_taken="Approved")
    db.session.add(log)
    db.session.commit()
    return jsonify(format_response("success", message="Response approved and sent"))

def resolve_ticket(id):
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404
    
    try:
        now = datetime.utcnow()
        ticket.status = "Resolved"
        ticket.resolved_at = now
        delta = now - ticket.feedback.created_at
        ticket.resolution_time = int(delta.total_seconds() / 60)
        
        history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
        history.append({
            "status": "Resolved",
            "timestamp": now.isoformat() + "Z",
            "action": "Marked as Resolved"
        })
        ticket.status_history_log = json.dumps(history)
        
        if ticket.assigned_to_user:
            ticket.assigned_to_user.active_tasks = max(0, ticket.assigned_to_user.active_tasks - 1)
            
        db.session.commit()
        return jsonify(format_response("success", message="Ticket resolved successfully"))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500

# --- STAFF PORTAL ENDPOINTS ---

def get_staff_profile():
    user = current_user
    max_tickets = 10
    load_pct = min(100, (user.active_tasks / max_tickets) * 100)
    
    return jsonify(format_response("success", data={
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "designation": user.designation,
        "active_tasks": user.active_tasks,
        "avg_res_time": round(user.avg_resolution_time),
        "success_rate": user.performance_rating,
        "load_pct": round(load_pct)
    }))

def get_staff_tasks():
    # Return any active task assigned to the current user (Open or In Progress)
    tickets = Ticket.query.filter(
        Ticket.assigned_user_id == current_user.id,
        Ticket.status.in_(['Open', 'In Progress', 'Escalated'])
    ).order_by(Ticket.sla_deadline.asc()).all()
    
    result = []
    for t in tickets:
        result.append({
            "id": t.id,
            "feedback_id": t.feedback_id,
            "patient_id": t.feedback.patient_id,
            "feedback_text": t.feedback.feedback_text,
            "severity": t.severity,
            "status": t.status,
            "sentiment": t.feedback.sentiment,
            "sla_deadline": t.sla_deadline.isoformat() + "Z",
            "ai_suggestion": t.ai_suggested_response
        })
    return jsonify(format_response("success", data=result))

def complete_staff_task(id):
    try:
        data = request.get_json(force=True, silent=True) or {}
        notes = data.get('notes', '').strip()
        
        ticket = Ticket.query.get(id)
        if not ticket:
            return jsonify(format_response("error", message="Ticket not found")), 404
        
        # Allow resolution if ticket is assigned to this user OR if it's unassigned in their department
        if ticket.assigned_user_id is not None and ticket.assigned_user_id != current_user.id:
            app_logger.warning(f"Staff {current_user.id} attempted to resolve ticket {id} assigned to user {ticket.assigned_user_id}")
            return jsonify(format_response("error", message="You are not assigned to this ticket")), 403
        
        if ticket.status == 'Resolved':
            return jsonify(format_response("error", message="Ticket is already resolved")), 400
        
        now = datetime.utcnow()
        ticket.status = "Resolved"
        ticket.resolved_at = now
        ticket.resolution_notes = notes
        
        # Assign to this user if not already assigned
        if ticket.assigned_user_id is None:
            ticket.assigned_user_id = current_user.id
        
        delta = now - ticket.feedback.created_at
        ticket.resolution_time = int(delta.total_seconds() / 60)
        
        history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
        history.append({
            "status": "Resolved",
            "timestamp": now.isoformat() + "Z",
            "action": f"Resolved by {current_user.name}",
            "notes": notes
        })
        ticket.status_history_log = json.dumps(history)
        
        # Decrement current user's active task count
        staff_user = User.query.get(current_user.id)
        if staff_user:
            staff_user.active_tasks = max(0, staff_user.active_tasks - 1)
        
        db.session.commit()
        app_logger.info(f"Ticket {id} resolved by staff user {current_user.id} ({current_user.name})")
        return jsonify(format_response("success", message="Ticket resolved successfully", data={"ticket_id": id}))
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error resolving ticket {id}: {e}")
        return jsonify(format_response("error", message=str(e))), 500

# --- OTHER ENDPOINTS ---

def get_department_performance():
    try:
        departments = Department.query.all()
        performance = []
        for dept in departments:
            total_tickets = Ticket.query.filter_by(department_id=dept.id).count()
            resolved_tickets = Ticket.query.filter_by(department_id=dept.id, status='Resolved').all()
            avg_res_time = sum([t.resolution_time for t in resolved_tickets]) / len(resolved_tickets) if resolved_tickets else 0
            sla_breaches = Ticket.query.filter_by(department_id=dept.id, escalation_flag=True).count()
            
            staff_in_dept = User.query.filter_by(department=dept.name, role='staff').all()
            
            performance.append({
                "department": dept.name,
                "totalTickets": total_tickets,
                "avgResolutionTime": round(avg_res_time, 1),
                "slaBreachPct": round((sla_breaches / total_tickets * 100) if total_tickets > 0 else 0, 1),
                "staffLoad": [{"name": s.name, "active": s.active_tasks, "load": round(min(100, (s.active_tasks/10)*100))} for s in staff_in_dept]
            })
        return jsonify(format_response("success", data=performance))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_heatmap_data():
    try:
        heatmap_raw = db.session.query(
            Department.name,
            func.strftime('%H', Feedback.created_at).label('hour'),
            func.count(Ticket.id).label('count')
        ).join(Ticket, Department.id == Ticket.department_id).join(Feedback, Ticket.feedback_id == Feedback.id).group_by(Department.name, 'hour').all()
        return jsonify(format_response("success", data=[{"department": d, "hour": int(h), "count": c} for d, h, c in heatmap_raw]))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_incident_trend():
    try:
        trend_raw = db.session.query(func.date(Feedback.created_at).label('date'), func.count(Ticket.id).label('count')).join(Ticket, Feedback.id == Ticket.feedback_id).group_by('date').order_by('date').all()
        return jsonify(format_response("success", data=[{"date": d, "count": c} for d, c in trend_raw]))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def check_sla():
    sla_tracker.check_breaches()
    return jsonify(format_response("success", message="SLA Check Complete"))
