# core/riesgo.py
# ══════════════════════════════════════════════════════════════
# GESTIÓN DE RIESGO — SIZING, STOP, OBJETIVO, RR
#
# REGLA: Toda lógica de sizing vive aquí.
# app.py y las estrategias llaman estas funciones,
# no calculan riesgo por su cuenta.
# ══════════════════════════════════════════════════════════════

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# SIZING DE POSICIÓN
# ─────────────────────────────────────────────────────────────

def calcular_sizing(
    capital_total: float,
    riesgo_pct: float,
    entrada: float,
    stop: float,
    factor_mercado: float = 1.0,
) -> dict:
    """
    Calcula el número de acciones y métricas de la operación.

    Args:
        capital_total:  Capital disponible en €
        riesgo_pct:     % del capital que se arriesga (ej: 1.0 = 1%)
        entrada:        Precio de entrada
        stop:           Precio de stop loss
        factor_mercado: Multiplicador por contexto (0.0-1.0). Ver core/contexto_mercado.py

    Returns:
        dict con: acciones, capital_invertido, riesgo_operacion,
                  riesgo_por_accion, riesgo_pct_real, viable
    """
    if not all([capital_total > 0, riesgo_pct > 0, entrada > 0, stop > 0]):
        return _sizing_vacio("Parámetros inválidos")

    if stop >= entrada:
        return _sizing_vacio("Stop debe ser menor que entrada")

    riesgo_por_accion = round(entrada - stop, 4)
    if riesgo_por_accion <= 0:
        return _sizing_vacio("Riesgo por acción es 0")

    # Capital en riesgo ajustado por contexto de mercado
    capital_en_riesgo = capital_total * (riesgo_pct / 100) * factor_mercado

    acciones = int(capital_en_riesgo / riesgo_por_accion)
    acciones = max(acciones, 0)

    capital_invertido = round(acciones * entrada, 2)
    riesgo_operacion  = round(acciones * riesgo_por_accion, 2)
    riesgo_pct_real   = round((riesgo_operacion / capital_total) * 100, 2) if capital_total > 0 else 0

    return {
        "viable":            acciones > 0,
        "acciones":          acciones,
        "capital_invertido": capital_invertido,
        "riesgo_operacion":  riesgo_operacion,
        "riesgo_por_accion": round(riesgo_por_accion, 4),
        "riesgo_pct_real":   riesgo_pct_real,
        "factor_mercado":    factor_mercado,
        "error":             None,
    }


def _sizing_vacio(motivo: str) -> dict:
    return {
        "viable": False, "acciones": 0, "capital_invertido": 0,
        "riesgo_operacion": 0, "riesgo_por_accion": 0,
        "riesgo_pct_real": 0, "factor_mercado": 0, "error": motivo,
    }


# ─────────────────────────────────────────────────────────────
# STOP LOSS
# ─────────────────────────────────────────────────────────────

def calcular_stop(
    entrada: float,
    atr: Optional[float] = None,
    precios: Optional[list] = None,
    min_reciente: Optional[float] = None,
    setup_score: int = 3,
    max_riesgo_pct: float = 5.0,
    min_riesgo_pct: float = 1.0,
) -> Optional[float]:
    """
    Calcula stop loss con múltiples métodos y selecciona el más alto
    (más cercano al precio → menor riesgo).

    Métodos (por prioridad):
      1. ATR × multiplicador  (más preciso)
      2. Volatilidad histórica
      3. Estructura (mínimo reciente)
      4. Porcentaje fijo       (siempre disponible)

    Args:
        entrada:         Precio de entrada
        atr:             ATR en €  (de core/indicadores.py)
        precios:         Lista de cierres para volatilidad
        min_reciente:    Mínimo reciente (soporte estructural)
        setup_score:     0-10, afecta multiplicadores
        max_riesgo_pct:  Stop máximo permitido (%)
        min_riesgo_pct:  Stop mínimo (%)

    Returns:
        float con el stop, o None si entrada es inválida.
    """
    if not entrada or entrada <= 0:
        logger.warning("calcular_stop: entrada inválida")
        return None

    candidatos = []

    # ── Método 1: ATR ──────────────────────────────────────
    if atr and atr > 0:
        mult = 2.5 if setup_score >= 7 else 2.0 if setup_score >= 5 else 1.8
        stop_atr = entrada - (atr * mult)
        if stop_atr > 0:
            candidatos.append(("ATR", stop_atr))

    # ── Método 2: Volatilidad ───────────────────────────────
    if precios and len(precios) >= 20:
        try:
            std = float(np.std(precios[-20:]))
            mult_vol = 2.0 if setup_score >= 5 else 1.5
            stop_vol = entrada - (std * mult_vol)
            if stop_vol > 0:
                candidatos.append(("Volatilidad", stop_vol))
        except Exception:
            pass

    # ── Método 3: Estructura ────────────────────────────────
    if min_reciente and min_reciente > 0:
        stop_struct = min_reciente * 0.995
        if stop_struct > 0:
            candidatos.append(("Estructura", stop_struct))

    # ── Método 4: Fijo (siempre) ────────────────────────────
    pct_fijo = 0.04 if setup_score >= 5 else 0.03
    candidatos.append(("Fijo", entrada * (1 - pct_fijo)))

    # Seleccionar el más alto (menos riesgo)
    metodo, stop = max(candidatos, key=lambda x: x[1])

    # Validar límites de riesgo
    riesgo_pct = ((entrada - stop) / entrada) * 100

    if riesgo_pct > max_riesgo_pct:
        stop = entrada * (1 - max_riesgo_pct / 100)
        metodo = f"Limitado {max_riesgo_pct}%"

    if riesgo_pct < min_riesgo_pct:
        stop = entrada * (1 - min_riesgo_pct / 100)
        metodo = f"Mínimo {min_riesgo_pct}%"

    if stop >= entrada:
        stop = entrada * 0.97
        metodo = "Corrección"

    logger.debug(f"Stop: {stop:.2f}€ ({metodo})")
    return round(stop, 2)


# ─────────────────────────────────────────────────────────────
# OBJETIVO
# ─────────────────────────────────────────────────────────────

def calcular_objetivo(
    entrada: float,
    stop: float,
    atr: Optional[float] = None,
    setup_score: int = 3,
    rr_minimo: float = 2.0,
) -> Optional[float]:
    """
    Calcula el objetivo de precio.

    El RR objetivo sube con el setup_score:
      score >= 7 → RR 3.0
      score >= 5 → RR 2.5
      score <  5 → RR 2.0

    Args:
        entrada:     Precio de entrada
        stop:        Precio de stop (para calcular riesgo unitario)
        atr:         ATR en € (opcional, para objetivo alternativo)
        setup_score: 0-10
        rr_minimo:   RR mínimo aceptable (default 2.0)

    Returns:
        float con el objetivo, o None si los parámetros son inválidos.
    """
    if not entrada or entrada <= 0 or not stop or stop <= 0 or stop >= entrada:
        return None

    riesgo_unitario = entrada - stop
    if riesgo_unitario <= 0:
        return None

    # RR según calidad del setup
    rr = 3.0 if setup_score >= 7 else 2.5 if setup_score >= 5 else 2.0
    objetivo_rr = entrada + (riesgo_unitario * rr)

    # Objetivo alternativo por ATR
    objetivo_atr = None
    if atr and atr > 0:
        mult_atr = 4.0 if setup_score >= 7 else 3.0 if setup_score >= 5 else 2.5
        objetivo_atr = entrada + (atr * mult_atr)

    # Tomar el más conservador
    objetivo = min(objetivo_rr, objetivo_atr) if objetivo_atr else objetivo_rr

    # Garantizar RR mínimo
    minimo = entrada + (riesgo_unitario * rr_minimo)
    objetivo = max(objetivo, minimo)

    return round(objetivo, 2)


# ─────────────────────────────────────────────────────────────
# RR (RISK/REWARD)
# ─────────────────────────────────────────────────────────────

def calcular_rr(entrada: float, stop: float, objetivo: float) -> Optional[float]:
    """
    Calcula el ratio Riesgo/Recompensa.

    Returns:
        float RR (ej: 2.5) o None si los datos son inválidos.
    """
    if not all([entrada, stop, objetivo]):
        return None
    riesgo = entrada - stop
    beneficio = objetivo - entrada
    if riesgo <= 0 or beneficio <= 0:
        return None
    return round(beneficio / riesgo, 2)


# ─────────────────────────────────────────────────────────────
# RESUMEN COMPLETO DE UNA OPERACIÓN
# ─────────────────────────────────────────────────────────────

def resumen_operacion(
    entrada: float,
    stop: float,
    objetivo: float,
    capital_total: float,
    riesgo_pct: float,
    factor_mercado: float = 1.0,
) -> dict:
    """
    Combina sizing + RR en un único dict listo para la template.

    Returns:
        dict con toda la información de la operación.
    """
    rr = calcular_rr(entrada, stop, objetivo)
    sizing = calcular_sizing(capital_total, riesgo_pct, entrada, stop, factor_mercado)

    beneficio_potencial = round((objetivo - entrada) * sizing["acciones"], 2) if sizing["acciones"] > 0 else 0

    return {
        **sizing,
        "entrada":             round(entrada, 2),
        "stop":                round(stop, 2),
        "objetivo":            round(objetivo, 2),
        "rr":                  rr,
        "beneficio_potencial": beneficio_potencial,
    }
