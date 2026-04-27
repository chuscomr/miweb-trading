"""
analisis/tecnico/canales_tendencia.py
══════════════════════════════════════════════════════════════
CANALES Y LÍNEAS DE TENDENCIA AUTOMÁTICAS

Metodología correcta:
  Línea alcista  → une 2 mínimos relevantes SIN que el precio
                   cruce la línea por debajo entre ellos
  Línea bajista  → une 2 máximos relevantes SIN que el precio
                   cruce la línea por encima entre ellos
  Canal          → línea de tendencia + paralela al nivel opuesto
  Canal lateral  → soporte/resistencia horizontal validado

Algoritmo:
  1. Detectar pivots (mínimos/máximos locales con rebote real)
  2. Para cada par de pivots (más reciente primero):
     a. Trazar recta entre los dos puntos
     b. Verificar que ninguna vela entre ellos viola la línea
     c. Si es válida → dibujar y parar
  3. Canal = línea base + paralela desplazada al pivot opuesto
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

MIN_SEPARACION_PIVOTS = 8    # velas mínimas entre dos pivots
MIN_REBOTE_PCT        = 1.5  # % mínimo de rebote tras el pivot
TOLERANCIA_VIOLACION  = 0.3  # % tolerancia para "cruce" (filtrar ruido)
N_VELAS_ANALISIS      = 120  # ventana de análisis por defecto


def detectar_canales_tendencia(df: pd.DataFrame,
                                n_velas: int = N_VELAS_ANALISIS) -> dict:
    """
    Punto de entrada principal.
    Detecta la mejor línea de tendencia alcista y/o bajista
    usando pivots validados, y construye el canal si es posible.
    """
    resultado = {
        "shapes":      [],
        "annotations": [],
        "tendencia":   None,
        "angulo":      0.0,
        "resumen":     "",
        "canales":     [],
    }

    try:
        if df is None or len(df) < 30:
            return resultado

        df_v   = df.tail(n_velas).copy().reset_index()
        closes = df_v["Close"].values.astype(float)
        highs  = df_v["High"].values.astype(float)
        lows   = df_v["Low"].values.astype(float)
        fechas = [str(d)[:10] for d in df_v.iloc[:, 0]]
        n      = len(closes)

        # ── Detectar pivots ──────────────────────────────────
        orden       = max(5, n // 18)
        pivots_min  = _pivots_validados(lows,  highs, closes, orden, "min")
        pivots_max  = _pivots_validados(highs, lows,  closes, orden, "max")

        shapes      = []
        annotations = []
        canales     = []

        # ── Línea de tendencia alcista ───────────────────────
        lt_alc = _mejor_linea_tendencia(
            pivots_min, lows, fechas, n,
            tipo="alcista",
            precio_actual=float(closes[-1])
        )
        if lt_alc:
            shapes.append(lt_alc["shape"])
            annotations.append(lt_alc["annotation"])
            canales.append({"tipo": "tendencia_alcista",
                            "descripcion": lt_alc["descripcion"]})

            # Canal alcista: paralela superior por el máximo entre los pivots
            canal_alc = _canal_paralelo(
                lt_alc, highs, fechas, n, "alcista"
            )
            if canal_alc:
                shapes.append(canal_alc["shape"])
                annotations.append(canal_alc["annotation"])
                canales.append({"tipo": "canal_alcista",
                                "descripcion": canal_alc["descripcion"],
                                "amplitud_pct": canal_alc["amplitud_pct"]})

        # ── Línea de tendencia bajista ───────────────────────
        lt_baj = _mejor_linea_tendencia(
            pivots_max, highs, fechas, n,
            tipo="bajista",
            precio_actual=float(closes[-1])
        )
        if lt_baj:
            shapes.append(lt_baj["shape"])
            annotations.append(lt_baj["annotation"])
            canales.append({"tipo": "tendencia_bajista",
                            "descripcion": lt_baj["descripcion"]})

            # Canal bajista: paralela inferior por el mínimo entre los pivots
            canal_baj = _canal_paralelo(
                lt_baj, lows, fechas, n, "bajista"
            )
            if canal_baj:
                shapes.append(canal_baj["shape"])
                annotations.append(canal_baj["annotation"])
                canales.append({"tipo": "canal_bajista",
                                "descripcion": canal_baj["descripcion"],
                                "amplitud_pct": canal_baj["amplitud_pct"]})

        # ── Canal lateral (si no hay líneas inclinadas claras) ─
        if not lt_alc and not lt_baj:
            canal_lat = _canal_lateral(
                pivots_min, pivots_max, lows, highs, fechas, closes[-1]
            )
            if canal_lat:
                shapes.extend(canal_lat["shapes"])
                annotations.extend(canal_lat["annotations"])
                canales.append({"tipo": "canal_lateral",
                                "descripcion": canal_lat["descripcion"],
                                "amplitud_pct": canal_lat["amplitud_pct"]})

        # ── Tendencia general ────────────────────────────────
        if lt_alc and not lt_baj:
            tendencia = "alcista"
        elif lt_baj and not lt_alc:
            tendencia = "bajista"
        elif lt_alc and lt_baj:
            tendencia = "compresión"  # cuña/triángulo
        else:
            tendencia = "lateral"

        resultado.update({
            "shapes":      shapes,
            "annotations": annotations,
            "tendencia":   tendencia,
            "canales":     canales,
            "resumen":     " · ".join(c["descripcion"] for c in canales)
                           if canales else f"Tendencia {tendencia} sin estructura definida",
        })

    except Exception as e:
        logger.warning(f"detectar_canales_tendencia: {e}")

    return resultado


# ─────────────────────────────────────────────────────────────
# PIVOTS VALIDADOS — mínimo/máximo local con rebote real
# ─────────────────────────────────────────────────────────────

def _pivots_validados(serie_pivot, serie_opuesta, closes,
                      orden, tipo) -> list:
    """
    Detecta pivots locales que tienen rebote real posterior.

    Un pivot mínimo válido:
    - Es el mínimo local en una ventana de 'orden' velas
    - El precio rebota al menos MIN_REBOTE_PCT después

    Devuelve lista de índices ordenados de más antiguo a más reciente.
    """
    pivots = []
    n = len(serie_pivot)

    for i in range(orden, n - orden):
        ventana = serie_pivot[i - orden: i + orden + 1]

        if tipo == "min" and serie_pivot[i] != ventana.min():
            continue
        if tipo == "max" and serie_pivot[i] != ventana.max():
            continue

        # Verificar rebote posterior
        post = serie_opuesta[i + 1: min(i + orden + 1, n)]
        if len(post) == 0:
            continue

        precio_pivot = serie_pivot[i]
        if precio_pivot <= 0:
            continue

        if tipo == "min":
            rebote = (post.max() - precio_pivot) / precio_pivot * 100
        else:
            rebote = (precio_pivot - post.min()) / precio_pivot * 100

        if rebote >= MIN_REBOTE_PCT:
            pivots.append(i)

    return pivots


# ─────────────────────────────────────────────────────────────
# MEJOR LÍNEA DE TENDENCIA — algoritmo de validación
# ─────────────────────────────────────────────────────────────

def _mejor_linea_tendencia(pivots, serie, fechas, n,
                            tipo, precio_actual) -> dict | None:
    """
    Busca la mejor línea de tendencia entre pares de pivots.

    Para cada par (más reciente → más antiguo):
    1. La recta debe ser inclinada correctamente
       (alcista: pendiente positiva, bajista: negativa)
    2. Ninguna vela entre los dos pivots viola la línea
       (con tolerancia TOLERANCIA_VIOLACION %)
    3. La línea debe estar cerca del precio actual
       (máx 15% de distancia) para ser relevante

    Devuelve la primera válida encontrada.
    """
    if len(pivots) < 2:
        return None

    # Iterar pares de más recientes a más antiguos
    for i in range(len(pivots) - 1, 0, -1):
        idx2 = pivots[i]        # más reciente
        for j in range(i - 1, -1, -1):
            idx1 = pivots[j]    # más antiguo

            # Separación mínima
            if idx2 - idx1 < MIN_SEPARACION_PIVOTS:
                continue

            v1 = float(serie[idx1])
            v2 = float(serie[idx2])

            # Pendiente correcta
            if tipo == "alcista" and v2 <= v1:
                continue
            if tipo == "bajista" and v2 >= v1:
                continue

            # Construir recta entre los dos pivots
            pendiente = (v2 - v1) / (idx2 - idx1)

            # Verificar que ninguna vela viola la línea entre idx1 e idx2
            valida = True
            for k in range(idx1 + 1, idx2):
                valor_linea = v1 + pendiente * (k - idx1)
                tolerancia  = valor_linea * (TOLERANCIA_VIOLACION / 100)
                if tipo == "alcista" and serie[k] < valor_linea - tolerancia:
                    valida = False
                    break
                if tipo == "bajista" and serie[k] > valor_linea + tolerancia:
                    valida = False
                    break

            if not valida:
                continue

            # Extender la línea hasta el final del gráfico
            y_final = v1 + pendiente * (n - 1 - idx1)

            # Relevancia: la línea debe estar cerca del precio actual
            dist_pct = abs(y_final - precio_actual) / precio_actual * 100
            if dist_pct > 20:
                continue

            # Pendiente razonable (no más de 40% en el período)
            pend_total = (y_final - v1) / v1 * 100 if v1 > 0 else 0
            if abs(pend_total) > 40:
                continue

            # ── Línea válida encontrada ──────────────────────
            color = "#22c55e" if tipo == "alcista" else "#ef4444"
            emoji = "↗" if tipo == "alcista" else "↘"
            label = "Tendencia alcista" if tipo == "alcista" else "Tendencia bajista"

            # Dibujar desde idx1 hasta el final
            y0 = float(v1)
            y1 = float(y_final)

            return {
                "shape": {
                    "type":  "line",
                    "x0":    fechas[idx1],
                    "x1":    fechas[n - 1],
                    "y0":    round(y0, 4),
                    "y1":    round(y1, 4),
                    "line":  {"color": color, "width": 1.8, "dash": "solid"},
                    "name":  f"tendencia_{tipo}",
                    "xref":  "x", "yref": "y", "layer": "below",
                },
                "annotation": {
                    "x":         fechas[n - 1],
                    "y":         round(y1, 4),
                    "text":      f"{emoji} {label}",
                    "font":      {"size": 10, "color": color},
                    "showarrow": False,
                    "xanchor":   "right",
                    "yshift":    8,
                    "bgcolor":   f"rgba({'34,197,94' if tipo == 'alcista' else '239,68,68'},0.12)",
                    "xref": "x", "yref": "y",
                },
                "descripcion": label,
                "idx1": idx1, "idx2": idx2,
                "pendiente": pendiente,
                "v1": v1,
            }

    return None


# ─────────────────────────────────────────────────────────────
# CANAL PARALELO — línea opuesta paralela a la tendencia
# ─────────────────────────────────────────────────────────────

def _canal_paralelo(lt, serie_opuesta, fechas, n, tipo) -> dict | None:
    """
    Construye la línea paralela del canal.
    - Canal alcista: línea superior paralela por los máximos entre los pivots
    - Canal bajista: línea inferior paralela por los mínimos entre los pivots

    La paralela pasa por el punto más extremo entre idx1 e idx2.
    """
    try:
        idx1      = lt["idx1"]
        idx2      = lt["idx2"]
        pendiente = lt["pendiente"]
        v1        = lt["v1"]

        # Encontrar el punto más extremo de la serie opuesta entre los pivots
        segmento = serie_opuesta[idx1:idx2 + 1]
        if len(segmento) == 0:
            return None

        if tipo == "alcista":
            idx_ext   = idx1 + int(np.argmax(segmento))
            val_ext   = float(segmento.max())
        else:
            idx_ext   = idx1 + int(np.argmin(segmento))
            val_ext   = float(segmento.min())

        # Desplazamiento = diferencia entre el punto extremo y la línea base en ese punto
        val_linea_base = v1 + pendiente * (idx_ext - idx1)
        despl          = val_ext - val_linea_base

        # Puntos de la paralela
        y0_par = v1 + despl                           # inicio
        y1_par = v1 + pendiente * (n - 1 - idx1) + despl  # fin

        if y0_par <= 0 or y1_par <= 0:
            return None

        # Amplitud del canal (en el punto medio)
        y_base_mid = v1 + pendiente * ((n - 1 - idx1) / 2)
        y_par_mid  = y_base_mid + despl
        amplitud_pct = abs(y_par_mid - y_base_mid) / y_base_mid * 100 if y_base_mid > 0 else 0

        if amplitud_pct < 1.5 or amplitud_pct > 35:
            return None

        color  = "#22c55e" if tipo == "alcista" else "#ef4444"
        label  = f"Canal {'alcista' if tipo == 'alcista' else 'bajista'} ({round(amplitud_pct, 1)}%)"

        return {
            "shape": {
                "type": "line",
                "x0":   fechas[idx1],
                "x1":   fechas[n - 1],
                "y0":   round(float(y0_par), 4),
                "y1":   round(float(y1_par), 4),
                "line": {"color": color, "width": 1.2, "dash": "dash"},
                "name": f"canal_{tipo}_par",
                "xref": "x", "yref": "y", "layer": "below",
            },
            "annotation": {
                "x":         fechas[n - 1],
                "y":         round(float(y1_par), 4),
                "text":      label,
                "font":      {"size": 9, "color": color},
                "showarrow": False,
                "xanchor":   "right",
                "yshift":    8,
                "bgcolor":   f"rgba({'34,197,94' if tipo == 'alcista' else '239,68,68'},0.08)",
                "xref": "x", "yref": "y",
            },
            "descripcion":  label,
            "amplitud_pct": round(amplitud_pct, 1),
        }
    except Exception as e:
        logger.debug(f"_canal_paralelo: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# CANAL LATERAL — soporte/resistencia horizontal
# ─────────────────────────────────────────────────────────────

def _canal_lateral(pivots_min, pivots_max, lows, highs,
                   fechas, precio_actual) -> dict | None:
    """
    Canal horizontal cuando no hay tendencia inclinada clara.
    Usa los últimos 4-6 pivots mínimos y máximos.
    """
    try:
        if len(pivots_min) < 2 or len(pivots_max) < 2:
            return None

        # Mínimos y máximos recientes
        min_recientes = lows[np.array(pivots_min[-5:])]
        max_recientes = highs[np.array(pivots_max[-5:])]

        nivel_sop = float(np.median(min_recientes))
        nivel_res = float(np.median(max_recientes))

        if nivel_sop >= nivel_res or nivel_sop <= 0:
            return None

        amplitud = (nivel_res - nivel_sop) / nivel_sop * 100

        # Canal demasiado estrecho o demasiado amplio
        if amplitud < 3.0 or amplitud > 25.0:
            return None

        # Precio debe estar dentro del canal
        if precio_actual < nivel_sop * 0.95 or precio_actual > nivel_res * 1.05:
            return None

        x0f = fechas[0]
        x1f = fechas[-1]

        return {
            "shapes": [
                {"type": "line", "x0": x0f, "x1": x1f,
                 "y0": round(nivel_sop, 4), "y1": round(nivel_sop, 4),
                 "line": {"color": "#3b82f6", "width": 1.5, "dash": "dot"},
                 "name": "canal_lat_sop", "xref": "x", "yref": "y", "layer": "below"},
                {"type": "line", "x0": x0f, "x1": x1f,
                 "y0": round(nivel_res, 4), "y1": round(nivel_res, 4),
                 "line": {"color": "#3b82f6", "width": 1.5, "dash": "dot"},
                 "name": "canal_lat_res", "xref": "x", "yref": "y", "layer": "below"},
            ],
            "annotations": [
                {"x": x1f, "y": round(nivel_sop, 4), "text": "Soporte canal",
                 "font": {"size": 9, "color": "#3b82f6"}, "showarrow": False,
                 "xanchor": "right", "yshift": -10,
                 "bgcolor": "rgba(59,130,246,0.08)", "xref": "x", "yref": "y"},
                {"x": x1f, "y": round(nivel_res, 4), "text": "Resistencia canal",
                 "font": {"size": 9, "color": "#3b82f6"}, "showarrow": False,
                 "xanchor": "right", "yshift": 8,
                 "bgcolor": "rgba(59,130,246,0.08)", "xref": "x", "yref": "y"},
            ],
            "descripcion":  f"Canal lateral ({round(amplitud, 1)}% amplitud)",
            "amplitud_pct": round(amplitud, 1),
        }
    except Exception as e:
        logger.debug(f"_canal_lateral: {e}")
        return None
