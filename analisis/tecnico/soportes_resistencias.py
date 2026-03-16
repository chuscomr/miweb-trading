# analisis/tecnico/soportes_resistencias.py
# ══════════════════════════════════════════════════════════════
# SOPORTES Y RESISTENCIAS
#
# Migrado desde soportes_resistencias.py del proyecto original.
# Cambios:
#   - Eliminada dependencia de scipy (argrelextrema) — reemplazada
#     por implementación propia compatible con Render free tier
#   - Imports limpios (sin yfinance directo)
#   - __main__ eliminado
# ══════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def detectar_soportes_resistencias(
    df:            pd.DataFrame,
    periodo:       int   = 20,
    tolerancia_pct: float = 2.0,
    min_toques:    int   = 2,
) -> dict:
    """
    Detecta soportes y resistencias basados en máximos/mínimos locales.

    Args:
        df:             DataFrame con columnas High, Low, Close
        periodo:        Ventana para detectar extremos
        tolerancia_pct: % para agrupar niveles cercanos
        min_toques:     Mínimo de toques para validar nivel

    Returns:
        dict con 'soportes', 'resistencias', 'precio_actual', 'analisis'
    """
    if len(df) < periodo * 2:
        return {
            "soportes":      [],
            "resistencias":  [],
            "precio_actual": float(df["Close"].iloc[-1]),
            "analisis":      "Histórico insuficiente para análisis S/R",
        }

    highs  = df["High"].values
    lows   = df["Low"].values
    closes = df["Close"].values

    # Máximos y mínimos locales (sin scipy)
    maximos_idx = _extremos_locales(highs, periodo, tipo="max")
    minimos_idx = _extremos_locales(lows,  periodo, tipo="min")

    niveles_resistencia = highs[maximos_idx]
    niveles_soporte     = lows[minimos_idx]

    resistencias = _agrupar_niveles(niveles_resistencia, tolerancia_pct, min_toques)
    soportes     = _agrupar_niveles(niveles_soporte,     tolerancia_pct, min_toques)

    precio_actual = float(closes[-1])

    # Filtrar por posición vs precio actual
    resistencias = [r for r in resistencias if r["nivel"] > precio_actual]
    soportes     = [s for s in soportes     if s["nivel"] < precio_actual]

    # Ordenar por número de toques
    resistencias = sorted(resistencias, key=lambda x: x["toques"], reverse=True)
    soportes     = sorted(soportes,     key=lambda x: x["toques"], reverse=True)

    analisis = _analizar_posicion_precio(precio_actual, soportes, resistencias)

    return {
        "soportes":      soportes[:10],
        "resistencias":  resistencias[:10],
        "precio_actual": precio_actual,
        "analisis":      analisis,
    }


def obtener_sr_mas_cercanos(
    precio_actual: float,
    soportes:      list,
    resistencias:  list,
) -> dict:
    """
    Devuelve el soporte y resistencia más cercanos al precio actual.
    Útil para integración con estrategias de trading.
    """
    soportes_debajo     = [s for s in soportes     if s["nivel"] < precio_actual]
    resistencias_encima = [r for r in resistencias if r["nivel"] > precio_actual]

    soporte_cercano     = soportes_debajo[0]     if soportes_debajo     else None
    resistencia_cercana = resistencias_encima[0]  if resistencias_encima else None

    return {
        "soporte":    soporte_cercano,
        "resistencia": resistencia_cercana,
        "distancia_soporte_pct": (
            (precio_actual - soporte_cercano["nivel"]) / precio_actual * 100
            if soporte_cercano else None
        ),
        "distancia_resistencia_pct": (
            (resistencia_cercana["nivel"] - precio_actual) / precio_actual * 100
            if resistencia_cercana else None
        ),
    }


# ─────────────────────────────────────────────────────────────
# HELPERS PRIVADOS
# ─────────────────────────────────────────────────────────────

def _extremos_locales(serie: np.ndarray, orden: int, tipo: str) -> np.ndarray:
    """
    Detecta índices de máximos o mínimos locales sin scipy.
    Equivalente a argrelextrema con np.greater / np.less.
    """
    indices = []
    for i in range(orden, len(serie) - orden):
        ventana = serie[i - orden: i + orden + 1]
        if tipo == "max" and serie[i] == ventana.max():
            indices.append(i)
        elif tipo == "min" and serie[i] == ventana.min():
            indices.append(i)
    return np.array(indices, dtype=int)


def _agrupar_niveles(niveles: np.ndarray, tolerancia_pct: float, min_toques: int) -> list:
    """Agrupa niveles de precio cercanos en zonas con recuento de toques."""
    if len(niveles) == 0:
        return []

    niveles_sorted = np.sort(niveles)
    grupos = []
    i = 0

    while i < len(niveles_sorted):
        nivel_actual = niveles_sorted[i]
        grupo = [nivel_actual]
        j = i + 1

        while j < len(niveles_sorted):
            dif_pct = abs((niveles_sorted[j] - nivel_actual) / nivel_actual) * 100
            if dif_pct <= tolerancia_pct:
                grupo.append(niveles_sorted[j])
                j += 1
            else:
                break

        if len(grupo) >= min_toques:
            grupos.append({
                "nivel":  round(float(np.mean(grupo)), 2),
                "toques": len(grupo),
                "fuerza": _calcular_fuerza(len(grupo)),
            })

        i = j if j > i + 1 else i + 1

    return grupos


def _calcular_fuerza(toques: int) -> str:
    if toques >= 5:
        return "FUERTE"
    elif toques >= 3:
        return "MEDIO"
    return "DÉBIL"


def _analizar_posicion_precio(
    precio_actual: float,
    soportes:      list,
    resistencias:  list,
) -> str:
    """Texto descriptivo de la posición del precio respecto a S/R cercanos."""
    analisis = []

    soportes_debajo     = [s for s in soportes     if s["nivel"] < precio_actual]
    resistencias_encima = [r for r in resistencias if r["nivel"] > precio_actual]

    soporte_cercano     = soportes_debajo[0]     if soportes_debajo     else None
    resistencia_cercana = resistencias_encima[0]  if resistencias_encima else None

    if soporte_cercano:
        dist = ((precio_actual - soporte_cercano["nivel"]) / precio_actual) * 100
        analisis.append(
            f"Soporte en {soporte_cercano['nivel']}€ ({soporte_cercano['fuerza']}) "
            f"a {dist:.1f}% abajo"
        )
        if dist < 3:
            analisis.append("✅ Precio CERCA del soporte — zona de compra potencial")
        elif dist > 8:
            analisis.append("⚠️ Precio LEJOS del soporte — esperar pullback mayor")

    if resistencia_cercana:
        dist = ((resistencia_cercana["nivel"] - precio_actual) / precio_actual) * 100
        analisis.append(
            f"Resistencia en {resistencia_cercana['nivel']}€ ({resistencia_cercana['fuerza']}) "
            f"a {dist:.1f}% arriba"
        )
        if dist < 2:
            analisis.append("🚫 Precio PEGADO a resistencia — evitar compra")

    if soporte_cercano and resistencia_cercana:
        rango = resistencia_cercana["nivel"] - soporte_cercano["nivel"]
        pos_en_rango = (precio_actual - soporte_cercano["nivel"]) / rango * 100
        if pos_en_rango < 30:
            analisis.append("📊 Precio en zona BAJA del rango — favorable compra")
        elif pos_en_rango > 70:
            analisis.append("📊 Precio en zona ALTA del rango — desfavorable compra")

    return " | ".join(analisis) if analisis else "Sin análisis S/R disponible"
