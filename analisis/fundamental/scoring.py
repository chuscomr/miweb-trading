# analisis/fundamental/scoring.py
# ══════════════════════════════════════════════════════════════
# SCORING FUNDAMENTAL — Puntuación 0–100
#
# Evalúa la calidad fundamental de un valor en 6 categorías:
#   1. Valoración      (PER, EV/EBITDA, P/Ventas)
#   2. Rentabilidad    (ROE, ROA, márgenes)
#   3. Crecimiento     (BPA, ingresos)
#   4. Solidez balance (deuda/equity, ratio corriente)
#   5. Dividendo       (yield, payout sostenible)
#   6. Analistas       (recomendación, precio objetivo)
# ══════════════════════════════════════════════════════════════

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pesos de cada categoría (suman 100)
PESOS = {
    "valoracion":   25,
    "rentabilidad": 25,
    "crecimiento":  20,
    "balance":      15,
    "dividendo":    10,
    "analistas":     5,
}


def calcular_score_fundamental(datos: dict) -> dict:
    """
    Calcula el score fundamental de un ticker.

    Args:
        datos: dict de obtener_datos_fundamentales()

    Returns:
        dict con 'score', 'nivel', 'categorias', 'resumen'
    """
    if datos.get("error") and not datos.get("per"):
        return _score_vacio(datos.get("ticker", ""))

    cats = {}

    cats["valoracion"]   = _evaluar_valoracion(datos)
    cats["rentabilidad"] = _evaluar_rentabilidad(datos)
    cats["crecimiento"]  = _evaluar_crecimiento(datos)
    cats["balance"]      = _evaluar_balance(datos)
    cats["dividendo"]    = _evaluar_dividendo(datos)
    cats["analistas"]    = _evaluar_analistas(datos)

    # Score ponderado
    score_total = sum(
        cats[cat]["score_normalizado"] * PESOS[cat] / 100
        for cat in PESOS
    )
    score_total = round(max(0, min(100, score_total)), 1)

    nivel, color, recomendacion = _nivel_desde_score(score_total)

    # Fortalezas y debilidades
    fortalezas  = [c["resumen"] for c in cats.values() if c["score_normalizado"] >= 70]
    debilidades = [c["resumen"] for c in cats.values() if c["score_normalizado"] < 40]

    return {
        "ticker":         datos.get("ticker"),
        "score":          score_total,
        "nivel":          nivel,
        "color":          color,
        "recomendacion":  recomendacion,
        "categorias":     cats,
        "fortalezas":     fortalezas,
        "debilidades":    debilidades,
    }


# ─────────────────────────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────────────────────────

def _evaluar_valoracion(d: dict) -> dict:
    puntos = 0
    max_pts = 0
    detalles = []

    # PER (ajustado para mercado español — PER razonable 10–18)
    per = d.get("per")
    if per is not None:
        max_pts += 40
        if   per <= 0:    pts, txt = 0,  f"PER negativo ({per:.1f}) — pérdidas"
        elif per <= 12:   pts, txt = 40, f"PER bajo ({per:.1f}) — barato"
        elif per <= 18:   pts, txt = 35, f"PER razonable ({per:.1f})"
        elif per <= 25:   pts, txt = 20, f"PER elevado ({per:.1f})"
        elif per <= 35:   pts, txt = 10, f"PER caro ({per:.1f})"
        else:             pts, txt =  0, f"PER muy caro ({per:.1f})"
        puntos += pts
        detalles.append(txt)

    # EV/EBITDA
    ev = d.get("ev_ebitda")
    if ev is not None:
        max_pts += 30
        if   ev <= 6:   pts, txt = 30, f"EV/EBITDA muy bajo ({ev:.1f})"
        elif ev <= 10:  pts, txt = 25, f"EV/EBITDA razonable ({ev:.1f})"
        elif ev <= 15:  pts, txt = 15, f"EV/EBITDA elevado ({ev:.1f})"
        else:           pts, txt =  5, f"EV/EBITDA caro ({ev:.1f})"
        puntos += pts
        detalles.append(txt)

    # P/Ventas
    pvs = d.get("precio_ventas")
    if pvs is not None:
        max_pts += 30
        if   pvs <= 1.0:  pts, txt = 30, f"P/Ventas muy bajo ({pvs:.1f})"
        elif pvs <= 2.5:  pts, txt = 20, f"P/Ventas razonable ({pvs:.1f})"
        elif pvs <= 5.0:  pts, txt = 10, f"P/Ventas elevado ({pvs:.1f})"
        else:             pts, txt =  0, f"P/Ventas caro ({pvs:.1f})"
        puntos += pts
        detalles.append(txt)

    return _cat(puntos, max_pts, detalles, "Valoración")


def _evaluar_rentabilidad(d: dict) -> dict:
    puntos = 0
    max_pts = 0
    detalles = []

    # ROE
    roe = d.get("roe")
    if roe is not None:
        max_pts += 40
        if   roe >= 20:  pts, txt = 40, f"ROE excelente ({roe:.1f}%)"
        elif roe >= 12:  pts, txt = 30, f"ROE bueno ({roe:.1f}%)"
        elif roe >= 5:   pts, txt = 15, f"ROE moderado ({roe:.1f}%)"
        else:            pts, txt =  0, f"ROE bajo ({roe:.1f}%)"
        puntos += pts
        detalles.append(txt)

    # Margen neto
    mn = d.get("margen_neto")
    if mn is not None:
        max_pts += 35
        if   mn >= 20:  pts, txt = 35, f"Margen neto excelente ({mn:.1f}%)"
        elif mn >= 10:  pts, txt = 25, f"Margen neto bueno ({mn:.1f}%)"
        elif mn >= 5:   pts, txt = 15, f"Margen neto moderado ({mn:.1f}%)"
        elif mn >= 0:   pts, txt =  5, f"Margen neto bajo ({mn:.1f}%)"
        else:           pts, txt =  0, f"Pérdidas ({mn:.1f}%)"
        puntos += pts
        detalles.append(txt)

    # ROA
    roa = d.get("roa")
    if roa is not None:
        max_pts += 25
        if   roa >= 10:  pts, txt = 25, f"ROA excelente ({roa:.1f}%)"
        elif roa >= 5:   pts, txt = 18, f"ROA bueno ({roa:.1f}%)"
        elif roa >= 2:   pts, txt = 10, f"ROA moderado ({roa:.1f}%)"
        else:            pts, txt =  3, f"ROA bajo ({roa:.1f}%)"
        puntos += pts
        detalles.append(txt)

    return _cat(puntos, max_pts, detalles, "Rentabilidad")


def _evaluar_crecimiento(d: dict) -> dict:
    puntos = 0
    max_pts = 0
    detalles = []

    # Crecimiento BPA
    bpa_g = d.get("crecimiento_bpa")
    if bpa_g is not None:
        max_pts += 60
        if   bpa_g >= 20:  pts, txt = 60, f"Crecimiento BPA excelente ({bpa_g:.1f}%)"
        elif bpa_g >= 10:  pts, txt = 45, f"Crecimiento BPA bueno ({bpa_g:.1f}%)"
        elif bpa_g >= 5:   pts, txt = 30, f"Crecimiento BPA moderado ({bpa_g:.1f}%)"
        elif bpa_g >= 0:   pts, txt = 15, f"Crecimiento BPA bajo ({bpa_g:.1f}%)"
        else:              pts, txt =  0, f"BPA decreciendo ({bpa_g:.1f}%)"
        puntos += pts
        detalles.append(txt)

    # Crecimiento ingresos
    ing_g = d.get("crecimiento_ingresos")
    if ing_g is not None:
        max_pts += 40
        if   ing_g >= 15:  pts, txt = 40, f"Ingresos creciendo fuerte ({ing_g:.1f}%)"
        elif ing_g >= 8:   pts, txt = 30, f"Ingresos creciendo bien ({ing_g:.1f}%)"
        elif ing_g >= 3:   pts, txt = 15, f"Ingresos creciendo ({ing_g:.1f}%)"
        elif ing_g >= 0:   pts, txt =  5, f"Ingresos estables ({ing_g:.1f}%)"
        else:              pts, txt =  0, f"Ingresos cayendo ({ing_g:.1f}%)"
        puntos += pts
        detalles.append(txt)

    return _cat(puntos, max_pts, detalles, "Crecimiento")


def _evaluar_balance(d: dict) -> dict:
    puntos = 0
    max_pts = 0
    detalles = []

    # Deuda/Equity (menor = mejor)
    de = d.get("deuda_equity")
    if de is not None:
        max_pts += 60
        if   de <= 30:   pts, txt = 60, f"Deuda/Equity muy bajo ({de:.0f}%)"
        elif de <= 60:   pts, txt = 45, f"Deuda/Equity razonable ({de:.0f}%)"
        elif de <= 100:  pts, txt = 25, f"Deuda/Equity elevado ({de:.0f}%)"
        elif de <= 200:  pts, txt = 10, f"Deuda/Equity alto ({de:.0f}%)"
        else:            pts, txt =  0, f"Deuda/Equity muy alto ({de:.0f}%)"
        puntos += pts
        detalles.append(txt)

    # Ratio corriente (liquidez)
    rc = d.get("ratio_corriente")
    if rc is not None:
        max_pts += 40
        if   rc >= 2.0:  pts, txt = 40, f"Liquidez excelente ({rc:.1f}x)"
        elif rc >= 1.5:  pts, txt = 30, f"Liquidez buena ({rc:.1f}x)"
        elif rc >= 1.0:  pts, txt = 15, f"Liquidez ajustada ({rc:.1f}x)"
        else:            pts, txt =  0, f"Liquidez preocupante ({rc:.1f}x)"
        puntos += pts
        detalles.append(txt)

    return _cat(puntos, max_pts, detalles, "Balance")


def _evaluar_dividendo(d: dict) -> dict:
    puntos = 0
    max_pts = 0
    detalles = []

    div = d.get("dividendo_yield")
    payout = d.get("payout_ratio")

    if div is not None:
        max_pts += 60
        if   div >= 5.0:  pts, txt = 60, f"Dividendo alto ({div:.1f}%)"
        elif div >= 3.0:  pts, txt = 45, f"Dividendo atractivo ({div:.1f}%)"
        elif div >= 1.5:  pts, txt = 25, f"Dividendo moderado ({div:.1f}%)"
        elif div > 0:     pts, txt = 10, f"Dividendo bajo ({div:.1f}%)"
        else:             pts, txt =  0, "Sin dividendo"
        puntos += pts
        detalles.append(txt)

    if payout is not None and div and div > 0:
        max_pts += 40
        if   payout <= 50:   pts, txt = 40, f"Payout sostenible ({payout:.0f}%)"
        elif payout <= 70:   pts, txt = 25, f"Payout razonable ({payout:.0f}%)"
        elif payout <= 90:   pts, txt = 10, f"Payout elevado ({payout:.0f}%)"
        else:                pts, txt =  0, f"Payout insostenible ({payout:.0f}%)"
        puntos += pts
        detalles.append(txt)

    return _cat(puntos, max_pts, detalles, "Dividendo")


def _evaluar_analistas(d: dict) -> dict:
    puntos = 0
    max_pts = 60
    detalles = []

    rec = (d.get("recomendacion") or "").lower()
    precio_obj = d.get("precio_objetivo")
    precio_act = d.get("precio_actual")

    # Recomendación
    mapa = {
        "strong_buy": 30, "buy": 25, "outperform": 20,
        "hold": 10, "neutral": 10, "underperform": 0,
        "sell": 0, "strong_sell": 0,
    }
    pts = mapa.get(rec, 10)
    txt = f"Analistas: {rec or 'N/A'}"
    puntos += pts
    detalles.append(txt)

    # Upside vs precio objetivo
    if precio_obj and precio_act and precio_act > 0:
        upside = ((precio_obj - precio_act) / precio_act) * 100
        if   upside >= 20:  pts, txt = 30, f"Upside {upside:.1f}% vs precio objetivo"
        elif upside >= 10:  pts, txt = 20, f"Upside {upside:.1f}%"
        elif upside >= 0:   pts, txt = 10, f"Upside limitado ({upside:.1f}%)"
        else:               pts, txt =  0, f"Downside {upside:.1f}%"
        puntos += pts
        detalles.append(txt)
    else:
        max_pts = 30  # ajustar si no hay precio objetivo

    return _cat(puntos, max_pts, detalles, "Analistas")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _cat(puntos: int, max_pts: int, detalles: list, nombre: str) -> dict:
    """Construye el dict de una categoría con score normalizado."""
    if max_pts == 0:
        norm = 50   # sin datos → score neutro
        resumen = f"{nombre}: sin datos"
    else:
        norm    = round(max(0, min(100, (puntos / max_pts) * 100)), 1)
        resumen = f"{nombre}: {detalles[0]}" if detalles else f"{nombre}: evaluado"

    return {
        "nombre":            nombre,
        "score_normalizado": norm,
        "puntos":            puntos,
        "max_puntos":        max_pts,
        "detalles":          detalles,
        "resumen":           resumen,
    }


def _nivel_desde_score(score: float) -> tuple:
    if   score >= 75: return "EXCELENTE", "success", "✅ Fundamentos sólidos"
    elif score >= 60: return "BUENO",     "success", "✅ Fundamentos correctos"
    elif score >= 45: return "ACEPTABLE", "warning", "🟡 Fundamentos mixtos"
    elif score >= 30: return "DÉBIL",     "warning", "🟠 Fundamentos débiles"
    return "MALO", "danger", "🔴 Fundamentos preocupantes"


def _score_vacio(ticker: str) -> dict:
    return {
        "ticker":        ticker,
        "score":         0,
        "nivel":         "SIN DATOS",
        "color":         "secondary",
        "recomendacion": "Sin datos fundamentales disponibles",
        "categorias":    {},
        "fortalezas":    [],
        "debilidades":   [],
    }
