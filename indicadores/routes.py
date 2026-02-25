# indicadores/routes.py
from flask import render_template
from . import indicadores_bp

@indicadores_bp.route("/")
def vista_indicadores():
    """Vista principal del laboratorio de indicadores"""
    return render_template("indicadores.html")

@indicadores_bp.route("/configuracion")
def ver_configuracion():
    """Vista para gestionar configuraciones guardadas"""
    return render_template("configuracion.html")  # Si decides crearla