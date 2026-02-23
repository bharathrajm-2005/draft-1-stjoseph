"""
Email Service for Aurevia Hospital
Sends appointment confirmations using Flask-Mail.
Falls back to console logging when SMTP is not configured.
"""
from flask_mail import Message
from utils.logger import app_logger


def send_appointment_confirmation(mail_instance, appointment, department_name, doctor_name=None):
    """Send an appointment confirmation email to the patient."""
    try:
        subject = "✅ Appointment Confirmed – Aurevia Medical Institute"
        doctor_line = f"Assigned Doctor: {doctor_name}" if doctor_name else "Doctor: To be assigned"
        
        html_body = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc;">
            <div style="background: linear-gradient(135deg, #1a56db, #0e9f6e); padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 26px;">⚕️ Aurevia Medical Institute</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0;">Appointment Confirmation</p>
            </div>
            <div style="background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <p style="color: #374151; font-size: 16px;">Dear <strong>{appointment.patient_name}</strong>,</p>
                <p style="color: #6b7280;">Your appointment has been successfully booked. Here are your details:</p>
                
                <div style="background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 8px; padding: 20px; margin: 24px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Appointment ID</td><td style="padding: 8px 0; font-weight: 700; color: #1f2937;">#{appointment.id:04d}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase;">Department</td><td style="padding: 8px 0; font-weight: 600; color: #1f2937;">{department_name}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase;">{doctor_line.split(':')[0]}</td><td style="padding: 8px 0; font-weight: 600; color: #1f2937;">{doctor_line.split(': ', 1)[1]}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase;">Date</td><td style="padding: 8px 0; font-weight: 600; color: #1f2937;">{appointment.appointment_date}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase;">Time</td><td style="padding: 8px 0; font-weight: 600; color: #1f2937;">{appointment.time_slot}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6b7280; font-size: 13px; text-transform: uppercase;">Status</td><td style="padding: 8px 0;"><span style="background: #d1fae5; color: #065f46; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700;">CONFIRMED</span></td></tr>
                    </table>
                </div>
                
                <div style="background: #fef3c7; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">⏰ <strong>Please arrive 15 minutes early</strong> with your ID card and relevant medical reports.</p>
                </div>
                
                <p style="color: #6b7280; font-size: 14px; margin-top: 24px;">For changes or cancellations, contact us at <a href="tel:+911234567890" style="color: #1a56db;">+91 1234 567 890</a> or reply to this email.</p>
                
                <div style="text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">© 2025 Aurevia Medical Institute · 123 Medical Plaza, Healthcare District</p>
                    <p style="color: #9ca3af; font-size: 12px; margin: 4px 0 0;">This is an automated confirmation. Do not reply.</p>
                </div>
            </div>
        </div>
        """
        
        msg = Message(
            subject=subject,
            recipients=[appointment.patient_email],
            html=html_body
        )
        mail_instance.send(msg)
        app_logger.info(f"Confirmation email sent to {appointment.patient_email} for appointment #{appointment.id}")
        return True
    except Exception as e:
        # Log the error but don't crash the booking flow
        app_logger.warning(f"Email send failed (booking still saved): {e}")
        # Print to console as fallback
        print(f"\n{'='*60}")
        print(f"[EMAIL FALLBACK] Appointment #{appointment.id} confirmed for {appointment.patient_name}")
        print(f"To: {appointment.patient_email} | Dept: {department_name} | {appointment.appointment_date} {appointment.time_slot}")
        print(f"{'='*60}\n")
        return False
