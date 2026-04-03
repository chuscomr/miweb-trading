# backtest/metrics.py
# ══════════════════════════════════════════════════════════════
# MÉTRICAS — Cálculo de estadísticas del backtest
# ══════════════════════════════════════════════════════════════

import numpy as np
from typing import List
from .trade import Trade


def calcular_metricas(trades: List[Trade], equity: List[float], capital_inicial: float) -> dict:
    """
    Calcula métricas completas de rendimiento a partir del historial de trades.

    Args:
        trades:           Lista de Trade cerrados
        equity:           Curva de equity (lista de floats)
        capital_inicial:  Capital de inicio del backtest

    Returns:
        dict con todas las métricas de rendimiento
    """
    if not trades:
        return _metricas_vacias()

    Rs            = [t.R for t in trades]
    ganadoras     = [t for t in trades if t.ganadora]
    perdedoras    = [t for t in trades if not t.ganadora]
    duraciones    = [t.duracion_dias for t in trades]
    resultados    = [t.resultado_neto for t in trades]

    # ── Básicas ───────────────────────────────────────────
    n_trades      = len(trades)
    n_ganadoras   = len(ganadoras)
    winrate       = n_ganadoras / n_trades if n_trades else 0
    expectancy_R  = float(np.mean(Rs)) if Rs else 0

    # ── Profit factor ─────────────────────────────────────
    ganancias_totales = sum(t.resultado_neto for t in ganadoras)
    perdidas_totales  = abs(sum(t.resultado_neto for t in perdedoras))
    profit_factor     = (ganancias_totales / perdidas_totales
                         if perdidas_totales > 0 else float("inf"))

    # ── Drawdown máximo ───────────────────────────────────
    max_dd_pct = _calcular_max_drawdown(equity)

    # ── Rentabilidad ──────────────────────────────────────
    capital_final        = equity[-1] if equity else capital_inicial
    rentabilidad_total   = ((capital_final - capital_inicial) / capital_inicial) * 100
    ganancia_media       = float(np.mean([t.resultado_neto for t in ganadoras])) if ganadoras else 0
    perdida_media        = float(np.mean([t.resultado_neto for t in perdedoras])) if perdedoras else 0

    # ── Duración ──────────────────────────────────────────
    duracion_media = float(np.mean(duraciones)) if duraciones else 0
    duracion_max   = max(duraciones) if duraciones else 0

    # ── Racha ─────────────────────────────────────────────
    racha_ganadora, racha_perdedora = _calcular_rachas(trades)

    # ── Sharpe simplificado ───────────────────────────────
    sharpe = _calcular_sharpe(equity)

    return {
        # Básicas
        "n_trades":            n_trades,
        "n_ganadoras":         n_ganadoras,
        "n_perdedoras":        len(perdedoras),
        "winrate":             round(winrate * 100, 2),
        "expectancy_R":        round(expectancy_R, 2),
        # Rentabilidad
        "capital_inicial":     round(capital_inicial, 2),
        "capital_final":       round(capital_final, 2),
        "rentabilidad_pct":    round(rentabilidad_total, 2),
        "ganancia_media":      round(ganancia_media, 2),
        "perdida_media":       round(perdida_media, 2),
        "profit_factor":       round(profit_factor, 2),
        # Riesgo
        "max_drawdown_pct":    round(max_dd_pct, 2),
        "sharpe":              round(sharpe, 2),
        # Operativa
        "duracion_media_dias": round(duracion_media, 1),
        "duracion_max_dias":   duracion_max,
        "racha_ganadora":      racha_ganadora,
        "racha_perdedora":     racha_perdedora,
        # Motivos de salida
        "salidas_stop":        sum(1 for t in trades if t.motivo_salida == "STOP"),
        "salidas_target":      sum(1 for t in trades if t.motivo_salida == "TARGET"),
        "salidas_trailing":    sum(1 for t in trades if t.motivo_salida == "TRAILING"),
        "salidas_fin":         sum(1 for t in trades if t.motivo_salida == "FIN_BACKTEST"),
    }


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _calcular_max_drawdown(equity: List[float]) -> float:
    """Drawdown máximo en % sobre la curva de equity."""
    if len(equity) < 2:
        return 0.0
    max_dd = 0.0
    peak   = equity[0]
    for e in equity:
        peak   = max(peak, e)
        dd     = (peak - e) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return max_dd * 100


def _calcular_rachas(trades: List[Trade]) -> tuple:
    """Devuelve (racha_ganadora_max, racha_perdedora_max)."""
    racha_g = racha_p = 0
    max_g   = max_p   = 0
    for t in trades:
        if t.ganadora:
            racha_g += 1
            racha_p  = 0
        else:
            racha_p += 1
            racha_g  = 0
        max_g = max(max_g, racha_g)
        max_p = max(max_p, racha_p)
    return max_g, max_p


def _calcular_sharpe(equity: List[float], rf: float = 0.0) -> float:
    """Sharpe ratio simplificado sobre retornos diarios."""
    if len(equity) < 2:
        return 0.0
    retornos = np.diff(equity) / np.array(equity[:-1])
    if retornos.std() == 0:
        return 0.0
    return float((retornos.mean() - rf) / retornos.std() * np.sqrt(252))


def _metricas_vacias() -> dict:
    return {
        "n_trades": 0, "n_ganadoras": 0, "n_perdedoras": 0,
        "winrate": 0, "expectancy_R": 0, "capital_inicial": 0,
        "capital_final": 0, "rentabilidad_pct": 0, "ganancia_media": 0,
        "perdida_media": 0, "profit_factor": 0, "max_drawdown_pct": 0,
        "sharpe": 0, "duracion_media_dias": 0, "duracion_max_dias": 0,
        "racha_ganadora": 0, "racha_perdedora": 0, "salidas_stop": 0,
        "salidas_target": 0, "salidas_trailing": 0, "salidas_fin": 0,
    }
