# ==========================================================
# BACKTEST - SISTEMA MEDIO PLAZO
# Motor completo de backtesting con métricas
# ==========================================================

import sys
from .config_medio import *
from .datos_medio import *
from .sistema_trading_medio import evaluar_entrada_medio_plazo
from .gestion_medio import PosicionMedioPlazo
import numpy as np


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 MOTOR DE BACKTEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ejecutar_backtest_medio_plazo(df_semanal, ticker=None, verbose=False):
    """
    Ejecuta backtest sobre datos semanales.
    
    Args:
        df_semanal: DataFrame con datos OHLCV semanales
        ticker: nombre del ticker (para logs)
        verbose: mostrar progreso
    
    Returns:
        dict con {trades: list, equity: list, metricas: dict}
    """
    if df_semanal is None or df_semanal.empty:
        return {"trades": [], "equity": [], "metricas": {}}
    
    trades = []
    equity_curve = [0.0]  # Equity en R
    posicion = None
    
    # Necesitamos suficiente histórico para empezar
    inicio_evaluacion = MIN_SEMANAS_HISTORICO
    total_semanas = len(df_semanal)
    
    if total_semanas < inicio_evaluacion:
        return {"trades": [], "equity": [], "metricas": {}}
    
    # Iterar semana a semana
    for i in range(inicio_evaluacion, total_semanas):
        
        # Datos hasta la semana actual
        df_hasta_ahora = df_semanal.iloc[:i+1]
        precio_actual = df_hasta_ahora['Close'].iloc[-1]
        high_actual = df_hasta_ahora['High'].iloc[-1]
        low_actual = df_hasta_ahora['Low'].iloc[-1]
        fecha_actual = df_hasta_ahora.index[-1]
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # GESTIÓN DE POSICIÓN ABIERTA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if posicion is not None:
            resultado = posicion.actualizar(precio_actual, high_actual, low_actual)
            posicion.aplicar_actualizacion(resultado)
            
            if verbose and resultado["motivo"]:
                print(f"   └─ {resultado['motivo']} (Stop: {resultado['stop_nuevo']:.2f})")
            
            # Salir si es necesario
            if resultado["salir"]:
                # Calcular R final
                R_final = posicion.calcular_R_actual(precio_actual)
                
                trades.append({
                    "entrada": posicion.entrada,
                    "stop_inicial": posicion.stop_inicial,
                    "salida": precio_actual,
                    "fecha_entrada": posicion.fecha_entrada,
                    "fecha_salida": fecha_actual,
                    "semanas": posicion.semanas_en_posicion,
                    "R": round(R_final, 2),
                    "motivo": resultado["motivo"]
                })
                
                # Actualizar equity
                equity_actual = equity_curve[-1] + R_final
                equity_curve.append(equity_actual)
                
                if verbose:
                    print(f"   └─ ❌ SALIDA: {R_final:+.2f}R ({resultado['motivo']})")
                
                posicion = None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BUSCAR NUEVA ENTRADA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if posicion is None:
            # Extraer datos históricos
            precios = df_hasta_ahora['Close'].tolist()
            volumenes = df_hasta_ahora['Volume'].tolist()
            
            # Evaluar entrada
            señal = evaluar_entrada_medio_plazo(
                precios=precios,
                volumenes=volumenes,
                df=df_hasta_ahora
            )
            
            if señal["decision"] == "COMPRA":
                entrada = señal["entrada"]
                stop = señal["stop"]
                
                # Abrir posición
                posicion = PosicionMedioPlazo(entrada, stop, fecha_actual)
                
                if verbose:
                    print(f"📌 {fecha_actual.date()}: ENTRADA ${entrada:.2f} | Stop: ${stop:.2f} | Riesgo: {señal['riesgo_pct']:.2f}%")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CERRAR POSICIÓN ABIERTA AL FINAL (si queda alguna)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if posicion is not None:
        precio_final = df_semanal['Close'].iloc[-1]
        R_final = posicion.calcular_R_actual(precio_final)
        
        trades.append({
            "entrada": posicion.entrada,
            "stop_inicial": posicion.stop_inicial,
            "salida": precio_final,
            "fecha_entrada": posicion.fecha_entrada,
            "fecha_salida": df_semanal.index[-1],
            "semanas": posicion.semanas_en_posicion,
            "R": round(R_final, 2),
            "motivo": "FIN_BACKTEST"
        })
        
        equity_actual = equity_curve[-1] + R_final
        equity_curve.append(equity_actual)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR MÉTRICAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    metricas = calcular_metricas(trades, equity_curve)
    
    return {
        "trades": trades,
        "equity": equity_curve,
        "metricas": metricas
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CÁLCULO DE MÉTRICAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_metricas(trades, equity_curve):
    """
    Calcula métricas de performance del sistema.
    
    Returns:
        dict con métricas clave
    """
    if not trades:
        return {
            "total_trades": 0,
            "expectancy_R": 0,
            "winrate": 0,
            "mejor_trade": 0,
            "peor_trade": 0,
            "avg_winner": 0,
            "avg_loser": 0,
            "profit_factor": 0,
            "max_drawdown_R": 0,
            "equity_final_R": 0
        }
    
    Rs = [t["R"] for t in trades]
    winners = [r for r in Rs if r > 0]
    losers = [r for r in Rs if r <= 0]
    
    # Métricas básicas
    total_trades = len(trades)
    expectancy_R = sum(Rs) / total_trades
    winrate = (len(winners) / total_trades) * 100 if total_trades > 0 else 0
    mejor_trade = max(Rs)
    peor_trade = min(Rs)
    
    # Promedio winners/losers
    avg_winner = sum(winners) / len(winners) if winners else 0
    avg_loser = sum(losers) / len(losers) if losers else 0
    
    # Profit factor
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Drawdown
    max_dd = calcular_max_drawdown(equity_curve)
    
    # Equity final
    equity_final = equity_curve[-1] if equity_curve else 0
    
    return {
        "total_trades": total_trades,
        "expectancy_R": round(expectancy_R, 2),
        "winrate": round(winrate, 1),
        "mejor_trade": round(mejor_trade, 2),
        "peor_trade": round(peor_trade, 2),
        "avg_winner": round(avg_winner, 2),
        "avg_loser": round(avg_loser, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_R": round(max_dd, 2),
        "equity_final_R": round(equity_final, 2)
    }


def calcular_max_drawdown(equity_curve):
    """
    Calcula el drawdown máximo en R.
    
    Returns:
        float: máximo drawdown (siempre negativo o 0)
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0
    
    equity = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity)
    drawdown = equity - running_max
    
    return min(drawdown)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 REPORTE DE RESULTADOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mostrar_reporte(resultado, ticker=None):
    """
    Muestra reporte formateado en consola.
    """
    metricas = resultado["metricas"]
    trades = resultado["trades"]
    
    print("\n" + "="*60)
    if ticker:
        print(f"📊 BACKTEST MEDIO PLAZO - {ticker}")
    else:
        print(f"📊 BACKTEST MEDIO PLAZO")
    print("="*60)
    
    print(f"\n🎯 RESUMEN:")
    print(f"   Trades totales: {metricas['total_trades']}")
    print(f"   Expectancy: {metricas['expectancy_R']:+.2f}R")
    print(f"   Winrate: {metricas['winrate']:.1f}%")
    print(f"   Equity final: {metricas['equity_final_R']:+.2f}R")
    
    print(f"\n📈 TRADES:")
    print(f"   Mejor: {metricas['mejor_trade']:+.2f}R")
    print(f"   Peor: {metricas['peor_trade']:+.2f}R")
    print(f"   Avg Winner: {metricas['avg_winner']:+.2f}R")
    print(f"   Avg Loser: {metricas['avg_loser']:+.2f}R")
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Profit Factor: {metricas['profit_factor']:.2f}")
    print(f"   Max Drawdown: {metricas['max_drawdown_R']:.2f}R")
    
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
    
    print(f"\n🎖️  EVALUACIÓN: {evaluacion}")
    
    if trades:
        print(f"\n📝 ÚLTIMOS 5 TRADES:")
        for t in trades[-5:]:
            fecha = t['fecha_salida'].date() if hasattr(t['fecha_salida'], 'date') else t['fecha_salida']
            print(f"   {fecha}: {t['R']:+.2f}R ({t['motivo']}) - {t['semanas']} semanas")
    
    print("="*60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 FUNCIÓN MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test backtest_medio.py")
    
    # Ticker de prueba
    ticker = "ACS.MC"
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    
    print(f"\n📥 Descargando {ticker}...")
    df_semanal, validacion = obtener_datos_semanales(ticker)
    
    if df_semanal is None:
        print(f"❌ Error: {validacion['errores']}")
        sys.exit(1)
    
    print(f"✅ {len(df_semanal)} semanas de datos")
    print(f"📅 Desde: {df_semanal.index[0].date()}")
    print(f"📅 Hasta: {df_semanal.index[-1].date()}")
    
    print(f"\n🔄 Ejecutando backtest...")
    resultado = ejecutar_backtest_medio_plazo(df_semanal, ticker, verbose=True)
    
    mostrar_reporte(resultado, ticker)
