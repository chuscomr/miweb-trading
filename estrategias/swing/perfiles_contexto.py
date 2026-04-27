# ══════════════════════════════════════════════════════════════════════
# PERFILES DE TRADING SEGÚN CONTEXTO DE MERCADO
# ══════════════════════════════════════════════════════════════════════
"""
Define parámetros de trading adaptativos según el contexto del mercado.

FILOSOFÍA PRO:
- NO bloquear estrategias → PONDERAR
- En ALCISTA: Ambas estrategias con peso completo
- En LATERAL: Breakouts penalizados, pullbacks favorecidos
- En BAJISTA: Ambas penalizadas (menos oportunidades en general)

VERSIÓN: v82.7 CORREGIDA
FECHA: 2026-04-25
IMPACTO ESPERADO: +40-100% en expectancy
"""

# ══════════════════════════════════════════════════════════════════════
# PERFILES DE TRADING (PONDERACIÓN PROFESIONAL)
# ══════════════════════════════════════════════════════════════════════

PERFILES = {
    "ALCISTA": {
        # Ponderación de estrategias (NO bloquear, PONDERAR)
        "peso_breakout": 1.0,
        "peso_pullback": 1.0,
        
        # Filtro mínimo (más permisivo en alcista)
        "score_base_minimo": 6.0,  # Acepta buenos y excelentes
        
        # Bonus/penalización para ranking
        "bonus_breakout": 0.3,   # Breakouts favorecidos (+0.3 al score)
        "bonus_pullback": 0.0,   # Pullbacks sin bonus
        "penalizacion_general": 0.0,
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 2.0,
        "max_posiciones_abiertas": 5,
        "max_exposicion_total_pct": 10.0,
        
        # Gestión de posición
        "trailing_desde_r": 2.0,
        "objetivo_parcial_r": 3.0,
        "venta_parcial_pct": 50,
        
        "descripcion": "Alcista: Favorece breakouts, score mínimo 6.0"
    },
    
    "LATERAL": {
        # Ponderación de estrategias
        "peso_breakout": 0.6,
        "peso_pullback": 1.0,
        
        # Filtro mínimo (más exigente)
        "score_base_minimo": 6.5,  # Solo buenos y excelentes
        
        # Bonus/penalización para ranking
        "bonus_breakout": 0.0,
        "bonus_pullback": 0.3,   # Pullbacks favorecidos (+0.3 al score)
        "penalizacion_general": 0.0,
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 1.5,
        "max_posiciones_abiertas": 3,
        "max_exposicion_total_pct": 6.0,
        
        # Gestión de posición
        "trailing_desde_r": 1.5,
        "objetivo_parcial_r": 2.0,
        "venta_parcial_pct": 50,
        
        "descripcion": "Lateral: Favorece pullbacks, score mínimo 6.5"
    },
    
    "BAJISTA": {
        # Ponderación de estrategias
        "peso_breakout": 0.3,
        "peso_pullback": 0.5,
        
        # Filtro mínimo (muy exigente)
        "score_base_minimo": 7.0,  # Solo excelentes
        
        # Bonus/penalización para ranking
        "bonus_breakout": 0.0,
        "bonus_pullback": 0.0,
        "penalizacion_general": 0.5,  # Todo penalizado en bajista
        
        # Gestión de riesgo
        "riesgo_por_trade_pct": 1.0,
        "max_posiciones_abiertas": 2,
        "max_exposicion_total_pct": 3.0,
        
        # Gestión de posición
        "trailing_desde_r": 1.0,
        "objetivo_parcial_r": 1.5,
        "venta_parcial_pct": 75,
        
        "descripcion": "Bajista: Muy conservador, solo excelentes, score mínimo 7.0"
    }
}


# ══════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL: CALCULAR SCORE PONDERADO
# ══════════════════════════════════════════════════════════════════════

def calcular_score_ponderado(score_base, tipo_estrategia, contexto_mercado):
    """
    Aplica ponderación al score según contexto y tipo de estrategia.
    
    Args:
        score_base: Score original de la señal (5.0 - 10.0)
        tipo_estrategia: "breakout" o "pullback"
        contexto_mercado: "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        float - Score ponderado
    
    Ejemplo:
        Score breakout = 6.0 en LATERAL
        → score_ponderado = 6.0 * 0.6 = 3.6
        → Si score_base_minimo = 6.5, este setup se RECHAZA
        
        Score pullback = 6.0 en LATERAL
        → score_ponderado = 6.0 * 1.0 = 6.0
        → Pasa el filtro ✅
    """
    perfil = obtener_perfil_trading(contexto_mercado)
    
    # Obtener peso según estrategia
    if tipo_estrategia == "breakout":
        peso = perfil["peso_breakout"]
    else:  # pullback
        peso = perfil["peso_pullback"]
    
    # Aplicar ponderación
    score_ponderado = score_base * peso
    
    return score_ponderado


def calcular_score_ranking(score_base, tipo_estrategia, contexto_mercado):
    """
    Calcula el score para RANKING (ordenación).
    Aplica bonus/penalizaciones según contexto para priorizar ciertos tipos.
    
    Este score NO se usa para filtrar (eso lo hace score_ponderado),
    sino para ORDENAR los setups que ya pasaron el filtro.
    
    Args:
        score_base: Score original (5.0-10.0)
        tipo_estrategia: "breakout" o "pullback"
        contexto_mercado: "ALCISTA", "LATERAL", "BAJISTA"
    
    Returns:
        float - Score de ranking (para ordenar)
    
    Ejemplo en ALCISTA:
        Breakout score 6.5 → 6.5 + 0.3 = 6.8 (favorecido)
        Pullback score 6.5 → 6.5 + 0.0 = 6.5 (neutral)
        → El breakout aparece ANTES en el ranking
    
    Ejemplo en LATERAL:
        Breakout score 7.0 → 7.0 + 0.0 = 7.0 (neutral)
        Pullback score 7.0 → 7.0 + 0.3 = 7.3 (favorecido)
        → El pullback aparece ANTES en el ranking
    """
    perfil = obtener_perfil_trading(contexto_mercado)
    
    # Empezar con score base
    score_ranking = score_base
    
    # Aplicar bonus según tipo de estrategia
    if tipo_estrategia == "breakout":
        score_ranking += perfil["bonus_breakout"]
    else:  # pullback
        score_ranking += perfil["bonus_pullback"]
    
    # Aplicar penalización general (en bajista penaliza todo)
    score_ranking -= perfil["penalizacion_general"]
    
    return score_ranking


def clasificar_calidad_setup(score):
    """
    Clasifica un setup según su calidad.
    
    Returns:
        str: "excelente", "bueno", "mediocre"
    """
    if score >= 8.0:
        return "excelente"
    elif score >= 6.5:
        return "bueno"
    else:
        return "mediocre"


def setup_pasa_filtro(score_base, tipo_estrategia, contexto_mercado):
    """
    Determina si un setup pasa el filtro de calidad según contexto.
    
    Returns:
        tuple: (pasa: bool, score_ponderado: float, score_minimo: float)
    """
    perfil = obtener_perfil_trading(contexto_mercado)
    score_ponderado = calcular_score_ponderado(score_base, tipo_estrategia, contexto_mercado)
    score_minimo = perfil["score_base_minimo"]
    
    pasa = score_ponderado >= score_minimo
    
    return pasa, score_ponderado, score_minimo


# ══════════════════════════════════════════════════════════════════════
# FUNCIÓN AUXILIAR
# ══════════════════════════════════════════════════════════════════════

def obtener_perfil_trading(contexto_mercado):
    """
    Obtiene el perfil de trading según el contexto actual del mercado.
    
    Args:
        contexto_mercado: str - "ALCISTA", "LATERAL" o "BAJISTA"
    
    Returns:
        dict - Perfil de trading con todos los parámetros
    """
    contexto = contexto_mercado.upper()
    
    if contexto not in PERFILES:
        # Default a LATERAL si contexto desconocido (más conservador)
        print(f"⚠️ Contexto '{contexto}' desconocido, usando perfil LATERAL por defecto")
        contexto = "LATERAL"
    
    perfil = PERFILES[contexto].copy()
    perfil["contexto"] = contexto
    
    return perfil


def mostrar_perfil(contexto_mercado):
    """
    Muestra el perfil activo de forma legible.
    """
    perfil = obtener_perfil_trading(contexto_mercado)
    
    print(f"\n{'='*70}")
    print(f"📊 PERFIL DE TRADING ACTIVO: {perfil['contexto']}")
    print(f"{'='*70}")
    print(f"📝 {perfil['descripcion']}")
    
    print(f"\n⚖️ PONDERACIÓN DE ESTRATEGIAS:")
    print(f"   • Peso Breakout:  {perfil['peso_breakout']:.1f}x")
    print(f"   • Peso Pullback:  {perfil['peso_pullback']:.1f}x")
    
    print(f"\n🎯 FILTROS DE ENTRADA:")
    print(f"   • Score base mínimo:  {perfil['score_base_minimo']}")
    
    print(f"\n💰 GESTIÓN DE RIESGO:")
    print(f"   • Riesgo por trade:        {perfil['riesgo_por_trade_pct']}%")
    print(f"   • Máx posiciones abiertas: {perfil['max_posiciones_abiertas']}")
    print(f"   • Máx exposición total:    {perfil['max_exposicion_total_pct']}%")
    
    print(f"\n📈 GESTIÓN DE POSICIÓN:")
    print(f"   • Trailing desde:          +{perfil['trailing_desde_r']}R")
    print(f"   • Objetivo parcial:        +{perfil['objetivo_parcial_r']}R")
    print(f"   • Venta parcial:           {perfil['venta_parcial_pct']}%")
    
    print(f"{'='*70}\n")
    
    return perfil


def mostrar_ejemplos_ponderacion():
    """
    Muestra ejemplos de cómo funciona la ponderación en cada contexto.
    """
    print("\n" + "="*70)
    print("📚 EJEMPLOS DE PONDERACIÓN")
    print("="*70)
    
    # Ejemplo 1: Breakout score 6.0 en diferentes contextos
    print("\n🔵 Setup BREAKOUT con score base = 6.0")
    print("─"*70)
    for contexto in ["ALCISTA", "LATERAL", "BAJISTA"]:
        pasa, score_pond, score_min = setup_pasa_filtro(6.0, "breakout", contexto)
        resultado = "✅ PASA" if pasa else "❌ RECHAZADO"
        print(f"  {contexto:10} → Score ponderado: {score_pond:.1f} (mín: {score_min}) → {resultado}")
    
    # Ejemplo 2: Pullback score 6.0 en diferentes contextos
    print("\n🟢 Setup PULLBACK con score base = 6.0")
    print("─"*70)
    for contexto in ["ALCISTA", "LATERAL", "BAJISTA"]:
        pasa, score_pond, score_min = setup_pasa_filtro(6.0, "pullback", contexto)
        resultado = "✅ PASA" if pasa else "❌ RECHAZADO"
        print(f"  {contexto:10} → Score ponderado: {score_pond:.1f} (mín: {score_min}) → {resultado}")
    
    # Ejemplo 3: Setup excelente score 8.0
    print("\n⭐ Setup EXCELENTE con score base = 8.0")
    print("─"*70)
    for contexto in ["ALCISTA", "LATERAL", "BAJISTA"]:
        pasa_b, score_b, _ = setup_pasa_filtro(8.0, "breakout", contexto)
        pasa_p, score_p, _ = setup_pasa_filtro(8.0, "pullback", contexto)
        print(f"  {contexto:10} → Breakout: {score_b:.1f} {'✅' if pasa_b else '❌'} | Pullback: {score_p:.1f} {'✅' if pasa_p else '❌'}")
    
    print("\n" + "="*70 + "\n")


# ══════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Mostrar los 3 perfiles
    for contexto in ["ALCISTA", "LATERAL", "BAJISTA"]:
        mostrar_perfil(contexto)
    
    # Mostrar ejemplos de ponderación
    mostrar_ejemplos_ponderacion()
