# ==========================================================
# BACKTEST POSICIONAL
# Motor de backtest para un ticker individual
# ==========================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from .datos_posicional import obtener_datos_semanales
    from .sistema_trading_posicional import evaluar_entrada_posicional
    from .gestion_posicional import PosicionPosicional
    from .config_posicional import *
except ImportError:
    from estrategias.posicional.datos_posicional import obtener_datos_semanales
    from estrategias.posicional.sistema_trading_posicional import evaluar_entrada_posicional
    from estrategias.posicional.gestion_posicional import PosicionPosicional
    from estrategias.posicional.config_posicional import *

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔙 BACKTEST INDIVIDUAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ejecutar_backtest_posicional(df_semanal, ticker, verbose=False, df_ibex=None):
    """
    Ejecuta backtest posicional sobre un ticker.

    ESTRATEGIA:
    - Evaluación semanal
    - Una posición a la vez
    - Stops amplios (6-15%)
    - Trailing conservador desde +8R
    - Duración mínima 26 semanas

    Args:
        df_semanal: DataFrame con datos semanales (OHLCV)
        ticker: Símbolo del ticker
        verbose: Mostrar progreso

    Returns:
        dict con resultados del backtest
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"🔙 BACKTEST POSICIONAL: {ticker}")
        print(f"{'='*60}")

    if df_semanal is None or df_semanal.empty:
        return {"error": "Sin datos"}

    if len(df_semanal) < MIN_SEMANAS_HISTORICO:
        return {"error": f"Histórico insuficiente ({len(df_semanal)} semanas)"}

    precios   = df_semanal['Close'].values
    volumenes = df_semanal['Volume'].values
    fechas    = df_semanal.index

    trades        = []
    posicion_actual = None
    equity_curve  = []
    r_acumulado   = 0.0

    COSTE_TOTAL = (COMISION_PCT + SLIPPAGE_PCT) / 100  # ida y vuelta × 2 se aplica abajo

    if verbose:
        print(f"  Periodo: {fechas[0].date()} a {fechas[-1].date()}")
        print(f"  Semanas: {len(df_semanal)}")
        print(f"  Buscando señales...\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ITERAR SEMANA A SEMANA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    for i in range(MIN_SEMANAS_HISTORICO, len(df_semanal)):
        fecha_actual  = fechas[i]
        precio_actual = precios[i]
        high_actual   = df_semanal['High'].iloc[i]
        low_actual    = df_semanal['Low'].iloc[i]

        precios_hist  = precios[:i+1]
        volumenes_hist = volumenes[:i+1]
        df_hist       = df_semanal.iloc[:i+1]

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # GESTIÓN DE POSICIÓN ABIERTA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        if posicion_actual is not None:
            debe_salir, motivo_salida = posicion_actual.actualizar(
                fecha_actual,
                precio_actual,
                high=high_actual,
                low=low_actual
            )

            if debe_salir:
                # CORRECCIÓN: precio de salida según motivo real
                motivo_lower = motivo_salida.lower()
                if "stop" in motivo_lower:
                    precio_salida = posicion_actual.stop  # salida en stop
                else:
                    precio_salida = precio_actual  # trailing, tiempo, etc.

                # Calcular R bruto
                r_trade = posicion_actual.calcular_R_actual(precio_salida)

                # Cap de seguridad: la pérdida máxima por stop nunca puede
                # superar -1.5R (evita distorsiones por R_unit muy pequeño)
                if "stop" in motivo_lower and r_trade < -1.5:
                    r_trade = -1.0  # pérdida estándar de 1R

                # Descontar costes de transacción (ida + vuelta)
                riesgo_euros = abs(posicion_actual.entrada - posicion_actual.stop_inicial)
                if riesgo_euros > 0:
                    coste_r = (posicion_actual.entrada * COSTE_TOTAL * 2) / riesgo_euros
                    r_trade -= coste_r

                # Advertencia stop ajustado
                advertencia = None
                riesgo_pct_entrada = (riesgo_euros / posicion_actual.entrada) * 100
                if RIESGO_MIN_PCT <= riesgo_pct_entrada < 8.0:
                    advertencia = "⚠️ Stop ajustado (6-8%), posible impacto por ruido semanal"

                trade_info = {
                    "entrada":       posicion_actual.entrada,
                    "salida":        precio_salida,
                    "fecha_entrada": posicion_actual.fecha_apertura,
                    "fecha_salida":  fecha_actual,
                    "stop_inicial":  posicion_actual.stop_inicial,
                    "r":             round(r_trade, 2),
                    "semanas":       posicion_actual.semanas_en_posicion,
                    "motivo_salida": motivo_salida,
                    "estado_final":  posicion_actual.estado,
                    "advertencia":   advertencia
                }

                trades.append(trade_info)
                r_acumulado += r_trade

                if verbose:
                    signo = "✅" if r_trade > 0 else "❌"
                    adv   = f" {advertencia}" if advertencia else ""
                    print(f"  {signo} Trade #{len(trades):2d}: {r_trade:+.2f}R | "
                          f"{posicion_actual.semanas_en_posicion} sem | {motivo_salida}{adv}")

                posicion_actual = None

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BUSCAR NUEVA ENTRADA (si no hay posición)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        if posicion_actual is None:
            evaluacion = evaluar_entrada_posicional(
                precios_hist,
                volumenes_hist,
                fechas=fechas[:i+1],
                df=df_hist,
                df_ibex=df_ibex
            )

            if evaluacion["decision"] == "COMPRA":
                # Usar trigger si existe, si no precio actual
                trigger = evaluacion.get("trigger", evaluacion["entrada"])
                entrada = trigger

                # Recalcular stop con entrada=trigger para que R_unit sea correcto
                # (el stop de evaluacion se calculó con precio_actual, no con trigger)
                from estrategias.posicional.logica_posicional import calcular_stop_inicial
                stop = calcular_stop_inicial(entrada, precios_hist, df_hist)

                posicion_actual = PosicionPosicional(entrada, stop, fecha_actual)

                if verbose:
                    print(f"  🔵 Nueva entrada en {fecha_actual.date()}")
                    print(f"     Trigger: {trigger:.2f} | Stop: {stop:.2f} | "
                          f"Riesgo: {evaluacion['riesgo_pct']:.1f}%")
                    if evaluacion.get("advertencia"):
                        print(f"     {evaluacion['advertencia']}")

        equity_curve.append(r_acumulado)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CERRAR POSICIÓN ABIERTA AL FINAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if posicion_actual is not None:
        precio_final = precios[-1]
        r_trade      = posicion_actual.calcular_R_actual(precio_final)

        # Descontar costes
        riesgo_euros = abs(posicion_actual.entrada - posicion_actual.stop_inicial)
        if riesgo_euros > 0:
            coste_r = (posicion_actual.entrada * COSTE_TOTAL * 2) / riesgo_euros
            r_trade -= coste_r

        trade_info = {
            "entrada":       posicion_actual.entrada,
            "salida":        precio_final,
            "fecha_entrada": posicion_actual.fecha_apertura,
            "fecha_salida":  fechas[-1],
            "stop_inicial":  posicion_actual.stop_inicial,
            "r":             round(r_trade, 2),
            "semanas":       posicion_actual.semanas_en_posicion,
            "motivo_salida": "Fin backtest",
            "estado_final":  posicion_actual.estado,
            "advertencia":   None
        }

        trades.append(trade_info)
        r_acumulado += r_trade

        if verbose:
            print(f"  🔵 Posición abierta al final: {r_trade:+.2f}R")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    metricas          = calcular_metricas(trades, equity_curve)
    metricas["ticker"] = ticker

    if verbose:
        print(f"\n📊 RESUMEN {ticker}:")
        print(f"  Total trades:   {metricas['total_trades']}")
        print(f"  Ganadores:      {metricas['trades_ganadores']} ({metricas['winrate']:.1f}%)")
        print(f"  Expectancy:     {metricas['expectancy']:.2f}R")
        print(f"  Equity final:   {metricas['equity_final']:.2f}R")
        print(f"  Sharpe:         {metricas['sharpe']:.2f}")
        print(f"  Mejor trade:    {metricas['mejor_trade']:.2f}R")
        print(f"  Peor trade:     {metricas['peor_trade']:.2f}R")
        print(f"  Duración media: {metricas['duracion_media']:.0f} semanas")
        print(f"{'='*60}\n")

    return metricas


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CÁLCULO DE MÉTRICAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_metricas(trades, equity_curve):
    """
    Calcula métricas de rendimiento.

    Returns:
        dict con todas las métricas
    """
    if not trades:
        return {
            "total_trades":     0,
            "trades_ganadores": 0,
            "trades_perdedores":0,
            "winrate":          0.0,
            "expectancy":       0.0,
            "equity_final":     0.0,
            "profit_factor":    0.0,
            "mejor_trade":      0.0,
            "peor_trade":       0.0,
            "r_medio_ganador":  0.0,
            "r_medio_perdedor": 0.0,
            "max_drawdown":     0.0,
            "duracion_media":   0.0,
            "sharpe":           0.0,
            "trades":           []
        }

    rs          = [t["r"] for t in trades]
    ganadores   = [r for r in rs if r > 0]
    perdedores  = [r for r in rs if r <= 0]

    total       = len(trades)
    n_ganadores = len(ganadores)
    n_perdedores= len(perdedores)

    winrate     = (n_ganadores / total * 100) if total > 0 else 0
    expectancy  = sum(rs) / total if total > 0 else 0
    equity_final= sum(rs)

    suma_ganadores  = sum(ganadores) if ganadores else 0
    suma_perdedores = abs(sum(perdedores)) if perdedores else 0
    profit_factor   = suma_ganadores / suma_perdedores if suma_perdedores > 0 else 0

    mejor = max(rs) if rs else 0
    peor  = min(rs) if rs else 0

    r_medio_ganador  = sum(ganadores) / len(ganadores) if ganadores else 0
    r_medio_perdedor = sum(perdedores) / len(perdedores) if perdedores else 0

    # Max drawdown
    max_dd = 0
    if equity_curve:
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = peak - val
            if dd > max_dd:
                max_dd = dd

    # Duración media
    duraciones    = [t.get("semanas", 0) for t in trades]
    duracion_media = sum(duraciones) / len(duraciones) if duraciones else 0

    # Sharpe ratio anualizado sobre R (base semanal)
    rs_array = np.array(rs)
    if len(rs_array) > 1 and rs_array.std() > 0:
        sharpe = (rs_array.mean() / rs_array.std()) * (52 ** 0.5)
    else:
        sharpe = 0.0

    return {
        "total_trades":     total,
        "trades_ganadores": n_ganadores,
        "trades_perdedores":n_perdedores,
        "winrate":          round(winrate, 1),
        "expectancy":       round(expectancy, 2),
        "equity_final":     round(equity_final, 2),
        "profit_factor":    round(profit_factor, 2),
        "mejor_trade":      round(mejor, 2),
        "peor_trade":       round(peor, 2),
        "r_medio_ganador":  round(r_medio_ganador, 2),
        "r_medio_perdedor": round(r_medio_perdedor, 2),
        "max_drawdown":     round(max_dd, 2),
        "duracion_media":   round(duracion_media, 1),
        "sharpe":           round(sharpe, 2),
        "trades":           trades
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test backtest_posicional.py")
    print("=" * 60)

    ticker_test = "ITX.MC"
    print(f"\n📥 Descargando datos de {ticker_test}...")

    df, validacion = obtener_datos_semanales(ticker_test, periodo_años=10)

    if df is not None:
        print(f"  ✅ {len(df)} semanas descargadas")

        resultado = ejecutar_backtest_posicional(df, ticker_test, verbose=True)

        if "error" not in resultado:
            print(f"\n🎯 RESULTADO FINAL:")
            print(f"  Expectancy:     {resultado['expectancy']}R")
            print(f"  Profit Factor:  {resultado['profit_factor']}")
            print(f"  Sharpe:         {resultado['sharpe']}")
            print(f"  Winrate:        {resultado['winrate']}%")
            print(f"  Total trades:   {resultado['total_trades']}")
            print(f"  Duración media: {resultado['duracion_media']} semanas")
        else:
            print(f"\n❌ Error: {resultado['error']}")
    else:
        print(f"  ❌ Error descargando datos")

    print("\n" + "=" * 60)
