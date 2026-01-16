"""
Dashboard API
=============
Endpoint untuk halaman Dashboard Overview.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.data_loader_service import DataLoaderService

bp = Blueprint('dashboard', __name__)

@bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_dashboard_metrics():
    # Parse filter groups dari query params: ?groups=A,B,C
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    
    metrics = DataLoaderService.get_dashboard_metrics(groups)
    return jsonify(metrics)

@bp.route('/risk-distribution', methods=['GET'])
@jwt_required()
def get_risk_distribution():
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    
    data = DataLoaderService.get_risk_distribution(groups)
    return jsonify(data)

@bp.route('/top-alerts', methods=['GET'])
@jwt_required()
def get_top_alerts():
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    
    # Check if 'limit' param exists
    limit = int(request.args.get('limit', 5))
    
    data = DataLoaderService.get_top_alerts(limit, groups)
    return jsonify(data)

@bp.route('/top-products', methods=['GET'])
@jwt_required()
def get_top_products():
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    limit = int(request.args.get('limit', 5))
    
    data = DataLoaderService.get_top_moving_products(limit, groups)
    return jsonify(data)

@bp.route('/abc-performance', methods=['GET'])
@jwt_required()
def get_abc_performance():
    """Get Stock Value and Performance metrics grouped by ABC Class"""
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    
    data = DataLoaderService.get_abc_performance(groups)
    return jsonify(data)

@bp.route('/category-summary', methods=['GET'])
@jwt_required()
def get_category_summary():
    """Get Health Category Summary (Healthy, Stable, Warning, Critical)"""
    groups_param = request.args.get('groups')
    groups = groups_param.split(',') if groups_param else None
    
    data = DataLoaderService.get_category_summary(groups)
    return jsonify(data)

@bp.route('/groups', methods=['GET'])
@jwt_required()
def get_available_groups():
    groups = DataLoaderService.get_groups_list()
    return jsonify({'groups': groups})

@bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'Dashboard API OK'}), 200
