# ══════════════════════════════════════════════════════════════════════
# PERFILES DE TRADING V2 - ARQUITECTURA PROFESIONAL
# ══════════════════════════════════════════════════════════════════════
"""
CAMBIO FUNDAMENTAL:
- ANTES: score_ponderado = score * peso → if >= umbral → ACEPTA/RECHAZA
- AHORA: Separar VALIDEZ TÉCNICA de AJUSTE POR CONTEXTO

FILOSOFÍA PRO:
1. VALIDEZ TÉCNICA (absoluta):
   - score >= 6.0 → Setup VÁLIDO (siempre)
   - No penalizar por contexto aquí
   
2. CONTEXTO (modula ejecución):
   - Tamaño de posición
   - Prioridad de estrategia
   - Gestión de riesgo
   - Confirmaciones extra

RESULTADO:
- Sin zonas muertas
- Todas las señales válidas se capturan
- El contexto ajusta CÓMO operar, no SI operar

VERSIÓN: v82.13 PRO
FECHA: 2026-05-05
IMPACTO: Elimina zonas muertas del sistema
"""

# ══════════════════════════════════════════════════════════════════════
# CONFIRMACIONES ESPECÍFICAS POR ESTRATEGIA
# ══════════════════════════════════════════════════════════════════════

CONFIRMACIONES = {
    "breakout": [
        "Cierre por encima de resistencia (no solo mecha)",
        "Volumen > 1.5x media últimos 20 días",
        "Mecha superior < 40% del rango de la vela",
        "Confirmación en vela siguiente (no reversión inmediata)"
    ],
    "pullback": [
        "Rebote en soporte clave (MM20/MM50/soporte previo)",
        "Vela de rechazo (mecha inferior larga)",
        "RSI girando al alza desde sobreventa (<40)",
        "Volumen decreciente en corrección, creciente en rebote"
    ]
}


def obtener_confirmaciones_requeridas(tipo_estrategia):
    """
    Obtiene la lista de confirmaciones concretas para una estrategia.
    
    Args:
        tipo_estrategia: "breakout" o "pullback"
    
    Returns:
        list - Lista de confirmaciones específicas a verificar
    """
    return CONFIRMACIONES.get(tipo_estrategia, [])


# ══════════════════════════════════════════════════════════════════════
# UMBRALES DE VALIDEZ TÉCNICA (DINÁMICOS POR CONTEXTO)
# ══════════════════════════════════════════════════════════════════════

UMBRALES_CONTEXTO = {
    "ALCISTA": 6.5,   # Más exigente (hay muchas opciones)
    "LATERAL": 6.0,   # Estándar (equilibrio)
    "BAJISTA": 6.2,   # Ligeramente más exigente (mercado difícil)
    "TRANSICION": 6.3 # Más conservador en incertidumbre
}

SCORE_MINIMO_ABSOLUTO = 6.0  # Mínimo absoluto (fallback)

CLASIFICACION_CALIDAD = {
    "excelente": 8.0,   # score >= 8.0
    "bueno":     6.5,   # score >= 6.5
    "mediocre":  6.0,   # score >= 6.0
}


# ══════════════════════════════════════════════════════════════════════
# PERFILES DE CONTEXTO (AJUSTAN EJECUCIÓN, NO VALIDEZ)
# ══════════════════════════════════════════════════════════════════════

PERFILES_V2 = {
    "ALCISTA": {
        # Preferencias de estrategia (para ranking)
        "prioridad_breakout": 1.2,   # Breakouts favorecidos
        "prioridad_pullback": 1.0,   # Pullbacks normales
        
        # Gestión de tamaño
        "factor_tamaño_breakout": 1.0,  # Tamaño normal
        "factor_tamaño_pullback": 1.0,  # Tamaño normal
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 2.0,
        "max_posiciones_abiertas": 5,
        "max_exposicion_total_pct": 10.0,
        
        # Confirmaciones extra
        "requiere_confirmacion_breakout": False,
        "requiere_confirmacion_pullback": False,
        
        # Trailing y objetivos
        "trailing_desde_r": 2.0,
        "objetivo_parcial_r": 3.0,
        "venta_parcial_pct": 50,
        
        "descripcion": "Alcista: Favorece breakouts, tamaño completo",
        "contexto": "ALCISTA"
    },
    
    "LATERAL": {
        # Preferencias de estrategia (para ranking)
        "prioridad_breakout": 0.8,   # Breakouts menos priorizados
        "prioridad_pullback": 1.3,   # Pullbacks MÁS priorizados
        
        # Gestión de tamaño
        "factor_tamaño_breakout": 0.6,  # Breakouts con 60% tamaño
        "factor_tamaño_pullback": 1.0,  # Pullbacks tamaño completo
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 1.5,
        "max_posiciones_abiertas": 3,
        "max_exposicion_total_pct": 6.0,
        
        # Confirmaciones extra
        "requiere_confirmacion_breakout": True,   # Breakouts necesitan confirmación
        "requiere_confirmacion_pullback": False,  # Pullbacks sin confirmación extra
        
        # Trailing y objetivos
        "trailing_desde_r": 1.5,
        "objetivo_parcial_r": 2.0,
        "venta_parcial_pct": 50,
        
        "descripcion": "Lateral: Pullbacks priorizados, breakouts con menor tamaño",
        "contexto": "LATERAL"
    },
    
    "BAJISTA": {
        # Preferencias de estrategia (para ranking)
        "prioridad_breakout": 0.5,   # Breakouts muy poco priorizados
        "prioridad_pullback": 0.9,   # Pullbacks algo priorizados
        
        # Gestión de tamaño
        "factor_tamaño_breakout": 0.4,  # Breakouts con 40% tamaño (muy conservador)
        "factor_tamaño_pullback": 0.7,  # Pullbacks con 70% tamaño
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 1.0,
        "max_posiciones_abiertas": 2,
        "max_exposicion_total_pct": 3.0,
        
        # Confirmaciones extra
        "requiere_confirmacion_breakout": True,   # Breakouts necesitan confirmación
        "requiere_confirmacion_pullback": True,   # Pullbacks también
        
        # Trailing y objetivos
        "trailing_desde_r": 1.0,
        "objetivo_parcial_r": 1.5,
        "venta_parcial_pct": 75,
        
        "descripcion": "Bajista: Muy conservador, ambos con tamaño reducido",
        "contexto": "BAJISTA"
    },
    
    "TRANSICION": {
        # Preferencias de estrategia (para ranking)
        "prioridad_breakout": 0.7,   # Breakouts poco priorizados
        "prioridad_pullback": 1.1,   # Pullbacks ligeramente favorecidos
        
        # Gestión de tamaño (CONSERVADOR)
        "factor_tamaño_breakout": 0.5,  # Breakouts con 50% tamaño
        "factor_tamaño_pullback": 0.8,  # Pullbacks con 80% tamaño
        
        # Gestión de riesgo (MUY CONSERVADOR)
        "riesgo_por_trade_pct": 1.2,
        "max_posiciones_abiertas": 2,   # Máximo 2 posiciones
        "max_exposicion_total_pct": 4.0,
        
        # Confirmaciones extra
        "requiere_confirmacion_breakout": True,   # Breakouts necesitan confirmación
        "requiere_confirmacion_pullback": True,   # Pullbacks también (mercado confuso)
        
        # Trailing y objetivos
        "trailing_desde_r": 1.2,
        "objetivo_parcial_r": 1.8,
        "venta_parcial_pct": 60,
        
        "descripcion": "Transición: Muy conservador, ambos requieren confirmación",
        "contexto": "TRANSICION"
    }
}


# ══════════════════════════════════════════════════════════════════════
# FUNCIONES V2
# ══════════════════════════════════════════════════════════════════════

def setup_es_valido(score_base, contexto_mercado="LATERAL"):
    """
    Determina si un setup es técnicamente válido según contexto.
    
    MEJORA V2.1: Umbral dinámico según contexto de mercado.
    - ALCISTA: 6.5 (más exigente, hay opciones)
    - LATERAL: 6.0 (estándar)
    - BAJISTA: 6.2 (ligeramente más exigente)
    - TRANSICION: 6.3 (conservador en incertidumbre)
    
    Args:
        score_base: Score técnico del setup (5.0 - 10.0)
        contexto_mercado: "ALCISTA", "LATERAL", "BAJISTA", "TRANSICION"
    
    Returns:
        bool - True si es válido técnicamente
    """
    contexto = contexto_mercado.upper()
    umbral = UMBRALES_CONTEXTO.get(contexto, SCORE_MINIMO_ABSOLUTO)
    return score_base >= umbral


def clasificar_calidad_setup(score):
    """
    Clasifica un setup según su calidad técnica.
    
    Returns:
        str: "excelente", "bueno", "mediocre"
    """
    if score >= CLASIFICACION_CALIDAD["excelente"]:
        return "excelente"
    elif score >= CLASIFICACION_CALIDAD["bueno"]:
        return "bueno"
    elif score >= CLASIFICACION_CALIDAD["mediocre"]:
        return "mediocre"
    else:
        return "invalido"


def calcular_score_ranking(score_base, tipo_estrategia, contexto_mercado):
    """
    Calcula el score para RANKING (ordenación).
    
    CAMBIO: Ya no penaliza el score, solo ajusta prioridad para ordenar.
    
    Args:
        score_base: Score original (sin modificar)
        tipo_estrategia: "breakout" o "pullback"
        contexto_mercado: "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        float - Score de ranking (para ordenar, NO filtrar)
    """
    perfil = obtener_perfil_trading(contexto_mercado)
    
    # Aplicar prioridad según estrategia
    if tipo_estrategia == "breakout":
        prioridad = perfil["prioridad_breakout"]
    else:  # pullback
        prioridad = perfil["prioridad_pullback"]
    
    # Score de ranking = score base * prioridad
    score_ranking = score_base * prioridad
    
    return score_ranking


def obtener_factor_tamaño(tipo_estrategia, contexto_mercado):
    """
    Obtiene el factor de tamaño de posición según contexto.
    
    NUEVO: El contexto ajusta tamaño, no validez.
    
    Args:
        tipo_estrategia: "breakout" o "pullback"
        contexto_mercado: "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        float - Factor multiplicador de tamaño (0.4 - 1.0)
    
    Ejemplo:
        Tamaño base = 1000€
        Factor = 0.6 (breakout en lateral)
        Tamaño real = 1000 * 0.6 = 600€
    """
    perfil = obtener_perfil_v2(contexto_mercado)
    
    if tipo_estrategia == "breakout":
        return perfil["factor_tamaño_breakout"]
    else:  # pullback
        return perfil["factor_tamaño_pullback"]


def requiere_confirmacion_extra(tipo_estrategia, contexto_mercado):
    """
    Determina si el setup requiere confirmación adicional.
    
    Args:
        tipo_estrategia: "breakout" o "pullback"
        contexto_mercado: "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        bool - True si requiere confirmación extra
    
    Ejemplo:
        Breakout en LATERAL → requiere confirmación de volumen
        Pullback en ALCISTA → sin confirmación extra
    """
    perfil = obtener_perfil_v2(contexto_mercado)
    
    if tipo_estrategia == "breakout":
        return perfil["requiere_confirmacion_breakout"]
    else:  # pullback
        return perfil["requiere_confirmacion_pullback"]


def obtener_perfil_v2(contexto_mercado):
    """
    Obtiene el perfil V2 según contexto.
    
    Args:
        contexto_mercado: str - "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        dict - Perfil de trading con parámetros de ejecución
    """
    contexto = contexto_mercado.upper()
    
    if contexto not in PERFILES_V2:
        # Fallback a LATERAL si contexto desconocido
        contexto = "LATERAL"
    
    return PERFILES_V2[contexto]


# ══════════════════════════════════════════════════════════════════════
# COMPATIBILIDAD CON CÓDIGO EXISTENTE
# ══════════════════════════════════════════════════════════════════════

# Mantener exports antiguos para compatibilidad
def obtener_perfil_trading(contexto_mercado):
    """DEPRECADO: Usar obtener_perfil_v2()"""
    return obtener_perfil_v2(contexto_mercado)


def setup_pasa_filtro(score_base, tipo_estrategia, contexto_mercado):
    """
    VERSIÓN V2.1: Umbral dinámico por contexto.
    
    Returns:
        tuple: (pasa: bool, score_ranking: float, score_minimo: float)
    """
    pasa = setup_es_valido(score_base, contexto_mercado)
    score_ranking = calcular_score_ranking(score_base, tipo_estrategia, contexto_mercado)
    
    # Obtener umbral usado para este contexto
    contexto = contexto_mercado.upper()
    umbral_usado = UMBRALES_CONTEXTO.get(contexto, SCORE_MINIMO_ABSOLUTO)
    
    return pasa, score_ranking, umbral_usado


def calcular_score_ponderado(score_base, tipo_estrategia, contexto_mercado):
    """
    DEPRECADO en V2: El score ya no se pondera para filtrar.
    Mantenido solo por compatibilidad.
    """
    # En V2, devolvemos el score original (sin ponderar)
    return score_base
