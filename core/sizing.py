"""
core/sizing.py
══════════════════════════════════════════════════════════════
SIZING MULTIPLICATIVO — Modelo de tamaño de posición

Formula:
    size_final = size_base × factor_fundamental × factor_contexto × factor_setup

Límites hard:
    min 30% (evita posiciones ridículas)
    max 100% (evita sobreexposición)

Uso:
    from core.sizing import calcular_sizing_recomendado
    sizing = calcular_sizing_recomendado(
        rating_fund=rating_fund,
        contexto_mercado=contexto,
        setup_score=9.5,
        score_max=10,
        sistema="medio"  # "swing" | "medio" | "posicional"
    )
"""

import logging


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# FACTORES
# ─────────────────────────────────────────────────────────────

FACTOR_FUNDAMENTAL = {
    "verde":    1.00,
    "amarillo": 0.75,
    "rojo":     0.50,
    "sin_datos": 0.85,  # sin datos → ligera cautela
}

FACTOR_CONTEXTO = {
    "ALCISTA":    1.00,
    "TRANSICION": 0.75,
    "NEUTRO":     0.75,
    "NEUTRAL":    0.75,
    "BAJISTA":    0.50,
}

# Calidad del setup según score normalizado (0-1)
# Swing: score /10 | Medio: score /10 | Posicional: score /100
def _factor_setup(score_normalizado: float) -> tuple:
    """
    Devuelve (factor, label) según score normalizado 0-1.
    A+: ≥0.85 | A: 0.70-0.85 | B: 0.55-0.70 | C: <0.55
    """
    if score_normalizado >= 0.85:
        return 1.00, "A+"
    if score_normalizado >= 0.70:
        return 0.85, "A"
    if score_normalizado >= 0.55:
        return 0.70, "B"
    return 0.55, "C"

SIZE_MIN = 0.30   # 30% mínimo
SIZE_MAX = 1.00   # 100% máximo


def calcular_sizing_recomendado(
    rating_fund: dict,
    contexto_mercado: dict | None,
    setup_score: float,
    score_max: float,
    sistema: str = "medio",
) -> dict:
    """
    Calcula el tamaño recomendado de posición.

    Args:
        rating_fund:      resultado de calcular_rating_fundamental()
        contexto_mercado: resultado de evaluar_contexto_ibex()
        setup_score:      score técnico del setup
        score_max:        máximo posible del score (10 para swing/medio, 100 para posicional)
        sistema:          "swing" | "medio" | "posicional"

    Returns:
        dict con size_pct, factores, motivos, label
    """
    # ── Factor fundamental ────────────────────────────────────
    color_fund = rating_fund.get("color", "sin_datos") if rating_fund else "sin_datos"
    f_fund     = FACTOR_FUNDAMENTAL.get(color_fund, 0.85)
    fund_label = rating_fund.get("etiqueta", "Sin datos") if rating_fund else "Sin datos"
    fund_emoji = rating_fund.get("emoji", "⚪") if rating_fund else "⚪"

    # ── Factor contexto ───────────────────────────────────────
    estado_mercado = "NEUTRAL"
    if contexto_mercado:
        estado_mercado = (
            contexto_mercado.get("estado") or
            contexto_mercado.get("tendencia") or
            "NEUTRAL"
        ).upper()
    f_ctx      = FACTOR_CONTEXTO.get(estado_mercado, 0.75)
    ctx_emoji  = "🟢" if f_ctx == 1.0 else "🟡" if f_ctx == 0.75 else "🔴"
    ctx_label  = estado_mercado.capitalize()

    # ── Factor setup ──────────────────────────────────────────
    score_norm  = min(1.0, setup_score / score_max) if score_max > 0 else 0.5
    f_setup, setup_label = _factor_setup(score_norm)
    setup_emoji = "🟢" if f_setup >= 1.0 else "🟡" if f_setup >= 0.70 else "🔴"

    # ── Cálculo multiplicativo ────────────────────────────────
    size_raw   = 1.0 * f_fund * f_ctx * f_setup
    size_final = round(min(SIZE_MAX, max(SIZE_MIN, size_raw)), 2)
    size_pct   = round(size_final * 100)

    # ── Motivos para UI ───────────────────────────────────────
    motivos = [
        {
            "emoji": fund_emoji,
            "texto": f"Fundamental {fund_label}",
            "factor": f"×{f_fund:.2f}",
            "ok": f_fund >= 0.75,
        },
        {
            "emoji": ctx_emoji,
            "texto": f"Contexto {ctx_label}",
            "factor": f"×{f_ctx:.2f}",
            "ok": f_ctx >= 0.75,
        },
        {
            "emoji": setup_emoji,
            "texto": f"Setup calidad {setup_label} ({setup_score:.1f}/{score_max:.0f})",
            "factor": f"×{f_setup:.2f}",
            "ok": f_setup >= 0.70,
        },
    ]

    # ── Label de resumen ──────────────────────────────────────
    if size_pct >= 90:
        resumen = "Tamaño completo — condiciones óptimas"
    elif size_pct >= 70:
        resumen = "Tamaño reducido — alguna cautela"
    elif size_pct >= 50:
        resumen = "Tamaño moderado — cautela elevada"
    else:
        resumen = "Tamaño mínimo — condiciones adversas"

    return {
        "size_pct":   size_pct,       # int: 30-100
        "size_final": size_final,     # float: 0.30-1.00
        "resumen":    resumen,
        "motivos":    motivos,
        "factores": {
            "fundamental": f_fund,
            "contexto":    f_ctx,
            "setup":       f_setup,
        },
        "labels": {
            "fundamental": fund_label,
            "contexto":    ctx_label,
            "setup":       setup_label,
        },
    }
