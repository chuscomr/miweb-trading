"""
═══════════════════════════════════════════════════════════════
SCORING UNIFICADO — Sistema único para todos los escáneres
═══════════════════════════════════════════════════════════════

Filosofía:
  - 1 solo lenguaje de calidad (score 0-100)
  - 3 estrategias distintas (swing/medio/posicional)
  - 1 criterio de decisión unificado

Componentes del score:
  - 40pts → Técnico (estructura + tendencia)
  - 25pts → Setup (calidad de oportunidad)
  - 20pts → Momentum (timing)
  - 10pts → Contexto IBEX
  - 5pts  → Fundamental (filtro suave)
"""

import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CLASIFICACIÓN UNIVERSAL
# ═══════════════════════════════════════════════════════════════

def clasificar_score(score: float) -> str:
    """
    Clasificación universal del score.
    
    Returns:
        "Excelente" | "Bueno" | "Mediocre" | "Descartar"
    """
    if score >= 80:
        return "Excelente"
    elif score >= 60:
        return "Bueno"
    elif score >= 40:
        return "Mediocre"
    else:
        return "Descartar"


def umbral_por_contexto(contexto: str) -> int:
    """
    Umbral mínimo de score según contexto IBEX.
    
    ALCISTA: Score ≥60 (criterios normales)
    LATERAL: Score ≥70 (más selectivo)
    BAJISTA: Score ≥80 (solo lo mejor)
    
    Returns:
        int: Umbral mínimo de score
    """
    if contexto == "ALCISTA":
        return 60
    elif contexto == "LATERAL":
        return 70
    else:  # BAJISTA
        return 80


def estado_operativo(score: float, contexto: str, confirmacion: bool = True) -> str:
    """
    Determina el estado operativo basado en score y contexto.
    
    Args:
        score: Score 0-100
        contexto: "ALCISTA" | "LATERAL" | "BAJISTA"
        confirmacion: Si tiene confirmación técnica
    
    Returns:
        "COMPRA" | "VIGILAR" | "ESPERAR"
    """
    umbral = umbral_por_contexto(contexto)
    
    if score >= umbral and confirmacion:
        return "COMPRA"
    elif score >= umbral - 10:  # Margen de 10pts bajo umbral
        return "VIGILAR"
    else:
        return "ESPERAR"


# ═══════════════════════════════════════════════════════════════
# CÁLCULO DE SCORE (0-100)
# ═══════════════════════════════════════════════════════════════

def calcular_score_tecnico(
    precio: float,
    mm50: float,
    mm200: float,
    maximos_crecientes: bool = False,
    minimos_crecientes: bool = False,
    estructura_limpia: bool = False
) -> float:
    """
    Score técnico (0-40 puntos).
    
    Evalúa:
      - Tendencia (20pts): precio vs MM50 vs MM200
      - Estructura (10pts): máximos/mínimos crecientes
      - Limpieza (10pts): velas sanas, sin ruido
    """
    score = 0.0
    
    # Tendencia (20pts)
    if precio > mm50 > mm200:
        score += 20  # Tendencia alcista perfecta
    elif precio > mm200:
        score += 10  # Al menos sobre MM200
    elif precio > mm50:
        score += 5   # Solo sobre MM50
    
    # Estructura (10pts)
    if maximos_crecientes and minimos_crecientes:
        score += 10  # Estructura alcista clara
    elif maximos_crecientes or minimos_crecientes:
        score += 5   # Estructura parcial
    
    # Limpieza (10pts)
    if estructura_limpia:
        score += 10
    
    return min(40, score)  # Cap en 40pts


def calcular_score_setup(
    tipo_setup: str,
    calidad_zona: str = "neutral",
    cerca_resistencia: bool = False
) -> float:
    """
    Score del setup (0-25 puntos).
    
    Evalúa:
      - Tipo de setup (base)
      - Calidad de zona
      - Proximidad a resistencia
    """
    score = 0.0
    
    # Base por tipo de setup
    if tipo_setup == "breakout":
        score += 25
    elif tipo_setup == "pullback":
        score += 18
    elif tipo_setup == "rebote":
        score += 10
    else:
        score += 5
    
    # Ajuste por zona
    if calidad_zona == "excelente":
        score += 3
    elif calidad_zona == "mala":
        score -= 5
    
    # Penalización si cerca de resistencia sin breakout
    if cerca_resistencia and tipo_setup != "breakout":
        score -= 3
    
    return max(0, min(25, score))  # Entre 0-25pts


def calcular_score_momentum(
    rsi: float,
    volumen_creciente: bool = False
) -> float:
    """
    Score de momentum (0-20 puntos).
    
    Evalúa:
      - RSI (10pts): zona óptima 55-65
      - Volumen (10pts): creciente vs neutro
    """
    score = 0.0
    
    # RSI (10pts)
    if 55 <= rsi <= 65:
        score += 10  # Zona óptima
    elif 50 <= rsi < 55 or 65 < rsi <= 70:
        score += 6   # Zona aceptable
    elif rsi > 70:
        score += 3   # Sobrecompra
    elif rsi < 45:
        score += 2   # Sobreventa
    else:
        score += 4   # RSI neutral
    
    # Volumen (10pts)
    if volumen_creciente:
        score += 10
    else:
        score += 5  # Volumen neutro
    
    return min(20, score)


def calcular_score_contexto(contexto_ibex: str) -> float:
    """
    Score por contexto de mercado (0-10 puntos).
    
    ALCISTA: 10pts
    LATERAL: 6pts
    BAJISTA: 2pts
    """
    if contexto_ibex == "ALCISTA":
        return 10
    elif contexto_ibex == "LATERAL":
        return 6
    else:  # BAJISTA
        return 2


def calcular_score_fundamental(semaforo: str) -> float:
    """
    Score fundamental (0-5 puntos).
    
    Filtro suave basado en semáforo.
    
    VERDE: 5pts
    NEUTRAL: 3pts
    ROJO: 0pts
    """
    if semaforo == "VERDE":
        return 5
    elif semaforo == "NEUTRAL":
        return 3
    else:  # ROJO
        return 0


# ═══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def calcular_score_total(
    # Técnico
    precio: float,
    mm50: float,
    mm200: float,
    maximos_crecientes: bool = False,
    minimos_crecientes: bool = False,
    estructura_limpia: bool = False,
    # Setup
    tipo_setup: str = "pullback",
    calidad_zona: str = "neutral",
    cerca_resistencia: bool = False,
    # Momentum
    rsi: float = 50,
    volumen_creciente: bool = False,
    # Contexto
    contexto_ibex: str = "LATERAL",
    # Fundamental
    semaforo_fundamental: str = "NEUTRAL"
) -> dict:
    """
    Calcula el score total unificado (0-100).
    
    Returns:
        dict con:
          - score: float (0-100)
          - clasificacion: str ("Excelente" | "Bueno" | "Mediocre")
          - estado: str ("COMPRA" | "VIGILAR" | "ESPERAR")
          - desglose: dict con scores parciales
    """
    # Calcular componentes
    score_tec = calcular_score_tecnico(
        precio, mm50, mm200,
        maximos_crecientes, minimos_crecientes, estructura_limpia
    )
    
    score_set = calcular_score_setup(
        tipo_setup, calidad_zona, cerca_resistencia
    )
    
    score_mom = calcular_score_momentum(rsi, volumen_creciente)
    
    score_ctx = calcular_score_contexto(contexto_ibex)
    
    score_fun = calcular_score_fundamental(semaforo_fundamental)
    
    # Score total
    score_total = score_tec + score_set + score_mom + score_ctx + score_fun
    
    # Normalizar (por si acaso)
    score_total = max(0, min(100, score_total))
    
    # Clasificar
    clasificacion = clasificar_score(score_total)
    
    # Estado operativo
    confirmacion = volumen_creciente and estructura_limpia
    estado = estado_operativo(score_total, contexto_ibex, confirmacion)
    
    return {
        "score": round(score_total, 1),
        "clasificacion": clasificacion,
        "estado": estado,
        "desglose": {
            "tecnico": round(score_tec, 1),
            "setup": round(score_set, 1),
            "momentum": round(score_mom, 1),
            "contexto": round(score_ctx, 1),
            "fundamental": round(score_fun, 1),
        },
        "umbral_contexto": umbral_por_contexto(contexto_ibex)
    }


# ═══════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════

def ordenar_por_score(resultados: list) -> list:
    """
    Ordena resultados por score descendente.
    Los mejores setups siempre primero.
    """
    return sorted(resultados, key=lambda x: x.get("score", 0), reverse=True)


def agrupar_por_clasificacion(resultados: list) -> dict:
    """
    Agrupa resultados por clasificación.
    
    Returns:
        {
            "Excelente": [...],
            "Bueno": [...],
            "Mediocre": [...]
        }
    """
    grupos = {
        "Excelente": [],
        "Bueno": [],
        "Mediocre": []
    }
    
    for r in resultados:
        clasificacion = r.get("clasificacion", "Mediocre")
        if clasificacion in grupos:
            grupos[clasificacion].append(r)
    
    return grupos


def mensaje_contexto(contexto: str) -> str:
    """
    Mensaje para mostrar en UI según contexto.
    
    Returns:
        str: Mensaje formateado
    """
    umbral = umbral_por_contexto(contexto)
    
    if contexto == "ALCISTA":
        return f"🟢 IBEX ALCISTA — operar setups ≥{umbral}"
    elif contexto == "LATERAL":
        return f"🟡 IBEX LATERAL — operar solo setups ≥{umbral}"
    else:
        return f"🔴 IBEX BAJISTA — operar ÚNICAMENTE setups ≥{umbral}"
