# indicadores/__init__.py
from flask import Blueprint

indicadores_bp = Blueprint(
    'indicadores',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes, api