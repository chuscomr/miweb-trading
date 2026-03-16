# core/contexto_mercado.py
# ══════════════════════════════════════════════════════════════
# CONTEXTO DE MERCADO — IBEX 35
#
# Evalúa el estado general del mercado español para
# filtrar señales y ajustar el sizing de riesgo.
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import logging
from typing import Optional
from .data_provider import get_df_ibex

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# ESTADOS POSIBLES
# ─────────────────────────────────────────────────────────────

ESTADO_ALCISTA    = "ALCISTA"      # Verde  — operar con normalidad
ESTADO_TRANSICION = "TRANSICION"   # Naranja — reducir tamaño posición
ESTADO_BAJISTA    = "BAJISTA"      # Rojo   — no abrir nuevas posiciones

# Mapeo a texto de riesgo (compatibilidad con código anterior)
_ESTADO_A_RIESGO = {
    ESTADO_ALCISTA:    "RIESGO BAJO",
    ESTADO_TRANSICION: "RIESGO MEDIO",
    ESTADO_BAJISTA:    "RIESGO ALTO",
}

_ESTADO_A_COLOR = {
    ESTADO_ALCISTA:    "green",
    ESTADO_TRANSICION: "orange",
    ESTADO_BAJISTA:    "red",
}


# ─────────────────────────────────────────────────────────────
# ANÁLISIS
# ─────────────────────────────────────────────────────────────

def _analizar_ibex(df: pd.DataFrame) -> dict:
    """
    Evalúa el IBEX con tres criterios:
      1. Precio vs MM200
      2. Pendiente MM200
      3. Precio vs MM50
    """
    close = df["Close"].astype(float)

    mm50  = close.rolling(50).mean()
    mm200 = close.rolling(200).mean()

    precio      = float(close.iloc[-1])
    mm50_val    = float(mm50.iloc[-1])
    mm200_val   = float(mm200.iloc[-1])
    mm200_prev  = float(mm200.iloc[-2]) if len(mm200) > 1 else mm200_val

    pendiente_mm200 = mm200_val - mm200_prev

    # Criterios booleanos
    sobre_mm200 = precio > mm200_val
    mm200_sube  = pendiente_mm200 > 0
    sobre_mm50  = precio > mm50_val

    # ── Clasificación ──────────────────────────────────────
    if sobre_mm200 and mm200_sube and sobre_mm50:
        estado = ESTADO_ALCISTA
        texto  = "IBEX alcista con momentum"
    elif not sobre_mm200 and not mm200_sube:
        estado = ESTADO_BAJISTA
        texto  = "IBEX bajo MM200 en tendencia bajista"
    else:
        estado = ESTADO_TRANSICION
        texto  = "IBEX en zona de transición"

    return {
        "estado":         estado,
        "riesgo":         _ESTADO_A_RIESGO[estado],
        "color":          _ESTADO_A_COLOR[estado],
        "texto":          texto,
        "precio":         round(precio, 2),
        "mm50":           round(mm50_val, 2),
        "mm200":          round(mm200_val, 2),
        "sobre_mm200":    sobre_mm200,
        "sobre_mm50":     sobre_mm50,
        "pendiente_mm200": round(pendiente_mm200, 2),
    }


# ─────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────

_FALLBACK = {
    "estado":  ESTADO_TRANSICION,
    "riesgo":  "RIESGO MEDIO",
    "color":   "grey",
    "texto":   "IBEX sin datos suficientes",
    "precio":  None,
    "mm50":    None,
    "mm200":   None,
}


def evaluar_contexto_ibex(cache=None) -> dict:
    """
    Evalúa el estado del IBEX 35.

    Args:
        cache: objeto Cache de Flask (opcional)

    Returns:
        dict con claves: estado, riesgo, color, texto, precio, mm50, mm200
    """
    try:
        df = get_df_ibex(cache=cache, periodo="1y")
        if df is None or len(df) < 210:
            logger.warning("⚠️ IBEX: datos insuficientes para contexto")
            return _FALLBACK

        return _analizar_ibex(df)

    except Exception as e:
        logger.error(f"❌ Error evaluando contexto IBEX: {e}")
        return _FALLBACK


def mercado_operable(cache=None) -> bool:
    """
    Devuelve True si el mercado permite abrir posiciones.
    En estado BAJISTA no se opera.
    """
    ctx = evaluar_contexto_ibex(cache)
    return ctx["estado"] != ESTADO_BAJISTA


def factor_riesgo_mercado(cache=None) -> float:
    """
    Multiplicador de tamaño de posición según contexto:
      ALCISTA    → 1.0  (tamaño normal)
      TRANSICION → 0.75 (reducir 25%)
      BAJISTA    → 0.0  (no operar)
    """
    ctx = evaluar_contexto_ibex(cache)
    return {
        ESTADO_ALCISTA:    1.0,
        ESTADO_TRANSICION: 0.75,
        ESTADO_BAJISTA:    0.0,
    }.get(ctx["estado"], 0.75)
