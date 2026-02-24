from flask import request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, case
from flask_login import current_user
from services.recovery_service import RecoveryService
from services.sla_tracker import SLATracker
from services.ai_response_service import AIResponseService
from services.triage_service import TriageService
from services.ambulance_service import AmbulanceService
from services.email_service import send_appointment_confirmation
# Phase 2 AI services
from services.stress_index_service import stress_index_service
from services.doctor_performance_service import doctor_performance_service
from services.forecast_service import forecast_service
from services.sla_risk_service import sla_risk_service
from services.driver_scoring_service import driver_scoring_service
from services.department_risk_service import department_risk_service
from services.repeat_complaint_service import repeat_complaint_service
from services.eta_service import eta_service
from database.models import (Feedback, Ticket, Department, User, Appointment, db,
                              EscalationLog, AIResponseLog, Ambulance,
                              EmergencyDispatch, EmergencyRequest,
                              StressIndexSnapshot, AppointmentForecast)
from utils.helpers import format_response
from utils.logger import app_logger
import json

recovery_service = RecoveryService()
sla_tracker = SLATracker()
ai_responder = AIResponseService()
triage_service = TriageService()
ambulance_service = AmbulanceService()

def submit_feedback():
    data = request.get_json()
    if not data or 'patient_id' not in data or 'feedback_text' not in data:
        return jsonify(format_response("error", message="Missing required fields")), 400
    
    try:
        patient_email = (data.get('email') or '').strip().lower()
        patient_name  = (data.get('name')  or '').strip()
        
        # ── Step 1: AI pipeline – commits its own session internally ──────
        feedback = recovery_service.process_new_feedback(
            data['patient_id'],
            data['feedback_text'],
            rating=data.get('rating')
        )
        feedback_id = feedback.id  # capture id before session expires

        # ── Step 2: Re-query cleanly and enrich with name / email / verified
        feedback = Feedback.query.get(feedback_id)
        feedback.patient_name  = patient_name
        feedback.patient_email = patient_email

        # === VERIFIED FEEDBACK INTELLIGENCE ===
        is_verified        = False
        linked_doctor_name = None

        if patient_email:
            appt = Appointment.query.filter(
                func.lower(Appointment.patient_email) == patient_email,
                Appointment.status == 'Completed'   # ← ONLY completed = verified
            ).order_by(Appointment.created_at.desc()).first()

            if appt:
                is_verified             = True
                feedback.is_verified    = True
                feedback.appointment_id = appt.id
                if appt.doctor:
                    linked_doctor_name = appt.doctor.name

                # === PRIORITY BOOST RULE (MASTER PHASE 1) ===
                ticket = Ticket.query.filter_by(feedback_id=feedback_id).first()
                if ticket:
                    # Determine current base from ticket severity
                    severity_map = {"Critical": "Emergency", "High": "Urgent", "Medium": "Normal", "Low": "Normal"}
                    base_type = severity_map.get(ticket.severity, "Normal")
                    
                    # Calculate boosted SLA
                    sla_mins = triage_service.calculate_dynamic_sla(base_type, is_verified=True)
                    new_deadline = feedback.created_at + timedelta(minutes=sla_mins)
                    ticket.sla_deadline = new_deadline

                    history = json.loads(ticket.status_history_log) if ticket.status_history_log else []
                    
                    # Re-assign ticket to appointing doctor if they are staff
                    if appt.doctor_id:
                        doctor = User.query.get(appt.doctor_id)
                        if doctor and doctor.role == 'staff':
                            if ticket.assigned_user_id != doctor.id:
                                if ticket.assigned_user_id:
                                    old = User.query.get(ticket.assigned_user_id)
                                    if old:
                                        old.active_tasks = max(0, old.active_tasks - 1)
                                ticket.assigned_user_id = doctor.id
                                ticket.status = 'In Progress'
                                doctor.active_tasks = (doctor.active_tasks or 0) + 1

                                history.append({
                                    "status":    ticket.status,
                                    "timestamp": datetime.utcnow().isoformat() + "Z",
                                    "action":    f"✅ VERIFIED – linked to Appointment #{appt.id}, doctor: {linked_doctor_name or 'N/A'}"
                                })

                    history.append({
                        "status":    ticket.status,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "action":    f"🚀 AI PRIORITY BOOST – SLA set to {sla_mins}m (Verified Patient)"
                    })
                    ticket.status_history_log = json.dumps(history)

        db.session.commit()

        # ── Phase 2: Repeat Complaint Detection (non-blocking) ────────────
        try:
            rep = repeat_complaint_service.evaluate(data['patient_id'])
            if rep.get('flagged'):
                app_logger.warning(
                    f"High-Risk Patient {data['patient_id']}: "
                    f"{rep['complaint_count']} complaints, "
                    f"ticket #{rep.get('ticket_id_escalated')} escalated"
                )
        except Exception as rep_err:
            app_logger.error(f"RepeatComplaint check failed (non-blocking): {rep_err}")

        return jsonify(format_response("success", data={
            "id":              feedback.id,
            "sentiment":       feedback.sentiment,
            "sentiment_score": feedback.sentiment_score,
            "issue_type":      feedback.issue_type,
            "severity":        feedback.severity,
            "is_verified":     is_verified,
            "linked_doctor":   linked_doctor_name
        })), 201
    except Exception as e:
        db.session.rollback()
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

        sentiment_filter = request.args.get('sentiment')
        if sentiment_filter and sentiment_filter != 'all':
            query = query.filter(Feedback.sentiment == sentiment_filter)

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
                "patient_name": t.feedback.patient_name or "",
                "patient_email": t.feedback.patient_email or "",
                "department": t.department_rel.name,
                "severity": t.severity,
                "sentiment": t.feedback.sentiment,
                "status": t.status,
                "is_verified": bool(t.feedback.is_verified),
                "assigned_staff": t.assigned_to_user.name if t.assigned_to_user else "Unassigned",
                "assigned_staff_id": t.assigned_user_id,
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
    
    # Build assigned staff info from ticket directly (avoids dept-mismatch)
    assigned_staff_info = None
    if ticket.assigned_to_user:
        s = ticket.assigned_to_user
        max_t = 10
        load_pct = min(100, (s.active_tasks / max_t) * 100)
        score = (s.active_tasks * 4) + (s.avg_resolution_time / 10) - (s.performance_rating * 2)
        assigned_staff_info = {
            "id":                 s.id,
            "name":               s.name,
            "designation":        s.designation,
            "active_tickets":     s.active_tasks,
            "avg_res_time":       round(s.avg_resolution_time),
            "performance_rating": s.performance_rating,
            "load_pct":           round(load_pct),
            "ai_score":           round(score, 1)
        }

    return jsonify(format_response("success", data={
        "id": ticket.id,
        "patient_id": ticket.feedback.patient_id,
        "patient_name": ticket.feedback.patient_name or "",
        "patient_email": ticket.feedback.patient_email or "",
        "department": ticket.department_rel.name,
        "sentiment": ticket.feedback.sentiment,
        "severity": ticket.severity,
        "feedback_text": ticket.feedback.feedback_text,
        "created_at": ticket.feedback.created_at.isoformat() + "Z",
        "status": ticket.status,
        "is_verified": bool(ticket.feedback.is_verified),
        "assigned_staff": ticket.assigned_to_user.name if ticket.assigned_to_user else "Unassigned",
        "assigned_staff_id": ticket.assigned_user_id,
        "assigned_staff_info": assigned_staff_info,
        "internal_notes": ticket.ai_suggested_response,
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
    """DYNAMIC PROFILE: Recalculate load from all active streams (Tickets + Emergencies)"""
    user = current_user
    
    # 1. Active Recovery Tickets
    active_tickets = Ticket.query.filter(
        Ticket.assigned_user_id == user.id,
        Ticket.status.in_(['Open', 'In Progress', 'Escalated'])
    ).count()
    
    # 2. Active Emergency Missions
    active_emergencies = EmergencyRequest.query.filter(
        EmergencyRequest.assigned_driver_id == user.id,
        EmergencyRequest.status.in_(['Dispatched', 'In Transit'])
    ).count()

    total_active = active_tickets + active_emergencies
    
    # Load Threshold: 5 active items = 100% Load
    # For drivers, 1 mission = 20% load, but "In Transit" is mentally 100%. 
    # For now, let's stick to a baseline of 5 total items for better visualization.
    load_pct = min(100, (total_active / 5) * 100)
    
    # Update the cache field if needed (mostly for admin stats consistency)
    if user.active_tasks != total_active:
        user.active_tasks = total_active
        db.session.commit()

    return jsonify(format_response("success", data={
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "designation": user.designation,
        "active_tasks": total_active,
        "avg_res_time": round(user.avg_resolution_time) if user.avg_resolution_time else 0,
        "success_rate": user.performance_rating,
        "load_pct": round(load_pct),
        # Phase 2 AI Intelligence
        "ai_performance_score": round(user.doctor_performance_score, 1) if user.role == 'staff' and user.doctor_performance_score else (
                                round(user.driver_efficiency_score, 1) if user.role == 'staff' and user.driver_efficiency_score else 0)
    }))

# ── DOCTOR APPOINTMENT CONTROLLERS ───────────────────────────────────────────

def get_doctor_appointments():
    """Return all appointments assigned to the logged-in doctor, newest first."""
    try:
        appts = Appointment.query.filter_by(
            doctor_id=current_user.id
        ).order_by(Appointment.appointment_date.desc()).all()

        result = []
        for a in appts:
            result.append({
                "id":               a.id,
                "patient_name":     a.patient_name,
                "patient_email":    a.patient_email,
                "department":       a.department.name if a.department else "—",
                "appointment_date": a.appointment_date,
                "time_slot":        a.time_slot,
                "status":           a.status,
                "type":             a.appointment_type,
                "completed_at":     a.completed_at.isoformat() + "Z" if a.completed_at else None,
                "created_at":       a.created_at.isoformat() + "Z"
            })
        return jsonify(format_response("success", data=result))
    except Exception as e:
        app_logger.error(f"get_doctor_appointments error: {e}")
        return jsonify(format_response("error", message=str(e))), 500


def complete_appointment(appt_id):
    """Doctor marks their own appointment as Completed."""
    try:
        appt = Appointment.query.get(appt_id)
        if not appt:
            return jsonify(format_response("error", message="Appointment not found")), 404

        # Safety Rule 1: Only the assigned doctor can complete it
        if appt.doctor_id != current_user.id:
            app_logger.warning(f"Unauthorised complete attempt: user {current_user.id} on appt {appt_id}")
            return jsonify(format_response("error", message="You are not assigned to this appointment")), 403

        # Safety Rule 2: Cannot complete an already-completed appointment
        if appt.status == 'Completed':
            return jsonify(format_response("error", message="Appointment is already completed")), 400

        # Mark completed
        appt.status       = 'Completed'
        appt.completed_at = datetime.utcnow()

        # Decrement doctor load (floor at 0)
        current_user.active_appointments = max(0, (current_user.active_appointments or 0) - 1)

        db.session.commit()
        app_logger.info(f"Dr. {current_user.name} completed Appointment #{appt_id} for {appt.patient_name}")
        return jsonify(format_response("success", message="Appointment marked as Completed",
                                       data={"id": appt.id, "status": appt.status,
                                             "completed_at": appt.completed_at.isoformat() + "Z"}))
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"complete_appointment error: {e}")
        return jsonify(format_response("error", message=str(e))), 500



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

def create_emergency():
    """PART 1 & 3: Create emergency and auto-dispatch nearest driver."""
    data = request.get_json(force=True, silent=True) or {}
    
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    lat = data.get('latitude')
    lng = data.get('longitude')
    
    if not name or not phone or not address:
        return jsonify(format_response("error", message="Missing Name, Phone or Address")), 400

    try:
        req = ambulance_service.handle_emergency_request(name, phone, address, lat, lng)
        if not req:
             return jsonify(format_response("error", message="No available ambulances. Please call emergency services.")), 404

        # Assigned driver info
        amb = Ambulance.query.filter_by(driver_id=req.assigned_driver_id).first()
        
        return jsonify(format_response("success",
            message="Emergency Dispatched.",
            data={
                "request_id": req.id,
                "ambulance": {
                    "number": amb.vehicle_number if amb else "N/A",
                    "driver": amb.driver_name if amb else "N/A"
                }
            }
        )), 201

    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Emergency Creation Error: {e}")
        return jsonify(format_response("error", message=str(e))), 500

def get_active_emergencies():
    """PART 6: Admin View - All active/recent emergency requests."""
    try:
        from database.models import EmergencyRequest
        # Show all for audit, order by most recent
        active = EmergencyRequest.query.order_by(EmergencyRequest.created_at.desc()).limit(50).all()
        
        result = []
        for r in active:
            result.append({
                "id": r.id,
                "patient_name": r.patient_name,
                "phone": r.phone_number,
                "address": r.address,
                "created_at": r.created_at.isoformat() + "Z",
                "accepted_at": r.accepted_at.isoformat() + "Z" if r.accepted_at else None,
                "completed_at": r.completed_at.isoformat() + "Z" if r.completed_at else None,
                "status": r.status,
                "assigned_driver": r.assigned_driver.name if r.assigned_driver else "N/A"
            })
        return jsonify(format_response("success", data=result))
    except Exception as e:
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

# =============================================
#   APPOINTMENT BOOKING ENDPOINTS
# =============================================

def get_departments_list():
    """Return all departments for the booking form dropdown."""
    try:
        departments = Department.query.order_by(Department.name).all()
        return jsonify(format_response("success", data=[
            {"id": d.id, "name": d.name} for d in departments
        ]))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_doctors_by_dept(dept_id):
    """Return staff doctors in a given department for the booking form."""
    try:
        dept = Department.query.get(dept_id)
        if not dept:
            return jsonify(format_response("error", message="Department not found")), 404
        doctors = User.query.filter_by(department=dept.name, role='staff').all()
        return jsonify(format_response("success", data=[
            {"id": d.id, "name": d.name, "designation": d.designation or "Specialist"} for d in doctors
        ]))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def book_appointment():
    """Book a new patient appointment and send email confirmation."""
    data = request.get_json(force=True, silent=True) or {}

    required = ['patient_name', 'patient_email', 'department_id', 'appointment_date', 'time_slot']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(format_response("error", message=f"Missing fields: {', '.join(missing)}")), 400

    try:
        dept = Department.query.get(data['department_id'])
        if not dept:
            return jsonify(format_response("error", message="Invalid department")), 400

        doctor_id = data.get('doctor_id') or None
        if doctor_id:
            doctor = User.query.get(doctor_id)
            if not doctor or doctor.role != 'staff':
                doctor_id = None

        # ── AI LOAD-BALANCING AUTO-ASSIGNMENT ─────────────────────────────
        # If no doctor was selected, pick the least-loaded doctor in the dept
        if not doctor_id:
            candidates = User.query.filter_by(
                department=dept.name, role='staff'
            ).order_by(User.active_appointments.asc()).all()
            # Exclude drivers (designation contains 'Driver')
            candidates = [u for u in candidates
                          if not (u.designation or '').lower().startswith('driver')]
            if candidates:
                assigned = candidates[0]
                doctor_id = assigned.id
                assigned.active_appointments += 1
                app_logger.info(f"AI assigned Dr. {assigned.name} (load: {assigned.active_appointments}) to new appointment")

        # AI TRIAGE LAYER
        patient_notes = data.get('notes', '')
        appt_type = triage_service.classify_appointment(patient_notes)
        
        appt = Appointment(
            patient_name=data['patient_name'].strip(),
            patient_email=data['patient_email'].strip().lower(),
            department_id=dept.id,
            doctor_id=doctor_id,
            appointment_date=data['appointment_date'],
            time_slot=data['time_slot'],
            status='Scheduled',
            appointment_type=appt_type
        )
        db.session.add(appt)
        db.session.flush() # get ID

        # AI AMBULANCE DISPATCH SYSTEM
        dispatched_amb = None
        if appt_type == "Emergency":
            dispatched_amb = ambulance_service.dispatch_ambulance(appt)

        # When doctor was manually chosen (not AI-assigned), still bump their counter
        elif doctor_id:
            manual_doc = User.query.get(doctor_id)
            if manual_doc:
                manual_doc.active_appointments += 1

        db.session.commit()

        # Send email confirmation (non-blocking — logs on failure)
        doctor_name = User.query.get(doctor_id).name if doctor_id else None
        try:
            mail = current_app.extensions.get('mail')
            if mail:
                send_appointment_confirmation(mail, appt, dept.name, doctor_name)
            else:
                app_logger.warning("Flask-Mail not configured; skipping appointment confirmation email")
        except Exception as mail_err:
            app_logger.warning(f"Email send failed (non-blocking): {mail_err}")

        app_logger.info(f"Appointment #{appt.id} booked: {appt.patient_name} -> {dept.name} on {appt.appointment_date}")

        return jsonify(format_response("success",
            message="Appointment booked successfully",
            data={
                "appointment_id": appt.id,
                "patient_name": appt.patient_name,
                "department": dept.name,
                "doctor": doctor_name or "To be assigned",
                "date": appt.appointment_date,
                "time": appt.time_slot,
                "status": appt.status,
                "type": appt.appointment_type,
                "ambulance": {
                    "number": dispatched_amb.vehicle_number,
                    "driver": dispatched_amb.driver_name
                } if dispatched_amb else None
            }
        )), 201
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Appointment booking error: {e}")
        return jsonify(format_response("error", message=str(e))), 500

def get_appointments():
    """Get all appointments for admin view (most recent first)."""
    try:
        appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
        result = []
        for a in appointments:
            result.append({
                "id":               a.id,
                "patient_name":     a.patient_name,
                "patient_email":    a.patient_email,
                "department":       a.department.name,
                "department_id":    a.department_id,
                "doctor":           a.doctor.name if a.doctor else None,
                "doctor_id":        a.doctor_id,
                "appointment_date": a.appointment_date,
                "time_slot":        a.time_slot,
                "status":           a.status,
                "type":             a.appointment_type,
                "ambulance_id":     a.ambulance_id,
                "ambulance_number": a.ambulance.vehicle_number if a.ambulance else None,
                "completed_at":     a.completed_at.isoformat() + "Z" if a.completed_at else None,
                "created_at":       a.created_at.isoformat() + "Z"
            })
        return jsonify(format_response("success", data=result))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_ambulances():
    """Get all ambulances for emergency monitor with dispatch details."""
    try:
        ambs = ambulance_service.get_all_ambulances()
        result = []
        for a in ambs:
            dispatch_info = None
            # Check for active dispatch involving this ambulance or driver
            active_dispatch = EmergencyDispatch.query.filter(
                (EmergencyDispatch.dispatch_status != 'Closed') &
                ((EmergencyDispatch.primary_driver_id == a.driver_id) | 
                 (EmergencyDispatch.secondary_driver_id == a.driver_id))
            ).order_by(EmergencyDispatch.first_alert_time.desc()).first()

            if active_dispatch:
                dispatch_info = {
                    "id": active_dispatch.id,
                    "status": active_dispatch.dispatch_status,
                    "primary_driver": active_dispatch.primary_driver.name if active_dispatch.primary_driver else "N/A",
                    "secondary_driver": active_dispatch.secondary_driver.name if active_dispatch.secondary_driver else "N/A",
                    "accepted_by": active_dispatch.assigned_driver.name if active_dispatch.assigned_driver else None,
                    "first_alert": active_dispatch.first_alert_time.isoformat() + "Z",
                    "accepted_at": active_dispatch.accepted_at.isoformat() + "Z" if active_dispatch.accepted_at else None
                }

            result.append({
                "id": a.id,
                "vehicle_number": a.vehicle_number,
                "driver_name": a.driver_name,
                "driver_id": a.driver_id,
                "status": a.status,
                "lat": a.current_lat,
                "lng": a.current_lng,
                "target_lat": a.target_lat,
                "target_lng": a.target_lng,
                "last_update": a.last_update.isoformat() + "Z" if a.last_update else None,
                "active_dispatch": dispatch_info
            })
        return jsonify(format_response("success", data=result))
    except Exception as e:
        return jsonify(format_response("error", message=str(e))), 500

def get_my_emergency():
    """DRIVER ALERT SYSTEM: GET /api/driver/emergency-status"""
    try:
        from database.models import EmergencyRequest, Ambulance
        # Check for active emergency assigned to current driver
        req = EmergencyRequest.query.filter(
            (EmergencyRequest.assigned_driver_id == current_user.id) &
            (EmergencyRequest.status.in_(['Dispatched', 'In Transit']))
        ).first()

        if not req:
            return jsonify(format_response("success", data=None))

        return jsonify(format_response("success", data={
            "id": req.id,
            "patient_name": req.patient_name or "Unknown",
            "phone": req.phone_number,
            "address": req.address or "Location details pending",
            "lat": req.latitude,
            "lng": req.longitude,
            "status": req.status,
            "created_at": req.created_at.isoformat() + "Z",
            "maps_link": f"https://www.google.com/maps?q={req.latitude},{req.longitude}" if req.latitude else None,
            "eta_minutes": round(req.eta_minutes) if req.eta_minutes else None
        }))
    except Exception as e:
        app_logger.error(f"Error in get_my_emergency: {e}")
        return jsonify(format_response("error", message=str(e))), 500

def accept_emergency_dispatch(id):
    """POST /api/driver/accept/<id> - Race-condition safe acceptance."""
    try:
        import random
        dispatch = EmergencyDispatch.query.get(id)
        if not dispatch:
            return jsonify(format_response("error", message="Dispatch not found")), 404
            
        if dispatch.assigned_driver_id is not None:
             return jsonify(format_response("error", message="Dispatch already handled.")), 400
             
        # Check if user IS a driver with an ambulance
        amb = Ambulance.query.filter_by(driver_id=current_user.id).first()
        if not amb:
            return jsonify(format_response("error", message="Access Denied: No ambulance linked to this account.")), 403

        # Lock Dispatch
        dispatch.assigned_driver_id = current_user.id
        dispatch.dispatch_status = "Accepted"
        dispatch.accepted_at = datetime.utcnow()
        
        # Simulated target (Patient location)
        p_lat = 12.9716 + (random.random() - 0.5) * 0.05
        p_lng = 77.5946 + (random.random() - 0.5) * 0.05
        
        # Update Ambulance status
        amb.status = "Busy"
        amb.target_lat = p_lat
        amb.target_lng = p_lng
        # Update Appointment
        appt = dispatch.appointment
        if appt:
            appt.status = "In Transit"
        # Update Ambulance status
        amb.status = "Busy"
        amb.target_lat = p_lat
        amb.target_lng = p_lng

        # IMPORTANT: Sync Active Task Count
        current_user.active_tasks = (current_user.active_tasks or 0) + 1
            
        db.session.commit()
        app_logger.info(f"Driver {current_user.name} accepted dispatch #{id}")
        
        return jsonify(format_response("success", message="Dispatch Accepted"))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500

def accept_emergency_request(id):
    """TRIP START FLOW: POST /api/driver/emergency/accept/<id>"""
    try:
        from database.models import EmergencyRequest, Ambulance
        req = EmergencyRequest.query.get(id)
        if not req:
            return jsonify(format_response("error", message="Emergency request not found")), 404
            
        if req.assigned_driver_id != current_user.id:
             return jsonify(format_response("error", message="This emergency is not assigned to you.")), 403

        if req.status != "Dispatched":
            return jsonify(format_response("error", message=f"Invalid state: Cannot accept from status '{req.status}'")), 400

        # Update to In Transit
        req.status = "In Transit"
        req.accepted_at = datetime.utcnow()
        
        # Sync Ambulance status
        amb = Ambulance.query.filter_by(driver_id=current_user.id).first()
        if amb:
            amb.status = "Busy"
            if req.latitude and req.longitude:
                amb.target_lat = req.latitude
                amb.target_lng = req.longitude
        
        # IMPORTANT: Sync Active Task Count
        current_user.active_tasks = (current_user.active_tasks or 0) + 1
        
        db.session.commit()
        app_logger.info(f"🚨 TRIP STARTED: Driver {current_user.name} for Emergency #{id}")
        return jsonify(format_response("success", message="Trip Started. Safe driving."))
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error accepting emergency {id}: {e}")
        return jsonify(format_response("error", message=str(e))), 500

def complete_emergency_request(id):
    """TRIP COMPLETION FLOW: POST /api/driver/complete/<id>"""
    try:
        from database.models import EmergencyRequest, Ambulance
        req = EmergencyRequest.query.get(id)
        if not req:
            return jsonify(format_response("error", message="Request not found")), 404
            
        if req.assigned_driver_id != current_user.id:
             return jsonify(format_response("error", message="Access Denied.")), 403

        # Update to Completed
        req.status = "Completed"
        req.completed_at = datetime.utcnow()
        
        # Free up Ambulance
        amb = Ambulance.query.filter_by(driver_id=current_user.id).first()
        if amb:
            amb.status = "Available"
            amb.target_lat = None
            amb.target_lng = None
        
        # IMPORTANT: Sync Active Task Count
        current_user.active_tasks = max(0, (current_user.active_tasks or 0) - 1)
        
        db.session.commit()
        app_logger.info(f"✅ TRIP COMPLETED: Emergency #{id}")
        return jsonify(format_response("success", message="Trip Completed. Ambulance available."))
    except Exception as e:
        db.session.rollback()
        return jsonify(format_response("error", message=str(e))), 500


VALID_APPT_STATUSES = {'Scheduled', 'In Progress', 'Completed', 'Cancelled'}

def update_appointment_status(appt_id):
    """PUT /api/admin/appointments/<id>/status — update status and set completed_at."""
    data = request.get_json(force=True, silent=True) or {}
    new_status = (data.get('status') or '').strip()

    if new_status not in VALID_APPT_STATUSES:
        return jsonify(format_response("error",
            message=f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(VALID_APPT_STATUSES))}"
        )), 400

    appt = Appointment.query.get(appt_id)
    if not appt:
        return jsonify(format_response("error", message="Appointment not found")), 404

    old_status = appt.status
    appt.status = new_status

    if new_status == 'Completed' and not appt.completed_at:
        appt.completed_at = datetime.utcnow()
    elif new_status != 'Completed':
        appt.completed_at = None  # reset if rolling back

    db.session.commit()
    app_logger.info(f"Appointment #{appt_id} status: {old_status} → {new_status}")

    return jsonify(format_response("success",
        message=f"Appointment #{appt_id} updated to '{new_status}'",
        data={
            "id":           appt.id,
            "status":       appt.status,
            "completed_at": appt.completed_at.isoformat() + "Z" if appt.completed_at else None
        }
    ))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 AI INTELLIGENCE — Controller Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_stress_index():
    """GET /api/ai/stress-index — real-time Hospital Stress Index."""
    try:
        data = stress_index_service.compute()
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_stress_index error: {e}')
        return jsonify(format_response('error', message=str(e))), 500


def get_doctor_performance():
    """GET /api/ai/doctor-performance — ranked doctor AI scores."""
    try:
        data = doctor_performance_service.score_all()
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_doctor_performance error: {e}')
        return jsonify(format_response('error', message=str(e))), 500


def get_appointment_forecast():
    """GET /api/ai/appointment-forecast — 7-day load prediction per department."""
    try:
        data = forecast_service.forecast_next_days(7)
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_appointment_forecast error: {e}')
        return jsonify(format_response('error', message=str(e))), 500


def get_sla_risk_tickets():
    """GET /api/ai/sla-risk — tickets with breach probability scored."""
    try:
        data = sla_risk_service.evaluate_all()
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_sla_risk_tickets error: {e}')
        return jsonify(format_response('error', message=str(e))), 500


def get_department_risk():
    """GET /api/ai/department-risk — GREEN/AMBER/RED risk per department."""
    try:
        data = department_risk_service.evaluate()
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_department_risk error: {e}')
        return jsonify(format_response('error', message=str(e))), 500


def get_driver_performance():
    """GET /api/ai/driver-performance — ranked driver efficiency scores."""
    try:
        data = driver_scoring_service.score_all()
        return jsonify(format_response('success', data=data)), 200
    except Exception as e:
        app_logger.error(f'get_driver_performance error: {e}')
        return jsonify(format_response('error', message=str(e))), 500
