from flask import Blueprint

bp = Blueprint('health', __name__)

@bp.route('/ping')
def ping():
    return {'status': 'health ok'}
