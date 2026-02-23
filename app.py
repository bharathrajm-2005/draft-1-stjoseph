from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from config import Config
from database.db import init_db
from database.models import db, User
from backend.routes import api_bp
from utils.logger import app_logger
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app)
    
    # Initialize Database
    init_db(app)

    # Initialize Flask-Mail
    mail = Mail(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register Blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/')
    def index():
        return render_template('patient.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # 1. If already logged in, skip the form
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('staff_dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            if user and user.password == password:
                # Use remember=True to persist across browser closing
                login_user(user, remember=True)
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('staff_dashboard'))
            flash('Invalid email or password')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        # Strict role check
        if getattr(current_user, 'role', None) != 'admin':
            return redirect(url_for('staff_dashboard'))
        return render_template('admin_dashboard.html')

    @app.route('/staff')
    @login_required
    def staff_dashboard():
        # Explicit check: If admin hits /staff, bounce to /admin
        if getattr(current_user, 'role', None) == 'admin':
            return redirect(url_for('admin_dashboard'))
        
        # fallback for non-staff
        if getattr(current_user, 'role', None) != 'staff':
            return redirect(url_for('login'))
            
        return render_template('staff_dashboard.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app_logger.info("Starting Patient Experience AI Backend Server...")
    app.run(debug=True, port=5000)