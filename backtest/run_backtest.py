# backtest/run_backtest.py
# ══════════════════════════════════════════════════════════════
# RUN BACKTEST — Punto de entrada único para ejecutar backtests
#
# Uso desde Flask (ruta):
#     resultado = ejecutar_backtest("BBVA.MC", config, cache)
#
# Uso desde CLI / notebook:
#     resultado = ejecutar_backtest("BBVA.MC", ConfigBacktest.para_breakout())
# ══════════════════════════════════════════════════════════════

import logging
from typing import Optional

from core.data_provider import get_df, get_df_con_fallback
from .config_backtest import ConfigBacktest
from .engine import BacktestEngine

logger = logging.getLogger(__name__)

# Mapa de estrategia → clase
def _cargar_estrategia(nombre: str):
    """Instancia la estrategia correcta según el nombre en config."""
    if nombre == "breakout":
        from estrategias.swing.breakout import BreakoutSwing
        return BreakoutSwing()
    if nombre == "pullback":
        from estrategias.swing.pullback import PullbackSwing
        return PullbackSwing()
    if nombre == "medio":
        from estrategias.medio.logica_medio import MedioPlazo
        return MedioPlazo()
    if nombre == "posicional":
        from estrategias.posicional.logica_posicional import Posicional
        return Posicional()
    if nombre in ("test", "simple"):
        from estrategias.swing.breakout import BreakoutSwing   # usa breakout como test
        return BreakoutSwing()
    raise ValueError(f"Estrategia '{nombre}' no reconocida")


def ejecutar_backtest(
    ticker:  str,
    config:  ConfigBacktest = None,
    cache=None,
) -> dict:
    """
    Ejecuta un backtest completo para un ticker.

    Args:
        ticker:  Ticker de Yahoo Finance (ej: "BBVA.MC")
        config:  ConfigBacktest. Si es None usa valores por defecto.
        cache:   Cache Flask (opcional)

    Returns:
        dict con 'metricas', 'trades', 'equity', 'config', 'error'
    """
    if config is None:
        config = ConfigBacktest()

    # ── Cargar datos ──────────────────────────────────────
    df = get_df_con_fallback(ticker, periodo=config.periodo, cache=cache)

    if df is None or len(df) < config.min_velas:
        msg = f"Datos insuficientes para {ticker} ({0 if df is None else len(df)} velas)"
        logger.warning(f"⚠️ {msg}")
        return {"error": msg, "metricas": None, "trades": [], "equity": []}

    # ── Cargar estrategia ─────────────────────────────────
    try:
        estrategia = _cargar_estrategia(config.estrategia)
    except ValueError as e:
        return {"error": str(e), "metricas": None, "trades": [], "equity": []}

    # ── Ejecutar engine ───────────────────────────────────
    engine    = BacktestEngine(df=df, estrategia=estrategia, config=config, ticker=ticker)
    resultado = engine.run()
    resultado["error"] = None

    logger.info(
        f"✅ Backtest {ticker} completado: "
        f"{resultado['metricas']['n_trades']} trades · "
        f"rentabilidad={resultado['metricas']['rentabilidad_pct']}%"
    )

    return resultado


def ejecutar_backtest_multiticker(
    tickers: list,
    config:  ConfigBacktest = None,
    cache=None,
    top_n:   int = None,
) -> dict:
    """
    Ejecuta el backtest sobre una lista de tickers y agrega resultados.

    Returns:
        dict con 'resultados' (por ticker), 'resumen' (métricas agregadas)
    """
    if config is None:
        config = ConfigBacktest()

    resultados = {}
    for ticker in tickers:
        try:
            resultados[ticker] = ejecutar_backtest(ticker, config, cache)
        except Exception as e:
            logger.error(f"❌ Backtest {ticker}: {e}")
            resultados[ticker] = {"error": str(e), "metricas": None}

    # Resumen agregado
    validos = [r for r in resultados.values() if r.get("metricas")]
    resumen = {
        "total_tickers":   len(tickers),
        "tickers_validos": len(validos),
        "rentabilidad_media": round(
            sum(r["metricas"]["rentabilidad_pct"] for r in validos) / len(validos), 2
        ) if validos else 0,
        "winrate_medio": round(
            sum(r["metricas"]["winrate"] for r in validos) / len(validos), 2
        ) if validos else 0,
        "max_drawdown_medio": round(
            sum(r["metricas"]["max_drawdown_pct"] for r in validos) / len(validos), 2
        ) if validos else 0,
    }

    # Ordenar por rentabilidad si se pide top_n
    if top_n:
        ranking = sorted(
            [(t, r) for t, r in resultados.items() if r.get("metricas")],
            key=lambda x: x[1]["metricas"]["rentabilidad_pct"],
            reverse=True,
        )[:top_n]
        resumen["top"] = [{"ticker": t, **r["metricas"]} for t, r in ranking]

    return {"resultados": resultados, "resumen": resumen}
