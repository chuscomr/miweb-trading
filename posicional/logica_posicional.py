# ==========================================================
# LÓGICA - SISTEMA POSICIONAL
# Detección de tendencias, consolidaciones y breakouts
# ==========================================================

import numpy as np
import pandas as pd

# Imports flexibles (funciona standalone y como módulo)
try:
    from .config_posicional import *
except ImportError:
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 DETECCIÓN DE TENDENCIA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_tendencia_largo_plazo(precios, df=None):
    """
    Detecta tendencia usando MM20, MM50 y MM200 semanales.
    
    Tendencia ALCISTA si:
    - Precio > MM50 > MM200
    - MM50 pendiente positiva
    - Precio al menos 5% sobre MM50
    
    Returns:
        dict con tendencia y detalles
    """
    if len(precios) < MM_TENDENCIA_LARGA:
        return {
            "tendencia": "SIN_DATOS",
            "motivo": f"Faltan datos para MM{MM_TENDENCIA_LARGA}"
        }
    
    precio_actual = precios[-1]
    
    # Calcular medias móviles
    mm20 = np.mean(precios[-MM_TENDENCIA_CORTA:])
    mm50 = np.mean(precios[-MM_TENDENCIA_MEDIA:])
    mm200 = np.mean(precios[-MM_TENDENCIA_LARGA:])
    
    # Pendiente MM50 (últimas 13 semanas vs anteriores 13)
    mm50_reciente = np.mean(precios[-MM_TENDENCIA_MEDIA:-MM_TENDENCIA_MEDIA+13])
    mm50_anterior = np.mean(precios[-MM_TENDENCIA_MEDIA-13:-MM_TENDENCIA_MEDIA])
    pendiente_mm50 = ((mm50_reciente - mm50_anterior) / mm50_anterior) * 100
    
    # Distancia precio vs MM50
    distancia_mm50_pct = ((precio_actual - mm50) / mm50) * 100
    
    # Evaluar tendencia
    condiciones = {
        "precio_sobre_mm50": precio_actual > mm50,
        "mm50_sobre_mm200": mm50 > mm200,
        "pendiente_positiva": pendiente_mm50 > 0,
        "distancia_suficiente": distancia_mm50_pct >= DISTANCIA_MIN_MM50_PCT
    }
    
    cumple_todas = all(condiciones.values())
    
    if cumple_todas:
        tendencia = "ALCISTA"
    elif precio_actual < mm50 and mm50 < mm200:
        tendencia = "BAJISTA"
    else:
        tendencia = "LATERAL"
    
    return {
        "tendencia": tendencia,
        "mm20": mm20,
        "mm50": mm50,
        "mm200": mm200,
        "pendiente_mm50": pendiente_mm50,
        "distancia_mm50_pct": distancia_mm50_pct,
        "condiciones": condiciones,
        "cumple_criterios": cumple_todas
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 DETECCIÓN DE CONSOLIDACIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_consolidacion(precios, lookback_max=26):
    """
    Detecta si el precio está en consolidación.
    
    Consolidación válida si:
    - Rango de 3-6 meses
    - Variación < 25% en ese periodo
    - Sin tendencia clara
    
    Returns:
        dict con info de consolidación
    """
    if len(precios) < lookback_max:
        return {
            "en_consolidacion": False,
            "motivo": "Histórico insuficiente"
        }
    
    # Analizar últimas N semanas
    periodo_consolidacion = precios[-lookback_max:]
    maximo = max(periodo_consolidacion)
    minimo = min(periodo_consolidacion)
    rango_pct = ((maximo - minimo) / minimo) * 100
    
    # Calcular posición actual en el rango
    precio_actual = precios[-1]
    posicion_en_rango = ((precio_actual - minimo) / (maximo - minimo)) * 100
    
    # Volatilidad del periodo
    returns = pd.Series(periodo_consolidacion).pct_change().dropna()
    volatilidad = returns.std() * (52 ** 0.5) * 100
    
    # Evaluar consolidación
    es_consolidacion = (
        CONSOLIDACION_MIN_SEMANAS <= lookback_max <= CONSOLIDACION_MAX_SEMANAS
        and rango_pct <= CONSOLIDACION_MAX_RANGO_PCT
        and volatilidad < 30  # Volatilidad moderada
    )
    
    return {
        "en_consolidacion": es_consolidacion,
        "semanas_consolidacion": lookback_max,
        "rango_pct": rango_pct,
        "maximo": maximo,
        "minimo": minimo,
        "precio_actual": precio_actual,
        "posicion_en_rango": posicion_en_rango,
        "volatilidad": volatilidad,
        "cerca_maximo": posicion_en_rango > 90,
        "cerca_minimo": posicion_en_rango < 10
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 DETECCIÓN DE BREAKOUT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_breakout(precios, volumenes=None, lookback=26):
    """
    Detecta breakout de máximos recientes.
    
    Breakout válido si:
    - Precio > máximo últimas N semanas
    - Volumen confirmación (si disponible)
    - Cierre cerca del máximo (no spike)
    
    Returns:
        dict con info de breakout
    """
    if len(precios) < lookback:
        return {
            "hay_breakout": False,
            "motivo": "Histórico insuficiente"
        }
    
    precio_actual = precios[-1]
    precios_previos = precios[-lookback-1:-1]  # Últimas N semanas (sin actual)
    maximo_previo = max(precios_previos)
    
    # Verificar si hay breakout
    hay_breakout = precio_actual > maximo_previo
    
    # Distancia del breakout
    distancia_breakout_pct = ((precio_actual - maximo_previo) / maximo_previo) * 100
    
    # Si hay volumenes, verificar confirmación
    volumen_confirma = True
    ratio_volumen = 1.0
    
    if volumenes is not None and len(volumenes) >= lookback:
        vol_actual = volumenes[-1]
        vol_medio = np.mean(volumenes[-lookback-1:-1])
        ratio_volumen = vol_actual / vol_medio if vol_medio > 0 else 1.0
        volumen_confirma = ratio_volumen >= BREAKOUT_VOLUMEN_MIN_RATIO
    
    # Evaluación final
    breakout_valido = (
        hay_breakout
        and distancia_breakout_pct >= 0.5  # Al menos 0.5% sobre máximo
        and volumen_confirma
    )
    
    return {
        "hay_breakout": breakout_valido,
        "precio_actual": precio_actual,
        "maximo_previo": maximo_previo,
        "distancia_breakout_pct": distancia_breakout_pct,
        "ratio_volumen": ratio_volumen,
        "volumen_confirma": volumen_confirma,
        "semanas_lookback": lookback
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ CÁLCULO DE STOP INICIAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_stop_inicial(entrada, precios, df=None):
    """
    Calcula stop inicial para posición de largo plazo.
    
    Usa el MAYOR de:
    - Mínimo últimas 26 semanas (6 meses)
    - Entrada - (2.5 × ATR semanal)
    
    Returns:
        float: precio de stop
    """
    # Stop por estructura (mínimo 6 meses)
    if len(precios) >= STOP_ESTRUCTURA_LOOKBACK:
        # Usar Low si está disponible
        if df is not None and 'Low' in df.columns:
            minimo_estructura = df['Low'].iloc[-STOP_ESTRUCTURA_LOOKBACK:].min()
        else:
            minimo_estructura = min(precios[-STOP_ESTRUCTURA_LOOKBACK:])
    else:
        minimo_estructura = min(precios) * 0.85  # 15% por debajo si no hay datos
    
    # Stop por ATR
    stop_atr = entrada
    if df is not None:
        atr = calcular_atr(df, ATR_PERIODO)
        if atr and atr > 0:
            stop_atr = entrada - (STOP_ATR_MULTIPLICADOR * atr)
    
    # Usar el más alto (menos agresivo)
    stop = max(minimo_estructura, stop_atr)
    
    # Asegurar que está dentro de rango permitido
    riesgo_pct = ((entrada - stop) / entrada) * 100
    
    if riesgo_pct < RIESGO_MIN_PCT:
        # Stop muy cerca, ampliar
        stop = entrada * (1 - RIESGO_MIN_PCT/100)
    elif riesgo_pct > RIESGO_MAX_PCT:
        # Stop muy lejos, acercar
        stop = entrada * (1 - RIESGO_MAX_PCT/100)
    
    return stop


def calcular_atr(df, periodo=20):
    """Calcula Average True Range."""
    if df is None or len(df) < periodo:
        return None
    
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periodo).mean().iloc[-1]
    
    return atr


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ VALIDACIÓN DE RIESGO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validar_riesgo(entrada, stop):
    """
    Valida que el riesgo esté dentro del rango aceptable.
    
    Returns:
        dict con validación
    """
    riesgo_pct = ((entrada - stop) / entrada) * 100
    riesgo_euros = entrada - stop
    
    riesgo_valido = RIESGO_MIN_PCT <= riesgo_pct <= RIESGO_MAX_PCT
    
    if not riesgo_valido:
        if riesgo_pct < RIESGO_MIN_PCT:
            motivo = f"Riesgo muy bajo ({riesgo_pct:.1f}% < {RIESGO_MIN_PCT}%)"
        else:
            motivo = f"Riesgo muy alto ({riesgo_pct:.1f}% > {RIESGO_MAX_PCT}%)"
    else:
        motivo = "Riesgo aceptable"
    
    return {
        "riesgo_valido": riesgo_valido,
        "riesgo_pct": riesgo_pct,
        "riesgo_euros": riesgo_euros,
        "motivo": motivo
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CALCULAR VOLATILIDAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_volatilidad(precios, periodo=52):
    """
    Calcula volatilidad anualizada.
    
    Returns:
        float: volatilidad en % anual
    """
    if len(precios) < periodo:
        periodo = len(precios)
    
    returns = pd.Series(precios[-periodo:]).pct_change().dropna()
    volatilidad_anual = returns.std() * (52 ** 0.5) * 100
    
    return volatilidad_anual


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test logica_posicional.py")
    print("=" * 60)
    
    # Crear datos simulados
    # Tendencia alcista con consolidación y breakout
    base = [100 + i*0.5 for i in range(200)]  # Tendencia alcista lenta
    consolidacion = [base[-1] + np.random.uniform(-2, 2) for _ in range(26)]  # 6 meses consolidando
    breakout = [consolidacion[-1] + i*1.5 for i in range(5)]  # Breakout
    
    precios_test = base + consolidacion + breakout
    
    print("\n📊 Test 1: Detección de tendencia")
    tendencia = detectar_tendencia_largo_plazo(precios_test)
    print(f"   Tendencia: {tendencia['tendencia']}")
    print(f"   Precio sobre MM50: {tendencia['condiciones']['precio_sobre_mm50']}")
    print(f"   MM50 sobre MM200: {tendencia['condiciones']['mm50_sobre_mm200']}")
    print(f"   Distancia MM50: {tendencia['distancia_mm50_pct']:.1f}%")
    
    print("\n📦 Test 2: Detección de consolidación")
    consolidacion_info = detectar_consolidacion(precios_test, lookback_max=26)
    print(f"   En consolidación: {consolidacion_info['en_consolidacion']}")
    print(f"   Rango: {consolidacion_info['rango_pct']:.1f}%")
    print(f"   Posición en rango: {consolidacion_info['posicion_en_rango']:.1f}%")
    
    print("\n🚀 Test 3: Detección de breakout")
    breakout_info = detectar_breakout(precios_test, lookback=26)
    print(f"   Hay breakout: {breakout_info['hay_breakout']}")
    print(f"   Distancia: {breakout_info['distancia_breakout_pct']:.2f}%")
    print(f"   Precio actual: {breakout_info['precio_actual']:.2f}")
    print(f"   Máximo previo: {breakout_info['maximo_previo']:.2f}")
    
    print("\n🛡️ Test 4: Cálculo de stop")
    entrada = precios_test[-1]
    stop = calcular_stop_inicial(entrada, precios_test)
    validacion_riesgo = validar_riesgo(entrada, stop)
    print(f"   Entrada: {entrada:.2f}")
    print(f"   Stop: {stop:.2f}")
    print(f"   Riesgo: {validacion_riesgo['riesgo_pct']:.1f}%")
    print(f"   Válido: {validacion_riesgo['riesgo_valido']}")
    
    print("\n" + "=" * 60)
