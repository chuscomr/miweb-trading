# ==========================================================
# LÓGICA TÉCNICA - SISTEMA MEDIO PLAZO
# Indicadores y análisis técnico para timeframe semanal
# ==========================================================

import numpy as np
import pandas as pd
from .config_medio import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 INDICADORES TÉCNICOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_atr_semanal(df, periodo=ATR_PERIODO):
    """
    Calcula ATR (Average True Range) sobre datos semanales.
    
    Args:
        df: DataFrame con OHLC
        periodo: ventana para el ATR (default: 14 semanas)
    
    Returns:
        float: ATR actual o None si no hay suficientes datos
    """
    if df is None or len(df) < periodo + 1:
        return None
    
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    # True Range
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR = media del TR
    atr = tr.rolling(periodo).mean()
    
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else None


def calcular_atr_desde_listas(precios, periodo=ATR_PERIODO):
    """
    Versión simplificada de ATR solo con cierres (para listas).
    Menos preciso pero funcional.
    
    Args:
        precios: lista de precios de cierre semanales
        periodo: ventana para el ATR
    
    Returns:
        float: ATR aproximado
    """
    if len(precios) < periodo + 1:
        return None
    
    precios = np.array(precios, dtype=float)
    
    # Rangos semanales (aproximación)
    rangos = np.abs(np.diff(precios))
    
    # Media de rangos
    atr = np.mean(rangos[-periodo:])
    
    return atr


def calcular_mm(precios, periodo):
    """
    Calcula media móvil simple.
    
    Args:
        precios: array/lista de precios
        periodo: ventana
    
    Returns:
        float: MM actual o None
    """
    if len(precios) < periodo:
        return None
    
    return np.mean(precios[-periodo:])


def calcular_volatilidad(precios, ventana=52):
    """
    Calcula volatilidad anualizada en %.
    
    Args:
        precios: lista/array de precios semanales
        ventana: semanas a considerar (default: 52 = 1 año)
    
    Returns:
        float: volatilidad en %
    """
    if len(precios) < ventana:
        ventana = len(precios)
    
    if ventana < 10:
        return None
    
    precios = np.array(precios[-ventana:])
    
    # Desviación estándar / media
    volatilidad = (np.std(precios) / np.mean(precios)) * 100
    
    return volatilidad


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 ANÁLISIS DE TENDENCIA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_tendencia_semanal(precios):
    """
    Detecta tendencia usando medias móviles semanales.
    
    Returns:
        dict con:
        - tendencia: "ALCISTA", "BAJISTA", "NEUTRAL"
        - mm10, mm20, mm40: valores de las MMs
        - precio_vs_mm20: relación precio/MM20 en %
    """
    if len(precios) < MM_TENDENCIA_LARGA:
        return {"tendencia": "INSUFICIENTE"}
    
    precio = precios[-1]
    mm10 = calcular_mm(precios, MM_TENDENCIA_CORTA)
    mm20 = calcular_mm(precios, MM_TENDENCIA_MEDIA)
    mm40 = calcular_mm(precios, MM_TENDENCIA_LARGA)
    
    # Calcular pendiente MM20 (últimas 4 semanas vs anteriores)
    mm20_actual = np.mean(precios[-20:])
    mm20_previa = np.mean(precios[-24:-4])
    pendiente_mm20 = mm20_actual - mm20_previa
    
    # Determinar tendencia
    if precio > mm20 and pendiente_mm20 > 0:
        tendencia = "ALCISTA"
    elif precio < mm20 and pendiente_mm20 < 0:
        tendencia = "BAJISTA"
    else:
        tendencia = "NEUTRAL"
    
    # Distancia precio vs MM20
    precio_vs_mm20 = ((precio - mm20) / mm20) * 100 if mm20 else None
    
    return {
        "tendencia": tendencia,
        "mm10": mm10,
        "mm20": mm20,
        "mm40": mm40,
        "precio_vs_mm20": precio_vs_mm20,
        "pendiente_mm20": pendiente_mm20
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 DETECCIÓN DE PULLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_pullback(precios, lookback=LOOKBACK_MAXIMO):
    """
    Detecta si hay un pullback válido.
    
    Pullback = retroceso desde máximo reciente dentro del rango permitido.
    
    Returns:
        dict con:
        - es_pullback: bool
        - maximo_reciente: float
        - retroceso_pct: float
        - semanas_desde_max: int
    """
    if len(precios) < lookback:
        return {"es_pullback": False, "motivo": "Histórico insuficiente"}
    
    precio_actual = precios[-1]
    ultimos_precios = precios[-lookback:]
    
    # Máximo reciente
    maximo_reciente = max(ultimos_precios)
    indice_max = len(ultimos_precios) - 1 - list(reversed(ultimos_precios)).index(maximo_reciente)
    semanas_desde_max = len(ultimos_precios) - 1 - indice_max
    
    # Retroceso actual
    retroceso_pct = ((maximo_reciente - precio_actual) / maximo_reciente) * 100
    
    # Validar rango
    es_pullback = PULLBACK_MIN_PCT <= retroceso_pct <= PULLBACK_MAX_PCT
    
    if retroceso_pct < PULLBACK_MIN_PCT:
        motivo = f"Retroceso insuficiente ({retroceso_pct:.1f}%)"
    elif retroceso_pct > PULLBACK_MAX_PCT:
        motivo = f"Retroceso excesivo ({retroceso_pct:.1f}%)"
    else:
        motivo = "Pullback válido"
    
    return {
        "es_pullback": es_pullback,
        "maximo_reciente": maximo_reciente,
        "retroceso_pct": retroceso_pct,
        "semanas_desde_max": semanas_desde_max,
        "motivo": motivo
    }


def detectar_giro_semanal(precios):
    """
    Detecta si hay confirmación de giro alcista.
    
    Giro = precio actual > precio semana anterior
    
    Returns:
        dict con:
        - hay_giro: bool
        - variacion_pct: float
    """
    if len(precios) < 2:
        return {"hay_giro": False}
    
    precio_actual = precios[-1]
    precio_anterior = precios[-2]
    
    variacion_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
    
    return {
        "hay_giro": precio_actual > precio_anterior,
        "variacion_pct": variacion_pct
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ CÁLCULO DE STOPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_stop_inicial(precio_entrada, precios, df=None, stop_atr_mult=None):
    lookback = min(STOP_ESTRUCTURA_LOOKBACK, len(precios))
    stop_estructura = min(precios[-lookback:])

    if df is not None:
        atr = calcular_atr_semanal(df)
    else:
        atr = calcular_atr_desde_listas(precios)

    if stop_atr_mult is None:
        stop_atr_mult = STOP_ATR_MULTIPLICADOR

    if atr:
        stop_atr = precio_entrada - (atr * stop_atr_mult)
        return max(stop_estructura, stop_atr)

    return stop_estructura


def validar_riesgo(entrada, stop):
    """
    Valida que el riesgo está en el rango aceptable.
    
    Returns:
        dict con:
        - riesgo_valido: bool
        - riesgo_pct: float
        - motivo: str
    """
    if stop >= entrada:
        return {
            "riesgo_valido": False,
            "riesgo_pct": 0,
            "motivo": "Stop >= entrada"
        }
    
    riesgo_pct = ((entrada - stop) / entrada) * 100
    
    if riesgo_pct < RIESGO_MIN_PCT:
        return {
            "riesgo_valido": False,
            "riesgo_pct": riesgo_pct,
            "motivo": f"Riesgo muy bajo ({riesgo_pct:.2f}%)"
        }
    
    if riesgo_pct > RIESGO_MAX_PCT:
        return {
            "riesgo_valido": False,
            "riesgo_pct": riesgo_pct,
            "motivo": f"Riesgo muy alto ({riesgo_pct:.2f}%)"
        }
    
    return {
        "riesgo_valido": True,
        "riesgo_pct": riesgo_pct,
        "motivo": "Riesgo dentro de rango"
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test logica_medio.py")
    print("=" * 50)
    
    # Datos de prueba
    precios_test = [10, 10.5, 11, 11.5, 12, 12.5, 13, 12, 11.5, 11, 10.8, 11.2]
    
    print("\n1️⃣ Tendencia:")
    tendencia = detectar_tendencia_semanal(precios_test + [0]*30)
    print(f"   {tendencia}")
    
    print("\n2️⃣ Pullback:")
    pullback = detectar_pullback(precios_test)
    print(f"   {pullback}")
    
    print("\n3️⃣ Giro:")
    giro = detectar_giro_semanal(precios_test)
    print(f"   {giro}")
    
    print("\n4️⃣ Stop:")
    stop = calcular_stop_inicial(11.2, precios_test)
    print(f"   Stop: {stop:.2f}")
    
    validacion = validar_riesgo(11.2, stop)
    print(f"   {validacion}")
