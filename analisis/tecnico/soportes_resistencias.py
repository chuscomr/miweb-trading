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

    # Pasar índices para calcular separación temporal entre toques
    resistencias = _agrupar_niveles(niveles_resistencia, tolerancia_pct, min_toques,
                                    indices=maximos_idx)
    soportes     = _agrupar_niveles(niveles_soporte,     tolerancia_pct, min_toques,
                                    indices=minimos_idx)

    precio_actual = float(closes[-1])

    # Filtrar por posición vs precio actual
    resistencias = [r for r in resistencias if r["nivel"] > precio_actual]
    soportes     = [s for s in soportes     if s["nivel"] < precio_actual]

    # Ordenar por cercanía al precio — el más cercano primero
    soportes     = sorted(soportes,     key=lambda x: (precio_actual - x["nivel"]))
    resistencias = sorted(resistencias, key=lambda x: (x["nivel"] - precio_actual))

    # Mostrar solo los N más cercanos — independiente de la distancia
    # Así funciona igual para valores volátiles y poco volátiles
    N_SOPORTES     = 5  # los 5 soportes más cercanos por debajo
    N_RESISTENCIAS = 3  # las 3 resistencias más cercanas por encima

    analisis = _analizar_posicion_precio(precio_actual, soportes, resistencias)

    return {
        "soportes":      soportes[:N_SOPORTES],
        "resistencias":  resistencias[:N_RESISTENCIAS],
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

def _extremos_locales(serie: np.ndarray, orden: int, tipo: str,
                      rebote_min_pct: float = 2.0) -> np.ndarray:
    """
    Detecta toques reales — no solo extremos locales.

    Un toque válido requiere:
    1. Precio llega a zona (mínimo/máximo local)
    2. Reacción posterior mínima de rebote_min_pct (2%)
    3. No es vela consecutiva del toque anterior (separación ≥ orden/2)
    """
    indices = []
    ultimo_idx = -999

    for i in range(orden, len(serie) - orden):
        ventana = serie[i - orden: i + orden + 1]

        es_extremo = False
        if tipo == "max" and serie[i] == ventana.max():
            es_extremo = True
        elif tipo == "min" and serie[i] == ventana.min():
            es_extremo = True

        if not es_extremo:
            continue

        # Separación temporal — no contar toques consecutivos
        if i - ultimo_idx < max(3, orden // 2):
            continue

        # Reacción posterior mínima
        precio_toque = serie[i]
        if precio_toque <= 0:
            continue

        ventana_post = serie[i+1: min(i + orden + 1, len(serie))]
        if len(ventana_post) == 0:
            indices.append(i)
            ultimo_idx = i
            continue

        if tipo == "min":
            # Para soporte: debe haber rebote alcista posterior
            rebote = (ventana_post.max() - precio_toque) / precio_toque * 100
        else:
            # Para resistencia: debe haber caída posterior
            rebote = (precio_toque - ventana_post.min()) / precio_toque * 100

        if rebote >= rebote_min_pct:
            indices.append(i)
            ultimo_idx = i

    return np.array(indices, dtype=int)


def _agrupar_niveles(niveles: np.ndarray, tolerancia_pct: float, min_toques: int,
                     indices: np.ndarray = None) -> list:
    """
    Agrupa niveles de precio en zonas con recuento de toques reales.
    Incorpora separación temporal para calcular fuerza correctamente.
    """
    if len(niveles) == 0:
        return []

    # Ordenar por precio manteniendo índices temporales si disponibles
    if indices is not None and len(indices) == len(niveles):
        orden = np.argsort(niveles)
        niveles_sorted = niveles[orden]
        indices_sorted  = indices[orden]
    else:
        niveles_sorted = np.sort(niveles)
        indices_sorted  = None

    grupos = []
    i = 0

    while i < len(niveles_sorted):
        nivel_actual = niveles_sorted[i]
        grupo_precios = [nivel_actual]
        grupo_indices = [indices_sorted[i]] if indices_sorted is not None else []
        j = i + 1

        while j < len(niveles_sorted):
            dif_pct = abs((niveles_sorted[j] - nivel_actual) / nivel_actual) * 100
            if dif_pct <= tolerancia_pct:
                grupo_precios.append(niveles_sorted[j])
                if indices_sorted is not None:
                    grupo_indices.append(indices_sorted[j])
                j += 1
            else:
                break

        if len(grupo_precios) >= min_toques:
            # Dispersión temporal — toques muy juntos son más débiles
            if len(grupo_indices) >= 2:
                separacion_media = np.mean(np.diff(sorted(grupo_indices)))
            else:
                separacion_media = 0

            grupos.append({
                "nivel":             round(float(np.mean(grupo_precios)), 2),
                "toques":            len(grupo_precios),
                "separacion_media":  round(float(separacion_media), 0),
                "fuerza":            _calcular_fuerza_avanzada(len(grupo_precios), separacion_media),
            })

        i = j if j > i + 1 else i + 1

    return grupos


def _calcular_fuerza(toques: int) -> str:
    if toques >= 5:
        return "FUERTE"
    elif toques >= 3:
        return "MEDIO"
    return "DÉBIL"


def _calcular_fuerza_avanzada(toques: int, separacion_media: float) -> str:
    """
    Fuerza real = f(toques, tiempo entre toques)

    3 toques en 2 velas  → DÉBIL  (probablemente el mismo movimiento)
    3 toques en 10 velas → MEDIO
    3 toques en 30 velas → FUERTE (respeto institucional confirmado)
    5+ toques bien separados → MUY FUERTE
    """
    if toques >= 5 and separacion_media >= 10:
        return "MUY FUERTE"
    elif toques >= 3 and separacion_media >= 20:
        return "FUERTE"
    elif toques >= 3 and separacion_media >= 8:
        return "MEDIO"
    elif toques >= 2 and separacion_media >= 5:
        return "DÉBIL"
    else:
        return "MUY DÉBIL"  # toques muy juntos = mismo impulso, no soporte real


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


# ══════════════════════════════════════════════════════════════
# EVALUADOR S/R PARA SCORING — Medio Plazo y Posicional
# ══════════════════════════════════════════════════════════════

def evaluar_sr(df: pd.DataFrame, periodo: int = 20, timeframe: str = "diario") -> dict:
    """
    Evaluador S/R para scoring — Medio Plazo y Posicional.

    3 funciones independientes con suma Y resta:

    1. SOPORTE EN PULLBACK
       ≥3 toques bien separados → +1.5
       2 toques bien separados  → +1.0
       Pierde soporte           → INVALIDAR

    2. CALIDAD DEL BREAKOUT (resistencia recién superada)
       ≥3 toques → +1.5
       2 toques  → +0.5
       Usa la resistencia rota — espacio usa la SIGUIENTE (sin doble contabilización)

    3. ESPACIO LIBRE hasta la SIGUIENTE resistencia
       >10%                          → +1.0
       5-10%                         → 0
       <5% con resistencia FUERTE    → -2.0
       <5% con resistencia DÉBIL     → -1.0
    """
    resultado = {
        "soporte_valido":        False,
        "soporte_toques":        0,
        "soporte_dist_pct":      None,
        "soporte_nivel":         None,
        "soporte_fuerza":        None,
        "resistencia_fuerte":    False,
        "resistencia_toques":    0,
        "espacio_libre_pct":     None,
        "resistencia_siguiente": None,
        "score_sr":              0.0,
        "invalidar":             False,
        "resumen":               "",
    }

    try:
        p  = periodo if timeframe == "diario" else max(10, periodo // 2)
        sr = detectar_soportes_resistencias(df, periodo=p, tolerancia_pct=2.0, min_toques=2)

        precio   = sr["precio_actual"]
        soportes = sr["soportes"]
        resists  = sr["resistencias"]
        score    = 0.0
        partes   = []

        # ── 1. SOPORTE EN PULLBACK ───────────────────────────────
        soporte_cercano = soportes[0] if soportes else None
        if soporte_cercano:
            dist   = (precio - soporte_cercano["nivel"]) / precio * 100
            toques = soporte_cercano["toques"]
            fuerza = soporte_cercano.get("fuerza", "DÉBIL")
            sep    = soporte_cercano.get("separacion_media", 0)

            resultado.update({
                "soporte_nivel":    soporte_cercano["nivel"],
                "soporte_toques":   toques,
                "soporte_dist_pct": round(dist, 1),
                "soporte_fuerza":   fuerza,
            })

            if dist < 0:
                # Precio por debajo del soporte → estructura rota
                resultado["invalidar"] = True
                partes.append(f"⚠️ Precio bajo soporte {soporte_cercano['nivel']}€ → INVALIDAR")
            elif dist <= 3.0 and fuerza not in ("MUY DÉBIL",):
                resultado["soporte_valido"] = True
                pts = 1.5 if toques >= 3 and sep >= 8 else 1.0
                score += pts
                partes.append(f"Soporte {soporte_cercano['nivel']}€ ({toques}t sep={int(sep)}v {fuerza}) +{pts}")
            else:
                partes.append(f"Soporte {soporte_cercano['nivel']}€ ({dist:.1f}% — lejos o débil)")

        # ── 2. CALIDAD DEL BREAKOUT ──────────────────────────────
        # Resistencia recién superada (precio cerca de ella ±2%)
        # La siguiente resistencia se usará para el espacio libre (sin doble contabilización)
        resist_rota   = None
        resist_idx    = None
        for idx, r in enumerate(resists):
            dist_r = (r["nivel"] - precio) / precio * 100
            if -2.0 <= dist_r <= 3.0:
                resist_rota = r
                resist_idx  = idx
                break

        if resist_rota:
            toques_r = resist_rota["toques"]
            fuerza_r = resist_rota.get("fuerza", "DÉBIL")
            sep_r    = resist_rota.get("separacion_media", 0)
            # Ajuste 2: umbral temporal mínimo 8 velas (~2 meses semanal)
            # 3 toques en 3 semanas = ruido · 3 toques en 3 meses = nivel real
            sep_minima = 8  # velas mínimas entre toques para nivel válido
            nivel_temporal_ok = sep_r >= sep_minima
            resultado["resistencia_fuerte"] = toques_r >= 3 and nivel_temporal_ok
            resultado["resistencia_toques"] = toques_r
            if toques_r >= 3 and nivel_temporal_ok:
                score += 1.5
                partes.append(f"Breakout resistencia fuerte {resist_rota['nivel']}€ ({toques_r}t sep={int(sep_r)}v) +1.5")
            elif toques_r >= 3 and not nivel_temporal_ok:
                # Toques demasiado juntos — nivel poco fiable
                score += 0.5
                partes.append(f"Breakout resistencia reciente {resist_rota['nivel']}€ ({toques_r}t sep={int(sep_r)}v — toques juntos) +0.5")
            elif toques_r >= 2 and nivel_temporal_ok:
                score += 0.5
                partes.append(f"Breakout resistencia débil {resist_rota['nivel']}€ ({toques_r}t sep={int(sep_r)}v) +0.5")
            # 2 toques sin separación temporal → no puntúa (ruido)

            # Espacio usa la SIGUIENTE resistencia (no la recién rota)
            siguiente_resist = resists[resist_idx + 1] if resist_idx is not None and resist_idx + 1 < len(resists) else None
        else:
            # No hay resistencia rota — espacio desde la primera
            siguiente_resist = resists[0] if resists else None

        # ── 3. ESPACIO LIBRE hasta siguiente resistencia ─────────
        # Umbral relativo a la volatilidad del activo (ATR%)
        # BBVA con ATR 1.5% → umbral libre = 1.5 * 1.5 = 2.25%
        # Solaria con ATR 4% → umbral libre = 4 * 1.5 = 6%
        # Evita que 10% fijo sea demasiado exigente para valores volátiles
        # y demasiado laxo para valores estables
        try:
            highs_arr = df["High"].values
            lows_arr  = df["Low"].values
            closes_arr = df["Close"].values
            n_atr = min(14, len(closes_arr) - 1)
            trs = [max(highs_arr[i]-lows_arr[i],
                       abs(highs_arr[i]-closes_arr[i-1]),
                       abs(lows_arr[i]-closes_arr[i-1]))
                   for i in range(len(closes_arr)-n_atr, len(closes_arr))]
            atr_pct = (sum(trs)/len(trs) / precio * 100) if trs and precio > 0 else 2.0
        except Exception:
            atr_pct = 2.0  # fallback

        umbral_libre = max(atr_pct * 1.5, 3.0)   # mínimo 3% siempre
        umbral_justo = max(atr_pct * 0.8, 1.5)   # zona de peligro

        if siguiente_resist:
            espacio = (siguiente_resist["nivel"] - precio) / precio * 100
            fuerza_sig = siguiente_resist.get("fuerza", "DÉBIL")
            resultado["espacio_libre_pct"]     = round(espacio, 1)
            resultado["resistencia_siguiente"] = siguiente_resist["nivel"]

            if espacio > umbral_libre:
                score += 1.0
                partes.append(f"Espacio libre {espacio:.1f}% > {umbral_libre:.1f}% (1.5×ATR) +1.0")
            elif espacio < umbral_justo:
                # Penalización según fuerza de la resistencia que bloquea
                if fuerza_sig in ("FUERTE", "MUY FUERTE"):
                    score -= 2.0
                    partes.append(f"⛔ Resistencia fuerte próxima {siguiente_resist['nivel']}€ ({espacio:.1f}%) -2.0")
                else:
                    score -= 1.0
                    partes.append(f"⚠️ Resistencia débil próxima {siguiente_resist['nivel']}€ ({espacio:.1f}%) -1.0")
            else:
                partes.append(f"Espacio neutro {espacio:.1f}% (umbral {umbral_libre:.1f}%)")
        else:
            # Sin resistencias → recorrido libre total
            score += 1.0
            resultado["espacio_libre_pct"] = 99.0
            partes.append("Sin resistencias detectadas → espacio libre +1.0")

        resultado["score_sr"] = round(score, 1)
        resultado["resumen"]  = " | ".join(partes)

    except Exception as e:
        logger.warning(f"evaluar_sr error: {e}")
        resultado["resumen"] = f"Error S/R: {e}"

    return resultado
