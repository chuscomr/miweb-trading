# indicadores/__init__.py
from flask import Blueprint

indicadores_bp = Blueprint(
    "indicadores",
    __name__,
    url_prefix="/indicadores",
    template_folder="templates",
    static_folder="static",
)

@indicadores_bp.after_request
def no_cache_indicadores(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

from . import routes, api
