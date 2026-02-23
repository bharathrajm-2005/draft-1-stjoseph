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
    complete_staff_task
)
from utils.helpers import staff_required

api_bp = Blueprint('api', __name__)

api_bp.route('/submit-feedback', methods=['POST'])(submit_feedback)
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
api_bp.route('/sla/check', methods=['POST'])(check_sla)

# Staff Portal APIs (Protected)
api_bp.route('/staff/profile', methods=['GET'])(staff_required(get_staff_profile))
api_bp.route('/staff/tasks', methods=['GET'])(staff_required(get_staff_tasks))
api_bp.route('/staff/complete/<int:id>', methods=['POST'])(staff_required(complete_staff_task))
