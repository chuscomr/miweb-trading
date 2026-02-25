# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO CONFIRMACIONES PULLBACK - Sistema Dual Trading
# ══════════════════════════════════════════════════════════════════════════════
# 
# ⚠️ ESTE MÓDULO ES EXCLUSIVO PARA LA ESTRATEGIA PULLBACK (Rebotes)
# 
# Filosofía PULLBACK: "Comprar barato en soporte"
# - Precio cerca de soporte (2-8% de distancia)
# - RSI en sobreventa (<40)
# - Patrón alcista (martillo, envolvente)
# - Volumen en rebote
# - Soporte fuerte (3+ toques)
#
# ❌ NO usar para validar BREAKOUTS (rupturas)
# ✅ Usar junto con: logica_pullback.py
#
# Sistema completo de validación con 10 factores
# Puntuación: 0-100 puntos
# ══════════════════════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np

def calcular_rsi(df, periodo=14):
    """
    Calcula el RSI (Relative Strength Index)
    Valores: 0-100
    
    INTERPRETACIÓN PULLBACK:
    - RSI < 30 = SOBREVENTA ✅ (zona de rebote ideal)
    - RSI < 40 = Bajo ✅ (zona de compra)
    - RSI > 60 = Alto ⚠️ (no es pullback)
    - RSI > 70 = SOBRECOMPRA ❌ (evitar)
    """
    delta = df['Close'].diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    
    rs = avg_ganancia / avg_perdida
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]


def calcular_adx(df, periodo=14):
    """
    Calcula el ADX (Average Directional Index)
    Valores: 0-100
    
    INTERPRETACIÓN PULLBACK:
    - ADX > 25 = Tendencia clara ✅ (pullback en tendencia)
    - ADX 20-25 = Tendencia débil ⚠️
    - ADX < 20 = Rango ❌ (no hay tendencia para hacer pullback)
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # Plus/Minus Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed averages
    atr = tr.rolling(window=periodo).mean()
    plus_di = 100 * (plus_dm.rolling(window=periodo).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=periodo).mean() / atr)
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=periodo).mean()
    
    return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 20


def calcular_macd(df, rapida=12, lenta=26, señal=9):
    """
    Calcula el MACD (Moving Average Convergence Divergence)
    Returns: (macd, signal, histograma)
    
    INTERPRETACIÓN PULLBACK:
    - Histograma > 0 y creciendo = Momentum recuperándose ✅
    - Histograma cambiando de negativo a positivo = Rebote confirmado ✅
    - Histograma < 0 y decreciendo = Todavía cayendo ⚠️
    """
    ema_rapida = df['Close'].ewm(span=rapida, adjust=False).mean()
    ema_lenta = df['Close'].ewm(span=lenta, adjust=False).mean()
    
    macd_line = ema_rapida - ema_lenta
    signal_line = macd_line.ewm(span=señal, adjust=False).mean()
    histograma = macd_line - signal_line
    
    return {
        'macd': macd_line.iloc[-1],
        'signal': signal_line.iloc[-1],
        'histograma': histograma.iloc[-1],
        'tendencia': 'ALCISTA' if histograma.iloc[-1] > 0 else 'BAJISTA'
    }


def analizar_volumen(df):
    """
    Analiza el volumen de la última vela vs promedio
    
    INTERPRETACIÓN PULLBACK:
    - Volumen > 1.5x = Rebote con confirmación ✅
    - Volumen > 2x = Rebote MUY fuerte ✅✅
    - Volumen normal = Rebote sin confirmación ⚠️
    - Volumen bajo = Rebote débil ❌
    """
    volumen_actual = df['Volume'].iloc[-1]
    volumen_promedio = df['Volume'].rolling(window=20).mean().iloc[-1]
    
    ratio = volumen_actual / volumen_promedio if volumen_promedio > 0 else 1
    
    if ratio >= 2.0:
        fuerza = "MUY ALTA"
        puntos = 30
    elif ratio >= 1.5:
        fuerza = "ALTA"
        puntos = 20
    elif ratio >= 1.0:
        fuerza = "NORMAL"
        puntos = 10
    else:
        fuerza = "BAJA"
        puntos = 0
    
    return {
        'ratio': ratio,
        'fuerza': fuerza,
        'puntos': puntos
    }


def analizar_posicion_cierre_vela(df):
    """
    Analiza dónde cerró la vela en su rango
    
    INTERPRETACIÓN PULLBACK:
    - Cierre en 75-100% del rango = Rechazo fuerte del soporte ✅✅
    - Cierre en 60-75% = Rebote confirmado ✅
    - Cierre en 25-60% = Rebote débil ⚠️
    - Cierre en 0-25% = Sin rebote ❌
    """
    ultima_vela = df.iloc[-1]
    
    high = ultima_vela['High']
    low = ultima_vela['Low']
    close = ultima_vela['Close']
    
    if high == low:
        return {'posicion_pct': 50, 'fuerza': 'NEUTRAL', 'puntos': 5}
    
    posicion_pct = ((close - low) / (high - low)) * 100
    
    if posicion_pct >= 75:
        fuerza = "MUY ALCISTA"
        puntos = 15
    elif posicion_pct >= 60:
        fuerza = "ALCISTA"
        puntos = 10
    elif posicion_pct >= 40:
        fuerza = "NEUTRAL"
        puntos = 5
    elif posicion_pct >= 25:
        fuerza = "BAJISTA"
        puntos = 0
    else:
        fuerza = "MUY BAJISTA"
        puntos = -10
    
    return {
        'posicion_pct': round(posicion_pct, 1),
        'fuerza': fuerza,
        'puntos': puntos
    }


def analizar_medias_moviles(df):
    """
    Analiza posición del precio respecto a MMs (20, 50, 200)
    
    INTERPRETACIÓN PULLBACK:
    - Precio cerca MM20 = Pullback a soporte dinámico ✅✅
    - Precio > MM200 = Tendencia alcista macro ✅
    - MM20 > MM50 > MM200 = Tendencia ordenada ✅
    - Precio < MM200 = Sin tendencia alcista ❌
    """
    close = df['Close'].iloc[-1]
    
    mm20 = df['Close'].rolling(window=20).mean().iloc[-1]
    mm50 = df['Close'].rolling(window=50).mean().iloc[-1] if len(df) >= 50 else None
    mm200 = df['Close'].rolling(window=200).mean().iloc[-1] if len(df) >= 200 else None
    
    puntos = 0
    detalles = []
    
    # Precio vs MM20
    if close > mm20:
        dist_mm20 = ((close - mm20) / mm20) * 100
        if dist_mm20 < 3:
            puntos += 10
            detalles.append(f"Cerca MM20 ({mm20:.2f}€) - soporte dinámico")
        else:
            puntos += 5
            detalles.append(f"Sobre MM20 ({mm20:.2f}€)")
    else:
        detalles.append(f"Bajo MM20 ({mm20:.2f}€)")
    
    # Precio vs MM50
    if mm50 and close > mm50:
        puntos += 5
        detalles.append(f"Sobre MM50 ({mm50:.2f}€)")
    
    # Precio vs MM200
    if mm200 and close > mm200:
        puntos += 5
        detalles.append(f"Sobre MM200 ({mm200:.2f}€)")
    
    return {
        'mm20': mm20,
        'mm50': mm50,
        'mm200': mm200,
        'puntos': puntos,
        'detalles': detalles
    }


def calcular_confirmaciones_pullback(df, patron, distancia_soporte_pct, fuerza_soporte):
    """
    ══════════════════════════════════════════════════════════════════════════════
    SISTEMA PROFESIONAL DE CONFIRMACIÓN PARA ESTRATEGIA PULLBACK
    ══════════════════════════════════════════════════════════════════════════════
    
    ⚠️ ESTE SISTEMA SOLO VALIDA PULLBACKS (REBOTES)
    
    Valida:
    ✅ Precio cerca de soporte (2-8%)
    ✅ RSI en sobreventa (<40)
    ✅ Patrón alcista (martillo, envolvente)
    ✅ Volumen en rebote
    ✅ Soporte fuerte
    
    NO valida:
    ❌ Breakouts (rupturas)
    ❌ RSI alto (>60)
    ❌ Precio en máximos
    
    Puntuación: 0-100 puntos
    - 75-100 = EXCELENTE (compra prioritaria)
    - 60-74 = BUENO (compra)
    - 45-59 = ACEPTABLE (revisar)
    - 30-44 = DUDOSO (esperar)
    - 0-29 = MALO (no operar)
    
    ══════════════════════════════════════════════════════════════════════════════
    
    Args:
        df: DataFrame con OHLCV
        patron: dict del patrón de velas detectado
        distancia_soporte_pct: distancia al soporte en % (CRÍTICO para pullback)
        fuerza_soporte: fuerza del soporte ('DÉBIL', 'MEDIO', 'FUERTE')
    
    Returns:
        dict con puntuación total, desglose y recomendación
    """
    
    puntuacion_total = 0
    max_puntos = 100
    desglose = {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 1: PATRÓN DE VELAS (0-15 puntos)
    # Busca: Martillo, Envolvente alcista, Piercing
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if patron['señal'] == 'ALCISTA':
        puntos_patron = int(patron['confianza'] * 0.15)  # 75% confianza = 11 puntos
        desglose['patron_velas'] = {
            'puntos': puntos_patron,
            'detalle': f"{patron['patron']} ({patron['confianza']}%)"
        }
    elif patron['señal'] == 'BAJISTA':
        puntos_patron = -20  # Penalización fuerte
        desglose['patron_velas'] = {
            'puntos': puntos_patron,
            'detalle': f"⚠️ {patron['patron']} BAJISTA"
        }
    else:
        puntos_patron = 0
        desglose['patron_velas'] = {
            'puntos': 0,
            'detalle': 'Sin patrón relevante'
        }
    
    puntuacion_total += puntos_patron
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 2: DISTANCIA A SOPORTE (0-15 puntos)
    # ⭐ CRÍTICO PARA PULLBACK
    # Ideal: 2-5% de distancia al soporte
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if distancia_soporte_pct is not None:
        if 2 <= distancia_soporte_pct <= 5:
            puntos_distancia = 15
            detalle_dist = f"✅ ÓPTIMA ({distancia_soporte_pct:.1f}%)"
        elif 1 <= distancia_soporte_pct < 2:
            puntos_distancia = 12
            detalle_dist = f"Muy cerca ({distancia_soporte_pct:.1f}%)"
        elif 5 < distancia_soporte_pct <= 8:
            puntos_distancia = 8
            detalle_dist = f"Aceptable ({distancia_soporte_pct:.1f}%)"
        elif distancia_soporte_pct > 8:
            puntos_distancia = 0
            detalle_dist = f"❌ Lejos ({distancia_soporte_pct:.1f}%) - NO ES PULLBACK"
        else:
            puntos_distancia = 5
            detalle_dist = f"Pegado ({distancia_soporte_pct:.1f}%)"
    else:
        puntos_distancia = 0
        detalle_dist = "❌ Sin soporte cercano - NO ES PULLBACK"
    
    desglose['distancia_soporte'] = {
        'puntos': puntos_distancia,
        'detalle': detalle_dist
    }
    puntuacion_total += puntos_distancia
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 3: VOLUMEN (0-30 puntos) - MUY IMPORTANTE
    # Busca: Volumen ALTO en el rebote (confirmación)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    volumen = analizar_volumen(df)
    desglose['volumen'] = {
        'puntos': volumen['puntos'],
        'detalle': f"{volumen['fuerza']} ({volumen['ratio']:.1f}x promedio)"
    }
    puntuacion_total += volumen['puntos']
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 4: RSI (0-10 puntos)
    # ⭐ CRÍTICO PARA PULLBACK
    # Busca: RSI < 40 (sobreventa, zona de rebote)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    rsi = calcular_rsi(df)
    
    if rsi < 30:
        puntos_rsi = 10
        detalle_rsi = f"✅ SOBREVENTA ({rsi:.1f})"
    elif rsi < 40:
        puntos_rsi = 7
        detalle_rsi = f"Bajo ({rsi:.1f})"
    elif rsi > 70:
        puntos_rsi = -10
        detalle_rsi = f"❌ SOBRECOMPRA ({rsi:.1f}) - NO ES PULLBACK"
    elif rsi > 60:
        puntos_rsi = 0
        detalle_rsi = f"⚠️ Alto ({rsi:.1f}) - NO ES PULLBACK"
    else:
        puntos_rsi = 3
        detalle_rsi = f"Neutral ({rsi:.1f})"
    
    desglose['rsi'] = {
        'puntos': puntos_rsi,
        'detalle': detalle_rsi
    }
    puntuacion_total += puntos_rsi
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 5: POSICIÓN DEL CIERRE (0-15 puntos)
    # Busca: Cierre alto en el rango (rechazo del soporte)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    cierre = analizar_posicion_cierre_vela(df)
    desglose['cierre_vela'] = {
        'puntos': cierre['puntos'],
        'detalle': f"{cierre['fuerza']} (cierre al {cierre['posicion_pct']:.0f}% del rango)"
    }
    puntuacion_total += cierre['puntos']
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 6: ADX - TENDENCIA (0-10 puntos)
    # Busca: Tendencia clara (ADX > 25) para hacer pullback
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    adx = calcular_adx(df)
    
    if adx > 40:
        puntos_adx = 10
        detalle_adx = f"✅ Tendencia MUY FUERTE ({adx:.0f})"
    elif adx > 25:
        puntos_adx = 7
        detalle_adx = f"Tendencia clara ({adx:.0f})"
    elif adx > 20:
        puntos_adx = 3
        detalle_adx = f"Tendencia débil ({adx:.0f})"
    else:
        puntos_adx = 0
        detalle_adx = f"⚠️ Sin tendencia - RANGO ({adx:.0f})"
    
    desglose['adx'] = {
        'puntos': puntos_adx,
        'detalle': detalle_adx
    }
    puntuacion_total += puntos_adx
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 7: MACD - MOMENTUM (0-10 puntos)
    # Busca: Momentum recuperándose (histograma mejorando)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    macd = calcular_macd(df)
    
    if macd['tendencia'] == 'ALCISTA' and macd['histograma'] > 0:
        puntos_macd = 10
        detalle_macd = f"✅ Momentum ALCISTA ({macd['histograma']:.3f})"
    elif macd['tendencia'] == 'ALCISTA':
        puntos_macd = 5
        detalle_macd = f"Momentum mejorando ({macd['histograma']:.3f})"
    elif macd['tendencia'] == 'BAJISTA' and macd['histograma'] < -0.05:
        puntos_macd = -10
        detalle_macd = f"❌ Momentum BAJISTA ({macd['histograma']:.3f})"
    else:
        puntos_macd = 0
        detalle_macd = f"Neutral ({macd['histograma']:.3f})"
    
    desglose['macd'] = {
        'puntos': puntos_macd,
        'detalle': detalle_macd
    }
    puntuacion_total += puntos_macd
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 8: MEDIAS MÓVILES (0-20 puntos)
    # Busca: Precio cerca de MM20 (soporte dinámico)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    mms = analizar_medias_moviles(df)
    desglose['medias_moviles'] = {
        'puntos': mms['puntos'],
        'detalle': ' | '.join(mms['detalles']) if mms['detalles'] else 'Bajo MMs'
    }
    puntuacion_total += mms['puntos']
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 9: FUERZA DEL SOPORTE (0-10 puntos)
    # ⭐ CRÍTICO PARA PULLBACK
    # Busca: Soporte FUERTE (5+ toques históricos)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if fuerza_soporte == 'FUERTE':
        puntos_fuerza = 10
        detalle_fuerza = "✅ Soporte FUERTE (5+ toques)"
    elif fuerza_soporte == 'MEDIO':
        puntos_fuerza = 6
        detalle_fuerza = "Soporte MEDIO (3-4 toques)"
    elif fuerza_soporte == 'DÉBIL':
        puntos_fuerza = 3
        detalle_fuerza = "Soporte DÉBIL (2 toques)"
    else:
        puntos_fuerza = 0
        detalle_fuerza = "❌ Sin soporte cercano - NO ES PULLBACK"
    
    desglose['fuerza_soporte'] = {
        'puntos': puntos_fuerza,
        'detalle': detalle_fuerza
    }
    puntuacion_total += puntos_fuerza
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR PUNTUACIÓN FINAL (0-100)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Normalizar a escala 0-100 (max teórico = 115 puntos)
    puntuacion_normalizada = max(0, min(100, int((puntuacion_total / 115) * 100)))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RECOMENDACIÓN BASADA EN PUNTUACIÓN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if puntuacion_normalizada >= 75:
        nivel = "EXCELENTE"
        recomendacion = "🟢 COMPRA PRIORITARIA"
        color = "success"
    elif puntuacion_normalizada >= 60:
        nivel = "BUENO"
        recomendacion = "🟢 COMPRA"
        color = "success"
    elif puntuacion_normalizada >= 45:
        nivel = "ACEPTABLE"
        recomendacion = "🟡 COMPRA CONDICIONAL (revisar setup)"
        color = "warning"
    elif puntuacion_normalizada >= 30:
        nivel = "DUDOSO"
        recomendacion = "🟠 ESPERAR MEJOR CONFIGURACIÓN"
        color = "warning"
    else:
        nivel = "MALO"
        recomendacion = "🔴 NO OPERAR"
        color = "danger"
    
    return {
        'puntuacion': puntuacion_normalizada,
        'nivel': nivel,
        'recomendacion': recomendacion,
        'color': color,
        'desglose': desglose,
        'puntuacion_bruta': puntuacion_total,
        'estrategia': 'PULLBACK'  # Identificador de estrategia
    }
