from flask import Blueprint
from .controllers import (
    submit_feedback, 
    get_tickets, 
    get_ticket_details, 
    get_dashboard_stats,
    get_staff_per_dept,
    assign_staff,
    resolve_ticket,
    get_department_performance,
    get_heatmap_data,
    get_incident_trend,
    check_sla,
    regenerate_response,
    approve_response,
    get_staff_profile,
    get_staff_tasks,
    complete_staff_task,
    # Appointment endpoints
    book_appointment,
    get_departments_list,
    get_doctors_by_dept,
    get_appointments,
    update_appointment_status,
    get_ambulances,
    accept_emergency_dispatch,
    create_emergency,
    get_my_emergency,
    accept_emergency_request,
    complete_emergency_request,
    get_active_emergencies,
    # Doctor appointment workflow
    get_doctor_appointments,
    complete_appointment,
)
from utils.helpers import staff_required, admin_required

api_bp = Blueprint('api', __name__)

# === PUBLIC ENDPOINTS ===
api_bp.route('/submit-feedback', methods=['POST'])(submit_feedback)
api_bp.route('/appointments', methods=['POST'])(book_appointment)
api_bp.route('/appointments/departments', methods=['GET'])(get_departments_list)
api_bp.route('/appointments/departments/<int:dept_id>/doctors', methods=['GET'])(get_doctors_by_dept)
api_bp.route('/emergency/create', methods=['POST'])(create_emergency)

# === ADMIN ENDPOINTS ===
api_bp.route('/stats/dashboard', methods=['GET'])(get_dashboard_stats)
api_bp.route('/tickets', methods=['GET'])(get_tickets)
api_bp.route('/tickets/<int:id>', methods=['GET'])(get_ticket_details)
api_bp.route('/tickets/<int:id>/assign', methods=['POST'])(assign_staff)
api_bp.route('/tickets/<int:id>/resolve', methods=['POST'])(resolve_ticket)
api_bp.route('/tickets/<int:id>/regenerate-response', methods=['POST'])(regenerate_response)
api_bp.route('/tickets/<int:id>/approve-response', methods=['POST'])(approve_response)
api_bp.route('/departments/<string:dept_name>/staff', methods=['GET'])(get_staff_per_dept)
api_bp.route('/analytics/performance', methods=['GET'])(get_department_performance)
api_bp.route('/analytics/heatmap', methods=['GET'])(get_heatmap_data)
api_bp.route('/analytics/trend', methods=['GET'])(get_incident_trend)
api_bp.route('/analytics/appointments', methods=['GET'])(admin_required(get_appointments))
api_bp.route('/admin/appointments/<int:appt_id>/status', methods=['PUT'])(admin_required(update_appointment_status))
api_bp.route('/admin/ambulances', methods=['GET'])(admin_required(get_ambulances))
api_bp.route('/admin/emergencies', methods=['GET'])(admin_required(get_active_emergencies))
api_bp.route('/sla/check', methods=['POST'])(check_sla)

# === STAFF/DRIVER PORTAL APIS (Protected) ===
api_bp.route('/staff/profile', methods=['GET'])(staff_required(get_staff_profile))
api_bp.route('/staff/tasks', methods=['GET'])(staff_required(get_staff_tasks))
api_bp.route('/staff/complete/<int:id>', methods=['POST'])(staff_required(complete_staff_task))

# === PHASE 1B DRIVER DISPATCH APIS ===
api_bp.route('/driver/emergency-status', methods=['GET'])(staff_required(get_my_emergency))
api_bp.route('/driver/accept/<int:id>', methods=['POST'])(staff_required(accept_emergency_dispatch))
api_bp.route('/driver/emergency/accept/<int:id>', methods=['POST'])(staff_required(accept_emergency_request))
api_bp.route('/driver/emergency/complete/<int:id>', methods=['POST'])(staff_required(complete_emergency_request))

# === DOCTOR APPOINTMENT WORKFLOW ===
api_bp.route('/doctor/appointments', methods=['GET'])(staff_required(get_doctor_appointments))
api_bp.route('/doctor/appointments/<int:appt_id>/complete', methods=['POST'])(staff_required(complete_appointment))
