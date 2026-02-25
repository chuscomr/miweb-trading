"""
CHECK RÁPIDO DEL SISTEMA
========================
Ejecuta backtest y muestra SOLO el resumen ejecutivo (sin logs)
Ideal para checks diarios o revisiones rápidas
"""

import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(parent_dir))

# Suprimir prints del backtest
import io
from contextlib import redirect_stdout

from logica import obtener_precios
from utils_validacion import construir_df_desde_listas
from backtest.datos import MarketData
from backtest.engine import BacktestEngine
from backtest.execution import ExecutionModel
from backtest.risk import RiskManager
from backtest.portfolio import Portfolio
from backtest.strategy import StrategyLogic
from backtest.metrics import calcular_metricas
from backtest.resumen_ejecutivo import generar_resumen_ejecutivo, resumen_rapido

# Configuración
CAPITAL_INICIAL = 10_000
RIESGO_POR_TRADE = 0.01
MIN_VOLATILIDAD = 12.0
MODO_TEST = False

IBEX_TICKERS = [
    "SAN.MC", "BBVA.MC", "REP.MC", "IBE.MC", "ITX.MC",
    "FER.MC", "MAP.MC", "ACS.MC", "AENA.MC", "ENG.MC",
    "GRF.MC", "COL.MC", "NTGY.MC", "SAB.MC", "TEF.MC",
    "CABK.MC", "UNI.MC", "ELE.MC", "RED.MC", "CLNX.MC",
]

class DummyCache:
    def cached(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator

cache = DummyCache()

print("⏳ Ejecutando backtest... (sin logs)")

# Ejecutar backtest silenciosamente
tickers_operados = []
tickers_excluidos = []
todos_trades = []
todas_equities = []

for ticker in IBEX_TICKERS:
    precios, volumenes, fechas, _ = obtener_precios(ticker, cache)
    
    if precios is None or len(precios) < 60:
        continue
    
    df = construir_df_desde_listas(precios, volumenes, fechas)
    volatilidad = (df['Close'].std() / df['Close'].mean()) * 100
    
    if volatilidad < MIN_VOLATILIDAD:
        tickers_excluidos.append({'ticker': ticker, 'vol': volatilidad})
        continue
    
    # Redirigir stdout para suprimir logs
    with redirect_stdout(io.StringIO()):
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

# Generar métricas
if todos_trades:
    metricas = calcular_metricas(todos_trades, todas_equities)
    
    # Configuración
    config_sistema = {
        'target': 3,
        'breakeven': 1,
        'riesgo_pct': RIESGO_POR_TRADE,
        'min_volatilidad': MIN_VOLATILIDAD,
    }
    
    # MOSTRAR SOLO RESUMEN
    generar_resumen_ejecutivo(
        metricas, 
        tickers_operados, 
        tickers_excluidos, 
        config_sistema
    )
else:
    print("\n⚠️  No se ejecutaron trades")

print()
