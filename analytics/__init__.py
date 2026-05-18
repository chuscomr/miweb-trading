"""
Módulo Analytics - Tracking real de resultados.
"""

from .integrador import registrar_apertura, registrar_cierre, registrar_señal_no_ejecutada
from .metrics import (
    analisis_mae_mfe,
    calcular_kpis,
    cruce_setup_contexto,
    mejor_peor_setup,
    resultados_por_contexto,
    resultados_por_fundamental,
    resultados_por_setup,
    trades_no_ejecutados,
    winrate_por_score,
)
from .trades_log import actualizar_trade, eliminar_trade, init_db, listar_trades, obtener_trade, registrar_trade


__all__ = [
    # trades_log
    'init_db',
    'registrar_trade',
    'actualizar_trade',
    'obtener_trade',
    'listar_trades',
    'eliminar_trade',

    # metrics
    'calcular_kpis',
    'winrate_por_score',
    'resultados_por_fundamental',
    'resultados_por_contexto',
    'resultados_por_setup',
    'mejor_peor_setup',
    'trades_no_ejecutados',
    'analisis_mae_mfe',
    'cruce_setup_contexto',

    # integrador
    'registrar_apertura',
    'registrar_cierre',
    'registrar_señal_no_ejecutada'
]
