"""
Auth Service
============
Business logic untuk autentikasi (Login, Register).
"""

from app.models.user import User
from app.extensions import db
from flask_jwt_extended import create_access_token
from datetime import timedelta

class AuthService:
    @staticmethod
    def login(username, password):
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            access_token = create_access_token(
                identity=str(user.id),  # Must be string for JWT
                additional_claims={'role': user.role, 'username': user.username},
                expires_delta=timedelta(hours=1)
            )
            return {
                'access_token': access_token,
                'user': user.to_dict()
            }
        return None

    @staticmethod
    def register(username, email, password, role='user'):
        if User.query.filter_by(username=username).first():
            return None, "Username already exists"
            
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return user.to_dict(), None
        
    @staticmethod
    def create_admin_if_not_exists():
        """Helper untuk membuat admin default saat startup."""
        if not User.query.filter_by(username="admin1").first():
            admin = User(username="admin1", email="admin@wpt.com", role="admin")
            admin.set_password("admin123")  # Default password
            db.session.add(admin)
            db.session.commit()
            print("👤 Created default admin user: admin1")
