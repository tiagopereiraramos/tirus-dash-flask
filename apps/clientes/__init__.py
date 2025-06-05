
"""
Blueprint para gerenciamento de clientes
"""

from flask import Blueprint

bp = Blueprint('clientes_bp', __name__, url_prefix='/clientes')

from apps.clientes import routes
