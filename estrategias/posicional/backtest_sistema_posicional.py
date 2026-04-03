# ==========================================================
# BACKTEST SISTEMA POSICIONAL
# Backtest completo sobre múltiples valores
# ==========================================================

import pandas as pd
import numpy as np
from datetime import datetime
import time

try:
    from .datos_posicional import obtener_datos_semanales, filtrar_universo_posicional
    from .backtest_posicional import ejecutar_backtest_posicional
    from .config_posicional import *
except ImportError:
    from datos_posicional import obtener_datos_semanales, filtrar_universo_posicional
    from backtest_posicional import ejecutar_backtest_posicional
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔙 BACKTEST SISTEMA COMPLETO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ejecutar_backtest_sistema_completo(universo=None, verbose=True):
    """
    Ejecuta backtest sobre todos los valores del universo posicional.

    Args:
        universo:   Lista de tickers (None = IBEX 35 completo)
        verbose:    Mostrar progreso

    Returns:
        dict con resultados agregados
    """
    if verbose:
        print("\n" + "=" * 70)
        print("🚀 BACKTEST SISTEMA POSICIONAL COMPLETO")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # OBTENER UNIVERSO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if universo is None:
        if verbose:
            print("\n🔍 Usando IBEX 35 completo...")
        universo = IBEX_35
        if verbose:
            print(f"  ✅ {len(universo)} valores seleccionados")

    if not universo:
        return {"error": "Universo vacío"}

    if verbose:
        print(f"\n📊 Valores a analizar: {len(universo)}")
        print(f"   {', '.join(universo)}")
        print(f"\n⏱️ Procesando (puede tardar 2-3 minutos)...\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PROCESAR TICKERS SECUENCIALMENTE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    resultados = []
    errores    = []

    # ── Descargar IBEX UNA SOLA VEZ ──────────────────────────────────────
    df_ibex_global = None
    try:
        import yfinance as yf
        import pandas as pd
        print("  📥 Descargando IBEX (^IBEX) una sola vez...")
        time.sleep(3)
        ibex_obj = yf.Ticker("^IBEX")
        datos_ibex = ibex_obj.history(period="10y", interval="1d")
        if not datos_ibex.empty:
            if datos_ibex.index.tz is not None:
                datos_ibex.index = datos_ibex.index.tz_localize(None)
            if isinstance(datos_ibex.columns, pd.MultiIndex):
                datos_ibex.columns = datos_ibex.columns.get_level_values(0)
            df_ibex_global = datos_ibex
            print(f"  ✅ IBEX descargado: {len(df_ibex_global)} días")
        else:
            print("  ⚠️ IBEX sin datos — el filtro de mercado se omitirá")
    except Exception as e:
        print(f"  ⚠️ No se pudo descargar IBEX ({e}) — el filtro de mercado se omitirá")
    # ─────────────────────────────────────────────────────────────────────

    def procesar_ticker(ticker):
        max_intentos = 3
        # En local usamos menos años para no saturar yfinance
        import os
        años = AÑOS_BACKTEST if os.getenv("ENTORNO", "local") != "local" else min(AÑOS_BACKTEST, 10)
        for intento in range(max_intentos):
            try:
                # Sleep progresivo reducido — ya no descargamos IBEX por ticker
                sleep_time = 1.0 + intento * 1.5
                time.sleep(sleep_time)

                df, _ = obtener_datos_semanales(ticker, periodo_años=años, validar=False)

                if df is None or df.empty:
                    print(f"  ❌ {ticker}: Sin datos")
                    return {"ticker": ticker, "error": "Sin datos"}

                print(f"  📊 {ticker}: {len(df)} semanas de datos")

                resultado = ejecutar_backtest_posicional(df, ticker, verbose=False,
                                                         df_ibex=df_ibex_global)

                trades = resultado.get("total_trades", 0)
                print(f"  {'✅' if trades > 0 else '⚠️'} {ticker}: {trades} trades")

                return resultado

            except Exception as e:
                err_str = str(e).lower()
                if "rate" in err_str or "429" in err_str or "too many" in err_str or                    "500" in err_str or "internal-error" in err_str:
                    wait = 5 * (intento + 1)  # 5s, 10s, 15s
                    if intento < max_intentos - 1:
                        if verbose:
                            print(f"  ⏳ {ticker}: rate limit, esperando {wait}s... ({intento+1}/{max_intentos})")
                        time.sleep(wait)
                        continue
                    else:
                        return {"ticker": ticker, "error": f"Rate limit tras {max_intentos} intentos"}
                else:
                    return {"ticker": ticker, "error": str(e)}

        return {"ticker": ticker, "error": "No se pudo procesar"}

    for i_ticker, ticker in enumerate(universo):
        # Pausa adicional cada 5 tickers para evitar rate limit
        if i_ticker > 0 and i_ticker % 5 == 0:
            if verbose:
                print(f"  ⏸️ Pausa anti-rate-limit ({i_ticker}/{len(universo)})...")
            time.sleep(8)
        try:
            resultado = procesar_ticker(ticker)

            if "error" in resultado:
                errores.append(resultado)
                if verbose:
                    print(f"  ⚠️ {ticker}: {resultado['error']}")
            else:
                resultados.append(resultado)
                if verbose:
                    exp    = resultado.get("expectancy", 0)
                    trades = resultado.get("total_trades", 0)
                    sharpe = resultado.get("sharpe", 0)
                    signo  = "✅" if exp > 0 else "❌"
                    print(f"  {signo} {ticker:12s} | {trades:3d} trades | "
                          f"{exp:+.2f}R expectancy | Sharpe: {sharpe:.2f}")

        except Exception as e:
            errores.append({"ticker": ticker, "error": str(e)})
            if verbose:
                print(f"  ❌ {ticker}: Error procesando")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS GLOBALES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if not resultados:
        return {
            "error":           "No se pudieron procesar valores",
            "tickers_error":   len(errores),
            "errores":         errores
        }

    metricas_globales = calcular_metricas_sistema(resultados)
    metricas_globales["tickers_analizados"]    = len(resultados)
    metricas_globales["tickers_con_error"]     = len(errores)
    metricas_globales["total_tickers"]         = len(universo)
    metricas_globales["resultados_detallados"] = resultados
    metricas_globales["errores"]               = errores

    if verbose:
        mostrar_resumen_sistema(metricas_globales)

    return metricas_globales


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 MÉTRICAS DEL SISTEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_metricas_sistema(resultados):
    """
    Calcula métricas agregadas del sistema completo.

    Returns:
        dict con métricas globales
    """
    total_trades          = sum(r.get("total_trades", 0) for r in resultados)
    todos_trades_ganadores= sum(r.get("trades_ganadores", 0) for r in resultados)

    if total_trades > 0:
        expectancy_global = sum(
            r.get("expectancy", 0) * r.get("total_trades", 0)
            for r in resultados
        ) / total_trades
        winrate_global = (todos_trades_ganadores / total_trades * 100)
    else:
        expectancy_global = 0
        winrate_global    = 0

    equity_total = sum(r.get("equity_final", 0) for r in resultados)

    resultados_con_trades = [r for r in resultados if r.get("total_trades", 0) > 0]

    if resultados_con_trades:
        mejor_ticker = max(resultados_con_trades, key=lambda x: x.get("expectancy", 0))
        peor_ticker  = min(resultados_con_trades, key=lambda x: x.get("expectancy", 0))
    else:
        mejor_ticker = None
        peor_ticker  = None

    suma_ganadores  = sum(
        r.get("trades_ganadores", 0) * r.get("r_medio_ganador", 0)
        for r in resultados
    )
    suma_perdedores = abs(sum(
        r.get("trades_perdedores", 0) * r.get("r_medio_perdedor", 0)
        for r in resultados
    ))
    profit_factor_global = suma_ganadores / suma_perdedores if suma_perdedores > 0 else 0

    tickers_rentables    = len([r for r in resultados if r.get("expectancy", 0) > 0])
    tickers_no_rentables = len([r for r in resultados if r.get("expectancy", 0) <= 0])

    duraciones           = [r.get("duracion_media", 0) for r in resultados if r.get("duracion_media", 0) > 0]
    duracion_media_global= sum(duraciones) / len(duraciones) if duraciones else 0

    # Sharpe medio (solo tickers con >2 trades)
    sharpes     = [r.get("sharpe", 0) for r in resultados if r.get("total_trades", 0) > 2]
    sharpe_medio= sum(sharpes) / len(sharpes) if sharpes else 0

    # Max drawdown medio
    drawdowns    = [r.get("max_drawdown", 0) for r in resultados if r.get("total_trades", 0) > 0]
    dd_medio     = sum(drawdowns) / len(drawdowns) if drawdowns else 0

    return {
        "total_trades":          total_trades,
        "expectancy_global":     round(expectancy_global, 2),
        "winrate_global":        round(winrate_global, 1),
        "equity_total":          round(equity_total, 2),
        "profit_factor_global":  round(profit_factor_global, 2),
        "mejor_ticker":          mejor_ticker,
        "peor_ticker":           peor_ticker,
        "tickers_rentables":     tickers_rentables,
        "tickers_no_rentables":  tickers_no_rentables,
        "duracion_media_global": round(duracion_media_global, 1),
        "sharpe_medio":          round(sharpe_medio, 2),
        "dd_medio":              round(dd_medio, 2)
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 MOSTRAR RESUMEN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mostrar_resumen_sistema(metricas):
    """Muestra resumen formateado del backtest."""

    print("\n" + "=" * 70)
    print("📊 RESULTADOS DEL SISTEMA POSICIONAL")
    print("=" * 70)

    print(f"\n📈 MÉTRICAS GLOBALES:")
    print(f"  Valores analizados: {metricas['tickers_analizados']}")
    print(f"  Total trades:       {metricas['total_trades']}")
    print(f"  Expectancy:         {metricas['expectancy_global']}R")
    print(f"  Winrate:            {metricas['winrate_global']}%")
    print(f"  Equity total:       {metricas['equity_total']:+.2f}R")
    print(f"  Profit Factor:      {metricas['profit_factor_global']}")
    print(f"  Sharpe medio:       {metricas['sharpe_medio']:.2f}")
    print(f"  Drawdown medio:     {metricas['dd_medio']:.2f}R")
    print(f"  Duración media:     {metricas['duracion_media_global']:.0f} sem "
          f"({metricas['duracion_media_global']/52:.1f} años)")

    print(f"\n📊 BALANCE POR TICKER:")
    print(f"  Rentables:      {metricas['tickers_rentables']}")
    print(f"  No rentables:   {metricas['tickers_no_rentables']}")
    pct = metricas['tickers_rentables'] / (
        metricas['tickers_rentables'] + metricas['tickers_no_rentables']
    ) * 100 if (metricas['tickers_rentables'] + metricas['tickers_no_rentables']) > 0 else 0
    print(f"  % Rentabilidad: {pct:.1f}%")

    resultados = metricas.get("resultados_detallados", [])

    print(f"\n🏆 TOP 5 MEJORES VALORES:")
    top5 = sorted(
        [r for r in resultados if r.get("total_trades", 0) > 0],
        key=lambda x: x.get("expectancy", 0),
        reverse=True
    )[:5]
    for i, r in enumerate(top5, 1):
        print(f"  {i}. {r.get('ticker','N/A'):12s} | "
              f"{r.get('total_trades',0):2d} trades | "
              f"{r.get('expectancy',0):+.2f}R | "
              f"WR:{r.get('winrate',0):4.1f}% | "
              f"Sharpe:{r.get('sharpe',0):.2f} | "
              f"Equity:{r.get('equity_final',0):+6.2f}R")

    print(f"\n💀 TOP 5 PEORES VALORES:")
    bottom5 = sorted(
        [r for r in resultados if r.get("total_trades", 0) > 0],
        key=lambda x: x.get("expectancy", 0)
    )[:5]
    for i, r in enumerate(bottom5, 1):
        print(f"  {i}. {r.get('ticker','N/A'):12s} | "
              f"{r.get('total_trades',0):2d} trades | "
              f"{r.get('expectancy',0):+.2f}R | "
              f"WR:{r.get('winrate',0):4.1f}% | "
              f"Sharpe:{r.get('sharpe',0):.2f} | "
              f"Equity:{r.get('equity_final',0):+6.2f}R")

    if metricas.get("tickers_con_error", 0) > 0:
        print(f"\n⚠️ Valores con error: {metricas['tickers_con_error']}")

    print(f"\n🎯 EVALUACIÓN:")
    exp = metricas['expectancy_global']
    sharpe = metricas['sharpe_medio']
    if exp >= 2.0 and sharpe >= 1.0:
        print(f"  ✅ EXCELENTE — Expectancy {exp}R y Sharpe {sharpe} superan objetivos")
    elif exp >= 1.0:
        print(f"  ✅ MUY BUENO — Expectancy {exp}R es bueno para posicional")
    elif exp >= 0.5:
        print(f"  ⚠️ ACEPTABLE — Expectancy {exp}R es marginal, revisar parámetros")
    else:
        print(f"  ❌ NO RENTABLE — Expectancy {exp}R es insuficiente")

    print("\n" + "=" * 70)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test backtest_sistema_posicional.py")

    resultado = ejecutar_backtest_sistema_completo(verbose=True)

    if "error" not in resultado:
        print(f"\n✅ Backtest completado exitosamente")
    else:
        print(f"\n❌ Error: {resultado['error']}")
