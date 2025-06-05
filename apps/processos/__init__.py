
from flask import Blueprint

bp = Blueprint('processos_bp', __name__, url_prefix='/processos')

from . import routes
