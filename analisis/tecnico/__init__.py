# -*- coding: utf-8 -*-
"""
Módulo de análisis técnico
"""

from analisis.tecnico.soportes_resistencias import (
    detectar_soportes_resistencias,
    obtener_sr_mas_cercanos,
    evaluar_sr,
)

from analisis.tecnico.confirmaciones import calcular_confirmaciones

from analisis.tecnico.patrones_velas import (
    detectar_patrones_velas,
    analizar_confluencia_velas_sr,
)

from analisis.tecnico.grafico_avanzado import (
    crear_grafico_analisis_tecnico,
    crear_grafico_simple_sr,
)

__all__ = [
    'detectar_soportes_resistencias',
    'obtener_sr_mas_cercanos',
    'evaluar_sr',
    'calcular_confirmaciones',
    'detectar_patrones_velas',
    'analizar_confluencia_velas_sr',
    'crear_grafico_analisis_tecnico',
    'crear_grafico_simple_sr',
]
