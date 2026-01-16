from flask import Blueprint

bp = Blueprint('forecasting', __name__)

@bp.route('/ping')
def ping():
    return {'status': 'forecasting ok'}
