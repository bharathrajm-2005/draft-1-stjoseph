from flask import Blueprint
from .controllers import submit_feedback, get_feedback_list, get_recovery_tasks, check_sla, update_task_status

api_bp = Blueprint('api', __name__)

api_bp.route('/submit-feedback', methods=['POST'])(submit_feedback)
api_bp.route('/get-feedback', methods=['GET'])(get_feedback_list)
api_bp.route('/tasks', methods=['GET'])(get_recovery_tasks)
api_bp.route('/tasks/<int:id>', methods=['PATCH'])(update_task_status)
api_bp.route('/sla/check', methods=['POST'])(check_sla)
