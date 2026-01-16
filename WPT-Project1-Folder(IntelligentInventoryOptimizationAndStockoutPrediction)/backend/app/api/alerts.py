from flask import Blueprint

bp = Blueprint('alerts', __name__)

@bp.route('/ping')
def ping():
    return {'status': 'alerts ok'}
