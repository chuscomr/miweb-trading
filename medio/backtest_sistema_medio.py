# ==========================================================
# BACKTEST SISTEMA COMPLETO - MEDIO PLAZO
# Backtest multi-ticker sobre IBEX 35
# ==========================================================

import sys
from datetime import datetime
import numpy as np
from .config_medio import *
from .datos_medio import obtener_datos_semanales
from .backtest_medio import ejecutar_backtest_medio_plazo, calcular_metricas


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 BACKTEST MULTI-TICKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ejecutar_backtest_sistema_completo(universo=None, verbose=True, usar_continuo=False):
    """
    Ejecuta backtest sobre todo el universo de valores.
    
    Args:
        universo: lista de tickers (None = usar IBEX_35)
        verbose: mostrar progreso
        usar_continuo: incluir Mercado Continuo
    
    Returns:
        dict con resultados agregados
    """
    # Determinar universo
    if universo is None:
        universo = IBEX_35.copy()
        if usar_continuo:
            universo.extend(MERCADO_CONTINUO)
    
    if verbose:
        print("\n" + "="*70)
        print(f"🚀 BACKTEST SISTEMA MEDIO PLAZO")
        print("="*70)
        print(f"📊 Universo: {len(universo)} valores")
        print(f"🔵 IBEX 35: {len(IBEX_35)} valores")
        if usar_continuo:
            print(f"🟡 Mercado Continuo: {len(MERCADO_CONTINUO)} valores")
        print("="*70 + "\n")
    
    # Almacenar resultados
    resultados_por_ticker = []
    todos_los_trades = []
    tickers_con_error = []
    tickers_sin_datos = []
    
    # Iterar por cada ticker
    for i, ticker in enumerate(universo, 1):
        if verbose:
            print(f"[{i}/{len(universo)}] Procesando {ticker}...", end=" ")
        
        try:
            # Descargar datos
            df_semanal, validacion = obtener_datos_semanales(ticker, validar=False)
            
            if df_semanal is None or len(df_semanal) < MIN_SEMANAS_HISTORICO:
                if verbose:
                    print(f"❌ Sin datos suficientes")
                tickers_sin_datos.append(ticker)
                continue
            
            # Ejecutar backtest individual
            resultado_bt = ejecutar_backtest_medio_plazo(df_semanal, ticker, verbose=False)
            
            # Guardar resultados
            if resultado_bt["trades"]:
                metricas = resultado_bt["metricas"]
                
                resultados_por_ticker.append({
                    "ticker": ticker,
                    "empresa": TICKER_EMPRESA.get(ticker, ticker.replace(".MC", "")),
                    "total_trades": metricas["total_trades"],
                    "expectancy_R": metricas["expectancy_R"],
                    "winrate": metricas["winrate"],
                    "profit_factor": metricas["profit_factor"],
                    "equity_final_R": metricas["equity_final_R"],
                    "mejor_trade": metricas["mejor_trade"],
                    "peor_trade": metricas["peor_trade"],
                    "max_drawdown_R": metricas["max_drawdown_R"],
                    "semanas_historico": len(df_semanal)
                })
                
                # Agregar trades con información del ticker
                for trade in resultado_bt["trades"]:
                    trade_con_ticker = trade.copy()
                    trade_con_ticker["ticker"] = ticker
                    todos_los_trades.append(trade_con_ticker)
                
                if verbose:
                    print(f"✅ {metricas['total_trades']} trades | Exp: {metricas['expectancy_R']:+.2f}R")
            else:
                if verbose:
                    print(f"⚠️  0 trades generados")
        
        except Exception as e:
            if verbose:
                print(f"❌ Error: {str(e)[:50]}")
            tickers_con_error.append(ticker)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS AGREGADAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if verbose:
        print("\n" + "="*70)
        print("📊 CALCULANDO MÉTRICAS AGREGADAS...")
        print("="*70 + "\n")
    
    metricas_globales = calcular_metricas_globales(todos_los_trades, resultados_por_ticker)
    
    # Identificar mejores y peores
    top_performers = identificar_top_performers(resultados_por_ticker, n=5)
    
    # Construir resultado final
    resultado_final = {
        "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "universo": {
            "total_tickers": len(universo),
            "analizados": len(resultados_por_ticker),
            "sin_datos": len(tickers_sin_datos),
            "con_error": len(tickers_con_error),
            "sin_trades": len(universo) - len(resultados_por_ticker) - len(tickers_sin_datos) - len(tickers_con_error)
        },
        "metricas_globales": metricas_globales,
        "resultados_por_ticker": resultados_por_ticker,
        "top_performers": top_performers,
        "todos_los_trades": todos_los_trades,
        "tickers_sin_datos": tickers_sin_datos,
        "tickers_con_error": tickers_con_error
    }
    
    if verbose:
        mostrar_resumen_final(resultado_final)
    
    return resultado_final


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 MÉTRICAS GLOBALES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_metricas_globales(todos_los_trades, resultados_por_ticker):
    """
    Calcula métricas del sistema completo.
    """
    if not todos_los_trades:
        return {
            "total_trades": 0,
            "expectancy_R": 0,
            "winrate": 0,
            "equity_final_R": 0
        }
    
    # Extraer todos los Rs
    Rs = [t["R"] for t in todos_los_trades]
    winners = [r for r in Rs if r > 0]
    losers = [r for r in Rs if r <= 0]
    
    # Calcular equity curve global (suma acumulada de todos los trades)
    equity_curve = [0]
    for r in Rs:
        equity_curve.append(equity_curve[-1] + r)
    
    # Métricas básicas
    total_trades = len(Rs)
    expectancy_R = sum(Rs) / total_trades if total_trades > 0 else 0
    winrate = (len(winners) / total_trades * 100) if total_trades > 0 else 0
    
    # Winners/Losers
    avg_winner = sum(winners) / len(winners) if winners else 0
    avg_loser = sum(losers) / len(losers) if losers else 0
    
    # Profit Factor
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Max Drawdown
    max_dd = calcular_max_drawdown_global(equity_curve)
    
    # Equity final
    equity_final = equity_curve[-1]
    
    # Métricas adicionales
    mejor_trade = max(Rs)
    peor_trade = min(Rs)
    
    # Expectancy promedio por ticker
    expectancies = [r["expectancy_R"] for r in resultados_por_ticker]
    expectancy_promedio_ticker = sum(expectancies) / len(expectancies) if expectancies else 0
    
    # Tickers rentables
    tickers_rentables = len([r for r in resultados_por_ticker if r["expectancy_R"] > 0])
    tickers_no_rentables = len(resultados_por_ticker) - tickers_rentables
    
    return {
        "total_trades": total_trades,
        "expectancy_R": round(expectancy_R, 2),
        "winrate": round(winrate, 1),
        "avg_winner": round(avg_winner, 2),
        "avg_loser": round(avg_loser, 2),
        "profit_factor": round(profit_factor, 2),
        "mejor_trade": round(mejor_trade, 2),
        "peor_trade": round(peor_trade, 2),
        "max_drawdown_R": round(max_dd, 2),
        "equity_final_R": round(equity_final, 2),
        "equity_curve": equity_curve,
        "expectancy_promedio_ticker": round(expectancy_promedio_ticker, 2),
        "tickers_rentables": tickers_rentables,
        "tickers_no_rentables": tickers_no_rentables
    }


def calcular_max_drawdown_global(equity_curve):
    """Calcula max drawdown de equity curve global."""
    if not equity_curve or len(equity_curve) < 2:
        return 0
    
    equity = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity)
    drawdown = equity - running_max
    
    return min(drawdown)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🏆 TOP PERFORMERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def identificar_top_performers(resultados_por_ticker, n=5):
    """
    Identifica mejores y peores valores.
    """
    if not resultados_por_ticker:
        return {"mejores": [], "peores": []}
    
    # Ordenar por expectancy
    ordenados = sorted(resultados_por_ticker, key=lambda x: x["expectancy_R"], reverse=True)
    
    mejores = ordenados[:n]
    peores = ordenados[-n:][::-1]  # Invertir para mostrar de peor a menos peor
    
    return {
        "mejores": mejores,
        "peores": peores
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 RESUMEN EN CONSOLA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mostrar_resumen_final(resultado):
    """Muestra resumen formateado en consola."""
    universo = resultado["universo"]
    metricas = resultado["metricas_globales"]
    top = resultado["top_performers"]
    
    print("\n" + "="*70)
    print("📊 RESUMEN BACKTEST SISTEMA MEDIO PLAZO")
    print("="*70)
    
    print(f"\n🎯 UNIVERSO:")
    print(f"   Total tickers: {universo['total_tickers']}")
    print(f"   Analizados: {universo['analizados']}")
    print(f"   Sin datos: {universo['sin_datos']}")
    print(f"   Con error: {universo['con_error']}")
    
    print(f"\n📈 RESULTADOS GLOBALES:")
    print(f"   Total trades: {metricas['total_trades']}")
    print(f"   Expectancy: {metricas['expectancy_R']:+.2f}R")
    print(f"   Winrate: {metricas['winrate']:.1f}%")
    print(f"   Equity final: {metricas['equity_final_R']:+.2f}R")
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Profit Factor: {metricas['profit_factor']:.2f}")
    print(f"   Mejor trade: {metricas['mejor_trade']:+.2f}R")
    print(f"   Peor trade: {metricas['peor_trade']:+.2f}R")
    print(f"   Max Drawdown: {metricas['max_drawdown_R']:.2f}R")
    
    print(f"\n📊 ANÁLISIS POR TICKER:")
    print(f"   Expectancy promedio: {metricas['expectancy_promedio_ticker']:+.2f}R")
    print(f"   Tickers rentables: {metricas['tickers_rentables']}")
    print(f"   Tickers no rentables: {metricas['tickers_no_rentables']}")
    
    if top["mejores"]:
        print(f"\n🏆 TOP 5 MEJORES:")
        for i, ticker_data in enumerate(top["mejores"], 1):
            print(f"   {i}. {ticker_data['ticker']}: {ticker_data['expectancy_R']:+.2f}R " +
                  f"({ticker_data['total_trades']} trades, {ticker_data['winrate']:.1f}% WR)")
    
    if top["peores"]:
        print(f"\n💀 TOP 5 PEORES:")
        for i, ticker_data in enumerate(top["peores"], 1):
            print(f"   {i}. {ticker_data['ticker']}: {ticker_data['expectancy_R']:+.2f}R " +
                  f"({ticker_data['total_trades']} trades, {ticker_data['winrate']:.1f}% WR)")
    
    # Evaluación
    exp = metricas['expectancy_R']
    if exp >= 0.40:
        evaluacion = "✅ EXCELENTE"
    elif exp >= 0.20:
        evaluacion = "✅ BUENO"
    elif exp > 0:
        evaluacion = "⚠️  MARGINAL"
    else:
        evaluacion = "❌ NO RENTABLE"
    
    print(f"\n🎖️  EVALUACIÓN SISTEMA: {evaluacion}")
    print("="*70 + "\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST STANDALONE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Ejecutando backtest sistema completo IBEX 35...")
    
    # Ejecutar backtest
    resultado = ejecutar_backtest_sistema_completo(
        universo=None,  # Usa IBEX_35 por defecto
        verbose=True,
        usar_continuo=False  # Solo IBEX por ahora
    )
    
    print(f"\n✅ Backtest completado")
    print(f"📊 Trades totales: {resultado['metricas_globales']['total_trades']}")
    print(f"💰 Expectancy: {resultado['metricas_globales']['expectancy_R']:+.2f}R")
