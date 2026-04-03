# core/__init__.py
# Núcleo del sistema — imports limpios para uso externo

try:
    from .universos import IBEX35, CONTINUO, TODOS, get_nombre, normalizar_ticker
except ImportError:
    IBEX35 = []
    CONTINUO = []
    TODOS = []

from .indicadores import calcular_rsi, calcular_atr, calcular_macd, calcular_bollinger
from .data_provider import get_df
from .contexto_mercado import evaluar_contexto_ibex

try:
    from .riesgo import calcular_sizing, calcular_stop, calcular_objetivo, calcular_rr
except ImportError:
    pass
