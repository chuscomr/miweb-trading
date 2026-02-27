"""
API Endpoint para Backtest
Ejecuta backtest y devuelve resumen ejecutivo en JSON
"""

from flask import Blueprint, jsonify

import io
import gc
import os
import requests as _requests
from datetime import datetime as _datetime, timedelta as _timedelta
from contextlib import redirect_stdout
from logica import obtener_precios
from utils_validacion import construir_df_desde_listas
from .datos import MarketData
from .engine import BacktestEngine
from .execution import ExecutionModel
from .risk import RiskManager
from .portfolio import Portfolio
from .strategy import StrategyLogic
from .metrics import calcular_metricas

# Crear Blueprint
backtest_bp = Blueprint('backtest', __name__)

# Configuración
CAPITAL_INICIAL = 10_000
RIESGO_POR_TRADE = 0.01
MIN_VOLATILIDAD = 12.0
MODO_TEST = False

IBEX_TICKERS = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","ANE.MC",
    "ENG.MC","FCC.MC","PUIG.MC","MTS.MC",

    "CIE.MC","VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC",
    "PHM.MC","SCYR.MC","OHLA.MC","DOM.MC","ENC.MC","GRE.MC",
    "MRL.MC","HOME.MC","CIRSA.MC","FAE.MC","NEA.MC","PSG.MC","LDA.MC",
    "MEL.MC","VIS.MC","ECR.MC","ENO.MC","DIA.MC","IMC.MC","LIB.MC",
    "A3M.MC","ATRY.MC","R4.MC","RLIA.MC","MVC.MC","EBROM.MC","AMP.MC",
    "HBX.MC","CASH.MC","ADX.MC","AMP.MC","IZER.MC", "AEDAS.MC"
    
]


IBEX35_TICKERS = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","ANE.MC",
    "ENG.MC","FCC.MC","PUIG.MC","MTS.MC"
]

TICKER_EMPRESA = {
    "ACS.MC":"ACS","AENA.MC":"AENA","AMS.MC":"Amadeus","ANA.MC":"Acciona",
    "BBVA.MC":"BBVA","CABK.MC":"CaixaBank","ELE.MC":"Endesa","FER.MC":"Ferrovial",
    "GRF.MC":"Grifols","IBE.MC":"Iberdrola","IAG.MC":"IAG","IDR.MC":"Indra",
    "ITX.MC":"Inditex","MAP.MC":"Mapfre","MRL.MC":"Merlin","ADX.MC":"AUDAX",
    "NTGY.MC":"Naturgy","RED.MC":"Redeia","REP.MC":"Repsol","ROVI.MC":"Rovi",
    "SAB.MC":"Sabadell","SAN.MC":"Santander","SCYR.MC":"Sacyr","SLR.MC":"Solaria",
    "TEF.MC":"Telefónica","UNI.MC":"Unicaja","CLNX.MC":"Cellnex","LOG.MC":"Logista",
    "ACX.MC":"Acerinox","BKT.MC":"Bankinter","COL.MC":"Colonial","ANE.MC":"Acciona Energía",
    "ENG.MC":"Enagás","FCC.MC":"FCC","PUIG.MC":"PUIG","MTS.MC":"ARCELOR",
     
    "CIE.MC":"CIE Automotive","VID.MC":"Vidrala",
    "TUB.MC":"Tubacex","TRE.MC":"Técnicas Reunidas","CAF.MC":"CAF",
    "GEST.MC":"Gestamp","APAM.MC":"Applus","PHM.MC":"PharmaMar",
    "OHLA.MC":"OHLA","DOM.MC":"Global Dominion",
    "ENC.MC":"ENCE","GRE.MC":"Grenergy","ADX.MC":"Audax Renovables",
    "HOME.MC":"Neinor Homes","NHH.MC":"NH Hotel Group","AMP.MC":"AMPER",
    "MEL.MC":"Meliá","VIS.MC":"Viscofan","ENO.MC":"Elecnor",
    "ECR.MC":"Ercros","A3M.MC":"Atresmedia","ATRY.MC":"Atrys Health",
    "R4.MC":"Renta 4","HBX.MC":"HBX Group","LIB.MC":"Libertas",
    "CASH.MC":"Cash Converters","NEA.MC":"Naturhouse",
    "PSG.MC":"Prosegur","AMP.MC":"Amper","MVC.MC":"Metrovacesa",
    "CIRSA.MC":"CIRSA","DIA.MC":"DIA","LDA.MC":"Linea Directa",
    "IMC.MC":"Inmocentro","FAE.MC":"Faes Farma","RLIA.MC":"Realia Business",
    "EBROM.MC":"Ebro Motor","IZER.MC":"Izertis","AEDAS.MC":"AEDAS Inmb."
}

def nombre_empresa(ticker: str) -> str:
    return TICKER_EMPRESA.get(ticker, ticker.replace(".MC", ""))

class DummyCache:
    def cached(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator

cache = DummyCache()



def _obtener_precios_backtest(ticker, periodo_anios=2):
    """Descarga solo los últimos N años limitando en el servidor EODHD, no en RAM."""
    import yfinance as yf
    import pandas as pd

    provider = (os.getenv("DATA_PROVIDER", "yfinance") or "yfinance").strip().lower()
    fecha_desde = (_datetime.now() - _timedelta(days=365 * periodo_anios)).strftime("%Y-%m-%d")

    if provider == "eodhd":
        try:
            token = os.getenv("EODHD_API_TOKEN")
            if token:
                url = f"https://eodhd.com/api/eod/{ticker}"
                params = {"api_token": token, "period": "d", "fmt": "json",
                          "order": "a", "from": fecha_desde}
                r = _requests.get(url, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and len(data) >= 50:
                    fechas  = [_datetime.strptime(row["date"], "%Y-%m-%d") for row in data]
                    precios = [float(row.get("adjusted_close") or row["close"]) for row in data]
                    vols    = [float(row.get("volume") or 0) for row in data]
                    return precios, vols, fechas, precios[-1]
        except Exception as e:
            print(f"EODHD backtest fallback yfinance: {ticker} - {e}")

    # Fallback yfinance
    try:
        datos = yf.download(ticker, start=fecha_desde, progress=False)
        if datos is None or datos.empty:
            return None, None, None, None
        close  = datos["Close"]
        volume = datos["Volume"]
        if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
        precios   = close.dropna().tolist()
        volumenes = volume.dropna().tolist()
        fechas    = close.index.to_pydatetime().tolist()
        if len(precios) < 50:
            return None, None, None, None
        return precios, volumenes, fechas, precios[-1]
    except Exception as e:
        print(f"yfinance backtest error: {ticker} - {e}")
        return None, None, None, None


@backtest_bp.route('/api/backtest/ejecutar/ibex', methods=['GET'])
def ejecutar_backtest_ibex():
    """Backtest IBEX 35 optimizado para Render: descarga limitada en servidor."""
    try:
        print(">>> EJECUTANDO ENDPOINT /IBEX CON _obtener_precios_backtest <<<")

        tickers_operados = []
        tickers_excluidos = []
        todos_trades = []
        todas_equities = []
        
        import signal
        signal.alarm(0)
        for ticker in IBEX35_TICKERS:
            try:
                precios, volumenes, fechas, _ = _obtener_precios_backtest(ticker, periodo_anios=2)
            except Exception:
                continue  # si falla el fetch de precios para ese ticker, saltamos al siguiente
            if precios is None or len(precios) < 60:
                continue

            df = construir_df_desde_listas(precios, volumenes, fechas)
            volatilidad = (df['Close'].std() / df['Close'].mean()) * 100

            if volatilidad < MIN_VOLATILIDAD:
                tickers_excluidos.append({'ticker': ticker, 'vol': round(volatilidad, 1)})
                continue

            with redirect_stdout(io.StringIO()):
                data      = MarketData(df)
                strategy  = StrategyLogic(modo_test=MODO_TEST, min_volatilidad_pct=MIN_VOLATILIDAD)
                execution = ExecutionModel(comision_pct=0.0005, slippage_atr_pct=0.01, slippage_min_pct=0.0003)
                risk      = RiskManager(CAPITAL_INICIAL, RIESGO_POR_TRADE)
                portfolio = Portfolio(CAPITAL_INICIAL)
                engine    = BacktestEngine(data, strategy, execution, risk, portfolio)
                engine.run()

            if portfolio.trades:
                todos_trades.extend(portfolio.trades)
                todas_equities.append(portfolio.equity_curve[-1])
                capital_final = portfolio.equity_curve[-1]
                retorno = ((capital_final - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
                tickers_operados.append({
                    'ticker': ticker, 'trades': len(portfolio.trades),
                    'retorno': round(retorno, 1), 'volatilidad': round(volatilidad, 1)
                })

            try:
                del data, strategy, execution, risk, portfolio, engine, df
            except Exception:
                pass
            gc.collect()

        if not todos_trades:
            return jsonify({'success': False, 'error': 'No se ejecutaron trades'}), 400

        metricas   = calcular_metricas(todos_trades, todas_equities)
        aprobados  = [t for t in tickers_operados if t['retorno'] >= 2.0]
        neutros    = [t for t in tickers_operados if -2.0 <= t['retorno'] < 2.0]
        rechazados = [t for t in tickers_operados if t['retorno'] < -2.0]

        expectancy = metricas['expectancy_R']
        if expectancy >= 0.40:   estado, color = "EXCELENTE", "success"
        elif expectancy >= 0.20: estado, color = "RENTABLE",  "success"
        elif expectancy > 0:     estado, color = "MARGINAL",  "warning"
        else:                    estado, color = "NO RENTABLE","danger"

        if expectancy >= 0.20 and len(aprobados) >= 5:
            recomendacion = "Sistema listo para operar"
            acciones = [f"Operar SOLO los {len(aprobados)} tickers aprobados", "Mantener configuracion actual"]
        elif expectancy >= 0.20:
            recomendacion = "Pocos tickers aprobados"
            acciones = [f"Reducir filtro volatilidad a {MIN_VOLATILIDAD-2:.0f}%", "Incluir tickers neutros en watchlist"]
        else:
            recomendacion = "Sistema requiere optimizacion"
            acciones = ["Revisar parametros de entrada", "NO operar hasta mejorar expectancy >0.20R"]

        return jsonify({
            'success': True,
            'mercado': 'IBEX 35',
            'estado': {'texto': estado, 'color': color},
            'metricas': {
                'expectancy': round(expectancy, 2),
                'winrate': round(metricas['winrate'], 1),
                'max_dd': round(metricas['max_drawdown_pct'], 1),
                'total_trades': metricas['trades'],
                'tickers_activos': len(tickers_operados)
            },
            'tickers': {
                'aprobados':  [{'nombre': t['ticker'].replace('.MC',''), 'empresa': nombre_empresa(t['ticker']), 'retorno': t['retorno'], 'trades': t['trades']} for t in sorted(aprobados,  key=lambda x: x['retorno'], reverse=True)],
                'neutros':    [{'nombre': t['ticker'].replace('.MC',''), 'empresa': nombre_empresa(t['ticker']), 'retorno': t['retorno'], 'trades': t['trades']} for t in sorted(neutros,    key=lambda x: x['retorno'], reverse=True)],
                'rechazados': [{'nombre': t['ticker'].replace('.MC',''), 'empresa': nombre_empresa(t['ticker']), 'retorno': t['retorno'], 'trades': t['trades']} for t in sorted(rechazados, key=lambda x: x['retorno'])],
                'excluidos':  [{'nombre': t['ticker'].replace('.MC',''), 'empresa': nombre_empresa(t['ticker']), 'vol': t['vol']} for t in sorted(tickers_excluidos, key=lambda x: x['vol'])]
            },
            'config': {'target': '3R', 'breakeven': '1R',
                       'riesgo': f"{RIESGO_POR_TRADE*100:.1f}%",
                       'filtro_vol': f">{MIN_VOLATILIDAD:.0f}%", 'periodo': '2 anios'},
            'recomendacion': {'titulo': recomendacion, 'acciones': acciones}
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@backtest_bp.route('/api/backtest/ejecutar', methods=['GET'])
def ejecutar_backtest():
    """
    Ejecuta backtest completo y devuelve resumen ejecutivo
    """
    try:
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
                tickers_excluidos.append({
                    'ticker': ticker,
                    'vol': round(volatilidad, 1)
                })
                continue
            
            # Ejecutar sin logs
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
                    'retorno': round(retorno, 1),
                    'volatilidad': round(volatilidad, 1)
                })
        
        if not todos_trades:
            return jsonify({
                'success': False,
                'error': 'No se ejecutaron trades'
            }), 400
        
        # Calcular métricas
        metricas = calcular_metricas(todos_trades, todas_equities)
        
        # Clasificar tickers
        aprobados = [t for t in tickers_operados if t['retorno'] >= 2.0]
        neutros = [t for t in tickers_operados if -2.0 <= t['retorno'] < 2.0]
        rechazados = [t for t in tickers_operados if t['retorno'] < -2.0]
        
        # Determinar estado
        expectancy = metricas['expectancy_R']
        if expectancy >= 0.40:
            estado = "EXCELENTE"
            color = "success"
        elif expectancy >= 0.20:
            estado = "RENTABLE"
            color = "success"
        elif expectancy > 0:
            estado = "MARGINAL"
            color = "warning"
        else:
            estado = "NO RENTABLE"
            color = "danger"
        
        # Recomendaciones
        if expectancy >= 0.20 and len(aprobados) >= 5:
            recomendacion = "Sistema listo para operar"
            acciones = [
                f"Operar SOLO los {len(aprobados)} tickers aprobados",
                "Mantener configuración actual"
            ]
        elif expectancy >= 0.20:
            recomendacion = "Pocos tickers aprobados"
            acciones = [
                f"Considerar reducir filtro volatilidad a {MIN_VOLATILIDAD-2:.0f}%",
                "O incluir tickers neutros en watchlist"
            ]
        else:
            recomendacion = "Sistema requiere optimización"
            acciones = [
                "Revisar parámetros de entrada",
                "Considerar aumentar target a +4R",
                "NO operar hasta mejorar expectancy >0.20R"
            ]
        
        # Preparar respuesta
        respuesta = {
            'success': True,
            'estado': {
                'texto': estado,
                'color': color
            },
            'metricas': {
                'expectancy': round(expectancy, 2),
                'winrate': round(metricas['winrate'], 1),
                'max_dd': round(metricas['max_drawdown_pct'], 1),
                'total_trades': metricas['trades'],
                'tickers_activos': len(tickers_operados)
            },
            'tickers': {
                'aprobados': [
                    {
                        'nombre': t['ticker'].replace('.MC', ''),
                        'empresa': nombre_empresa(t['ticker']),
                        'retorno': t['retorno'],
                        'trades': t['trades']
                    } for t in sorted(aprobados, key=lambda x: x['retorno'], reverse=True)
                ],
                'neutros': [
                    {
                        'nombre': t['ticker'].replace('.MC', ''),
                        'empresa': nombre_empresa(t['ticker']),
                        'retorno': t['retorno'],
                        'trades': t['trades']
                    } for t in sorted(neutros, key=lambda x: x['retorno'], reverse=True)
                ],
                'rechazados': [
                    {
                        'nombre': t['ticker'].replace('.MC', ''),
                        'empresa': nombre_empresa(t['ticker']),
                        'retorno': t['retorno'],
                        'trades': t['trades']
                    } for t in sorted(rechazados, key=lambda x: x['retorno'])
                ],
                'excluidos': [
                    {
                        'nombre': t['ticker'].replace('.MC', ''),
                        'empresa': nombre_empresa(t['ticker']),
                        'vol': t['vol']
                    } for t in sorted(tickers_excluidos, key=lambda x: x['vol'])
                ]
            },
            'config': {
                'target': '3R',
                'breakeven': '1R',
                'riesgo': f"{RIESGO_POR_TRADE*100:.1f}%",
                'filtro_vol': f">{MIN_VOLATILIDAD:.0f}%"
            },
            'recomendacion': {
                'titulo': recomendacion,
                'acciones': acciones
            }
        }
        
        return jsonify(respuesta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backtest_bp.route('/api/backtest/config', methods=['GET'])
def obtener_config():
    """
    Devuelve la configuración actual del sistema
    """
    return jsonify({
        'capital_inicial': CAPITAL_INICIAL,
        'riesgo_por_trade': RIESGO_POR_TRADE,
        'min_volatilidad': MIN_VOLATILIDAD,
        'target': 3,
        'breakeven': 1,
        'tickers': IBEX_TICKERS
    })
