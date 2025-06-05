
from flask import Blueprint

bp = Blueprint('processos_bp', __name__)

from . import routes
