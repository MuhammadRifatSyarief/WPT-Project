"""
Auth Endpoints
==============
API Routings untuk Authentication.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.services.auth_service import AuthService

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    result = AuthService.login(username, password)
    if result:
        return jsonify(result), 200
        
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/register', methods=['POST'])
def register():
    # Optional: Proteksi endpoint ini hanya untuk admin jika perlu
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not password or not email:
        return jsonify({'error': 'Username, email, and password required'}), 400
        
    user, error = AuthService.register(username, email, password)
    if error:
        return jsonify({'error': error}), 400
        
    return jsonify({'message': 'User created', 'user': user}), 201

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    return jsonify({
        'id': current_user_id,
        'username': claims.get('username'),
        'role': claims.get('role')
    }), 200

@bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'Auth Service OK'}), 200
