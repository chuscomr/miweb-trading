# ==========================================================
# BACKTEST SISTEMA POSICIONAL
# Backtest completo sobre múltiples valores
# ==========================================================

import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def ejecutar_backtest_sistema_completo(universo=None, verbose=True, max_workers=4):
    """
    Ejecuta backtest sobre todos los valores del universo posicional.
    
    Args:
        universo: Lista de tickers (None = filtrar automáticamente)
        verbose: Mostrar progreso
        max_workers: Número de hilos para procesamiento paralelo
    
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
        from .config_posicional import IBEX_35
        universo = IBEX_35
        if verbose:
            print(f"   ✅ {len(universo)} valores seleccionados")
    
    if not universo:
        return {"error": "Universo vacío"}
    
    if verbose:
        print(f"\n📊 Valores a analizar: {len(universo)}")
        print(f"   {', '.join(universo)}")
        print(f"\n⏱️  Procesando (puede tardar 2-3 minutos)...\n")
    
       
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EJECUTAR BACKTESTS EN PARALELO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    resultados = []
    errores = []
    
    import time
    
    def procesar_ticker(ticker):
        """Procesa un ticker individual con reintentos."""
        max_intentos = 3
        
        for intento in range(max_intentos):
            try:
                # DELAY entre peticiones (crucial para evitar bloqueo)
                time.sleep(0.8)  # 800ms entre cada ticker
                
                # Descargar datos
                df, _ = obtener_datos_semanales(ticker, periodo_años=AÑOS_BACKTEST)
                
                if df is None or df.empty:
                    print(f"   ❌ {ticker}: Sin datos")
                    return {"ticker": ticker, "error": "Sin datos"}
                
                print(f"   📊 {ticker}: {len(df)} semanas de datos")

                # Ejecutar backtest
                resultado = ejecutar_backtest_posicional(df, ticker, verbose=False)
                # ⚠️ DIAGNÓSTICO - AÑADIR ESTE BLOQUE
                trades = resultado.get("total_trades", 0)
                print(f"   {'✅' if trades > 0 else '⚠️'} {ticker}: {trades} trades")

                return resultado
                
            except Exception as e:
                if "500" in str(e) or "internal-error" in str(e):
                    # Error de Yahoo Finance - reintentar
                    if intento < max_intentos - 1:
                        if verbose:
                            print(f"   ⏳ {ticker}: Error Yahoo Finance, reintentando... ({intento+1}/{max_intentos})")
                        time.sleep(3)  # Esperar 3 segundos antes de reintentar
                        continue
                    else:
                        return {"ticker": ticker, "error": f"Yahoo Finance bloqueó después de {max_intentos} intentos"}
                else:
                    return {"ticker": ticker, "error": str(e)}
        
        return {"ticker": ticker, "error": "No se pudo procesar"}
    
    # Procesar SECUENCIALMENTE todos los tickers
    for ticker in universo:
        try:
            resultado = procesar_ticker(ticker)
            
            if "error" in resultado:
                errores.append(resultado)
                if verbose:
                    print(f"   ⚠️  {ticker}: {resultado['error']}")
            else:
                resultados.append(resultado)
                if verbose:
                    exp = resultado.get('expectancy', 0)
                    trades = resultado.get('total_trades', 0)
                    signo = "✅" if exp > 0 else "❌"
                    print(f"   {signo} {ticker:12s} | {trades:3d} trades | {exp:+.2f}R expectancy")
        
        except Exception as e:
            errores.append({"ticker": ticker, "error": str(e)})
            if verbose:
                print(f"   ❌ {ticker}: Error procesando")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS GLOBALES
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS GLOBALES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if not resultados:
        return {
            "error": "No se pudieron procesar valores",
            "tickers_error": len(errores),
            "errores": errores
        }
    
    metricas_globales = calcular_metricas_sistema(resultados)
    metricas_globales["tickers_analizados"] = len(resultados)
    metricas_globales["tickers_con_error"] = len(errores)
    metricas_globales["total_tickers"] = len(universo)
    metricas_globales["resultados_detallados"] = resultados
    metricas_globales["errores"] = errores
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MOSTRAR RESUMEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
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
    # Métricas globales
    total_trades = sum(r.get("total_trades", 0) for r in resultados)
    todos_trades_ganadores = sum(r.get("trades_ganadores", 0) for r in resultados)
    
    # Expectancy ponderado por número de trades
    if total_trades > 0:
        expectancy_global = sum(
            r.get("expectancy", 0) * r.get("total_trades", 0)
            for r in resultados
        ) / total_trades
        
        winrate_global = (todos_trades_ganadores / total_trades * 100)
    else:
        expectancy_global = 0
        winrate_global = 0
    
    # Equity total
    equity_total = sum(r.get("equity_final", 0) for r in resultados)
    
    # Mejor y peor ticker
    resultados_con_trades = [r for r in resultados if r.get("total_trades", 0) > 0]
    
    if resultados_con_trades:
        mejor_ticker = max(resultados_con_trades, key=lambda x: x.get("expectancy", 0))
        peor_ticker = min(resultados_con_trades, key=lambda x: x.get("expectancy", 0))
    else:
        mejor_ticker = None
        peor_ticker = None
    
    # Profit factor global
    suma_ganadores = sum(
        r.get("trades_ganadores", 0) * r.get("r_medio_ganador", 0)
        for r in resultados
    )
    suma_perdedores = abs(sum(
        r.get("trades_perdedores", 0) * r.get("r_medio_perdedor", 0)
        for r in resultados
    ))
    
    profit_factor_global = suma_ganadores / suma_perdedores if suma_perdedores > 0 else 0
    
    # Tickers rentables vs no rentables
    tickers_rentables = len([r for r in resultados if r.get("expectancy", 0) > 0])
    tickers_no_rentables = len([r for r in resultados if r.get("expectancy", 0) <= 0])
    
    # Duración media
    duraciones = [r.get("duracion_media", 0) for r in resultados if r.get("duracion_media", 0) > 0]
    duracion_media_global = sum(duraciones) / len(duraciones) if duraciones else 0
    
    return {
        "total_trades": total_trades,
        "expectancy_global": round(expectancy_global, 2),
        "winrate_global": round(winrate_global, 1),
        "equity_total": round(equity_total, 2),
        "profit_factor_global": round(profit_factor_global, 2),
        "mejor_ticker": mejor_ticker,
        "peor_ticker": peor_ticker,
        "tickers_rentables": tickers_rentables,
        "tickers_no_rentables": tickers_no_rentables,
        "duracion_media_global": round(duracion_media_global, 1)
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 MOSTRAR RESUMEN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mostrar_resumen_sistema(metricas):
    """Muestra resumen formateado del backtest."""
    
    print("\n" + "=" * 70)
    print("📊 RESULTADOS DEL SISTEMA POSICIONAL")
    print("=" * 70)
    
    # Métricas globales
    print(f"\n📈 MÉTRICAS GLOBALES:")
    print(f"   Valores analizados: {metricas['tickers_analizados']}")
    print(f"   Total trades: {metricas['total_trades']}")
    print(f"   Expectancy: {metricas['expectancy_global']}R")
    print(f"   Winrate: {metricas['winrate_global']}%")
    print(f"   Equity total: {metricas['equity_total']:+.2f}R")
    print(f"   Profit Factor: {metricas['profit_factor_global']}")
    print(f"   Duración media: {metricas['duracion_media_global']:.0f} semanas ({metricas['duracion_media_global']/52:.1f} años)")
    
    # Balance
    print(f"\n📊 BALANCE POR TICKER:")
    print(f"   Rentables: {metricas['tickers_rentables']}")
    print(f"   No rentables: {metricas['tickers_no_rentables']}")
    print(f"   % Rentabilidad: {metricas['tickers_rentables']/(metricas['tickers_rentables']+metricas['tickers_no_rentables'])*100:.1f}%")
    
    # Top 5 mejores
    print(f"\n🏆 TOP 5 MEJORES VALORES:")
    resultados = metricas.get("resultados_detallados", [])
    top5 = sorted(
        [r for r in resultados if r.get("total_trades", 0) > 0],
        key=lambda x: x.get("expectancy", 0),
        reverse=True
    )[:5]
    
    for i, r in enumerate(top5, 1):
        ticker = r.get("ticker", "N/A")
        exp = r.get("expectancy", 0)
        trades = r.get("total_trades", 0)
        wr = r.get("winrate", 0)
        eq = r.get("equity_final", 0)
        print(f"   {i}. {ticker:12s} | {trades:2d} trades | {exp:+.2f}R | WR:{wr:4.1f}% | Equity:{eq:+6.2f}R")
    
    # Top 5 peores
    print(f"\n💀 TOP 5 PEORES VALORES:")
    bottom5 = sorted(
        [r for r in resultados if r.get("total_trades", 0) > 0],
        key=lambda x: x.get("expectancy", 0)
    )[:5]
    
    for i, r in enumerate(bottom5, 1):
        ticker = r.get("ticker", "N/A")
        exp = r.get("expectancy", 0)
        trades = r.get("total_trades", 0)
        wr = r.get("winrate", 0)
        eq = r.get("equity_final", 0)
        print(f"   {i}. {ticker:12s} | {trades:2d} trades | {exp:+.2f}R | WR:{wr:4.1f}% | Equity:{eq:+6.2f}R")
    
    # Errores
    if metricas.get("tickers_con_error", 0) > 0:
        print(f"\n⚠️  Valores con error: {metricas['tickers_con_error']}")
    
    # Evaluación
    print(f"\n🎯 EVALUACIÓN:")
    exp = metricas['expectancy_global']
    if exp >= 2.0:
        print(f"   ✅ EXCELENTE - Expectancy {exp}R es superior al objetivo (+2.0R)")
    elif exp >= 1.0:
        print(f"   ✅ MUY BUENO - Expectancy {exp}R es bueno para posicional")
    elif exp >= 0.5:
        print(f"   ⚠️  ACEPTABLE - Expectancy {exp}R es marginal")
    else:
        print(f"   ❌ NO RENTABLE - Expectancy {exp}R es insuficiente")
    
    print("\n" + "=" * 70)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test backtest_sistema_posicional.py")
    
    # Ejecutar backtest completo
    resultado = ejecutar_backtest_sistema_completo(verbose=True)
    
    if "error" not in resultado:
        print(f"\n✅ Backtest completado exitosamente")
    else:
        print(f"\n❌ Error: {resultado['error']}")
