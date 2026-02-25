# ==========================================================
# BACKTEST POSICIONAL
# Motor de backtest para un ticker individual
# ==========================================================

import pandas as pd
from datetime import datetime, timedelta

try:
    from .datos_posicional import obtener_datos_semanales
    from .sistema_trading_posicional import evaluar_entrada_posicional
    from .gestion_posicional import PosicionPosicional
    from .config_posicional import *
except ImportError:
    from datos_posicional import obtener_datos_semanales
    from sistema_trading_posicional import evaluar_entrada_posicional
    from gestion_posicional import PosicionPosicional
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔙 BACKTEST INDIVIDUAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ejecutar_backtest_posicional(df_semanal, ticker, verbose=False):
    """
    Ejecuta backtest posicional sobre un ticker.
    
    ESTRATEGIA:
    - Evaluación semanal
    - Una posición a la vez
    - Stops amplios (8-15%)
    - Trailing conservador
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
    
    # Validar datos
    if df_semanal is None or df_semanal.empty:
        return {"error": "Sin datos"}
    
    if len(df_semanal) < MIN_SEMANAS_HISTORICO:
        return {"error": f"Histórico insuficiente ({len(df_semanal)} semanas)"}
    
    # Preparar datos
    precios = df_semanal['Close'].values
    volumenes = df_semanal['Volume'].values
    fechas = df_semanal.index
    
    # Resultado
    trades = []
    posicion_actual = None
    equity_curve = []
    r_acumulado = 0.0
    
    if verbose:
        print(f"   Periodo: {fechas[0].date()} a {fechas[-1].date()}")
        print(f"   Semanas: {len(df_semanal)}")
        print(f"   Buscando señales...\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ITERAR SEMANA A SEMANA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    for i in range(MIN_SEMANAS_HISTORICO, len(df_semanal)):
        fecha_actual = fechas[i]
        precio_actual = precios[i]
        high_actual = df_semanal['High'].iloc[i]
        low_actual = df_semanal['Low'].iloc[i]
        
        # Datos históricos hasta esta semana
        precios_hist = precios[:i+1]
        volumenes_hist = volumenes[:i+1]
        df_hist = df_semanal.iloc[:i+1]
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # GESTIÓN DE POSICIÓN ABIERTA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if posicion_actual is not None:
            # Actualizar posición
            debe_salir, motivo_salida = posicion_actual.actualizar(
                fecha_actual,
                precio_actual,
                high=high_actual,
                low=low_actual
            )
            
            if debe_salir:
                # Cerrar posición
                precio_salida = posicion_actual.stop  # Asumimos salida en stop
                r_trade = posicion_actual.calcular_R_actual(precio_salida)
                
                trade_info = {
                    "entrada": posicion_actual.entrada,
                    "salida": precio_salida,
                    "fecha_entrada": posicion_actual.fecha_apertura,
                    "fecha_salida": fecha_actual,
                    "stop_inicial": posicion_actual.stop_inicial,
                    "r": round(r_trade, 2),
                    "semanas": posicion_actual.semanas_en_posicion,
                    "motivo_salida": motivo_salida,
                    "estado_final": posicion_actual.estado
                }
                
                trades.append(trade_info)
                r_acumulado += r_trade
                
                if verbose:
                    signo = "✅" if r_trade > 0 else "❌"
                    print(f"   {signo} Trade #{len(trades):2d}: {r_trade:+.2f}R | {posicion_actual.semanas_en_posicion} sem | {motivo_salida}")
                
                posicion_actual = None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BUSCAR NUEVA ENTRADA (si no hay posición)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if posicion_actual is None:
            # Evaluar señal
            evaluacion = evaluar_entrada_posicional(
                precios_hist,
                volumenes_hist,
                fechas=fechas[:i+1],
                df=df_hist
            )
            
            if evaluacion["decision"] == "COMPRA":
                # Abrir posición
                entrada = evaluacion["entrada"]
                stop = evaluacion["stop"]
                
                posicion_actual = PosicionPosicional(
                    entrada,
                    stop,
                    fecha_actual
                )
                
                if verbose:
                    print(f"   🔵 Nueva entrada en {fecha_actual.date()}")
                    print(f"      Precio: {entrada:.2f} | Stop: {stop:.2f} | Riesgo: {evaluacion['riesgo_pct']:.1f}%")
        
        # Equity curve
        equity_curve.append(r_acumulado)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CERRAR POSICIÓN ABIERTA AL FINAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if posicion_actual is not None:
        # Cerrar a precio final
        precio_final = precios[-1]
        r_trade = posicion_actual.calcular_R_actual(precio_final)
        
        trade_info = {
            "entrada": posicion_actual.entrada,
            "salida": precio_final,
            "fecha_entrada": posicion_actual.fecha_apertura,
            "fecha_salida": fechas[-1],
            "stop_inicial": posicion_actual.stop_inicial,
            "r": round(r_trade, 2),
            "semanas": posicion_actual.semanas_en_posicion,
            "motivo_salida": "Fin backtest",
            "estado_final": posicion_actual.estado
        }
        
        trades.append(trade_info)
        r_acumulado += r_trade
        
        if verbose:
            print(f"   🔵 Posición abierta al final: {r_trade:+.2f}R")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    metricas = calcular_metricas(trades, equity_curve)
    metricas["ticker"] = ticker
    
    if verbose:
        print(f"\n📊 RESUMEN {ticker}:")
        print(f"   Total trades: {metricas['total_trades']}")
        print(f"   Ganadores: {metricas['trades_ganadores']} ({metricas['winrate']:.1f}%)")
        print(f"   Expectancy: {metricas['expectancy']:.2f}R")
        print(f"   Equity final: {metricas['equity_final']:.2f}R")
        print(f"   Mejor trade: {metricas['mejor_trade']:.2f}R")
        print(f"   Peor trade: {metricas['peor_trade']:.2f}R")
        print(f"   Duración media: {metricas['duracion_media']:.0f} semanas")
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
            "total_trades": 0,
            "trades_ganadores": 0,
            "trades_perdedores": 0,
            "winrate": 0.0,
            "expectancy": 0.0,
            "equity_final": 0.0,
            "profit_factor": 0.0,
            "mejor_trade": 0.0,
            "peor_trade": 0.0,
            "r_medio_ganador": 0.0,
            "r_medio_perdedor": 0.0,
            "max_drawdown": 0.0,
            "duracion_media": 0.0
        }
    
    # Separar ganadores y perdedores
    rs = [t["r"] for t in trades]
    ganadores = [r for r in rs if r > 0]
    perdedores = [r for r in rs if r <= 0]
    
    total = len(trades)
    n_ganadores = len(ganadores)
    n_perdedores = len(perdedores)
    
    # Winrate
    winrate = (n_ganadores / total * 100) if total > 0 else 0
    
    # Expectancy
    expectancy = sum(rs) / total if total > 0 else 0
    
    # Equity final
    equity_final = sum(rs)
    
    # Profit factor
    suma_ganadores = sum(ganadores) if ganadores else 0
    suma_perdedores = abs(sum(perdedores)) if perdedores else 0
    profit_factor = suma_ganadores / suma_perdedores if suma_perdedores > 0 else 0
    
    # Best/worst
    mejor = max(rs) if rs else 0
    peor = min(rs) if rs else 0
    
    # Promedios
    r_medio_ganador = sum(ganadores) / len(ganadores) if ganadores else 0
    r_medio_perdedor = sum(perdedores) / len(perdedores) if perdedores else 0
    
    # Drawdown
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
    duraciones = [t.get("semanas", 0) for t in trades]
    duracion_media = sum(duraciones) / len(duraciones) if duraciones else 0
    
    return {
        "total_trades": total,
        "trades_ganadores": n_ganadores,
        "trades_perdedores": n_perdedores,
        "winrate": round(winrate, 1),
        "expectancy": round(expectancy, 2),
        "equity_final": round(equity_final, 2),
        "profit_factor": round(profit_factor, 2),
        "mejor_trade": round(mejor, 2),
        "peor_trade": round(peor, 2),
        "r_medio_ganador": round(r_medio_ganador, 2),
        "r_medio_perdedor": round(r_medio_perdedor, 2),
        "max_drawdown": round(max_dd, 2),
        "duracion_media": round(duracion_media, 1),
        "trades": trades
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test backtest_posicional.py")
    print("=" * 60)
    
    # Descargar datos reales
    ticker_test = "ITX.MC"
    print(f"\n📥 Descargando datos de {ticker_test}...")
    
    df, validacion = obtener_datos_semanales(ticker_test, periodo_años=10)
    
    if df is not None:
        print(f"   ✅ {len(df)} semanas descargadas")
        
        # Ejecutar backtest
        resultado = ejecutar_backtest_posicional(df, ticker_test, verbose=True)
        
        if "error" not in resultado:
            print(f"\n🎯 RESULTADO FINAL:")
            print(f"   Expectancy: {resultado['expectancy']}R")
            print(f"   Profit Factor: {resultado['profit_factor']}")
            print(f"   Winrate: {resultado['winrate']}%")
            print(f"   Total trades: {resultado['total_trades']}")
            print(f"   Duración media: {resultado['duracion_media']} semanas")
        else:
            print(f"\n❌ Error: {resultado['error']}")
    else:
        print(f"   ❌ Error descargando datos")
    
    print("\n" + "=" * 60)
