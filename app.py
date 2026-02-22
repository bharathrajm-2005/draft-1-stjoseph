from flask import Flask
from config import Config
from database.db import init_db
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
    
    # Register Blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.route('/')
    def index():
        return {"project": "AI-Driven Patient Experience Analytics", "version": "1.0.0"}

    return app

if __name__ == '__main__':
    app = create_app()
    app_logger.info("Starting Patient Experience AI Backend Server...")
    app.run(debug=True, port=5000)