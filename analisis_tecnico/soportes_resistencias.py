# ==========================================================
# MÓDULO SOPORTES Y RESISTENCIAS
# Detección automática de zonas clave de precio
# ==========================================================

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

def detectar_soportes_resistencias(df, periodo=20, tolerancia_pct=2.0, min_toques=2):
    """
    Detecta soportes y resistencias en base a máximos/mínimos locales.
    
    Args:
        df: DataFrame con columnas ['High', 'Low', 'Close']
        periodo: ventana para detectar extremos (default: 20 períodos)
        tolerancia_pct: agrupar niveles dentro de X% (default: 2%)
        min_toques: mínimo de toques para validar nivel (default: 2)
    
    Returns:
        dict con soportes, resistencias y análisis del precio actual
    """
    
    if len(df) < periodo * 2:
        return {
            "soportes": [],
            "resistencias": [],
            "precio_actual": float(df['Close'].iloc[-1]),
            "analisis": "Histórico insuficiente para análisis S/R"
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 1: Detectar máximos y mínimos locales
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    
    # Índices de máximos/mínimos locales
    maximos_idx = argrelextrema(highs, np.greater, order=periodo)[0]
    minimos_idx = argrelextrema(lows, np.less, order=periodo)[0]
    
    # Niveles de precio
    niveles_resistencia = highs[maximos_idx]
    niveles_soporte = lows[minimos_idx]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 2: Agrupar niveles cercanos
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    resistencias = agrupar_niveles(niveles_resistencia, tolerancia_pct, min_toques)
    soportes = agrupar_niveles(niveles_soporte, tolerancia_pct, min_toques)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 3: FILTRAR POR POSICIÓN vs PRECIO ACTUAL (CRÍTICO)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    precio_actual = float(closes[-1])
    
    # Resistencias = Solo niveles POR ENCIMA del precio actual
    resistencias = [r for r in resistencias if r['nivel'] > precio_actual]
    
    # Soportes = Solo niveles POR DEBAJO del precio actual
    soportes = [s for s in soportes if s['nivel'] < precio_actual]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 4: Ordenar por relevancia (más toques = más fuerte)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    resistencias = sorted(resistencias, key=lambda x: x['toques'], reverse=True)
    soportes = sorted(soportes, key=lambda x: x['toques'], reverse=True)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 5: Analizar precio actual vs S/R
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis = analizar_posicion_precio(precio_actual, soportes, resistencias)
    
    return {
        "soportes": soportes[:10],  # Top 10 soportes más fuertes
        "resistencias": resistencias[:10],  # Top 10 resistencias más fuertes
        "precio_actual": precio_actual,
        "analisis": analisis
    }


def agrupar_niveles(niveles, tolerancia_pct, min_toques):
    """
    Agrupa niveles de precio cercanos en zonas.
    Ejemplo: 3.95, 3.97, 3.99 → 3.97 (3 toques)
    """
    
    if len(niveles) == 0:
        return []
    
    niveles_sorted = np.sort(niveles)
    grupos = []
    
    i = 0
    while i < len(niveles_sorted):
        nivel_actual = niveles_sorted[i]
        grupo = [nivel_actual]
        
        # Agrupar niveles dentro de tolerancia_pct
        j = i + 1
        while j < len(niveles_sorted):
            diferencia_pct = abs((niveles_sorted[j] - nivel_actual) / nivel_actual) * 100
            
            if diferencia_pct <= tolerancia_pct:
                grupo.append(niveles_sorted[j])
                j += 1
            else:
                break
        
        # Solo guardar si tiene suficientes toques
        if len(grupo) >= min_toques:
            grupos.append({
                "nivel": round(np.mean(grupo), 2),  # Promedio del grupo
                "toques": len(grupo),
                "fuerza": calcular_fuerza(len(grupo))
            })
        
        i = j if j > i + 1 else i + 1
    
    return grupos


def calcular_fuerza(toques):
    """
    Calcula fuerza del nivel según número de toques.
    2 toques = débil, 3-4 = medio, 5+ = fuerte
    """
    if toques >= 5:
        return "FUERTE"
    elif toques >= 3:
        return "MEDIO"
    else:
        return "DÉBIL"


def analizar_posicion_precio(precio_actual, soportes, resistencias):
    """
    Analiza posición del precio actual respecto a S/R más cercanos.
    """
    
    # Soporte más cercano por debajo
    soportes_debajo = [s for s in soportes if s['nivel'] < precio_actual]
    soporte_cercano = soportes_debajo[0] if soportes_debajo else None
    
    # Resistencia más cercana por encima
    resistencias_encima = [r for r in resistencias if r['nivel'] > precio_actual]
    resistencia_cercana = resistencias_encima[0] if resistencias_encima else None
    
    analisis = []
    
    # Distancia a soporte
    if soporte_cercano:
        dist_soporte = ((precio_actual - soporte_cercano['nivel']) / precio_actual) * 100
        analisis.append(f"Soporte en {soporte_cercano['nivel']}€ ({soporte_cercano['fuerza']}) a {dist_soporte:.1f}% abajo")
        
        if dist_soporte < 3:
            analisis.append("✅ Precio CERCA del soporte - Zona de compra potencial")
        elif dist_soporte > 8:
            analisis.append("⚠️ Precio LEJOS del soporte - Esperar pullback mayor")
    
    # Distancia a resistencia
    if resistencia_cercana:
        dist_resistencia = ((resistencia_cercana['nivel'] - precio_actual) / precio_actual) * 100
        analisis.append(f"Resistencia en {resistencia_cercana['nivel']}€ ({resistencia_cercana['fuerza']}) a {dist_resistencia:.1f}% arriba")
        
        if dist_resistencia < 2:
            analisis.append("🚫 Precio PEGADO a resistencia - Evitar compra (probable rechazo)")
    
    # Zona de valor
    if soporte_cercano and resistencia_cercana:
        rango = resistencia_cercana['nivel'] - soporte_cercano['nivel']
        posicion_en_rango = (precio_actual - soporte_cercano['nivel']) / rango * 100
        
        if posicion_en_rango < 30:
            analisis.append("📊 Precio en zona BAJA del rango (30% inferior) - Favorable compra")
        elif posicion_en_rango > 70:
            analisis.append("📊 Precio en zona ALTA del rango (30% superior) - Desfavorable compra")
    
    return " | ".join(analisis) if analisis else "Sin análisis S/R disponible"


def obtener_sr_mas_cercanos(precio_actual, soportes, resistencias):
    """
    Devuelve el soporte y resistencia más cercanos al precio actual.
    Útil para integración con sistema de trading.
    """
    
    # Soporte más cercano por debajo
    soportes_debajo = [s for s in soportes if s['nivel'] < precio_actual]
    soporte_cercano = soportes_debajo[0] if soportes_debajo else None
    
    # Resistencia más cercana por encima
    resistencias_encima = [r for r in resistencias if r['nivel'] > precio_actual]
    resistencia_cercana = resistencias_encima[0] if resistencias_encima else None
    
    return {
        "soporte": soporte_cercano,
        "resistencia": resistencia_cercana,
        "distancia_soporte_pct": ((precio_actual - soporte_cercano['nivel']) / precio_actual * 100) if soporte_cercano else None,
        "distancia_resistencia_pct": ((resistencia_cercana['nivel'] - precio_actual) / precio_actual * 100) if resistencia_cercana else None
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EJEMPLO DE USO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import yfinance as yf
    
    # Descargar datos de ejemplo
    ticker = "TEF.MC"
    df = yf.download(ticker, period="1y", interval="1d")
    
    # Detectar S/R
    resultado = detectar_soportes_resistencias(df)
    
    print(f"\n📊 ANÁLISIS S/R: {ticker}")
    print(f"Precio actual: {resultado['precio_actual']:.2f}€\n")
    
    print("🟢 SOPORTES:")
    for s in resultado['soportes']:
        print(f"  {s['nivel']:.2f}€ - {s['toques']} toques ({s['fuerza']})")
    
    print("\n🔴 RESISTENCIAS:")
    for r in resultado['resistencias']:
        print(f"  {r['nivel']:.2f}€ - {r['toques']} toques ({r['fuerza']})")
    
    print(f"\n💡 ANÁLISIS:")
    print(f"  {resultado['analisis']}")
