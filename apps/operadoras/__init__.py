
from flask import Blueprint

bp = Blueprint(
    'operadoras_bp', __name__,
    url_prefix='/operadoras'
)

from apps.operadoras import routes
