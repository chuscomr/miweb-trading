# ==========================================================
# PAQUETE ANÁLISIS TÉCNICO
# Módulo complementario para sistema Swing Trading
# ==========================================================

from .confirmaciones_profesionales import calcular_confirmaciones_profesionales
from .confirmaciones_breakout import calcular_confirmaciones_breakout  # ← NUEVO

from .soportes_resistencias import (
    detectar_soportes_resistencias,
    obtener_sr_mas_cercanos
)

from .patrones_velas import (
    detectar_patrones_velas,
    analizar_confluencia_velas_sr
)

from .grafico_avanzado import (
    crear_grafico_analisis_tecnico,
    crear_grafico_simple_sr
)

__version__ = "1.0.0"

__all__ = [
    'calcular_confirmaciones_profesionales',
    'calcular_confirmaciones_breakout',  # ← NUEVO
    'detectar_soportes_resistencias',
    'obtener_sr_mas_cercanos',
    'detectar_patrones_velas',
    'analizar_confluencia_velas_sr',
    'crear_grafico_analisis_tecnico',
    'crear_grafico_simple_sr'
]