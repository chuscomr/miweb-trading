"""
alertas_routes.py — MiWeb Swing Trading
Blueprint Flask para los endpoints de alertas.

Registrar en app.py:
    from alertas.alertas_routes import alertas_bp
    app.register_blueprint(alertas_bp)
"""

from flask import Blueprint, jsonify, request
from alertas.detector_alertas import detectar_alertas, priorizar_alertas, alertas_por_ticker
from alertas.alertas_ia import interpretar_alertas, interpretar_cartera

import pandas as pd
import numpy as np


def _sanitizar(obj):
    """Convierte tipos numpy a tipos Python nativos para que jsonify no falle."""
    if isinstance(obj, dict):
        return {k: _sanitizar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitizar(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj

# ── Importa las mismas funciones que ya usan logica_breakout.py y logica_pullback.py ──
try:
    from logica_breakout import obtener_datos_swing
    _FUENTE_DATOS = "logica_breakout"
except ImportError:
    try:
        from datos import obtener_datos as obtener_datos_swing
        _FUENTE_DATOS = "datos"
    except ImportError:
        obtener_datos_swing = None
        _FUENTE_DATOS = "yfinance_fallback"

alertas_bp = Blueprint('alertas', __name__, url_prefix='/api')


# ─────────────────────────────────────────────
# HELPER: obtener datos
# Reutiliza el mismo DataFrame que genera el sistema swing,
# con los indicadores ya calculados (MA, RSI, ATR, ADX, BB).
# ─────────────────────────────────────────────
def _get_df(ticker: str, periodo: str = "1y"):
    """
    Obtiene OHLCV + indicadores para un ticker.

    Prioridad:
      1. Función obtener_datos_swing (la misma que usa logica_breakout/pullback)
      2. yfinance como fallback si no encuentra la función del sistema

    El ticker llega SIN sufijo .MC desde el frontend (el JS ya lo quita).
    Si tu función interna espera el sufijo, se añade automáticamente.
    """
    # ── OPCIÓN 1: usar la función del propio sistema swing ────────────
    if obtener_datos_swing is not None:
        try:
            # Prueba primero sin sufijo
            df = obtener_datos_swing(ticker)
            if df is not None and not df.empty:
                df = _normalizar_columnas(df)
                df = _calcular_indicadores_faltantes(df)
                return df
        except Exception:
            pass

        try:
            # Prueba con sufijo .MC (mercado español)
            df = obtener_datos_swing(ticker + ".MC")
            if df is not None and not df.empty:
                df = _normalizar_columnas(df)
                df = _calcular_indicadores_faltantes(df)
                return df
        except Exception as e:
            print(f"[alertas] Error con función swing para {ticker}: {e}")

    # ── OPCIÓN 2: fallback yfinance ───────────────────────────────────
    # (solo si la función del sistema no está disponible)
    try:
        import yfinance as yf

        df = yf.download(ticker + ".MC", period=periodo, progress=False, auto_adjust=True)
        if df.empty:
            df = yf.download(ticker, period=periodo, progress=False, auto_adjust=True)
        if df.empty:
            return None

        df = _normalizar_columnas(df)
        df = _calcular_indicadores_faltantes(df)
        return df

    except Exception as e:
        print(f"[alertas] Error yfinance fallback para {ticker}: {e}")
        return None


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas a minúsculas y nombres estándar.
    Compatible con DataFrames de EODHD, yfinance y tu sistema propio.
    """
    # Aplanar MultiIndex de yfinance (columnas tipo ('Close', 'SAN.MC'))
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                      for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    # Renombrar variantes comunes al nombre estándar
    renombrar = {
        'adj_close': 'close', 'adjusted_close': 'close',
        'vol': 'volume',
        'sma50': 'ma50',  'sma_50': 'ma50',  'mm50': 'ma50',
        'sma200': 'ma200', 'sma_200': 'ma200', 'mm200': 'ma200',
        'bb_high': 'bb_upper', 'bb_low': 'bb_lower',
        'bollinger_upper': 'bb_upper', 'bollinger_lower': 'bb_lower',
    }
    df.rename(columns=renombrar, inplace=True)

    # Asegurar que 'close' existe (a veces viene como 'price')
    if 'close' not in df.columns and 'price' in df.columns:
        df['close'] = df['price']

    return df


def _calcular_indicadores_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula solo los indicadores que NO estén ya en el DataFrame.
    Si el sistema swing ya los calculó, no los recalcula.
    """
    if len(df) < 30:
        return df

    # MA50 y MA200
    if 'ma50' not in df.columns:
        df['ma50'] = df['close'].rolling(50).mean()
    if 'ma200' not in df.columns:
        df['ma200'] = df['close'].rolling(200).mean()

    # RSI (14)
    if 'rsi' not in df.columns:
        delta = df['close'].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))

    # ATR (14) — True Range
    if 'atr' not in df.columns:
        hl  = df['high'] - df['low']
        hpc = (df['high'] - df['close'].shift()).abs()
        lpc = (df['low']  - df['close'].shift()).abs()
        df['atr'] = pd.concat([hl, hpc, lpc], axis=1).max(axis=1).rolling(14).mean()

    # Bandas de Bollinger (20, 2σ)
    if 'bb_upper' not in df.columns:
        sma = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bb_upper'] = sma + 2 * std
        df['bb_lower'] = sma - 2 * std

    # ADX (14)
    if 'adx' not in df.columns:
        tr       = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low']  - df['close'].shift()).abs()
        ], axis=1).max(axis=1)
        dm_plus  = df['high'].diff().clip(lower=0)
        dm_minus = (-df['low'].diff()).clip(lower=0)
        atr14    = tr.rolling(14).mean()
        di_plus  = 100 * (dm_plus.rolling(14).mean()  / atr14.replace(0, np.nan))
        di_minus = 100 * (dm_minus.rolling(14).mean() / atr14.replace(0, np.nan))
        dx       = (100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan))
        df['adx'] = dx.rolling(14).mean()

    return df


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@alertas_bp.route('/alertas/<ticker>')
def alertas_ticker(ticker: str):
    """
    GET /api/alertas/SAN
    GET /api/alertas/SAN?ia=1          ← incluye análisis IA
    GET /api/alertas/SAN?sistema=medio ← ajusta contexto IA
    """
    ticker = ticker.upper()
    usar_ia = request.args.get('ia', '0') == '1'
    sistema = request.args.get('sistema', 'swing')

    df = _get_df(ticker)
    if df is None:
        return jsonify({"error": f"No se pudieron obtener datos para {ticker}"}), 404

    alertas = detectar_alertas(df, ticker)
    alertas = priorizar_alertas(alertas)

    analisis_ia = None
    if usar_ia and alertas:
        analisis_ia = interpretar_alertas(alertas, ticker, sistema=sistema)

    return jsonify(_sanitizar({
        "ticker":      ticker,
        "total":       len(alertas),
        "alertas":     alertas,
        "analisis_ia": analisis_ia,
    }))


@alertas_bp.route('/alertas/scanner')
def alertas_scanner():
    """
    GET /api/alertas/scanner?universo=ibex35
    GET /api/alertas/scanner?universo=continuo
    GET /api/alertas/scanner?universo=ibex35&solo_altas=1

    Escanea todo el universo y devuelve alertas ordenadas por severidad.
    Sin IA (para minimizar coste en scans masivos).
    """
    universo_key  = request.args.get('universo', 'ibex35')
    solo_altas    = request.args.get('solo_altas', '0') == '1'

    # Importa tus universos — ajusta según tu archivo
    try:
        from config import IBEX35_TICKERS, MERCADO_CONTINUO_TICKERS
        universos = {
            'ibex35':   IBEX35_TICKERS,
            'continuo': MERCADO_CONTINUO_TICKERS,
            'ambos':    IBEX35_TICKERS + MERCADO_CONTINUO_TICKERS,
        }
    except ImportError:
        # Fallback con lista básica si no encuentra el config
        universos = {
            'ibex35': ['SAN', 'BBVA', 'ITX', 'TEF', 'IBE', 'REP', 'CABK', 'AMS',
                       'FER', 'GRF', 'IAG', 'ELE', 'ENG', 'MAP', 'BKT', 'ACS',
                       'AENA', 'ACX', 'ANA', 'CLNX', 'COL', 'IDR', 'LOG', 'MEL',
                       'MRL', 'MTS', 'NTGY', 'PHM', 'REE', 'SAB', 'SCYR', 'SGRE',
                       'SLR', 'UNI', 'VIS'],
        }

    tickers = universos.get(universo_key, universos['ibex35'])
    todas_alertas = []
    errores = []

    for ticker in tickers:
        try:
            df = _get_df(ticker)
            if df is not None:
                alertas = detectar_alertas(df, ticker)
                todas_alertas.extend(alertas)
        except Exception as e:
            errores.append({"ticker": ticker, "error": str(e)})

    todas_alertas = priorizar_alertas(todas_alertas)

    if solo_altas:
        todas_alertas = [a for a in todas_alertas if a['severidad'] == 'ALTA']

    return jsonify(_sanitizar({
        "universo":     universo_key,
        "tickers_ok":  len(tickers) - len(errores),
        "total_alertas": len(todas_alertas),
        "alertas":     todas_alertas,
        "errores":     errores,
    }))


@alertas_bp.route('/alertas/cartera', methods=['POST'])
def alertas_cartera():
    """
    POST /api/alertas/cartera
    Body JSON: {
        "posiciones": [
            {"ticker": "SAN", "lado": "largo", "entrada": 4.20, "stop": 3.90},
            ...
        ],
        "ia": true
    }

    Analiza alertas activas en las posiciones abiertas de la cartera.
    """
    data       = request.get_json()
    posiciones = data.get('posiciones', [])
    usar_ia    = data.get('ia', False)

    if not posiciones:
        return jsonify({"error": "No se enviaron posiciones"}), 400

    tickers = [p['ticker'].upper() for p in posiciones]
    todas_alertas = []

    for ticker in tickers:
        df = _get_df(ticker)
        if df is not None:
            alertas = detectar_alertas(df, ticker)
            todas_alertas.extend(alertas)

    agrupadas   = alertas_por_ticker(todas_alertas)
    priorizadas = priorizar_alertas(todas_alertas)

    analisis_cartera = None
    if usar_ia and todas_alertas:
        analisis_cartera = interpretar_cartera(posiciones, agrupadas)

    return jsonify(_sanitizar({
        "total_alertas":    len(priorizadas),
        "alertas":          priorizadas,
        "por_ticker":       agrupadas,
        "analisis_cartera": analisis_cartera,
    }))
