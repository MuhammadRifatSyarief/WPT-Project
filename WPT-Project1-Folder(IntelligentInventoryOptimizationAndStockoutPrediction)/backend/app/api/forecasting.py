from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.data_loader_service import DataLoaderService

bp = Blueprint('forecasting', __name__)

@bp.route('/data', methods=['GET'])
@jwt_required()
def get_forecasting_data():
    """Get filtered data for demand forecasting"""
    search = request.args.get('search')
    category = request.args.get('category')
    abc_class = request.args.get('abc_class')
    
    data = DataLoaderService.get_forecasting_data(
        search_query=search,
        category_filter=category,
        abc_filter=abc_class
    )
    return jsonify(data)

@bp.route('/ping')
def ping():
    return {'status': 'forecasting ok'}
