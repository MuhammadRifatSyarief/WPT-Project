"""
Flask Application Factory
=========================
Membuat instance Flask app dengan konfigurasi dan extensions.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import Config
from .extensions import cache, db


def create_app(config_class=Config):
    """
    Factory function untuk membuat Flask app.
    
    Sama seperti st.set_page_config() di Streamlit,
    ini adalah setup awal aplikasi.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Extensions
    CORS(app, origins=app.config['CORS_ORIGINS'].split(','))
    jwt = JWTManager(app)
    cache.init_app(app)
    db.init_app(app)
    
    # JWT Error Handlers untuk debugging
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        print(f"❌ JWT Invalid Token: {error_string}")
        return jsonify({'error': 'Invalid token', 'message': error_string}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        print(f"❌ JWT Missing Token: {error_string}")
        return jsonify({'error': 'Missing token', 'message': error_string}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print(f"❌ JWT Expired: {jwt_payload}")
        return jsonify({'error': 'Token expired'}), 401
    
    # Register Blueprints
    from .api import auth, dashboard, forecasting, health, alerts, inventory
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard.bp, url_prefix='/api/dashboard')
    app.register_blueprint(forecasting.bp, url_prefix='/api/forecasting')
    app.register_blueprint(health.bp, url_prefix='/api/health')
    app.register_blueprint(alerts.bp, url_prefix='/api/alerts')
    # inventory.bp sudah punya url_prefix di dalam blueprint definition
    app.register_blueprint(inventory.bp)
    
    # Health check endpoint
    @app.route('/api/health-check')
    def health_check():
        return {'status': 'ok', 'message': 'Flask API is running!'}
    
    # Create DB tables & Default Admin
    with app.app_context():
        from .models.user import User
        db.create_all()
        
        from .services.auth_service import AuthService
        AuthService.create_admin_if_not_exists()
    
    return app

