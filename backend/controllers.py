from flask import request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, case
from services.recovery_service import RecoveryService
from services.sla_tracker import SLATracker
from services.ai_response_service import AIResponseService
from database.models import Feedback, Ticket, Department, Staff, db, EscalationLog, AIResponseLog
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
        
        # Dept-wise counts
        dept_counts = db.session.query(Department.name, func.count(Ticket.id)).join(Ticket).filter(Ticket.status != 'Resolved').group_by(Department.name).all()
        
        return jsonify(format_response("success", data={
            "activeTickets": active_tickets,
            "averageRating": round(float(avg_rating), 1),
            "criticalCases": critical_cases,
            "waitTimeAlert": in_progress_count, # Mapped to "In Progress" in UI
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
        "assigned_staff": ticket.assigned_staff.name if ticket.assigned_staff else "Unassigned",
        "assigned_staff_id": ticket.assigned_staff_id,
        "internal_notes": ticket.internal_notes,
        "ai_suggested_response": ticket.ai_suggested_response,
        "sla_deadline": ticket.sla_deadline.isoformat() + "Z",
        "escalation_level": ticket.escalation_level,
        "status_history": json.loads(ticket.status_history_log) if ticket.status_history_log else []
    }))

def get_staff_per_dept(dept_name):
    dept = Department.query.filter_by(name=dept_name).first()
    if not dept:
        return jsonify(format_response("error", message="Department not found")), 404
    
    staff_list = Staff.query.filter_by(department_id=dept.id).all()
    result = []
    for s in staff_list:
        # Load Meter Rules: (activeTickets / maxTicketsPerStaff) × 100
        max_tickets = 10
        load_pct = min(100, (s.active_ticket_count / max_tickets) * 100)
        
        # Hybrid Scoring for suggestion explanation
        score = (s.active_ticket_count * 3) + (s.avg_resolution_time * 1.5) - (s.performance_rating * 2)
        
        result.append({
            "id": s.id,
            "name": s.name,
            "designation": s.designation,
            "active_tickets": s.active_ticket_count,
            "avg_res_time": round(s.avg_resolution_time),
            "performance_rating": s.performance_rating,
            "load_pct": round(load_pct),
            "ai_score": round(score, 1)
        })
    
    # Sort by AI score to show best suggestions first
    result.sort(key=lambda x: x['ai_score'])
    return jsonify(format_response("success", data=result))

def assign_staff(id):
    data = request.get_json()
    staff_id = data.get('staff_id')
    notes = data.get('notes')
    
    ticket = Ticket.query.get(id)
    if not ticket:
        return jsonify(format_response("error", message="Ticket not found")), 404

    # Handle unassigning old staff if any
    if ticket.assigned_staff_id and ticket.assigned_staff_id != staff_id:
        old_staff = Staff.query.get(ticket.assigned_staff_id)
        if old_staff:
            old_staff.active_ticket_count = max(0, old_staff.active_ticket_count - 1)

    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify(format_response("error", message="Staff not found")), 404
    
    try:
        history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
        history.append({
            "status": "In Progress",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": f"Assigned to {staff.name} (Admin Override)" if ticket.assigned_staff_id else f"Assigned to {staff.name}"
        })
        
        ticket.assigned_staff_id = staff.id
        ticket.status = "In Progress"
        ticket.internal_notes = notes
        ticket.status_history_log = json.dumps(history)
        staff.active_ticket_count += 1
        
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
    
    # Log regeneration
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
    
    # In a real app, send actual email/SMS here
    app_logger.info(f"Response approved for ticket {id}: {final_content[:50]}...")
    
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
            "action": "Marked as Resolved by Admin"
        })
        ticket.status_history_log = json.dumps(history)
        
        if ticket.assigned_staff:
            ticket.assigned_staff.active_ticket_count = max(0, ticket.assigned_staff.active_ticket_count - 1)
            
        db.session.commit()
        return jsonify(format_response("success", message="Ticket resolved successfully"))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500

def get_department_performance():
    try:
        departments = Department.query.all()
        performance = []
        for dept in departments:
            total_tickets = Ticket.query.filter_by(department_id=dept.id).count()
            resolved_tickets = Ticket.query.filter_by(department_id=dept.id, status='Resolved').all()
            avg_res_time = sum([t.resolution_time for t in resolved_tickets]) / len(resolved_tickets) if resolved_tickets else 0
            sla_breaches = Ticket.query.filter_by(department_id=dept.id, escalation_flag=True).count()
            
            performance.append({
                "department": dept.name,
                "totalTickets": total_tickets,
                "avgResolutionTime": round(avg_res_time, 1),
                "slaBreachPct": round((sla_breaches / total_tickets * 100) if total_tickets > 0 else 0, 1),
                "staffLoad": [{"name": s.name, "active": s.active_ticket_count, "load": round(min(100, (s.active_ticket_count/10)*100))} for s in dept.staff]
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
