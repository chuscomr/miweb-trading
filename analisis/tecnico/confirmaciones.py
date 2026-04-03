# analisis/tecnico/confirmaciones.py
# ══════════════════════════════════════════════════════════════
# CONFIRMACIONES TÉCNICAS — BREAKOUT y PULLBACK
#
# Migrado desde confirmaciones_breakout.py y confirmaciones_pullback.py.
# Unificado en una sola función pública calcular_confirmaciones()
# que delega a la implementación correcta según tipo de señal.
#
# Puntuación 0–100 normalizada.
# Breakout:  10 factores específicos de rupturas
# Pullback:  10 factores específicos de rebotes en soporte
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────

def calcular_confirmaciones(df: pd.DataFrame, señal: dict) -> dict:
    """
    Calcula la puntuación de confirmación técnica (0–100) para una señal.
    Detecta automáticamente si es BREAKOUT o PULLBACK.

    Args:
        df:    DataFrame con OHLCV e indicadores calculados (MM20, ATR, RSI)
        señal: dict estándar de respuesta de una estrategia swing

    Returns:
        dict con 'puntuacion', 'nivel', 'recomendacion', 'color', 'desglose'
    """
    tipo = señal.get("tipo", "BREAKOUT").upper()

    if tipo == "PULLBACK":
        return _confirmaciones_pullback(df, señal)
    return _confirmaciones_breakout(df, señal)


# ─────────────────────────────────────────────────────────────
# BREAKOUT (10 factores, máx 130 pts brutos → normalizado 0–100)
# ─────────────────────────────────────────────────────────────

def _confirmaciones_breakout(df: pd.DataFrame, señal: dict) -> dict:
    total    = 0
    desglose = {}

    precio_actual = señal.get("precio_actual", 0)

    # 1. Volumen en ruptura (0–30)
    vol = señal.get("volumen_ruptura", 1.0)
    if   vol >= 2.5: pts, det, col = 30, f"🔥 MUY ALTA ({vol:.1f}x)",     "positivo"
    elif vol >= 2.0: pts, det, col = 25, f"✅ ALTA ({vol:.1f}x)",          "positivo"
    elif vol >= 1.5: pts, det, col = 20, f"✅ Buena ({vol:.1f}x)",         "positivo"
    elif vol >= 1.2: pts, det, col = 10, f"Normal ({vol:.1f}x)",           "neutro"
    else:            pts, det, col =  0, f"❌ BAJA ({vol:.1f}x)",          "negativo"
    desglose["volumen_ruptura"] = {"nombre": "Volumen Ruptura", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 2. Fuerza resistencia rota (0–15)
    res = señal.get("resistencia_rota", 0)
    if res > 0:
        d = ((precio_actual - res) / res) * 100
        if   d >= 2.0:  pts, det, col = 15, f"✅ Rota con claridad (+{d:.1f}%)",  "positivo"
        elif d >= 0.5:  pts, det, col = 12, f"✅ Rota (+{d:.1f}%)",               "positivo"
        elif d >= -0.5: pts, det, col =  8, f"En resistencia",                    "neutro"
        else:           pts, det, col =  3, f"⚠️ Bajo resistencia",               "neutro"
    else:
        pts, det, col = 0, "Sin resistencia identificada", "neutro"
    desglose["resistencia"] = {"nombre": "Fuerza Resistencia", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 3. RSI momentum 60–75 (0–10, penaliza >78)
    rsi = señal.get("rsi", 50)
    if   62 <= rsi <= 72:  pts, det, col = 10, f"✅ ÓPTIMO ({rsi:.1f})",          "positivo"
    elif 55 <= rsi < 62 or 72 < rsi <= 75: pts, det, col = 7, f"Bueno ({rsi:.1f})", "positivo"
    elif 50 <= rsi < 55 or 75 < rsi <= 78: pts, det, col = 3, f"Aceptable ({rsi:.1f})", "neutro"
    elif rsi > 78:         pts, det, col = -5, f"⚠️ Sobrecompra ({rsi:.1f})",     "negativo"
    else:                  pts, det, col =  0, f"Bajo ({rsi:.1f})",               "neutro"
    desglose["rsi"] = {"nombre": "RSI Momentum", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 4. ATR creciendo (0–10)
    pts, det, col = _factor_atr_expansion(df)
    desglose["atr"] = {"nombre": "ATR (Volatilidad)", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 5. Precio vs máximo (0–15)
    dist_max = señal.get("dist_maximo_pct", señal.get("distancia_maximo_pct", 0))
    if   abs(dist_max) <= 0.5: pts, det, col = 15, f"✅ En máximo ({dist_max:+.1f}%)",      "positivo"
    elif abs(dist_max) <= 1.5: pts, det, col = 12, f"✅ Muy cerca ({dist_max:+.1f}%)",      "positivo"
    elif abs(dist_max) <= 3.0: pts, det, col =  8, f"Cerca ({dist_max:+.1f}%)",             "neutro"
    else:                      pts, det, col =  3, f"Lejos del máximo ({dist_max:+.1f}%)",  "neutro"
    desglose["precio_maximo"] = {"nombre": "Precio vs Máximo", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 6. MACD acelerando (0–10)
    pts, det, col = _factor_macd(df)
    desglose["macd"] = {"nombre": "MACD", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 7. Consolidación previa (0–10)
    cons = señal.get("consolidacion_dias", 0)
    if   cons >= 20: pts, det, col = 10, f"✅ Consolidación larga ({cons}d)",   "positivo"
    elif cons >= 12: pts, det, col =  7, f"✅ Consolidación buena ({cons}d)",   "positivo"
    elif cons >= 8:  pts, det, col =  3, f"Consolidación mínima ({cons}d)",     "neutro"
    else:            pts, det, col =  0, f"Sin consolidación clara",            "neutro"
    desglose["consolidacion"] = {"nombre": "Consolidación Previa", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 8. MM20 pendiente (0–10, penaliza bajista)
    pts, det, col = _factor_mm20_pendiente(df)
    desglose["mm20_pendiente"] = {"nombre": "Pendiente MM20", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 9. Velas alcistas consecutivas (0–10)
    pts, det, col = _factor_velas_alcistas(df)
    desglose["velas_alcistas"] = {"nombre": "Velas Alcistas", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 10. Sin resistencia próxima (0–10)
    pts, det, col = _factor_resistencia_proxima(df, precio_actual)
    desglose["resistencia_proxima"] = {"nombre": "Resistencias Superiores", "puntos": pts, "detalle": det, "color": col}
    total += pts

    return _construir_resultado(total, 130, desglose, "BREAKOUT")


# ─────────────────────────────────────────────────────────────
# PULLBACK (10 factores, máx 100 pts brutos → normalizado 0–100)
# ─────────────────────────────────────────────────────────────

def _confirmaciones_pullback(df: pd.DataFrame, señal: dict) -> dict:
    total    = 0
    desglose = {}

    precio_actual = señal.get("precio_actual", 0)

    # 1. Soporte cercano (0–25) — factor más crítico en pullback
    dist_sop = señal.get("dist_soporte_pct", señal.get("distancia_soporte_pct", 5))
    if   dist_sop <= 1.0: pts, det, col = 25, f"✅ EN soporte ({dist_sop:.1f}%)",         "positivo"
    elif dist_sop <= 2.0: pts, det, col = 20, f"✅ Muy cerca soporte ({dist_sop:.1f}%)",  "positivo"
    elif dist_sop <= 3.5: pts, det, col = 15, f"Cerca soporte ({dist_sop:.1f}%)",         "positivo"
    elif dist_sop <= 5.0: pts, det, col =  8, f"Moderado ({dist_sop:.1f}%)",              "neutro"
    else:                 pts, det, col =  0, f"⚠️ Lejos del soporte ({dist_sop:.1f}%)", "negativo"
    desglose["soporte_cercano"] = {"nombre": "Soporte Cercano", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 2. RSI sobreventa (0–20) — criterio inverso al breakout
    rsi = señal.get("rsi", 50)
    if   rsi <= 30:  pts, det, col = 20, f"✅ Sobreventa fuerte ({rsi:.1f})",    "positivo"
    elif rsi <= 38:  pts, det, col = 17, f"✅ Sobreventa clara ({rsi:.1f})",     "positivo"
    elif rsi <= 45:  pts, det, col = 12, f"RSI bajo ({rsi:.1f})",               "positivo"
    elif rsi <= 50:  pts, det, col =  6, f"RSI aceptable ({rsi:.1f})",          "neutro"
    else:            pts, det, col =  0, f"❌ RSI alto ({rsi:.1f})",            "negativo"
    desglose["rsi_sobreventa"] = {"nombre": "RSI Sobreventa", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 3. Retroceso desde máximo (0–15)
    ret = señal.get("retroceso_pct", 0)
    if   8  <= ret <= 12: pts, det, col = 15, f"✅ Retroceso ideal ({ret:.1f}%)",    "positivo"
    elif 5  <= ret < 8:   pts, det, col = 10, f"Retroceso bueno ({ret:.1f}%)",      "positivo"
    elif 12 < ret <= 15:  pts, det, col = 10, f"Retroceso profundo ({ret:.1f}%)",   "neutro"
    elif 15 < ret <= 20:  pts, det, col =  5, f"Retroceso muy profundo ({ret:.1f}%)", "neutro"
    else:                 pts, det, col =  0, f"Retroceso fuera de rango ({ret:.1f}%)", "negativo"
    desglose["retroceso"] = {"nombre": "Retroceso desde Máximo", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 4. Tendencia macro MM200 (0–15)
    pts, det, col = _factor_tendencia_mm200(df, precio_actual)
    desglose["tendencia_macro"] = {"nombre": "Tendencia MM200", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 5. Volumen decreciente en caída (0–10)
    pts, det, col = _factor_volumen_decreciente(df)
    desglose["volumen_decreciente"] = {"nombre": "Volumen en Caída", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 6. ATR normal (0–5) — no queremos expansión en pullback
    pts, det, col = _factor_atr_normal(df)
    desglose["atr"] = {"nombre": "ATR (Volatilidad)", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 7. MM20 pendiente (0–5)
    pts, det, col = _factor_mm20_pendiente(df, max_pts=5)
    desglose["mm20_pendiente"] = {"nombre": "Pendiente MM20", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 8. Velas de agotamiento bajista (0–5)
    pts, det, col = _factor_velas_agotamiento(df)
    desglose["velas_agotamiento"] = {"nombre": "Agotamiento Bajista", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 9. Precio vs MM50 (0–5)
    pts, det, col = _factor_precio_mm50(df, precio_actual)
    desglose["precio_mm50"] = {"nombre": "Precio vs MM50", "puntos": pts, "detalle": det, "color": col}
    total += pts

    # 10. Historial de soporte (0–5 bonus)
    pts = min(5, señal.get("setup_score", 0))
    det = f"Setup score base: {señal.get('setup_score', 0)}"
    col = "positivo" if pts >= 4 else "neutro"
    desglose["setup_base"] = {"nombre": "Setup Score Base", "puntos": pts, "detalle": det, "color": col}
    total += pts

    return _construir_resultado(total, 110, desglose, "PULLBACK")


# ─────────────────────────────────────────────────────────────
# FACTORES COMPARTIDOS
# ─────────────────────────────────────────────────────────────

def _factor_atr_expansion(df: pd.DataFrame) -> tuple:
    if "ATR" not in df.columns or len(df) < 20:
        return 0, "No disponible", "neutro"
    atr_hoy  = float(df["ATR"].iloc[-1])
    atr_med  = float(df["ATR"].rolling(20).mean().iloc[-1])
    ratio    = atr_hoy / atr_med if atr_med > 0 else 1.0
    if   ratio >= 1.25: return 10, f"✅ Expansión fuerte ({ratio:.2f}x)",   "positivo"
    elif ratio >= 1.15: return  7, f"✅ Expansión moderada ({ratio:.2f}x)", "positivo"
    elif ratio >= 1.05: return  3, f"Ligera expansión ({ratio:.2f}x)",      "neutro"
    return 0, f"Sin expansión ({ratio:.2f}x)", "neutro"


def _factor_atr_normal(df: pd.DataFrame) -> tuple:
    if "ATR" not in df.columns or len(df) < 20:
        return 3, "No disponible", "neutro"
    atr_hoy = float(df["ATR"].iloc[-1])
    atr_med = float(df["ATR"].rolling(20).mean().iloc[-1])
    ratio   = atr_hoy / atr_med if atr_med > 0 else 1.0
    if   ratio <= 1.1:  return 5, f"✅ Volatilidad normal ({ratio:.2f}x)",     "positivo"
    elif ratio <= 1.25: return 2, f"Volatilidad elevada ({ratio:.2f}x)",        "neutro"
    return 0, f"⚠️ Volatilidad alta ({ratio:.2f}x)", "negativo"


def _factor_macd(df: pd.DataFrame) -> tuple:
    if "MACD" not in df.columns or len(df) < 3:
        return 0, "No disponible", "neutro"
    hist_hoy  = float(df["MACD_HIST"].iloc[-1])  if "MACD_HIST"  in df.columns else 0
    hist_prev = float(df["MACD_HIST"].iloc[-2])  if "MACD_HIST"  in df.columns else 0
    macd_hoy  = float(df["MACD"].iloc[-1])
    señal_hoy = float(df["MACD_SEÑAL"].iloc[-1]) if "MACD_SEÑAL" in df.columns else 0
    if macd_hoy > señal_hoy and hist_hoy > hist_prev and hist_hoy > 0:
        return 10, "✅ MACD alcista acelerando", "positivo"
    elif macd_hoy > señal_hoy:
        return  6, "MACD alcista",              "positivo"
    elif hist_hoy > hist_prev:
        return  3, "MACD mejorando",            "neutro"
    return 0, "MACD bajista", "negativo"


def _factor_mm20_pendiente(df: pd.DataFrame, max_pts: int = 10) -> tuple:
    if "MM20" not in df.columns or len(df) < 6:
        return 0, "No disponible", "neutro"
    mm20_hoy  = float(df["MM20"].iloc[-1])
    mm20_prev = float(df["MM20"].iloc[-5])
    pend      = ((mm20_hoy - mm20_prev) / mm20_prev) * 100 if mm20_prev > 0 else 0
    escala    = max_pts / 10
    if   pend >= 1.5:  return int(10 * escala), f"✅ Fuerte alcista ({pend:+.1f}%)",   "positivo"
    elif pend >= 0.5:  return int(7  * escala), f"✅ Alcista ({pend:+.1f}%)",           "positivo"
    elif pend >= 0.0:  return int(3  * escala), f"Plana ({pend:+.1f}%)",               "neutro"
    return 0, f"❌ Bajista ({pend:+.1f}%)", "negativo"


def _factor_velas_alcistas(df: pd.DataFrame) -> tuple:
    if len(df) < 5 or "Open" not in df.columns:
        return 0, "No disponible", "neutro"
    verdes = 0
    for i in range(1, min(6, len(df) + 1)):
        c = float(df["Close"].iloc[-i])
        o = float(df["Open"].iloc[-i])
        if c > o:
            verdes += 1
        else:
            break
    if   verdes >= 4: return 10, f"✅ {verdes} velas alcistas seguidas", "positivo"
    elif verdes >= 3: return  7, f"✅ {verdes} velas alcistas",          "positivo"
    elif verdes >= 2: return  3, f"{verdes} velas alcistas",             "neutro"
    return 0, "Pocas velas alcistas", "neutro"


def _factor_velas_agotamiento(df: pd.DataFrame) -> tuple:
    """Detecta velas pequeñas o de agotamiento bajista (doji, mecha larga abajo)."""
    if len(df) < 3 or "Open" not in df.columns:
        return 0, "No disponible", "neutro"
    ultima = df.iloc[-1]
    cuerpo = abs(float(ultima["Close"]) - float(ultima["Open"]))
    rango  = float(ultima["High"]) - float(ultima["Low"])
    if rango == 0:
        return 0, "Sin datos", "neutro"
    cuerpo_pct = cuerpo / rango
    if cuerpo_pct <= 0.25:
        return 5, "✅ Doji / agotamiento detectado", "positivo"
    elif cuerpo_pct <= 0.4:
        return 3, "Vela pequeña (posible giro)", "neutro"
    return 0, "Sin señal de agotamiento", "neutro"


def _factor_resistencia_proxima(df: pd.DataFrame, precio_actual: float) -> tuple:
    if len(df) < 30:
        return 5, "Histórico insuficiente", "neutro"
    resistencias = []
    for i in range(5, len(df) - 5):
        ventana = df["High"].iloc[i - 5: i + 6]
        valor   = float(df["High"].iloc[i])
        if valor == float(ventana.max()) and valor > precio_actual * 1.03:
            resistencias.append(valor)
    if not resistencias:
        return 10, "✅ Sin resistencias próximas", "positivo"
    distancia = ((min(resistencias) - precio_actual) / precio_actual) * 100
    if   distancia >= 10: return  7, f"Resistencia lejana (+{distancia:.1f}%)", "positivo"
    elif distancia >= 5:  return  3, f"Resistencia a +{distancia:.1f}%",        "neutro"
    return 0, f"⚠️ Resistencia cerca (+{distancia:.1f}%)", "negativo"


def _factor_tendencia_mm200(df: pd.DataFrame, precio_actual: float) -> tuple:
    if "MM200" not in df.columns:
        return 5, "MM200 no disponible", "neutro"
    mm200 = float(df["MM200"].iloc[-1])
    if pd.isna(mm200):
        return 5, "MM200 no disponible", "neutro"
    dist = ((precio_actual - mm200) / mm200) * 100
    if   dist >= 5:   return 15, f"✅ Muy sobre MM200 (+{dist:.1f}%)",  "positivo"
    elif dist >= 0:   return 10, f"✅ Sobre MM200 (+{dist:.1f}%)",      "positivo"
    elif dist >= -5:  return  5, f"Cerca MM200 ({dist:.1f}%)",          "neutro"
    return 0, f"⚠️ Bajo MM200 ({dist:.1f}%)", "negativo"


def _factor_precio_mm50(df: pd.DataFrame, precio_actual: float) -> tuple:
    if "MM50" not in df.columns:
        return 2, "MM50 no disponible", "neutro"
    mm50 = float(df["MM50"].iloc[-1])
    if pd.isna(mm50):
        return 2, "MM50 no disponible", "neutro"
    dist = ((precio_actual - mm50) / mm50) * 100
    if   dist >= 0:  return 5, f"✅ Sobre MM50 (+{dist:.1f}%)",  "positivo"
    elif dist >= -5: return 2, f"Cerca MM50 ({dist:.1f}%)",      "neutro"
    return 0, f"Bajo MM50 ({dist:.1f}%)", "negativo"


def _factor_volumen_decreciente(df: pd.DataFrame) -> tuple:
    if "Volume" not in df.columns or len(df) < 10:
        return 3, "No disponible", "neutro"
    vol_reciente = float(df["Volume"].tail(5).mean())
    vol_anterior = float(df["Volume"].tail(10).head(5).mean())
    if vol_anterior == 0:
        return 3, "Sin referencia", "neutro"
    ratio = vol_reciente / vol_anterior
    if   ratio <= 0.7:  return 10, f"✅ Volumen muy decreciente ({ratio:.2f}x)", "positivo"
    elif ratio <= 0.85: return  7, f"✅ Volumen decreciente ({ratio:.2f}x)",     "positivo"
    elif ratio <= 1.0:  return  4, f"Volumen estable ({ratio:.2f}x)",            "neutro"
    return 0, f"⚠️ Volumen creciente en caída ({ratio:.2f}x)", "negativo"


# ─────────────────────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────────────────────

def _construir_resultado(total: int, max_bruto: int, desglose: dict, tipo: str) -> dict:
    normalizada = max(0, min(100, int((total / max_bruto) * 100)))

    if   normalizada >= 75: nivel, rec, color = "EXCELENTE", "🟢 COMPRA PRIORITARIA",      "success"
    elif normalizada >= 60: nivel, rec, color = "BUENO",     "🟢 COMPRA",                  "success"
    elif normalizada >= 45: nivel, rec, color = "ACEPTABLE", "🟡 COMPRA CONDICIONAL",       "warning"
    elif normalizada >= 30: nivel, rec, color = "DUDOSO",    "🟠 ESPERAR MEJOR MOMENTO",    "warning"
    else:                   nivel, rec, color = "MALO",      "🔴 NO OPERAR",                "danger"

    return {
        "puntuacion":       normalizada,
        "puntuacion_bruta": total,
        "nivel":            nivel,
        "recomendacion":    rec,
        "color":            color,
        "desglose":         desglose,
        "tipo_estrategia":  tipo,
    }
