# estrategias/medio/backtest_sistema_medio.py
# Backtest multi-ticker del sistema medio plazo completo

from datetime import datetime
import numpy as np
from estrategias.medio.config_medio import MIN_SEMANAS_HISTORICO, TICKER_EMPRESA
from core.data_provider import get_df_semanal
from estrategias.medio.backtest_medio import ejecutar_backtest_medio_plazo


# ──────────────────────────────────────────────────────────
# BACKTEST MULTI-TICKER
# ──────────────────────────────────────────────────────────

def ejecutar_backtest_sistema_completo(universo=None, verbose=True, usar_continuo=False):
    """
    Ejecuta backtest sobre todo el universo de valores.
    Returns dict con resultados agregados compatible con backtest_sistema_medio.html
    """
    from core.universos import IBEX35, CONTINUO

    if universo is None:
        universo = IBEX35.copy()
        if usar_continuo:
            universo.extend(CONTINUO)

    if verbose:
        print(f"\n🚀 BACKTEST SISTEMA MEDIO PLAZO — {len(universo)} valores")

    resultados_por_ticker = []
    todos_los_trades      = []
    tickers_con_error     = []
    tickers_sin_datos     = []

    for i, ticker in enumerate(universo, 1):
        if verbose:
            print(f"  [{i}/{len(universo)}] {ticker}...", end=" ")

        try:
            df_semanal, validacion = get_df_semanal(ticker, periodo_años=10)

            if df_semanal is None or len(df_semanal) < MIN_SEMANAS_HISTORICO:
                if verbose:
                    print("❌ Sin datos")
                tickers_sin_datos.append(ticker)
                continue

            resultado_bt = ejecutar_backtest_medio_plazo(df_semanal, ticker, verbose=False)

            if resultado_bt["trades"]:
                m = resultado_bt["metricas"]
                resultados_por_ticker.append({
                    "ticker":           ticker,
                    "empresa":          TICKER_EMPRESA.get(ticker, ticker.replace(".MC", "")),
                    "total_trades":     m["total_trades"],
                    "expectancy_R":     m["expectancy_R"],
                    "winrate":          m["winrate"],
                    "profit_factor":    m["profit_factor"],
                    "equity_final_R":   m["equity_final_R"],
                    "mejor_trade":      m["mejor_trade"],
                    "peor_trade":       m["peor_trade"],
                    "max_drawdown_R":   m["max_drawdown_R"],
                    "semanas_historico": len(df_semanal),
                })
                for trade in resultado_bt["trades"]:
                    t = trade.copy()
                    t["ticker"] = ticker
                    todos_los_trades.append(t)
                if verbose:
                    print(f"✅ {m['total_trades']} trades | Exp: {m['expectancy_R']:+.2f}R")
            else:
                if verbose:
                    print("⚠️  0 trades")

        except Exception as e:
            if verbose:
                print(f"❌ Error: {str(e)[:60]}")
            tickers_con_error.append(ticker)

    metricas_globales = _calcular_metricas_globales(todos_los_trades, resultados_por_ticker)
    top_performers    = _identificar_top_performers(resultados_por_ticker)

    return {
        "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "universo": {
            "total_tickers": len(universo),
            "analizados":    len(resultados_por_ticker),
            "sin_datos":     len(tickers_sin_datos),
            "con_error":     len(tickers_con_error),
            "sin_trades":    len(universo) - len(resultados_por_ticker) - len(tickers_sin_datos) - len(tickers_con_error),
        },
        "metricas_globales":      metricas_globales,
        "resultados_por_ticker":  resultados_por_ticker,
        "top_performers":         top_performers,
        "todos_los_trades":       todos_los_trades,
        "tickers_sin_datos":      tickers_sin_datos,
        "tickers_con_error":      tickers_con_error,
    }


# ──────────────────────────────────────────────────────────
# MÉTRICAS GLOBALES
# ──────────────────────────────────────────────────────────

def _calcular_metricas_globales(todos_los_trades, resultados_por_ticker):
    if not todos_los_trades:
        return {
            "total_trades": 0, "expectancy_R": 0, "winrate": 0,
            "avg_winner": 0, "avg_loser": 0, "profit_factor": 0,
            "mejor_trade": 0, "peor_trade": 0, "max_drawdown_R": 0,
            "equity_final_R": 0, "equity_curve": [0],
            "expectancy_promedio_ticker": 0,
            "tickers_rentables": 0, "tickers_no_rentables": 0,
        }

    Rs      = [t["R"] for t in todos_los_trades]
    winners = [r for r in Rs if r > 0]
    losers  = [r for r in Rs if r <= 0]

    equity_curve = [0]
    for r in Rs:
        equity_curve.append(equity_curve[-1] + r)

    eq  = np.array(equity_curve)
    dd  = float(min(eq - np.maximum.accumulate(eq))) if len(eq) > 1 else 0
    pf  = sum(winners) / abs(sum(losers)) if losers else 0

    expectancies            = [r["expectancy_R"] for r in resultados_por_ticker]
    exp_promedio_ticker     = sum(expectancies) / len(expectancies) if expectancies else 0
    tickers_rentables       = len([r for r in resultados_por_ticker if r["expectancy_R"] > 0])

    return {
        "total_trades":              len(Rs),
        "expectancy_R":              round(sum(Rs) / len(Rs), 2),
        "winrate":                   round(len(winners) / len(Rs) * 100, 1),
        "avg_winner":                round(sum(winners) / len(winners), 2) if winners else 0,
        "avg_loser":                 round(sum(losers)  / len(losers),  2) if losers  else 0,
        "profit_factor":             round(pf, 2),
        "mejor_trade":               round(max(Rs), 2),
        "peor_trade":                round(min(Rs), 2),
        "max_drawdown_R":            round(dd, 2),
        "equity_final_R":            round(equity_curve[-1], 2),
        "equity_curve":              equity_curve,
        "expectancy_promedio_ticker": round(exp_promedio_ticker, 2),
        "tickers_rentables":         tickers_rentables,
        "tickers_no_rentables":      len(resultados_por_ticker) - tickers_rentables,
    }


def _identificar_top_performers(resultados_por_ticker, n=5):
    if not resultados_por_ticker:
        return {"mejores": [], "peores": []}
    ordenados = sorted(resultados_por_ticker, key=lambda x: x["expectancy_R"], reverse=True)
    return {"mejores": ordenados[:n], "peores": ordenados[-n:][::-1]}
