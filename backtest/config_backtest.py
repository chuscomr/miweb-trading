# backtest/config_backtest.py
# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL BACKTEST
#
# Centraliza todos los parámetros en un único objeto.
# Cambiar un parámetro aquí afecta a todo el sistema.
# Sin config dispersa por engine, strategy y risk.
# ══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfigBacktest:
    """
    Parámetros de configuración para un backtest.

    Uso:
        config = ConfigBacktest(capital_inicial=20000, riesgo_pct=1.5)
        resultado = ejecutar_backtest("BBVA.MC", config=config)

    O con valores por defecto:
        resultado = ejecutar_backtest("BBVA.MC")
    """

    # ── Capital ───────────────────────────────────────────
    capital_inicial: float = 10_000.0       # € de partida
    riesgo_pct:      float = 1.0            # % del capital arriesgado por operación

    # ── Datos ─────────────────────────────────────────────
    periodo:         str   = "2y"           # periodo yfinance para descarga
    min_velas:       int   = 60             # mínimo de barras para evaluar

    # ── Estrategia ────────────────────────────────────────
    estrategia:      str   = "breakout"     # "breakout" | "pullback" | "medio" | "posicional"
    modo_test:       bool  = False          # True = estrategia simple para validar el motor

    # ── Ejecución (slippage y comisiones) ─────────────────
    slippage_pct:    float = 0.10           # % de deslizamiento en entrada/salida
    comision_pct:    float = 0.10           # % de comisión por operación (ida y vuelta)

    # ── Gestión de posición ───────────────────────────────
    rr_objetivo:     float = 2.5            # ratio R:R para calcular target automático
    trailing_stop:   bool  = False          # activar trailing stop
    trailing_pct:    float = 0.05           # % de trailing desde máximo

    # ── Filtros ───────────────────────────────────────────
    filtrar_mercado: bool  = True           # cancelar si IBEX bajista
    min_volatilidad: float = 0.0            # ATR% mínimo para operar (0 = desactivado)

    # ── Resultado ─────────────────────────────────────────
    guardar_trades:  bool  = True           # guardar detalle de cada trade
    verbose:         bool  = False          # imprimir cada barra procesada

    def __post_init__(self):
        """Validaciones básicas al construir el objeto."""
        assert self.capital_inicial > 0,   "capital_inicial debe ser > 0"
        assert 0 < self.riesgo_pct <= 10,  "riesgo_pct debe estar entre 0 y 10"
        assert self.rr_objetivo >= 1.0,    "rr_objetivo debe ser >= 1.0"
        assert self.estrategia in (
            "breakout", "pullback", "medio", "posicional", "test"
        ), f"estrategia '{self.estrategia}' no reconocida"

    @classmethod
    def para_breakout(cls, **kwargs) -> "ConfigBacktest":
        return cls(estrategia="breakout", periodo="6mo", min_velas=60, **kwargs)

    @classmethod
    def para_pullback(cls, **kwargs) -> "ConfigBacktest":
        return cls(estrategia="pullback", periodo="1y", min_velas=100, **kwargs)

    @classmethod
    def para_medio(cls, **kwargs) -> "ConfigBacktest":
        return cls(estrategia="medio", periodo="2y", min_velas=210, rr_objetivo=2.5, **kwargs)

    @classmethod
    def para_posicional(cls, **kwargs) -> "ConfigBacktest":
        return cls(estrategia="posicional", periodo="2y", min_velas=250,
                   riesgo_pct=0.75, rr_objetivo=3.0, **kwargs)

    @classmethod
    def test(cls, **kwargs) -> "ConfigBacktest":
        return cls(estrategia="test", modo_test=True, verbose=True, **kwargs)
