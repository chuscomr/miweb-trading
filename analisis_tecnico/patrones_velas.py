# ==========================================================
# MÓDULO PATRONES DE VELAS JAPONESAS
# 3 patrones básicos y efectivos
# ==========================================================

import pandas as pd
import numpy as np

def detectar_patrones_velas(df, ultimas_n=2):
    """
    Detecta patrones de velas en las últimas N velas.
    
    Args:
        df: DataFrame con columnas ['Open', 'High', 'Low', 'Close']
        ultimas_n: número de velas a analizar (default: 2)
    
    Returns:
        dict con patrones detectados y señal
    """
    
    if len(df) < ultimas_n:
        return {
            "patron": "INSUFICIENTE",
            "descripcion": "No hay suficientes velas para análisis",
            "señal": "NEUTRAL",
            "confianza": 0
        }
    
    # Extraer últimas N velas
    velas = df.tail(ultimas_n).copy()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PATRONES DE 1 VELA (última vela)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    ultima_vela = velas.iloc[-1]
    
    # MARTILLO ALCISTA
    martillo = detectar_martillo(ultima_vela)
    if martillo:
        return martillo
    
    # SHOOTING STAR BAJISTA
    shooting = detectar_shooting_star(ultima_vela)
    if shooting:
        return shooting
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PATRONES DE 2 VELAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if len(velas) >= 2:
        # ENVOLVENTE ALCISTA
        envolvente = detectar_envolvente_alcista(velas.iloc[-2], velas.iloc[-1])
        if envolvente:
            return envolvente
        
        # ENVOLVENTE BAJISTA
        envolvente_bajista = detectar_envolvente_bajista(velas.iloc[-2], velas.iloc[-1])
        if envolvente_bajista:
            return envolvente_bajista
    
    # Sin patrón relevante
    return {
        "patron": "NINGUNO",
        "descripcion": "Sin patrones relevantes detectados",
        "señal": "NEUTRAL",
        "confianza": 0
    }


def detectar_martillo(vela):
    """
    MARTILLO ALCISTA:
    - Cuerpo pequeño en parte superior
    - Sombra inferior 2-3x el cuerpo
    - Poca/sin sombra superior
    - Indica rechazo de mínimos → REVERSIÓN ALCISTA
    """
    
    open_price = vela['Open']
    high = vela['High']
    low = vela['Low']
    close = vela['Close']
    
    # Calcular componentes
    cuerpo = abs(close - open_price)
    sombra_inferior = min(open_price, close) - low
    sombra_superior = high - max(open_price, close)
    rango_total = high - low
    
    # Evitar división por cero
    if rango_total == 0 or cuerpo == 0:
        return None
    
    # CONDICIONES MARTILLO:
    # 1. Sombra inferior al menos 2x el cuerpo
    # 2. Sombra superior pequeña (< 30% del cuerpo)
    # 3. Cuerpo en tercio superior del rango
    # 4. Vela puede ser alcista o bajista (color no importa)
    
    condicion1 = sombra_inferior >= 2 * cuerpo
    condicion2 = sombra_superior < 0.3 * cuerpo
    condicion3 = (min(open_price, close) - low) / rango_total > 0.6  # Cuerpo arriba
    
    if condicion1 and condicion2 and condicion3:
        return {
            "patron": "MARTILLO_ALCISTA",
            "descripcion": "🔨 Martillo alcista - Rechazo fuerte de mínimos",
            "señal": "ALCISTA",
            "confianza": 75,
            "detalles": f"Sombra inferior {sombra_inferior/cuerpo:.1f}x el cuerpo"
        }
    
    return None


def detectar_shooting_star(vela):
    """
    SHOOTING STAR (ESTRELLA FUGAZ) BAJISTA:
    - Cuerpo pequeño en parte inferior
    - Sombra superior 2-3x el cuerpo
    - Poca/sin sombra inferior
    - Indica rechazo de máximos → REVERSIÓN BAJISTA
    """
    
    open_price = vela['Open']
    high = vela['High']
    low = vela['Low']
    close = vela['Close']
    
    # Calcular componentes
    cuerpo = abs(close - open_price)
    sombra_superior = high - max(open_price, close)
    sombra_inferior = min(open_price, close) - low
    rango_total = high - low
    
    if rango_total == 0 or cuerpo == 0:
        return None
    
    # CONDICIONES SHOOTING STAR:
    # 1. Sombra superior al menos 2x el cuerpo
    # 2. Sombra inferior pequeña (< 30% del cuerpo)
    # 3. Cuerpo en tercio inferior del rango
    
    condicion1 = sombra_superior >= 2 * cuerpo
    condicion2 = sombra_inferior < 0.3 * cuerpo
    condicion3 = (high - max(open_price, close)) / rango_total > 0.6  # Cuerpo abajo
    
    if condicion1 and condicion2 and condicion3:
        return {
            "patron": "SHOOTING_STAR",
            "descripcion": "⭐ Shooting Star - Rechazo fuerte de máximos",
            "señal": "BAJISTA",
            "confianza": 75,
            "detalles": f"Sombra superior {sombra_superior/cuerpo:.1f}x el cuerpo"
        }
    
    return None


def detectar_envolvente_alcista(vela1, vela2):
    """
    ENVOLVENTE ALCISTA (Bullish Engulfing):
    - Vela 1: Bajista (roja)
    - Vela 2: Alcista (verde) que ENVUELVE completamente a la vela 1
    - Cierre vela 2 > Apertura vela 1
    - Indica CAMBIO DE CONTROL a compradores
    """
    
    # Vela 1 (anterior)
    open1 = vela1['Open']
    close1 = vela1['Close']
    
    # Vela 2 (actual)
    open2 = vela2['Open']
    close2 = vela2['Close']
    
    # CONDICIONES:
    # 1. Vela 1 bajista (close < open)
    # 2. Vela 2 alcista (close > open)
    # 3. Open2 < Close1 (abre por debajo del cierre anterior)
    # 4. Close2 > Open1 (cierra por encima de apertura anterior) → ENVUELVE
    
    vela1_bajista = close1 < open1
    vela2_alcista = close2 > open2
    envuelve = open2 < close1 and close2 > open1
    
    if vela1_bajista and vela2_alcista and envuelve:
        tamaño_envolvente = abs(close2 - open2) / abs(close1 - open1)
        
        return {
            "patron": "ENVOLVENTE_ALCISTA",
            "descripcion": "📈 Envolvente alcista - Toma de control compradores",
            "señal": "ALCISTA",
            "confianza": 80,
            "detalles": f"Vela alcista {tamaño_envolvente:.1f}x más grande"
        }
    
    return None


def detectar_envolvente_bajista(vela1, vela2):
    """
    ENVOLVENTE BAJISTA (Bearish Engulfing):
    - Vela 1: Alcista (verde)
    - Vela 2: Bajista (roja) que ENVUELVE completamente a la vela 1
    - Indica CAMBIO DE CONTROL a vendedores
    """
    
    open1 = vela1['Open']
    close1 = vela1['Close']
    
    open2 = vela2['Open']
    close2 = vela2['Close']
    
    # CONDICIONES:
    # 1. Vela 1 alcista (close > open)
    # 2. Vela 2 bajista (close < open)
    # 3. Open2 > Close1 (abre por encima del cierre anterior)
    # 4. Close2 < Open1 (cierra por debajo de apertura anterior) → ENVUELVE
    
    vela1_alcista = close1 > open1
    vela2_bajista = close2 < open2
    envuelve = open2 > close1 and close2 < open1
    
    if vela1_alcista and vela2_bajista and envuelve:
        tamaño_envolvente = abs(close2 - open2) / abs(close1 - open1)
        
        return {
            "patron": "ENVOLVENTE_BAJISTA",
            "descripcion": "📉 Envolvente bajista - Toma de control vendedores",
            "señal": "BAJISTA",
            "confianza": 80,
            "detalles": f"Vela bajista {tamaño_envolvente:.1f}x más grande"
        }
    
    return None


def analizar_confluencia_velas_sr(patron, distancia_soporte_pct):
    """
    Analiza confluencia entre patrón de velas y distancia a soporte.
    Combina dos señales para mayor confianza.
    
    Args:
        patron: dict resultado de detectar_patrones_velas()
        distancia_soporte_pct: distancia al soporte más cercano en %
    
    Returns:
        dict con análisis de confluencia
    """
    
    if patron['señal'] == "NEUTRAL":
        return {
            "confluencia": False,
            "mensaje": "Sin patrón de velas relevante"
        }
    
    # CONFLUENCIA ALCISTA: Patrón alcista + cerca de soporte
    if patron['señal'] == "ALCISTA":
        if distancia_soporte_pct is not None and 2 <= distancia_soporte_pct <= 5:
            return {
                "confluencia": True,
                "confianza_combinada": min(95, patron['confianza'] + 15),
                "mensaje": f"✅ CONFLUENCIA FUERTE: {patron['patron']} + Cerca soporte ({distancia_soporte_pct:.1f}%)",
                "recomendacion": "COMPRA PRIORITARIA"
            }
        else:
            return {
                "confluencia": False,
                "confianza_combinada": patron['confianza'],
                "mensaje": f"⚠️ Patrón alcista pero lejos de soporte",
                "recomendacion": "ESPERAR MEJOR PRECIO"
            }
    
    # SEÑAL BAJISTA: NO COMPRAR
    if patron['señal'] == "BAJISTA":
        return {
            "confluencia": False,
            "confianza_combinada": 0,
            "mensaje": f"🚫 EVITAR COMPRA: {patron['patron']} detectado",
            "recomendacion": "NO OPERAR"
        }
    
    return {
        "confluencia": False,
        "mensaje": "Sin confluencia clara"
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EJEMPLO DE USO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import yfinance as yf
    
    # Descargar datos
    ticker = "TEF.MC"
    df = yf.download(ticker, period="3mo", interval="1d")
    
    # Detectar patrón
    resultado = detectar_patrones_velas(df, ultimas_n=2)
    
    print(f"\n🕯️ ANÁLISIS VELAS: {ticker}")
    print(f"Patrón: {resultado['patron']}")
    print(f"Descripción: {resultado['descripcion']}")
    print(f"Señal: {resultado['señal']}")
    print(f"Confianza: {resultado['confianza']}%")
    
    if 'detalles' in resultado:
        print(f"Detalles: {resultado['detalles']}")
