import numpy as np

import yfinance as yf
import pandas as pd

# ==========================================
# LÓGICA BASE (mínima para medio plazo)
# ==========================================

def calcular_atr(precios, periodo=14):
    """
    ATR simplificado sobre cierres.
    Suficiente para medio plazo.
    """
    if precios is None or len(precios) < periodo + 1:
        return None

    precios = np.array(precios, dtype=float)

    rangos = np.abs(np.diff(precios))
    atr = np.mean(rangos[-periodo:])

    return atr

def obtener_precios(ticker, años=10):
    """
    Descarga precios diarios y devuelve:
    precios, volumenes, fechas
    """
    periodo = f"{años}y"
    df = yf.download(ticker, period=periodo, interval="1d", progress=False)

    if df.empty:
        return None, None, None

    
    
    fechas = df.index.to_pydatetime().tolist()
    close = df["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    precios = close.dropna().tolist()

    vol = df["Volume"]

    if isinstance(vol, pd.DataFrame):
        vol = vol.iloc[:, 0]

    volumenes = vol.dropna().tolist()
    
    return precios, volumenes, fechas

def sistema_trading_medio(precios_semanales, volumenes_semanales, fechas=None, precio_actual=None):
    """
    Sistema MEDIO PLAZO (4–24 semanas)
    Versión inicial para backtesting
    """
    motivos = []

    if precios_semanales is None or len(precios_semanales) < 25:
        return {
            "decision": "NO_OPERAR",
            "motivos": ["Histórico semanal insuficiente"]
        }

    precio = precio_actual if precio_actual else precios_semanales[-1]

    # MM20 semanal
    mm20 = np.mean(precios_semanales[-20:])
    mm20_prev = np.mean(precios_semanales[-23:-3])

    # Condiciones básicas de tendencia
    if precio <= mm20:
        return {"decision": "NO_OPERAR", "motivos": ["Precio bajo MM20 semanal"]}

    if mm20 <= mm20_prev:
        return {"decision": "NO_OPERAR", "motivos": ["MM20 sin pendiente positiva"]}

    # Breakout 12–20 semanas
    max_20 = max(precios_semanales[-20:])
    if precio < max_20 * 0.96:
        return {"decision": "NO_OPERAR", "motivos": ["Sin breakout semanal"]}

    # Stop por ATR semanal
    atr = calcular_atr(precios_semanales, periodo=14)
    if atr is None:
        return {"decision": "NO_OPERAR", "motivos": ["ATR no disponible"]}

    stop = precio - atr * 2.5
    riesgo_pct = (precio - stop) / precio * 100

    if riesgo_pct < 3 or riesgo_pct > 6:
        return {
            "decision": "NO_OPERAR",
            "motivos": [f"Riesgo fuera de rango ({riesgo_pct:.2f}%)"]
        }

    return {
        "decision": "COMPRA",
        "entrada": precio,
        "stop": stop,
        "riesgo_pct": round(riesgo_pct, 2),
        "motivos": [
            "Tendencia semanal válida",
            "Breakout 12–20 semanas",
            "Stop por ATR / estructura semanal"
        ]
    }

def analizar_medio_plazo(precios, volumenes, fechas):
    return sistema_trading_medio(
        precios_semanales=precios,
        volumenes_semanales=volumenes,
        fechas=fechas,
        precio_actual=precios[-1] if precios else None
    )

def convertir_a_semanal(precios, volumenes, fechas):
    """
    Convierte datos diarios a semanales.

    - Precio: cierre del último día de la semana
    - Volumen: volumen acumulado semanal

    Parámetros:
    precios   -> lista de precios diarios (float)
    volumenes -> lista de volúmenes diarios (float/int)
    fechas    -> lista de datetime (o pandas Timestamp)

    Devuelve:
    precios_semanales, volumenes_semanales, fechas_semanales
    """

    precios_semanales = []
    volumenes_semanales = []
    fechas_semanales = []

    if not precios or not volumenes or not fechas:
        return precios_semanales, volumenes_semanales, fechas_semanales

    semana_actual = fechas[0].isocalendar()[1]
    cierre_semana = precios[0]
    volumen_semana = 0

    for precio, volumen, fecha in zip(precios, volumenes, fechas):
        semana = fecha.isocalendar()[1]

        if semana != semana_actual:
            # cerramos semana anterior
            precios_semanales.append(cierre_semana)
            volumenes_semanales.append(volumen_semana)
            fechas_semanales.append(fecha)

            # iniciamos nueva semana
            semana_actual = semana
            cierre_semana = precio
            volumen_semana = volumen
        else:
            cierre_semana = precio
            volumen_semana += volumen

    # última semana
    precios_semanales.append(cierre_semana)
    volumenes_semanales.append(volumen_semana)
    fechas_semanales.append(fechas[-1])

    return precios_semanales, volumenes_semanales, fechas_semanales
