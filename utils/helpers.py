import json
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify
from flask_login import current_user

def format_response(status, data=None, message=None):
    return {
        "status": status,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def calculate_deadline(hours):
    return datetime.utcnow() + timedelta(hours=hours)

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "staff":
            return jsonify({"status": "error", "message": "Staff access denied"}), 403
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            return jsonify({"status": "error", "message": "Admin access denied"}), 403
        return f(*args, **kwargs)
    return decorated
