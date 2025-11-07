"""
Blueprint de Execuções
"""

from flask import Blueprint

bp = Blueprint(
    'execucoes_bp',
    __name__,
    url_prefix='/execucoes',
    template_folder='templates'
)

from . import routes
