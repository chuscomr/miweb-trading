"""
═══════════════════════════════════════════════════════════════
ADAPTADOR DE ESCÁNERES — Normalización de salidas
═══════════════════════════════════════════════════════════════

Convierte la salida de los 3 escáneres (swing/medio/posicional) 
al formato unificado con scoring 0-100.

Este módulo es temporal hasta que se refactoricen los escáneres
para usar scoring_unificado.py directamente.
"""

from core.scoring_unificado import clasificar_score, mensaje_contexto


def adaptar_resultado_swing(resultado_original, contexto_ibex="LATERAL"):
    """
    Adapta resultado del scanner swing al formato unificado.
    
    Args:
        resultado_original: dict con formato actual de swing
        contexto_ibex: "ALCISTA" | "LATERAL" | "BAJISTA"
    
    Returns:
        dict con formato unificado
    """
    # El scanner swing ya tiene un score 0-10
    # Lo normalizamos a 0-100
    score_original = resultado_original.get("score", 5.0)
    score_100 = min(100, score_original * 10)  # 5.0 → 50, 10.0 → 100
    
    return {
        "ticker": resultado_original.get("ticker_completo", ""),
        "nombre": resultado_original.get("ticker", "").replace(".MC", ""),
        "score": round(score_100, 0),
        "clasificacion": clasificar_score(score_100),
        "setup": resultado_original.get("tipo", "pullback"),
        "sistema": "swing",
        "contexto": contexto_ibex,
        # Campos adicionales específicos
        "precio": resultado_original.get("precio", 0),
        "rsi": resultado_original.get("rsi", 0),
        "entrada": resultado_original.get("entrada", 0),
        "stop": resultado_original.get("stop", 0),
        "detalles": resultado_original.get("setup_tecnico", ""),
    }


def adaptar_resultado_medio(resultado_original, contexto_ibex="LATERAL"):
    """
    Adapta resultado del scanner medio al formato unificado.
    
    Args:
        resultado_original: dict con formato actual de medio
        contexto_ibex: "ALCISTA" | "LATERAL" | "BAJISTA"
    
    Returns:
        dict con formato unificado
    """
    # El scanner medio usa categorías "Excelente" / "Sólido" / "Básico"
    # Las mapeamos a scores
    categoria = resultado_original.get("calidad", "Básico")
    
    if categoria == "Excelente":
        score_100 = 85
    elif categoria == "Sólido":
        score_100 = 72
    else:  # Básico
        score_100 = 55
    
    return {
        "ticker": resultado_original.get("ticker", ""),
        "nombre": resultado_original.get("ticker", "").replace(".MC", ""),
        "score": score_100,
        "clasificacion": clasificar_score(score_100),
        "setup": "pullback",  # Medio siempre es pullback
        "sistema": "medio",
        "contexto": contexto_ibex,
        # Campos adicionales
        "precio": resultado_original.get("precio", 0),
        "pullback_pct": resultado_original.get("pullback_pct", 0),
        "rsi": resultado_original.get("rsi", 0),
        "entrada": resultado_original.get("entrada", 0),
        "stop": resultado_original.get("stop", 0),
    }


def adaptar_resultado_posicional(resultado_original, contexto_ibex="LATERAL"):
    """
    Adapta resultado del scanner posicional al formato unificado.
    
    El posicional YA tiene score 0-100 y clasificación.
    Solo necesitamos normalizar el formato.
    
    Args:
        resultado_original: dict con formato actual de posicional
        contexto_ibex: "ALCISTA" | "LATERAL" | "BAJISTA"
    
    Returns:
        dict con formato unificado
    """
    return {
        "ticker": resultado_original.get("ticker", ""),
        "nombre": resultado_original.get("nombre", ""),
        "score": resultado_original.get("score", 0),
        "clasificacion": resultado_original.get("clasificacion", "Mediocre"),
        "setup": "breakout",  # Posicional siempre es breakout
        "sistema": "posicional",
        "contexto": contexto_ibex,
        # Campos adicionales
        "precio": resultado_original.get("precio", 0),
        "entrada": resultado_original.get("entrada", 0),
        "stop": resultado_original.get("stop", 0),
        "riesgo_pct": resultado_original.get("riesgo_pct", 0),
        "fuerza_relativa": resultado_original.get("fuerza_relativa", ""),
        "es_watchlist": resultado_original.get("es_watchlist", False),
    }


def agrupar_por_clasificacion(resultados):
    """
    Agrupa resultados normalizados por clasificación.
    
    Args:
        resultados: lista de dict con formato unificado
    
    Returns:
        dict con {
            "excelente": [],
            "bueno": [],
            "mediocre": [],
            "total_analizados": int,
            "total_señales": int,
        }
    """
    excelente = []
    bueno = []
    mediocre = []
    
    for r in resultados:
        clasificacion = r.get("clasificacion", "Mediocre")
        
        if clasificacion == "Excelente":
            excelente.append(r)
        elif clasificacion == "Bueno":
            bueno.append(r)
        else:  # Mediocre
            mediocre.append(r)
    
    # Ordenar cada grupo por score
    excelente.sort(key=lambda x: x.get("score", 0), reverse=True)
    bueno.sort(key=lambda x: x.get("score", 0), reverse=True)
    mediocre.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return {
        "excelente": excelente,
        "bueno": bueno,
        "mediocre": mediocre,
        "total_analizados": len(resultados),
        "total_señales": len(excelente) + len(bueno) + len(mediocre),
    }


def preparar_para_template(resultados, contexto_ibex="LATERAL", sistema="swing"):
    """
    Prepara resultados normalizados para el template HTML.
    
    Args:
        resultados: lista de dict (formato original del escáner)
        contexto_ibex: "ALCISTA" | "LATERAL" | "BAJISTA"
        sistema: "swing" | "medio" | "posicional"
    
    Returns:
        dict listo para pasar al template
    """
    # Normalizar resultados según el sistema
    if sistema == "swing":
        normalizados = [adaptar_resultado_swing(r, contexto_ibex) for r in resultados]
    elif sistema == "medio":
        normalizados = [adaptar_resultado_medio(r, contexto_ibex) for r in resultados]
    else:  # posicional
        normalizados = [adaptar_resultado_posicional(r, contexto_ibex) for r in resultados]
    
    # Agrupar por clasificación
    agrupados = agrupar_por_clasificacion(normalizados)
    
    # Preparar para template
    return {
        "excelente": agrupados["excelente"],
        "bueno": agrupados["bueno"],
        "mediocre": agrupados["mediocre"],
        "total_analizados": agrupados["total_analizados"],
        "total_señales": agrupados["total_señales"],
        "contexto": contexto_ibex,
        "mensaje_contexto": mensaje_contexto(contexto_ibex),
        "sistema": sistema,
    }
