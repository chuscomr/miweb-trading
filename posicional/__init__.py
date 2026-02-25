# ==========================================================
# SISTEMA POSICIONAL - PACKAGE INIT
# ==========================================================

"""
Sistema de Trading Posicional
Timeframe: 6 meses - 2 años
Estrategia: Trend Following + Position Trading
"""

__version__ = "0.1.0"
__author__ = "Salva"

# Imports principales
from .config_posicional import *

# Hacer disponibles las funciones principales
try:
    from .datos_posicional import (
        obtener_datos_semanales,
        validar_datos,
        filtrar_universo_posicional
    )
    
    from .logica_posicional import (
        detectar_tendencia_largo_plazo,
        detectar_consolidacion,
        detectar_breakout,
        calcular_stop_inicial,
        validar_riesgo
    )
except ImportError:
    # Si falla, no pasa nada (aún no están todos los módulos)
    pass
