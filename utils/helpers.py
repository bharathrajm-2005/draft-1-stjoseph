import json
from datetime import datetime, timedelta

def format_response(status, data=None, message=None):
    return {
        "status": status,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def calculate_deadline(hours):
    return datetime.utcnow() + timedelta(hours=hours)
