"""
SISTEMA DE BACKTESTING - VERSIÓN FINAL
=======================================
Target: +3R | Break-even: +1R | Filtro volatilidad: 12%
"""

print(">>> BACKTEST SISTEMA FINAL <<<")

import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(parent_dir))

from logica import obtener_precios
from utils_validacion import construir_df_desde_listas
from backtest.datos import MarketData
from backtest.engine import BacktestEngine
from backtest.execution import ExecutionModel
from backtest.risk import RiskManager
from backtest.portfolio import Portfolio
from backtest.strategy import StrategyLogic
from backtest.metrics import calcular_metricas
from backtest.montecarlo import monte_carlo_R, resumen_montecarlo

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

CAPITAL_INICIAL = 10_000
RIESGO_POR_TRADE = 0.01          # 1% del capital
MIN_VOLATILIDAD = 8.0           # Solo tickers >12% volatilidad
MODO_TEST = False
IBEX_TICKERS = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","ANE.MC",
    "ENG.MC","FCC.MC","PUIG.MC","MTS.MC"

]

class DummyCache:
    def cached(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator

cache = DummyCache()

# ══════════════════════════════════════════════════════════════
# EJECUTAR BACKTEST
# ══════════════════════════════════════════════════════════════

print(f"\n💰 Capital: €{CAPITAL_INICIAL:,}")
print(f"🎲 Riesgo: {RIESGO_POR_TRADE*100}% | Target: +3R | Break-even: +1R")
print(f"⚡ Filtro volatilidad: >{MIN_VOLATILIDAD}%")
print(f"📊 Modo: {'TEST' if MODO_TEST else 'REAL'}")
print("\n" + "="*70)

tickers_operados = []
tickers_excluidos = []
todos_trades = []
todas_equities = []

for ticker in IBEX_TICKERS:
    print(f"\n📊 {ticker:<10}", end=" ")
    
    precios, volumenes, fechas, _ = obtener_precios(ticker, cache)
    
    if precios is None or len(precios) < 60:
        print("⚠️  Datos insuficientes")
        continue
    
    df = construir_df_desde_listas(precios, volumenes, fechas)
    volatilidad = (df['Close'].std() / df['Close'].mean()) * 100
    
    # Filtro de volatilidad
    if volatilidad < MIN_VOLATILIDAD:
        print(f"❌ Excluido (vol: {volatilidad:.1f}%)")
        tickers_excluidos.append({'ticker': ticker, 'vol': volatilidad})
        continue
    
    print(f"✅ Vol: {volatilidad:.1f}%", end=" ")
    
    # Ejecutar backtest
    data = MarketData(df)
    strategy = StrategyLogic(modo_test=MODO_TEST, min_volatilidad_pct=MIN_VOLATILIDAD)
    execution = ExecutionModel(
        comision_pct=0.0005,
        slippage_atr_pct=0.01,
        slippage_min_pct=0.0003
    )
    risk = RiskManager(CAPITAL_INICIAL, RIESGO_POR_TRADE)
    portfolio = Portfolio(CAPITAL_INICIAL)
    
    engine = BacktestEngine(data, strategy, execution, risk, portfolio)
    engine.run()
    
    if portfolio.trades:
        todos_trades.extend(portfolio.trades)
        todas_equities.extend(portfolio.equity_curve)
        
        capital_final = portfolio.equity_curve[-1]
        retorno = ((capital_final - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
        
        tickers_operados.append({
            'ticker': ticker,
            'trades': len(portfolio.trades),
            'retorno': retorno,
            'volatilidad': volatilidad
        })
        
        print(f"→ {len(portfolio.trades)} trades, {retorno:+.1f}%")
    else:
        print("→ Sin trades")

# ══════════════════════════════════════════════════════════════
# RESULTADOS
# ══════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("📊 RESULTADOS FINALES")
print("="*70)

print(f"\n🎯 Tickers operados: {len(tickers_operados)}/{len(IBEX_TICKERS)}")
print(f"❌ Excluidos: {len(tickers_excluidos)}")

if tickers_excluidos:
    print(f"\n📋 Excluidos por volatilidad <{MIN_VOLATILIDAD}%:")
    for t in sorted(tickers_excluidos, key=lambda x: x['vol']):
        print(f"  • {t['ticker']}: {t['vol']:.1f}%")

if not todos_trades:
    print("\n⚠️  No se ejecutaron trades")
    sys.exit(0)

metricas = calcular_metricas(todos_trades, todas_equities)

print(f"\n🎯 Total Trades: {metricas['trades']}")
print(f"📈 Win Rate: {metricas['winrate']:.1f}%")
print(f"💰 Expectancy: {metricas['expectancy_R']:.2f}R")
print(f"📉 Max Drawdown: {metricas['max_drawdown_pct']:.1f}%")

if todas_equities:
    capital_final = todas_equities[-1]
    retorno_total = ((capital_final - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
    print(f"💵 Capital Final: €{capital_final:,.0f} ({retorno_total:+.1f}%)")

Rs = [t.R for t in todos_trades]
ganadores = [r for r in Rs if r > 0]
perdedores = [r for r in Rs if r < 0]

print(f"\n📊 Distribución R:")
print(f"  • Media: {sum(Rs)/len(Rs):+.2f}R")
if ganadores and perdedores:
    print(f"  • Ganadores: {sum(ganadores)/len(ganadores):+.2f}R ({len(ganadores)} trades)")
    print(f"  • Perdedores: {sum(perdedores)/len(perdedores):+.2f}R ({len(perdedores)} trades)")

# Rendimiento por ticker
print(f"\n📋 Rendimiento por ticker:")
for t in sorted(tickers_operados, key=lambda x: x['retorno'], reverse=True):
    icono = "✅" if t['retorno'] > 0 else "❌"
    print(f"  {icono} {t['ticker']:<10} {t['retorno']:>+7.1f}%  ({t['trades']} trades)")

# Monte Carlo
if len(Rs) >= 20:
    print("\n" + "="*70)
    print("🎲 SIMULACIÓN MONTE CARLO (10,000 iteraciones)")
    print("="*70)
    
    resultados_mc = monte_carlo_R(Rs, CAPITAL_INICIAL, RIESGO_POR_TRADE, 10_000)
    resumen = resumen_montecarlo(resultados_mc)
    
    print(f"\n💰 Capital Proyectado:")
    print(f"  • P5 (peor 5%): €{resumen['capital_p5']:,.0f}")
    print(f"  • Mediana: €{resumen['capital_mediano']:,.0f}")
    print(f"  • P95 (mejor 5%): €{resumen['capital_p95']:,.0f}")
    
    retorno_mediano = ((resumen['capital_mediano'] - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
    print(f"\n📈 Retorno esperado: {retorno_mediano:+.1f}%")

# ══════════════════════════════════════════════════════════════
# RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════════

from backtest.resumen_ejecutivo import (
    generar_resumen_ejecutivo, 
    guardar_historico, 
    comparar_con_anterior
)

config_sistema = {
    'target': 3,
    'breakeven': 1,
    'riesgo_pct': RIESGO_POR_TRADE,
    'min_volatilidad': MIN_VOLATILIDAD,
}

resumen = generar_resumen_ejecutivo(
    metricas, 
    tickers_operados, 
    tickers_excluidos, 
    config_sistema
)

# Guardar histórico
archivo_guardado = guardar_historico(resumen)

# Comparar con anterior (si existe)
comparar_con_anterior(resumen)

print("\n✅ Backtest completado\n")
