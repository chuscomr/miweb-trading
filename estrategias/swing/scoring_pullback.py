# ══════════════════════════════════════════════════════════════════════
# SCORING ESPECIALIZADO PARA PULLBACKS
# ══════════════════════════════════════════════════════════════════════
"""
Componentes de scoring específicos para estrategia PULLBACK.

FILOSOFÍA:
- NO binario (all or nothing)
- Sistema probabilístico ponderado
- Cada criterio SUMA al score base

CRITERIOS CLAVE PULLBACKS:
1. Soporte fuerte (peso alto) - Nivel respetado históricamente
2. Tendencia clara (peso alto) - Contexto alcista definido
3. Volumen decreciente (peso medio) - Pullback ordenado
4. No sobrevendido (peso bajo) - Evitar caídas en pánico

VERSIÓN: v82.7
"""



def evaluar_soporte_pullback(precio_actual, nivel_soporte, rebotes_historicos):
    """
    Evalúa la calidad del soporte.
    
    Soporte fuerte: Respetado múltiples veces en el pasado
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if nivel_soporte == 0:
        return 0.0, "Sin nivel de soporte"

    distancia_pct = abs((precio_actual - nivel_soporte) / nivel_soporte) * 100

    # Número de veces que rebotó en este nivel
    n_rebotes = rebotes_historicos

    puntos = 0.0

    # Proximidad al soporte
    if distancia_pct <= 1.0:
        puntos += 2.0
        desc_dist = f"En soporte ({distancia_pct:.1f}%)"
    elif distancia_pct <= 2.0:
        puntos += 1.5
        desc_dist = f"Cerca soporte ({distancia_pct:.1f}%)"
    elif distancia_pct <= 3.0:
        puntos += 1.0
        desc_dist = f"Próximo soporte ({distancia_pct:.1f}%)"
    else:
        puntos += 0.0
        desc_dist = f"Lejos soporte ({distancia_pct:.1f}%)"

    # Fuerza histórica del soporte
    if n_rebotes >= 3:
        puntos += 1.5
        desc_fuerza = f"{n_rebotes} rebotes previos"
    elif n_rebotes >= 2:
        puntos += 1.0
        desc_fuerza = f"{n_rebotes} rebotes previos"
    elif n_rebotes >= 1:
        puntos += 0.5
        desc_fuerza = f"{n_rebotes} rebote previo"
    else:
        desc_fuerza = "Sin historial"

    return puntos, f"{desc_dist}, {desc_fuerza}"


def evaluar_tendencia_pullback(mm20, mm50, mm200, pendiente_mm50):
    """
    Evalúa la claridad de la tendencia alcista.
    
    Pullbacks funcionan SOLO en tendencia alcista clara
    
    Returns:
        tuple: (puntos, descripcion)
    """
    puntos = 0.0
    descripciones = []

    # Alineación de medias
    if mm20 > mm50 > mm200:
        puntos += 2.5
        descripciones.append("MMs alineadas")
    elif mm20 > mm50:
        puntos += 1.5
        descripciones.append("MM20 > MM50")
    else:
        puntos += 0.0
        descripciones.append("MMs no alineadas")

    # Pendiente de MM50 (indica fuerza de tendencia)
    if pendiente_mm50 > 2.0:
        puntos += 1.0
        descripciones.append("Tendencia fuerte")
    elif pendiente_mm50 > 0.5:
        puntos += 0.5
        descripciones.append("Tendencia moderada")
    else:
        descripciones.append("Tendencia débil")

    return puntos, ", ".join(descripciones)


def evaluar_volumen_pullback(volumen_pullback, volumen_tendencia):
    """
    Evalúa si el volumen es decreciente durante el pullback.
    
    Pullback sano: Volumen BAJO durante corrección
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if volumen_tendencia == 0:
        return 0.0, "Sin referencia de volumen"

    ratio = volumen_pullback / volumen_tendencia

    # Volumen BAJO es bueno en pullbacks
    if ratio <= 0.5:
        return 2.0, f"Volumen muy bajo ({ratio:.1f}x) - Pullback ordenado"
    if ratio <= 0.7:
        return 1.5, f"Volumen bajo ({ratio:.1f}x) - Corrección sana"
    if ratio <= 0.9:
        return 1.0, f"Volumen moderado ({ratio:.1f}x)"
    return 0.0, f"Volumen alto ({ratio:.1f}x) - Posible distribución"


def evaluar_nivel_rsi_pullback(rsi):
    """
    Evalúa si RSI indica pullback (no pánico).
    
    RSI ideal: 35-50 (corrección sana, no sobreventa extrema)
    
    Returns:
        tuple: (puntos, descripcion)
    """
    if 40 <= rsi <= 50:
        return 1.5, f"RSI ideal para pullback ({rsi:.0f})"
    if 35 <= rsi < 40:
        return 1.0, f"RSI en zona de pullback ({rsi:.0f})"
    if 30 <= rsi < 35:
        return 0.5, f"RSI sobrevendido leve ({rsi:.0f})"
    if rsi < 30:
        return 0.0, f"RSI en pánico ({rsi:.0f}) - Evitar"
    # RSI > 50
    return 0.0, f"RSI alto ({rsi:.0f}) - No es pullback"


def calcular_score_pullback_especializado(datos):
    """
    Calcula el score ESPECIALIZADO para pullbacks.
    
    Args:
        datos: dict con {
            'precio_actual': float,
            'nivel_soporte': float,
            'rebotes_historicos': int,
            'mm20': float,
            'mm50': float,
            'mm200': float,
            'pendiente_mm50': float,
            'volumen_pullback': float,
            'volumen_tendencia': float,
            'rsi': float,
        }
    
    Returns:
        dict: {
            'score_total': float (0-11.5),
            'componentes': dict,
            'descripcion': str
        }
    """
    score_base = 0.0
    componentes = {}

    # 1. SOPORTE FUERTE (peso alto: 3.5 puntos max)
    pts_sop, desc_sop = evaluar_soporte_pullback(
        datos.get('precio_actual', 0),
        datos.get('nivel_soporte', 0),
        datos.get('rebotes_historicos', 0)
    )
    score_base += pts_sop
    componentes['soporte'] = {'puntos': pts_sop, 'descripcion': desc_sop}

    # 2. TENDENCIA CLARA (peso alto: 3.5 puntos max)
    pts_tend, desc_tend = evaluar_tendencia_pullback(
        datos.get('mm20', 0),
        datos.get('mm50', 0),
        datos.get('mm200', 0),
        datos.get('pendiente_mm50', 0)
    )
    score_base += pts_tend
    componentes['tendencia'] = {'puntos': pts_tend, 'descripcion': desc_tend}

    # 3. VOLUMEN DECRECIENTE (peso medio: 2.0 puntos max)
    pts_vol, desc_vol = evaluar_volumen_pullback(
        datos.get('volumen_pullback', 0),
        datos.get('volumen_tendencia', 1)
    )
    score_base += pts_vol
    componentes['volumen'] = {'puntos': pts_vol, 'descripcion': desc_vol}

    # 4. RSI ADECUADO (peso bajo: 1.5 puntos max)
    pts_rsi, desc_rsi = evaluar_nivel_rsi_pullback(
        datos.get('rsi', 50)
    )
    score_base += pts_rsi
    componentes['rsi'] = {'puntos': pts_rsi, 'descripcion': desc_rsi}

    # Score total: 0 a 10.5 (componentes específicos)
    # Se suma al score base general (5.0) → Total final: 5.0 a 15.5

    return {
        'score_especializado': score_base,
        'componentes': componentes,
        'max_posible': 10.5,
        'descripcion': f"Pullback score: {score_base:.1f}/10.5"
    }


# ══════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Setup de ejemplo
    datos_ejemplo = {
        'precio_actual': 9.95,
        'nivel_soporte': 10.0,
        'rebotes_historicos': 3,
        'mm20': 11.0,
        'mm50': 10.5,
        'mm200': 9.5,
        'pendiente_mm50': 2.5,
        'volumen_pullback': 300000,
        'volumen_tendencia': 600000,  # Volumen 0.5x durante pullback
        'rsi': 42,
    }

    resultado = calcular_score_pullback_especializado(datos_ejemplo)

    print("="*70)
    print("EVALUACIÓN PULLBACK ESPECIALIZADA")
    print("="*70)
    print(f"\n{resultado['descripcion']}")
    print("\nComponentes:")
    for nombre, comp in resultado['componentes'].items():
        print(f"  • {nombre.capitalize():12} +{comp['puntos']:.1f} - {comp['descripcion']}")
    print(f"\nScore especializado: {resultado['score_especializado']:.1f}/{resultado['max_posible']}")
    print("="*70)
