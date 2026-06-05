# ==========================================================
# LÓGICA TÉCNICA - SISTEMA MEDIO PLAZO
# Indicadores y análisis técnico para timeframe semanal
# ==========================================================

import logging

import numpy as np
import pandas as pd

from core.indicadores import calcular_rsi

from .config_medio import *


logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTES DE SCORING V2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Estructura (0-5 puntos)
ESTRUCTURA_MM50_MM200 = 2.0          # MM50 > MM200 (tendencia macro alcista)
ESTRUCTURA_MM20_ASCENDENTE = 1.5     # MM20 con pendiente positiva
ESTRUCTURA_MM20_BAJISTA = -1.0       # MM20 girando a la baja (penalización)
ESTRUCTURA_MM50_ASCENDENTE = 1.0     # MM50 con pendiente positiva
ESTRUCTURA_PRECIO_SOBRE_MM50 = 0.5   # Precio sobre MM50 (fortaleza)
ESTRUCTURA_MAXIMOS_CRECIENTES = 0.5  # Máximos ascendentes (estructura intacta)
ESTRUCTURA_MM = 20                   # Períodos de MM para estructura
ESTRUCTURA_BAJO_MM = -0.5            # Penalización precio muy bajo MM
ESTRUCTURA_LOOKBACK = 50             # Períodos lookback estructura

# Timing (0-3 puntos)
TIMING_PULLBACK_SUAVE = 1.5          # Corrección 5-15%
TIMING_PULLBACK_PROFUNDO = 1.0       # Corrección 15-25%
TIMING_PRECIO_CERCA_MM20 = 1.0       # Precio a 2-5% de MM20
TIMING_PRECIO_SOBRE_MM20 = 0.5       # Precio sobre MM20 (señal prematura)
TIMING_VELAS_COMPRESION = 0.5        # 3+ velas de rango reducido
TIMING_PERFECTO_PUNTOS = 3.0         # Timing perfecto (máximo)
TIMING_PERFECTO_MIN = -2.0           # % mínimo desde máximo (perfecto)
TIMING_PERFECTO_MAX = -5.0           # % máximo desde máximo (perfecto)
TIMING_PULLBACK_OPTIMO_PUNTOS = 2.0  # Pullback óptimo
TIMING_PULLBACK_OPTIMO_MIN = -5.0    # % mínimo pullback óptimo
TIMING_PULLBACK_OPTIMO_MAX = -15.0   # % máximo pullback óptimo
TIMING_PULLBACK_VALIDO_PUNTOS = 1.0  # Pullback válido
TIMING_PULLBACK_VALIDO_MIN = -15.0   # % mínimo pullback válido
TIMING_SANO_PUNTOS = 0.5             # Pullback sano
TIMING_SANO_MIN = -20.0              # % mínimo pullback sano
TIMING_DETERIORO_PENALIZACION = -2.0 # Penalización por deterioro
TIMING_DETERIORO_UMBRAL = -25.0      # % umbral deterioro
TIMING_EXTENDIDO_PENALIZACION = -1.0 # Penalización precio extendido
TIMING_EXTENDIDO_UMBRAL = 10.0       # % umbral extendido sobre MM
TIMING_CERCA_SOPORTE_PUNTOS = 0.5    # Bonus cerca de soporte
TIMING_CERCA_SOPORTE_UMBRAL = 3.0    # % distancia a soporte
TIMING_MM = 5                        # Períodos MM corta para timing
TIMING_CORTA = 5                     # MM corta (timing)
TIMING_MEDIA = 8                     # MM media (timing)

# Momentum (0-2 puntos)
MOMENTUM_RSI_ZONA_COMPRA = 1.0       # RSI 35-50 (comprador sin sobrecompra)
MOMENTUM_RSI_SOBREVENTA = 0.5        # RSI <35 (rebote probable)
MOMENTUM_RSI_SOBREVENTA_PENALIZACION = -0.5  # RSI <25 (muy débil)
MOMENTUM_RSI_PUNTOS = 1.0            # Puntos base RSI
MOMENTUM_VOLUMEN_EXPANSION = 0.5     # Volumen creciente
MOMENTUM_VOLUMEN_PUNTOS = 0.5        # Puntos base volumen
MOMENTUM_VOLUMEN_RATIO = 1.2         # Ratio expansión volumen
MOMENTUM_VOLUMEN_VENDEDOR_PENALIZACION = -0.5  # Volumen vendedor
MOMENTUM_VOLUMEN_VENDEDOR_RATIO = 1.5  # Ratio volumen vendedor
MOMENTUM_VELA_ALCISTA = 0.5          # Última vela verde
MOMENTUM_VELA_REVERSION_PUNTOS = 0.5 # Vela de reversión
MOMENTUM_VELA_REVERSION_RATIO = 2.0  # Ratio cuerpo/sombra reversión

# Umbrales de validación
SCORE_MIN_ESTRUCTURA = 2.0           # Mínimo en estructura para validar setup
SCORE_MIN_TIMING = 0.5               # Mínimo en timing para validar setup


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 SCORING PROFESIONAL V2 — Sistema de componentes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_score_medio_v2(precios, tendencia, pullback, df=None):
    """
    Sistema de scoring profesional con componentes separados.
    
    Arquitectura:
    - ESTRUCTURA (0-5): Calidad de la tendencia macro
    - TIMING (0-3): Momento óptimo de entrada
    - MOMENTUM (0-2): Fuerza compradora actual
    
    Total: 0-10 puntos
    
    Ventaja vs sistema anterior:
    - Separa calidad estructural de timing de entrada
    - Estar bajo MM20 puede ser POSITIVO si estructura intacta
    - Penalización contextual (no binaria)
    - Distingue pullback sano de deterioro real
    
    Returns:
        dict con score, desglose y validación
    """

    # ═══════════════════════════════════════
    # COMPONENTE 1: ESTRUCTURA (0-5)
    # ═══════════════════════════════════════
    estructura_score = 0

    mm20 = tendencia.get("mm20", 0) or 0
    mm50 = tendencia.get("mm50", 0) or 0
    mm200 = tendencia.get("mm200", 0) or 0
    pendiente_mm20 = tendencia.get("pendiente_mm20", 0) or 0
    mm50_sobre_mm200 = tendencia.get("mm50_sobre_mm200", False)
    precio = precios[-1] if precios else 0

    # 1.1 Tendencia macro (MM50 > MM200) - OBLIGATORIO
    if mm50_sobre_mm200:
        estructura_score += ESTRUCTURA_MM50_MM200
    else:
        # Filtro duro: sin tendencia macro no hay setup
        return {
            "score": 0,
            "score_max": 10,
            "valido": False,
            "desglose": {"estructura": 0, "timing": 0, "momentum": 0},
            "motivo_rechazo": "MM50 no está sobre MM200"
        }

    # 1.2 MM20 ascendente/descendente
    if pendiente_mm20 > 0:
        estructura_score += ESTRUCTURA_MM20_ASCENDENTE
    elif pendiente_mm20 < -1:  # Girando claramente a la baja
        estructura_score += ESTRUCTURA_MM20_BAJISTA

    # 1.3 MM50 ascendente (pendiente medio plazo)
    # RELAJADO: Requiere menos datos históricos
    if len(precios) >= 52:  # 1 año de datos semanales
        # Comparar MM50 actual vs MM50 de hace 2 semanas (no 50)
        mm50_hace_2sem = sum(precios[-52:-2]) / 50 if len(precios) >= 52 else 0
        if mm50_hace_2sem > 0:
            pendiente_mm50 = (mm50 - mm50_hace_2sem) / mm50_hace_2sem * 100
            # Menos estricto: solo necesita NO estar bajando claramente
            if pendiente_mm50 > -1:  # Incluso plana cuenta como válida
                estructura_score += ESTRUCTURA_MM50_ASCENDENTE

    # 1.4 Precio vs MM50 - Posición estructural
    # NOTA: En medio plazo, estar +9-10% sobre MM50 es NORMAL en tendencia alcista
    # Solo penalizamos si está BAJO soporte principal
    if mm50 > 0:
        dist_mm50 = (precio - mm50) / mm50 * 100
        # Ya no penalizamos por estar extendido (era incorrectamente castigador)
        if dist_mm50 < -2:  # Bajo soporte principal
            estructura_score += ESTRUCTURA_BAJO_MM

    # 1.5 Máximos crecientes (estructura alcista)
    if len(precios) >= 20:
        max_reciente = max(precios[-10:])
        max_anterior = max(precios[-20:-10])
        if max_reciente > max_anterior:
            estructura_score += ESTRUCTURA_MAXIMOS_CRECIENTES

    # Bonus base: estructura macro sólida (MM50>MM200 confirmado)
    # No depende del score acumulado — es una recompensa por tener la base correcta
    if mm50_sobre_mm200 and estructura_score >= 1.5:
        estructura_score += 0.5

    # Cap estructura entre 0-5
    estructura_score = max(0, min(5, estructura_score))

    # ═══════════════════════════════════════
    # COMPONENTE 2: TIMING (0-3)
    # ═══════════════════════════════════════
    timing_score = 0

    # 2.1 Distancia a MM20 - CONTEXTUAL
    # CLAVE: Estar bajo MM20 NO es malo si estructura intacta
    if mm20 > 0:
        dist_mm20 = (precio - mm20) / mm20 * 100

        if pendiente_mm20 > 0:  # Tendencia corto plazo intacta
            # Timing perfecto: cerca de MM20 (±1.5%)
            if TIMING_PERFECTO_MIN <= dist_mm20 <= TIMING_PERFECTO_MAX:
                timing_score += TIMING_PERFECTO_PUNTOS
            # Pullback sano: moderadamente bajo (-3% a -1.5%)
            elif TIMING_SANO_MIN <= dist_mm20 < TIMING_PERFECTO_MIN:
                timing_score += TIMING_SANO_PUNTOS
            # Deterioro real: muy bajo MM20 (<-3%)
            elif dist_mm20 < TIMING_DETERIORO_UMBRAL:
                timing_score += TIMING_DETERIORO_PENALIZACION
            # Muy extendido: lejos arriba (>3%)
            elif dist_mm20 > TIMING_EXTENDIDO_UMBRAL:
                timing_score += TIMING_EXTENDIDO_PENALIZACION
        else:  # MM20 plana o bajando
            # Solo penalizar si precio está claramente bajo MM20 con MM20 bajando
            # -8% = deterioro real; menos de eso es pullback normal
            if dist_mm20 < -8:
                timing_score += TIMING_DETERIORO_PENALIZACION

    # 2.2 Calidad del pullback
    # retroceso_pct es POSITIVO (% caída desde máximos): 5% = corrección del 5%
    retroceso = pullback.get("retroceso_pct", 0)
    if 5.0 <= retroceso <= 15.0:       # Pullback óptimo: 5-15%
        timing_score += TIMING_PULLBACK_OPTIMO_PUNTOS
    elif 15.0 < retroceso <= 25.0:     # Pullback válido pero profundo: 15-25%
        timing_score += TIMING_PULLBACK_VALIDO_PUNTOS
    elif retroceso > 25.0:             # Deterioro real: > 25%
        timing_score += TIMING_DETERIORO_PENALIZACION
    elif retroceso < 2.0:              # Casi sin retroceso: precio extendido
        timing_score += TIMING_EXTENDIDO_PENALIZACION

    # 2.3 Proximidad a soporte previo (mínimo 10 semanas)
    if df is not None and len(df) >= 10:
        try:
            minimo_10w = float(df["Low"].iloc[-10:].min())
            if minimo_10w > 0:
                dist_soporte = (precio - minimo_10w) / minimo_10w * 100
                if 0 <= dist_soporte <= TIMING_CERCA_SOPORTE_UMBRAL:
                    timing_score += TIMING_CERCA_SOPORTE_PUNTOS
        except Exception as e:
            logger.debug(f"Error calculando soporte: {e}")

    # Cap timing entre -1 y 3
    timing_score = max(-1, min(3, timing_score))

    # ═══════════════════════════════════════
    # COMPONENTE 3: MOMENTUM (0-2)
    # ═══════════════════════════════════════
    momentum_score = 0

    # 3.1 RSI semanal en zona pullback — método Wilder correcto
    rsi_val = None
    if len(precios) >= 15:
        try:
            rsi_series = calcular_rsi(pd.Series(precios), periodo=14)
            rsi_val = round(rsi_series.iloc[-1], 1) if not pd.isna(rsi_series.iloc[-1]) else None

            if rsi_val is not None:
                if 40 <= rsi_val <= 55:
                    momentum_score += MOMENTUM_RSI_PUNTOS
                elif rsi_val < MOMENTUM_RSI_SOBREVENTA:
                    momentum_score += MOMENTUM_RSI_SOBREVENTA_PENALIZACION
        except Exception as e:
            logger.debug(f"Error calculando RSI: {e}")

    # 3.2 Volumen decreciente en pullback
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            vol_media = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            if vol_actual < vol_media * MOMENTUM_VOLUMEN_RATIO:
                momentum_score += MOMENTUM_VOLUMEN_PUNTOS
            elif vol_actual > vol_media * MOMENTUM_VOLUMEN_VENDEDOR_RATIO:
                momentum_score += MOMENTUM_VOLUMEN_VENDEDOR_PENALIZACION
        except Exception as e:
            logger.debug(f"Error calculando volumen: {e}")

    # 3.3 Vela de reversión (doji/martillo)
    if df is not None and len(df) >= 2:
        try:
            ultima_vela = df.iloc[-1]
            body = abs(float(ultima_vela["Close"]) - float(ultima_vela["Open"]))
            rango = float(ultima_vela["High"]) - float(ultima_vela["Low"])
            if rango > 0 and (body / rango) < MOMENTUM_VELA_REVERSION_RATIO:
                momentum_score += MOMENTUM_VELA_REVERSION_PUNTOS
        except Exception as e:
            logger.debug(f"Error calculando vela: {e}")

    # Cap momentum entre 0 y 2 (NO permitir momentum negativo)
    momentum_score = max(0, min(2, momentum_score))

    # Bonus base: Si hay pullback válido, mínimo 0.5 momentum
    # Evita que RSI fuera de rango destruya setup completo
    if pullback.get("es_pullback", False) and momentum_score < 0.5:
        momentum_score = 0.5

    # ═══════════════════════════════════════
    # SCORE FINAL
    # ═══════════════════════════════════════
    score_final = estructura_score + timing_score + momentum_score
    score_final = max(0, min(10, score_final))

    # ═══════════════════════════════════════
    # VALIDACIÓN FINAL
    # ═══════════════════════════════════════
    # Requiere estructura mínima Y timing no negativo
    valido = (estructura_score >= SCORE_MIN_ESTRUCTURA and
              timing_score >= SCORE_MIN_TIMING)

    return {
        "score": round(score_final, 1),
        "score_max": 10,
        "valido": valido,
        "desglose": {
            "estructura": round(estructura_score, 1),
            "timing": round(timing_score, 1),
            "momentum": round(momentum_score, 1)
        },
        "rsi": rsi_val
    }


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
    Doble confirmación: MM20↑ + MM50 > MM200

    Returns:
        dict con:
        - tendencia: "ALCISTA", "BAJISTA", "NEUTRAL"
        - mm10, mm20, mm40, mm50, mm200: valores de las MMs
        - precio_vs_mm20: relación precio/MM20 en %
        - mm50_sobre_mm200: bool — filtro de calidad de tendencia
    """
    if len(precios) < MM_TENDENCIA_LARGA:
        return {"tendencia": "INSUFICIENTE"}

    precio = precios[-1]
    mm5  = calcular_mm(precios, MM_TIMING_CORTA)   # timing entrada
    mm8  = calcular_mm(precios, MM_TIMING_MEDIA)   # timing alternativo
    mm10 = calcular_mm(precios, MM_TENDENCIA_CORTA)
    mm20 = calcular_mm(precios, MM_TENDENCIA_MEDIA)  # estructura
    mm40 = calcular_mm(precios, MM_TENDENCIA_LARGA)

    # Calcular pendiente MM20 (últimas 4 semanas vs anteriores)
    mm20_actual = np.mean(precios[-20:])
    mm20_previa = np.mean(precios[-24:-4])
    pendiente_mm20 = mm20_actual - mm20_previa

    # Filtro calidad tendencia: MM50 > MM200
    mm50 = calcular_mm(precios, MM_FILTRO_TENDENCIA) if len(precios) >= MM_FILTRO_TENDENCIA else None
    mm200 = calcular_mm(precios, MM_FILTRO_LARGO) if len(precios) >= MM_FILTRO_LARGO else None
    mm50_sobre_mm200 = (mm50 is not None and mm200 is not None and mm50 > mm200)

    # Determinar tendencia — estructura alcista aunque precio esté en pullback bajo MM20
    # Clave: durante un pullback válido el precio PUEDE estar bajo MM20 con MM20 bajando
    # Lo que importa es la estructura macro: MM50 > MM200
    if mm50_sobre_mm200:
        if pendiente_mm20 > 0:
            tendencia = "ALCISTA"    # estructura alcista con momentum corto plazo
        else:
            tendencia = "ALCISTA"    # pullback con estructura macro intacta
    elif precio < mm20 and pendiente_mm20 < 0:
        tendencia = "BAJISTA"        # estructura macro rota (MM50 < MM200) + MM20 bajando
    else:
        tendencia = "NEUTRAL"

    precio_vs_mm20 = ((precio - mm20) / mm20) * 100 if mm20 else None

    # Distancia precio a MM5 para timing
    dist_mm5 = abs(precio - mm5) / precio * 100 if mm5 and precio > 0 else None

    return {
        "tendencia":        tendencia,
        "mm5":              mm5,
        "mm8":              mm8,
        "mm10":             mm10,
        "mm20":             mm20,
        "mm40":             mm40,
        "mm50":             mm50,
        "mm200":            mm200,
        "precio_vs_mm20":   precio_vs_mm20,
        "dist_mm5":         dist_mm5,
        "pendiente_mm20":   pendiente_mm20,
        "mm50_sobre_mm200": mm50_sobre_mm200,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 DETECCIÓN DE PULLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_pullback(precios, lookback=LOOKBACK_MAXIMO):
    """
    Detecta si hay un pullback válido.
    Rango 5-8%: evita ruido (3%) y correcciones profundas (12%).

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
    # CORRECCIÓN LOOKAHEAD: Excluye el precio actual del análisis
    # de máximo (no usamos información futura)
    ultimos_precios_historicos = precios[-lookback:-1]

    if not ultimos_precios_historicos:
        return {"es_pullback": False, "motivo": "Histórico insuficiente"}

    maximo_reciente = max(ultimos_precios_historicos)
    indice_max = len(ultimos_precios_historicos) - 1 - list(reversed(ultimos_precios_historicos)).index(maximo_reciente)
    semanas_desde_max = len(ultimos_precios_historicos) - 1 - indice_max

    retroceso_pct = ((maximo_reciente - precio_actual) / maximo_reciente) * 100

    es_pullback = PULLBACK_MIN_PCT <= retroceso_pct <= PULLBACK_MAX_PCT

    if retroceso_pct < PULLBACK_MIN_PCT:
        motivo = f"Retroceso insuficiente ({retroceso_pct:.1f}%) — mínimo {PULLBACK_MIN_PCT}%"
    elif retroceso_pct > PULLBACK_MAX_PCT:
        motivo = f"Retroceso excesivo ({retroceso_pct:.1f}%) — máximo {PULLBACK_MAX_PCT}%"
    else:
        motivo = f"Pullback válido ({retroceso_pct:.1f}%)"

    return {
        "es_pullback":      es_pullback,
        "maximo_reciente":  maximo_reciente,
        "retroceso_pct":    retroceso_pct,
        "semanas_desde_max": semanas_desde_max,
        "motivo":           motivo
    }


def detectar_giro_semanal(precios, highs=None):
    """
    Calcula el trigger de entrada para la sesión siguiente.

    Trigger = high de la semana actual × 1.001
    Si el precio supera ese nivel la semana siguiente → giro confirmado.

    Returns:
        dict con:
        - hay_giro: bool (precio actual ya superó el high anterior)
        - trigger: float (nivel Buy Stop para broker)
        - variacion_pct: float
    """
    if len(precios) < 2:
        return {"hay_giro": False, "trigger": None}

    precio_actual  = precios[-1]
    precio_anterior = precios[-2]
    variacion_pct  = ((precio_actual - precio_anterior) / precio_anterior) * 100

    # Trigger = high semana actual × 1.001
    high_actual = highs[-1] if highs is not None and len(highs) > 0 else precio_actual
    trigger = round(high_actual * 1.001, 2)

    return {
        "hay_giro":      precio_actual > precio_anterior,
        "trigger":       trigger,
        "variacion_pct": variacion_pct,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ CÁLCULO DE STOPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_stop_inicial(precio_entrada, precios, df=None, stop_atr_mult=None):
    """
    Stop = max(mínimo estructura × 0.98, entrada - ATR × 2)
    
    MEJORA v82.4: Stop híbrido mejorado para medio plazo
    
    En semanal el stop por estructura tiende a quedar muy lejos —
    el ATR lo acerca y hace el riesgo más manejable.
    
    Usa el MAYOR de:
    - Mínimo últimas 20 semanas × 0.98 (estructura sólida)
    - Entrada - (ATR × 2) (protección volatilidad)
    
    Resultado: Stop ni muy ajustado (ruido) ni muy amplio (mal RR)
    
    CORRECCIÓN LOOKAHEAD: Usa histórico (excluye el precio actual)
    """
    lookback = min(STOP_ESTRUCTURA_LOOKBACK, len(precios) - 1)  # -1 para excluir actual

    # Excluye el precio actual (no usamos información futura)
    precios_historicos = precios[-(lookback + 1):-1]

    if not precios_historicos:
        # Fallback: usa estructura simple si no hay histórico
        stop_estructura = precio_entrada * 0.95
    else:
        stop_estructura = min(precios_historicos) * 0.98

    if df is not None:
        atr = calcular_atr_semanal(df)
    else:
        atr = calcular_atr_desde_listas(precios)

    if stop_atr_mult is None:
        stop_atr_mult = STOP_ATR_MULTIPLICADOR

    # STOP HÍBRIDO: Toma el MAYOR (más conservador)
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

# ══════════════════════════════════════════════════════════════
# CLASE WRAPPER — para compatibilidad con medio_routes.py
# ══════════════════════════════════════════════════════════════


def calcular_score_medio(precios, tendencia, pullback, df=None):
    """
    Score 0-10 alineado con los filtros reales del sistema.

    Criterios:
    - MM50 > MM200 (tendencia macro):        +3.0  obligatorio ya filtrado
    - MM20 pendiente positiva:               +1.0
    - Pullback 5-8% (óptimo):               +2.0  |  4-5% (válido): +1.0
    - RSI semanal 40-55 (zona pullback):     +1.5
    - Precio cerca MM10 ≤3% (+1.5) | ≤5% (+0.5)
    - Volumen decreciente en pullback:       +1.0
    Total máximo: 10.0
    """
    score = 0
    score_max = 10

    precio    = precios[-1] if precios else 0
    mm20      = tendencia.get("mm20", 0) or 0
    mm50      = tendencia.get("mm50", 0) or 0
    mm200     = tendencia.get("mm200", 0) or 0
    pendiente = tendencia.get("pendiente_mm20", 0) or 0
    mm50_ok   = tendencia.get("mm50_sobre_mm200", False)

    # 1. MM50 > MM200 — tendencia macro (+3.0)
    if mm50_ok:
        score += 3.0

    # 2. MM20 pendiente positiva (+1.0)
    if pendiente > 0:
        score += 1.0

    # 3. Calidad del pullback — variable escalonada (+0.5, +1, +2)
    retroceso = pullback.get("retroceso_pct", 0)
    if 5.0 <= retroceso <= 8.0:
        score += 2.0   # rango óptimo
    elif 4.0 <= retroceso < 5.0:
        score += 1.0   # válido zona media
    elif 3.0 <= retroceso < 4.0:
        score += 0.5   # válido zona baja

    # 4. RSI semanal 40-55 zona pullback sano (+1.5)
    #    IMPORTANTE: RSI calculado con método Wilder sobre datos SEMANALES
    rsi_val = None
    if len(precios) >= 15:
        try:
            rsi_series = calcular_rsi(pd.Series(precios), periodo=14)
            rsi_val = round(rsi_series.iloc[-1], 1) if not pd.isna(rsi_series.iloc[-1]) else None
            if rsi_val is not None and 40 <= rsi_val <= 55:
                score += 1.5
        except Exception as _e:
            logger.debug(f'logica_medio cálculo RSI ignorado: {_e}')

    # 5. Precio cerca de MM20 — timing de entrada
    #    ≤2% → muy buen timing (+1.5) | 2-3% → aceptable (+0.5)
    if mm20 > 0:
        dist_mm20 = abs(precio - mm20) / mm20 * 100
        if dist_mm20 <= 2.0:
            score += 1.5
        elif dist_mm20 <= 3.0:
            score += 0.5

    # 6. Volumen decreciente en pullback — confirma corrección sana (+1.0)
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            vol_media  = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            if vol_actual < vol_media * 0.85:
                score += 1.0
        except Exception as _e:
            logger.debug(f'logica_medio cálculo ignorado: {_e}')

    # 7. S/R — Soporte en pullback + espacio libre (suma Y resta)
    # Timeframe semanal → periodo más largo para detectar niveles relevantes
    if df is not None and len(df) >= 40:
        try:
            from analisis.tecnico.soportes_resistencias import evaluar_sr
            sr = evaluar_sr(df, periodo=20, timeframe="semanal")
            score += sr["score_sr"]   # puede ser negativo (penalización)
        except Exception as _e:
            logger.debug(f'logica_medio cálculo ignorado: {_e}')

    return round(min(score, score_max), 1), score_max


def calcular_semaforo_medio(precios, tendencia, pullback, df=None):
    """
    Semáforo de prioridad para señales de medio plazo.
    No es un filtro — es un ranking de calidad cuando hay varias señales.

    Confirmaciones evaluadas:
    - RSI semanal 40-55
    - Volumen decreciente en pullback
    - ESTRUCTURA: precio > MM20 semanal
    - TIMING: precio cerca MM5 semanal (≤7%)

    🟢 Operar    — 3/3 confirmaciones
    🟡 En radar  — 2/3 confirmaciones
    🔴 Esperar   — 1/3 o menos
    """
    confirmaciones = []

    # RSI 40-55
    rsi_ok = False
    if len(precios) >= 15:
        try:
            deltas    = [precios[i]-precios[i-1] for i in range(1, min(15, len(precios)))]
            ganancias = [d for d in deltas if d > 0]
            perdidas  = [-d for d in deltas if d < 0]
            avg_g     = sum(ganancias)/14 if ganancias else 0
            avg_p     = sum(perdidas)/14  if perdidas  else 0.001
            rsi       = 100-(100/(1+avg_g/avg_p))
            rsi_ok    = 40 <= rsi <= 55
        except Exception as _e:
            logger.debug(f'logica_medio cálculo ignorado: {_e}')
    confirmaciones.append(("RSI 40-55 (zona pullback sano)", rsi_ok))

    # Volumen decreciente
    vol_ok = False
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            vol_media  = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            vol_ok     = vol_actual < vol_media * 0.85
        except Exception as _e:
            logger.debug(f'logica_medio cálculo ignorado: {_e}')
    confirmaciones.append(("Volumen decreciente en pullback", vol_ok))

    # ESTRUCTURA: precio > MM20 semanal (tendencia válida)
    mm20_val   = tendencia.get("mm20", 0) or 0
    precio     = precios[-1] if precios else 0
    struct_ok  = (mm20_val > 0 and precio > mm20_val)
    confirmaciones.append(("Precio > MM20 semanal (estructura)", struct_ok))

    # TIMING: precio cerca de MM5 semanal (~MM20 diaria)
    # ≤5%: buen timing | 5-10%: aceptable | >10%: extendido
    mm5_val    = tendencia.get("mm5", 0) or 0
    if mm5_val > 0 and precio > 0:
        dist_mm5   = abs(precio - mm5_val) / precio * 100
        timing_ok  = dist_mm5 <= 7.0   # ≤7% buen timing
        if dist_mm5 <= 5.0:
            timing_txt = f"Timing MM5 ≤5% ({dist_mm5:.1f}%) ✓"
        elif dist_mm5 <= 7.0:
            timing_txt = f"Timing MM5 aceptable ({dist_mm5:.1f}%)"
        else:
            timing_txt = f"Extendido vs MM5 ({dist_mm5:.1f}%)"
    else:
        timing_ok  = False
        timing_txt = "Timing MM5 semanal"
    confirmaciones.append((timing_txt, timing_ok))

    n_ok = sum(1 for _, ok in confirmaciones if ok)
    # 4 criterios ahora: RSI + Volumen + Estructura MM20 + Timing MM5
    if n_ok >= 4:
        semaforo = {"color": "verde",    "emoji": "🟢", "texto": "Operar",   "n": n_ok}
    elif n_ok >= 3:
        semaforo = {"color": "amarillo", "emoji": "🟡", "texto": "En radar", "n": n_ok}
    elif n_ok == 2:
        semaforo = {"color": "naranja",  "emoji": "🟠", "texto": "Vigilar",  "n": n_ok}
    else:
        semaforo = {"color": "rojo",     "emoji": "🔴", "texto": "Esperar",  "n": n_ok}

    semaforo["confirmaciones"] = [{"texto": t, "ok": ok} for t, ok in confirmaciones]
    return semaforo


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 CLASIFICACIÓN UNIFICADA MEDIO PLAZO (v82.3)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clasificar_setup_medio(score_0_10, valido_criticos=True):
    """
    Clasificación unificada del setup medio plazo.
    
    MEJORA v82.3: Score es la única fuente de verdad.
    Elimina doble criterio (criticos booleano + score separado).
    
    Args:
        score_0_10: Score calculado (escala 0-10)
        valido_criticos: ¿Pasó validaciones críticas?
    
    Returns:
        dict con decision y clasificacion
    
    LÓGICA UNIFICADA (escala 0-10):
    ├─ Score >= 8.5 (EXCELENTE): COMPRA fuerte
    ├─ Score 6.5-8.4 (BUENO): COMPRA
    ├─ Score 5.5-6.4 (MEDIOCRE): VIGILAR (si criticos ok)
    ├─ Score < 5.5 (DÉBIL): NO_OPERAR
    └─ Si criticos invalidan: SIEMPRE NO_OPERAR
    """
    if not valido_criticos:
        return {
            "decision": "NO_OPERAR",
            "clasificacion": "RECHAZADO",
        }

    if score_0_10 >= 8.5:
        clasificacion = "EXCELENTE"
        decision = "COMPRA"
    elif score_0_10 >= 6.5:
        clasificacion = "BUENO"
        decision = "COMPRA"
    elif score_0_10 >= 5.5:
        clasificacion = "MEDIOCRE"
        decision = "VIGILAR"
    else:
        clasificacion = "DÉBIL"
        decision = "NO_OPERAR"

    return {
        "decision": decision,
        "clasificacion": clasificacion,
    }


def clasificar_fundamental(score_fundamental):
    """
    Clasifica el score fundamental con emoji y etiqueta.
    
    Args:
        score_fundamental: Score 0-10 del análisis fundamental
    
    Returns:
        dict con emoji, etiqueta, color
    """
    if score_fundamental >= 8.0:
        return {
            "emoji": "🟢",
            "etiqueta": "SÓLIDO",
            "color": "#10b981",  # Verde
            "score": score_fundamental
        }
    if score_fundamental >= 6.0:
        return {
            "emoji": "🟡",
            "etiqueta": "ACEPTABLE",
            "color": "#f59e0b",  # Amarillo
            "score": score_fundamental
        }
    if score_fundamental >= 4.0:
        return {
            "emoji": "🟠",
            "etiqueta": "DÉBIL",
            "color": "#f97316",  # Naranja
            "score": score_fundamental
        }
    return {
        "emoji": "🔴",
        "etiqueta": "RIESGO",
        "color": "#ef4444",  # Rojo
        "score": score_fundamental
    }


def calcular_setup_global(score_tecnico, score_fundamental):
    """
    Calcula el setup global combinando técnico y fundamental.
    
    Ponderación: 70% técnico / 30% fundamental (somos traders)
    
    Args:
        score_tecnico: Score 0-10 técnico
        score_fundamental: Score 0-10 fundamental
    
    Returns:
        dict con score_global y clasificacion_global
    """
    PESO_TECNICO = 0.70
    PESO_FUNDAMENTAL = 0.30

    score_global = (score_tecnico * PESO_TECNICO) + (score_fundamental * PESO_FUNDAMENTAL)
    score_global = round(score_global, 1)

    # Clasificación del setup global
    if score_global >= 8.5:
        clasificacion = "EXCELENTE"
    elif score_global >= 7.5:
        clasificacion = "MUY BUENO"
    elif score_global >= 6.5:
        clasificacion = "BUENO"
    elif score_global >= 5.5:
        clasificacion = "ACEPTABLE"
    else:
        clasificacion = "DÉBIL"

    return {
        "score_global": score_global,
        "clasificacion_global": clasificacion
    }


class MedioPlazo:
    """
    Wrapper OOP sobre las funciones de logica_medio.py.
    medio_routes.py llama: señal = _medio.evaluar(ticker, cache)
    """

    def evaluar(self, ticker: str, cache=None) -> dict:
        """
        Evalúa señal de medio plazo:
          1. Tendencia macro: MM20↑ + MM50 > MM200
          2. Pullback válido 5-8% en últimas 10 semanas
          3. RSI semanal > 45
          4. Volatilidad mínima 8%
          5. Riesgo controlado 1.5-8%
          6. Trigger: high semana × 1.001
        """
        from core.riesgo import calcular_rr
        from estrategias.posicional.datos_posicional import obtener_datos_semanales

        # Intentar con get_df_semanal primero, fallback a get_df + resample
        df = None
        try:
            from estrategias.posicional.datos_posicional import obtener_datos_semanales
            df, _ = obtener_datos_semanales(ticker, periodo_años=5, validar=False)
        except Exception as _e:
            logger.debug(f'logica_medio cálculo ignorado: {_e}')

        # Fallback: get_df diario + resamplear
        if df is None or df.empty:
            try:
                from core.data_provider import get_df_semanal
                df, _ = get_df_semanal(ticker, periodo_años=5)
            except Exception as _e:
                logger.debug(f'logica_medio cálculo ignorado: {_e}')

        if df is None or df.empty:
            try:
                from core.data_provider import get_df
                df_d = get_df(ticker, periodo="5y", cache=cache)
                if df_d is not None and not df_d.empty:
                    df = pd.DataFrame({
                        "Open":   df_d["Open"].resample("W-FRI").first(),
                        "High":   df_d["High"].resample("W-FRI").max(),
                        "Low":    df_d["Low"].resample("W-FRI").min(),
                        "Close":  df_d["Close"].resample("W-FRI").last(),
                        "Volume": df_d["Volume"].resample("W-FRI").sum(),
                    }).dropna()
                    df = df[df["Close"] > 0]
            except Exception as _e:
                logger.debug(f'logica_medio cálculo ignorado: {_e}')

        if df is None or df.empty or len(df) < MM_TENDENCIA_LARGA:
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": 0, "entrada": 0, "stop": 0,
                "objetivo": None, "setup_score": 0, "setup_max": 10,
                "motivos": [{"ok": False, "texto": f"Histórico insuficiente ({len(df) if df is not None else 0} semanas)"}],
                "advertencias": [], "fecha_desde": "", "fecha_hasta": "", "semanas": 0,
                "detalles": {},
            }

        precios       = df["Close"].tolist()
        highs         = df["High"].tolist()
        precio_actual = round(precios[-1], 2)
        fecha_desde   = str(df.index[0].date())
        fecha_hasta   = str(df.index[-1].date())
        semanas       = len(df)

        # ── Indicadores ───────────────────────────────────────────────────────
        tendencia = detectar_tendencia_semanal(precios)
        pullback  = detectar_pullback(precios)
        giro      = detectar_giro_semanal(precios, highs=highs)
        vol_anual = calcular_volatilidad(precios, ventana=52)

        # Scoring V2 profesional (estructura + timing + momentum)
        resultado_score = calcular_score_medio_v2(precios, tendencia, pullback, df=df)
        score = resultado_score["score"]
        score_max = resultado_score["score_max"]
        desglose_scoring = resultado_score.get("desglose", {})

        semaforo         = calcular_semaforo_medio(precios, tendencia, pullback, df=df)

        # Valores de MMs
        mm20  = round(tendencia.get("mm20", 0) or 0, 2)
        mm50  = round(tendencia.get("mm50", 0) or 0, 2)
        mm200 = round(tendencia.get("mm200", 0) or 0, 2)
        mm50_sobre_mm200 = tendencia.get("mm50_sobre_mm200", False)
        tendencia_str    = tendencia.get("tendencia", "NEUTRAL")
        retroceso        = pullback.get("retroceso_pct", 0)
        trigger          = giro.get("trigger", round(precio_actual * 1.001, 2))

        # RSI semanal — método Wilder correcto sobre datos SEMANALES
        rsi_val = None
        if len(precios) >= 15:
            try:
                rsi_series = calcular_rsi(pd.Series(precios), periodo=14)
                rsi_val = round(rsi_series.iloc[-1], 1) if not pd.isna(rsi_series.iloc[-1]) else None
            except Exception as _e:
                logger.debug(f'logica_medio cálculo RSI ignorado: {_e}')

        # ── Detalles para el template ─────────────────────────────────────────
        detalles_base = {
            "tendencia":        tendencia_str,
            "retroceso_pct":    round(retroceso, 1),
            "volatilidad_pct":  round(vol_anual, 1) if vol_anual else None,
            "mm20":             mm20,
            "mm50":             mm50,
            "mm200":            mm200,
            "mm50_sobre_mm200": mm50_sobre_mm200,
            "rsi":              rsi_val,
            "giro_semanal":     giro.get("hay_giro", False),
            "trigger":          trigger,
        }

        # ── Construir motivos completos (siempre, compra o no) ────────────────
        motivos = []

        # 1. Tendencia macro — criterio: MM50 > MM200 (estructura macro)
        # La MM20 con pendiente negativa es pullback válido, no tendencia bajista
        tendencia_ok = mm50_sobre_mm200
        if mm200 > 0:
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Tendencia macro: precio {precio_actual}€ vs MM200 {mm200}€ | MM50 {mm50}€ {'>' if mm50_sobre_mm200 else '<'} MM200"
            })
        else:
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Tendencia: {tendencia_str.lower()} (precio {precio_actual}€ vs MM20 {mm20}€)"
            })

        # 2. Pullback
        motivos.append({
            "ok":    pullback.get("es_pullback", False),
            "texto": pullback.get("motivo", f"Pullback: {retroceso:.1f}%")
        })

        # 3. RSI — zona pullback sano 40-55 (alineado con score y semáforo)
        if rsi_val is not None:
            rsi_ok = 40 <= rsi_val <= 55
            motivos.append({
                "ok":    rsi_ok,
                "texto": f"RSI semanal {rsi_val} ({'zona pullback' if rsi_ok else 'fuera de zona 40-55'})"
            })

        # 4. Volatilidad
        if vol_anual is not None:
            vol_ok = vol_anual >= VOL_MIN_PCT
            motivos.append({
                "ok":    vol_ok,
                "texto": f"Volatilidad anual {vol_anual:.1f}% (mínimo {VOL_MIN_PCT}%)"
            })

        # 5. MM50 > MM200
        if mm50 > 0 and mm200 > 0:
            motivos.append({
                "ok":    mm50_sobre_mm200,
                "texto": f"MM50 {'>' if mm50_sobre_mm200 else '<'} MM200 ({mm50}€ vs {mm200}€)"
            })

        # ── Filtros eliminatorios ─────────────────────────────────────────────
        # Evaluación S/R — puede invalidar si pierde soporte
        sr_eval = None
        if df is not None and len(df) >= 40:
            try:
                from analisis.tecnico.soportes_resistencias import evaluar_sr
                sr_eval = evaluar_sr(df, periodo=20, timeframe="semanal")
            except Exception as _e:
                logger.debug(f'logica_medio cálculo ignorado: {_e}')

        rechazos = []
        if not tendencia_ok:
            rechazos.append("Tendencia no alcista")
        if not pullback.get("es_pullback"):
            rechazos.append(pullback.get("motivo", "Sin pullback válido"))
        if vol_anual is not None and vol_anual < VOL_MIN_PCT:
            rechazos.append(f"Volatilidad baja ({vol_anual:.1f}%)")
        if sr_eval and sr_eval.get("invalidar"):
            rechazos.append("Precio por debajo de soporte relevante")

        if rechazos:
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": precio_actual,
                "entrada": 0, "stop": 0, "objetivo": None, "trigger": trigger,
                "setup_score": score, "setup_max": score_max,
                "motivos": motivos,
                "advertencias": [], "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta, "semanas": semanas,
                "detalles": detalles_base,
            }

        # ── Stop y riesgo ─────────────────────────────────────────────────────
        entrada    = precio_actual
        stop       = calcular_stop_inicial(entrada, precios, df=df)
        if stop is None or stop <= 0:
            stop = entrada * (1 - RIESGO_MAX_PCT / 100)

        val_riesgo = validar_riesgo(trigger, stop)  # riesgo desde trigger (precio real de entrada)
        riesgo_pct = val_riesgo.get("riesgo_pct", 0)

        if not val_riesgo["riesgo_valido"]:
            motivos.append({"ok": False, "texto": f"Riesgo fuera de rango: {val_riesgo['motivo']}"})
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": precio_actual,
                "entrada": entrada, "stop": round(stop, 2), "objetivo": None,
                "trigger": trigger, "setup_score": score, "setup_max": score_max,
                "motivos": motivos, "advertencias": [],
                "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta,
                "semanas": semanas, "detalles": detalles_base,
            }

        # ── DECISIÓN UNIFICADA (v82.3) ──────────────────────────────────────
        # Score es la ÚNICA fuente de verdad para clasificación
        # Eliminación doble criterio (criticos + score umbral)
        valido_criticos = len(rechazos) == 0 and val_riesgo["riesgo_valido"]
        clasificacion_unif = clasificar_setup_medio(score, valido_criticos)

        atr      = calcular_atr_semanal(df)
        R_unit   = trigger - stop
        objetivo = round(trigger + 6.0 * R_unit, 2) if R_unit > 0 else None

        # MEJORA v82.5: Validar RR mínimo
        # RR < 1.5 no tiene ventaja matemática (necesita winrate > 67%)
        rr = None
        if objetivo:
            from core.riesgo import calcular_rr
            rr_calc = calcular_rr(trigger, stop, objetivo, rr_minimo=1.5)
            if rr_calc is None:
                # RR insuficiente: rechaza operación
                clasificacion_unif = {"decision": "NO_OPERAR", "clasificacion": "DÉBIL"}
                motivos.append({
                    "ok": False,
                    "texto": f"RR insuficiente: necesita >= 1.5 (calculado: {round((objetivo-trigger)/(trigger-stop), 2)})"
                })
            else:
                rr = rr_calc

        return {
            "valido":      clasificacion_unif["decision"] != "NO_OPERAR",
            "decision":    clasificacion_unif["decision"],
            "ticker":      ticker,
            "tipo":        "MEDIO",
            "precio_actual": precio_actual,
            "entrada":     round(entrada, 2),
            "trigger":     trigger,
            "stop":        round(stop, 2),
            "objetivo":    objetivo,
            "rr":          rr,
            "riesgo_pct":  round(riesgo_pct, 1),
            "setup_score": score,
            "setup_max":   score_max,
            "desglose_scoring": desglose_scoring,  # NUEVO: Estructura/Timing/Momentum
            "semaforo":    semaforo,
            "motivos":     motivos,
            "advertencias": [],
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "semanas":     semanas,
            "detalles":    detalles_base,
        }

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        filtrar_mercado: bool = True,
        top_n: int = None,
    ) -> list:
        """
        Escanea una lista de tickers y devuelve señales ordenadas por score.
        """
        from core.universos import TODOS
        lista = tickers or TODOS
        señales = []

        for ticker in lista:
            try:
                señal = self.evaluar(ticker, cache)
                señal["ticker"] = ticker
                señales.append(señal)
            except Exception as e:
                logging.getLogger(__name__).warning(f"ScannerMedio: error en {ticker}: {e}")

        # Ordenar: primero válidas, luego por score descendente
        señales.sort(key=lambda s: (s.get("valido", False), s.get("setup_score", 0)), reverse=True)

        if top_n:
            señales = señales[:top_n]

        return señales
