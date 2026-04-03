# ==========================================================
# BLUEPRINT - CONTEXTO DE MERCADO
# Página de entrada a los módulos de análisis
# ==========================================================

from flask import Blueprint, render_template

contexto_bp = Blueprint('contexto', __name__, url_prefix='/contexto')

@contexto_bp.route('/')
def index():
    """Página principal de Contexto de Mercado con acceso a los 3 módulos"""
    return render_template('contexto_index.html')

print("✅ Blueprint contexto_bp cargado")
