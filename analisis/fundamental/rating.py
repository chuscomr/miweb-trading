"""
analisis/fundamental/rating.py
══════════════════════════════════════════════════════════════
RATING FUNDAMENTAL — Semáforo 🟢🟡🔴

4 ratios clave con ajustes finos:
  1. EV/EBITDA    — con excepción sectorial (utilities/renovables)
  2. Deuda/EBITDA — solidez financiera
  3. ROE          — penalizado si deuda alta (evita trampa)
  4. FCF          — consistencia ≥3/4 años (no FCF puntual)

Lógica de color final:
  ≥2 rojos  → 🔴 Riesgo elevado  (tamaño 50%)
  ≥2 verdes → 🟢 Calidad alta    (tamaño 100%)
  resto     → 🟡 Neutral         (tamaño 75%)
"""

import logging


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# SECTORES CON MÚLTIPLOS NATURALMENTE ELEVADOS
# utilities, renovables, infraestructuras cotizan con EV/EBITDA
# alto por la estabilidad y visibilidad de sus flujos
# ─────────────────────────────────────────────────────────────
SECTORES_MULTIPLOS_ALTOS = {
    "utilities", "utilities-regulated", "utilities-renewable",
    "renewable energy", "renewables", "solar", "wind",
    "real estate", "reit", "infrastructure",
    "communication services",
}

def _es_sector_multiplos_altos(sector: str) -> bool:
    if not sector:
        return False
    s = sector.lower()
    return any(k in s for k in SECTORES_MULTIPLOS_ALTOS)


def calcular_rating_fundamental(datos: dict) -> dict:
    """
    Calcula el rating fundamental simplificado.
    Devuelve dict con color, emoji, etiqueta, tamaño_pct, criterios.
    """
    if not datos or (datos.get("error") and not datos.get("ev_ebitda")):
        return _sin_datos()

    sector     = datos.get("sector") or ""
    multiplos_altos = _es_sector_multiplos_altos(sector)
    criterios  = []

    # ── 1. EV/EBITDA (con excepción sectorial) ───────────────
    ev = datos.get("ev_ebitda")
    if ev is not None and ev > 0:
        if multiplos_altos:
            # Utilities/renovables: umbrales más tolerantes
            if ev <= 15:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "verde",
                          f"Valoración razonable sector ({ev:.1f}x)")
            elif ev <= 25:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "amarillo",
                          f"Múltiplo elevado típico del sector ({ev:.1f}x)")
            else:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "rojo",
                          f"Valoración cara incluso para el sector ({ev:.1f}x)")
        else:
            # Resto de sectores: umbrales estándar
            if ev <= 10:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "verde",
                          f"Valoración atractiva ({ev:.1f}x)")
            elif ev <= 20:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "amarillo",
                          f"Valoración elevada ({ev:.1f}x)")
            else:
                c = _crit("EV/EBITDA", f"{ev:.1f}x", "rojo",
                          f"Valoración cara ({ev:.1f}x)")
        criterios.append(c)

    # ── 2. Deuda/EBITDA ───────────────────────────────────────
    de = datos.get("deuda_ebitda")
    deuda_alta = False  # flag para penalizar ROE
    if de is not None:
        if de <= 3:
            c = _crit("Deuda/EBITDA", f"{de:.1f}x", "verde",
                      f"Deuda sólida ({de:.1f}x)")
        elif de <= 5:
            c = _crit("Deuda/EBITDA", f"{de:.1f}x", "amarillo",
                      f"Deuda elevada ({de:.1f}x)")
            deuda_alta = (de > 4)
        else:
            c = _crit("Deuda/EBITDA", f"{de:.1f}x", "rojo",
                      f"Deuda preocupante ({de:.1f}x)")
            deuda_alta = True
        criterios.append(c)

    # ── 3. ROE — penalizado si deuda alta ─────────────────────
    # ROE alto con mucha deuda = equity pequeño = ROE artificial
    roe = datos.get("roe")
    if roe is not None:
        if deuda_alta and roe >= 12:
            # ROE inflado por apalancamiento — degradar un nivel
            c = _crit("ROE", f"{roe:.1f}%*", "amarillo",
                      f"ROE aparentemente bueno ({roe:.1f}%) pero inflado por deuda alta")
        elif roe >= 12:
            c = _crit("ROE", f"{roe:.1f}%", "verde",
                      f"Rentabilidad sólida ({roe:.1f}%)")
        elif roe >= 6:
            c = _crit("ROE", f"{roe:.1f}%", "amarillo",
                      f"Rentabilidad moderada ({roe:.1f}%)")
        else:
            c = _crit("ROE", f"{roe:.1f}%", "rojo",
                      f"Rentabilidad baja ({roe:.1f}%)")
        criterios.append(c)

    # ── 4. FCF — consistencia ≥3/4 años ──────────────────────
    # No usamos FCF último año (ruido) sino consistencia histórica
    fcf_str = datos.get("fcf_positivo_anos")  # ej: "3/4 años"
    if fcf_str:
        try:
            partes    = str(fcf_str).replace(" años", "").replace(" anos", "").split("/")
            pos, tot  = int(partes[0]), int(partes[1])
            ratio_fcf = pos / tot if tot > 0 else 0
            if ratio_fcf >= 0.75:   # ≥3/4 años
                c = _crit("FCF", fcf_str, "verde",
                          f"FCF consistente ({fcf_str})")
            elif ratio_fcf >= 0.50:  # 2/4 años
                c = _crit("FCF", fcf_str, "amarillo",
                          f"FCF irregular ({fcf_str})")
            else:                    # <2/4 años
                c = _crit("FCF", fcf_str, "rojo",
                          f"FCF negativo frecuente ({fcf_str})")
            criterios.append(c)
        except Exception as e:
            logger.debug(f"FCF parse: {e}")

    # Garantizar los 4 slots siempre visibles — N/D si el dato no está disponible
    nombres_presentes = {c["nombre"] for c in criterios}
    slots_obligatorios = [
        ("EV/EBITDA",    datos.get("ev_ebitda")),
        ("Deuda/EBITDA", datos.get("deuda_ebitda")),
        ("ROE",          datos.get("roe")),
        ("FCF",          datos.get("fcf_positivo_anos")),
    ]
    for nombre, valor in slots_obligatorios:
        if nombre not in nombres_presentes:
            criterios.append(_crit(nombre, "N/D", "amarillo", f"{nombre}: sin dato disponible"))

    if not criterios:
        return _sin_datos()

    # ── Lógica de color final ─────────────────────────────────
    # Regla robusta: no media simple — cuenta rojos y verdes
    n_verde    = sum(1 for c in criterios if c["color"] == "verde")
    n_amarillo = sum(1 for c in criterios if c["color"] == "amarillo")
    n_rojo     = sum(1 for c in criterios if c["color"] == "rojo")

    if n_rojo >= 2:
        color, emoji, etiqueta, tamaño = "rojo",     "🔴", "Riesgo elevado", 50
    elif n_verde >= 2 and n_rojo == 0:
        color, emoji, etiqueta, tamaño = "verde",    "🟢", "Calidad alta",   100
    else:
        color, emoji, etiqueta, tamaño = "amarillo", "🟡", "Neutral",        75

    # Aviso contextual
    aviso = None
    if color == "rojo":
        aviso = "⚠️ Fundamental débil — mayor volatilidad esperada"
    elif color == "amarillo" and deuda_alta:
        aviso = "⚠️ Deuda elevada — gestión de posición más estricta"

    return {
        "color":      color,
        "emoji":      emoji,
        "etiqueta":   etiqueta,
        "tamaño_pct": tamaño,
        "criterios":  criterios,
        "n_verde":    n_verde,
        "n_amarillo": n_amarillo,
        "n_rojo":     n_rojo,
        "n_total":    len(criterios),
        "aviso":      aviso,
        "sector":     sector,
        "disponible": True,
    }


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _crit(nombre: str, valor: str, color: str, texto: str) -> dict:
    emojis = {"verde": "✅", "amarillo": "⚠️", "rojo": "❌"}
    return {
        "nombre": nombre,
        "valor":  valor,
        "color":  color,
        "emoji":  emojis.get(color, "—"),
        "texto":  texto,
    }


def _sin_datos() -> dict:
    return {
        "color":      "sin_datos",
        "emoji":      "⚪",
        "etiqueta":   "Sin datos",
        "tamaño_pct": 100,
        "criterios":  [],
        "n_verde":    0,
        "n_amarillo": 0,
        "n_rojo":     0,
        "n_total":    0,
        "aviso":      None,
        "sector":     "",
        "disponible": False,
    }
