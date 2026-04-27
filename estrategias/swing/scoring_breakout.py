# ══════════════════════════════════════════════════════════════════════
# SCORING ESPECIALIZADO PARA BREAKOUTS
# ══════════════════════════════════════════════════════════════════════
"""
Componentes de scoring específicos para estrategia BREAKOUT.

FILOSOFÍA:
- NO binario (all or nothing)
- Sistema probabilístico ponderado
- Cada criterio SUMA al score base

CRITERIOS CLAVE BREAKOUTS:
1. Volumen (peso alto) - Confirma fuerza del movimiento
2. Volatilidad (peso medio) - Indica actividad
3. Breakout limpio (peso alto) - Calidad del breakout
4. Impulso (peso medio) - Momentum presente

VERSIÓN: v82.7
"""

import numpy as np


def evaluar_volumen_breakout(volumen_actual, volumen_historico, dias_lookback=20):
    """
    Evalúa si el volumen confirma el breakout.
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if len(volumen_historico) < dias_lookback:
        return 0.0, "Histórico insuficiente"
    
    volumen_medio = np.mean(volumen_historico[-dias_lookback:])
    
    if volumen_medio == 0:
        return 0.0, "Sin volumen"
    
    ratio = volumen_actual / volumen_medio
    
    # Scoring gradual
    if ratio >= 2.0:
        return 2.5, f"Volumen excepcional ({ratio:.1f}x)"
    elif ratio >= 1.5:
        return 2.0, f"Volumen alto ({ratio:.1f}x)"
    elif ratio >= 1.2:
        return 1.0, f"Volumen moderado ({ratio:.1f}x)"
    elif ratio >= 1.0:
        return 0.5, f"Volumen normal ({ratio:.1f}x)"
    else:
        return 0.0, f"Volumen bajo ({ratio:.1f}x)"


def evaluar_volatilidad_breakout(atr_actual, atr_historico, dias_lookback=50):
    """
    Evalúa si hay volatilidad activa (necesaria para breakouts).
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if len(atr_historico) < dias_lookback:
        return 0.0, "Histórico insuficiente"
    
    atr_medio = np.mean(atr_historico[-dias_lookback:])
    
    if atr_medio == 0:
        return 0.0, "ATR cero"
    
    ratio = atr_actual / atr_medio
    
    # Volatilidad activa es buena para breakouts
    if ratio >= 1.5:
        return 2.0, f"Volatilidad muy activa ({ratio:.1f}x)"
    elif ratio >= 1.2:
        return 1.5, f"Volatilidad activa ({ratio:.1f}x)"
    elif ratio >= 1.0:
        return 1.0, f"Volatilidad normal ({ratio:.1f}x)"
    else:
        return 0.5, f"Volatilidad baja ({ratio:.1f}x)"


def evaluar_calidad_breakout(precio_actual, nivel_resistencia, rango_precio):
    """
    Evalúa la calidad/limpieza del breakout.
    
    Breakout limpio: Precio claramente por encima de resistencia
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if rango_precio == 0:
        return 0.0, "Precio sin rango"
    
    distancia_pct = ((precio_actual - nivel_resistencia) / nivel_resistencia) * 100
    
    # Breakout debe estar ENCIMA de resistencia
    if distancia_pct >= 3.0:
        return 2.5, f"Breakout muy limpio (+{distancia_pct:.1f}%)"
    elif distancia_pct >= 2.0:
        return 2.0, f"Breakout limpio (+{distancia_pct:.1f}%)"
    elif distancia_pct >= 1.0:
        return 1.5, f"Breakout moderado (+{distancia_pct:.1f}%)"
    elif distancia_pct >= 0.5:
        return 0.5, f"Breakout débil (+{distancia_pct:.1f}%)"
    else:
        return 0.0, f"No hay breakout real ({distancia_pct:.1f}%)"


def evaluar_impulso_breakout(rsi, roc=None):
    """
    Evalúa el impulso/momentum del breakout.
    
    RSI > 60 indica fuerza (pero < 80 para no sobrecompra extrema)
    
    Returns:
        tuple: (puntos, descripcion)
    """
    puntos = 0.0
    descripciones = []
    
    # RSI
    if 65 <= rsi <= 75:
        puntos += 2.0
        descripciones.append(f"RSI ideal ({rsi:.0f})")
    elif 60 <= rsi < 65:
        puntos += 1.5
        descripciones.append(f"RSI fuerte ({rsi:.0f})")
    elif 55 <= rsi < 60:
        puntos += 1.0
        descripciones.append(f"RSI moderado ({rsi:.0f})")
    elif rsi >= 80:
        puntos += 0.5
        descripciones.append(f"RSI sobrecomprado ({rsi:.0f})")
    else:
        puntos += 0.0
        descripciones.append(f"RSI débil ({rsi:.0f})")
    
    return puntos, ", ".join(descripciones)


def calcular_score_breakout_especializado(datos):
    """
    Calcula el score ESPECIALIZADO para breakouts.
    
    Args:
        datos: dict con {
            'precio_actual': float,
            'volumen_actual': float,
            'volumen_historico': array,
            'atr_actual': float,
            'atr_historico': array,
            'nivel_resistencia': float,
            'rango_precio': float,
            'rsi': float,
        }
    
    Returns:
        dict: {
            'score_total': float (0-14),
            'componentes': dict,
            'descripcion': str
        }
    """
    score_base = 0.0
    componentes = {}
    
    # 1. VOLUMEN (peso alto: 2.5 puntos max)
    pts_vol, desc_vol = evaluar_volumen_breakout(
        datos.get('volumen_actual', 0),
        datos.get('volumen_historico', [])
    )
    score_base += pts_vol
    componentes['volumen'] = {'puntos': pts_vol, 'descripcion': desc_vol}
    
    # 2. VOLATILIDAD (peso medio: 2.0 puntos max)
    pts_atr, desc_atr = evaluar_volatilidad_breakout(
        datos.get('atr_actual', 0),
        datos.get('atr_historico', [])
    )
    score_base += pts_atr
    componentes['volatilidad'] = {'puntos': pts_atr, 'descripcion': desc_atr}
    
    # 3. CALIDAD BREAKOUT (peso alto: 2.5 puntos max)
    pts_break, desc_break = evaluar_calidad_breakout(
        datos.get('precio_actual', 0),
        datos.get('nivel_resistencia', 0),
        datos.get('rango_precio', 1)
    )
    score_base += pts_break
    componentes['breakout'] = {'puntos': pts_break, 'descripcion': desc_break}
    
    # 4. IMPULSO (peso medio: 2.0 puntos max)
    pts_impulso, desc_impulso = evaluar_impulso_breakout(
        datos.get('rsi', 50)
    )
    score_base += pts_impulso
    componentes['impulso'] = {'puntos': pts_impulso, 'descripcion': desc_impulso}
    
    # Score total: 0 a 9.0 (componentes específicos)
    # Se suma al score base general (5.0) → Total final: 5.0 a 14.0
    
    return {
        'score_especializado': score_base,
        'componentes': componentes,
        'max_posible': 9.0,
        'descripcion': f"Breakout score: {score_base:.1f}/9.0"
    }


# ══════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Setup de ejemplo
    datos_ejemplo = {
        'precio_actual': 10.5,
        'volumen_actual': 1500000,
        'volumen_historico': [500000] * 20,  # Volumen 3x la media
        'atr_actual': 0.45,
        'atr_historico': [0.30] * 50,  # ATR 1.5x la media
        'nivel_resistencia': 10.0,
        'rango_precio': 2.0,
        'rsi': 68,
    }
    
    resultado = calcular_score_breakout_especializado(datos_ejemplo)
    
    print("="*70)
    print("EVALUACIÓN BREAKOUT ESPECIALIZADA")
    print("="*70)
    print(f"\n{resultado['descripcion']}")
    print(f"\nComponentes:")
    for nombre, comp in resultado['componentes'].items():
        print(f"  • {nombre.capitalize():12} +{comp['puntos']:.1f} - {comp['descripcion']}")
    print(f"\nScore especializado: {resultado['score_especializado']:.1f}/{resultado['max_posible']}")
    print("="*70)
