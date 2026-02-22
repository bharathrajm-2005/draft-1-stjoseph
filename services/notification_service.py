from utils.logger import app_logger

class NotificationService:
    def __init__(self):
        pass

    def send_notification(self, recipient, message):
        """ Simulated notification service (Email/SMS/Slack) """
        app_logger.info(f"NOTIFICATION to [{recipient}]: {message}")
        
        # In a real system, you would integrate with SendGrid, Twilio, or another provider here
        return True
