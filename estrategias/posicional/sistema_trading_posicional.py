# ==========================================================
# SISTEMA TRADING POSICIONAL
# Evaluador completo de señales de entrada
# ==========================================================

import yfinance as yf
import pandas as pd
import numpy as np

# Imports flexibles
try:
    from .logica_posicional import *
    from .config_posicional import *
    from .datos_posicional import obtener_precio_tiempo_real
except ImportError:
    from logica_posicional import *
    from config_posicional import *
    from datos_posicional import obtener_precio_tiempo_real


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 EVALUADOR PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluar_entrada_posicional(precios, volumenes=None, fechas=None, df=None, usar_filtro_mercado=True, df_ibex=None):
    """
    Evaluador completo para entrada en sistema posicional.
    
    ESTRATEGIA POSICIONAL:
    1. Tendencia alcista FUERTE (precio > MM50 > MM200)
    2. Consolidación de 3-6 meses
    3. Breakout de máximos confirmado
    4. Volumen creciente
    5. Riesgo 8-15%
    
    Args:
        precios: lista de precios semanales
        volumenes: lista de volúmenes semanales (opcional)
        fechas: lista de fechas (opcional)
        df: DataFrame completo (opcional, más preciso)
    
    Returns:
        dict con decisión y detalles
    """
    motivos_rechazo = []
    detalles = {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VALIDACIONES PREVIAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if precios is None or len(precios) < MIN_SEMANAS_HISTORICO:
        return {
            "decision": "NO_OPERAR",
            "motivos": [f"Histórico insuficiente (<{MIN_SEMANAS_HISTORICO} semanas)"],
            "detalles": {}
        }
    
    precio_actual = precios[-1]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚨 FILTRO CRÍTICO: MERCADO ALCISTA IBEX
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if usar_filtro_mercado:
        try:
            import pandas as pd

            # Usar df_ibex pre-descargado si está disponible, si no descargar
            if df_ibex is not None and not df_ibex.empty:
                datos_ibex = df_ibex
            else:
                ibex_obj = yf.Ticker("^IBEX")
                datos_ibex = ibex_obj.history(period="1y", interval="1d")
                if not datos_ibex.empty and datos_ibex.index.tz is not None:
                    datos_ibex.index = datos_ibex.index.tz_localize(None)
                if isinstance(datos_ibex.columns, pd.MultiIndex):
                    datos_ibex.columns = datos_ibex.columns.get_level_values(0)

            if isinstance(datos_ibex, pd.DataFrame) and len(datos_ibex) >= 200:
                # Filtrar datos hasta la fecha actual del backtest si tenemos fechas
                close_col = datos_ibex['Close']
                if fechas is not None and len(fechas) > 0:
                    fecha_vela = pd.Timestamp(fechas[-1])
                    close_col = close_col[close_col.index <= fecha_vela]
                    if len(close_col) < 200:
                        close_col = datos_ibex['Close']  # fallback sin filtro

                mm200_ibex = float(close_col.rolling(200).mean().iloc[-1])
                precio_ibex = float(close_col.iloc[-1])

                detalles["mercado_ibex"] = "ALCISTA" if precio_ibex > mm200_ibex else "BAJISTA"
                detalles["precio_ibex"] = round(precio_ibex, 2)
                detalles["mm200_ibex"] = round(mm200_ibex, 2)

                if precio_ibex < mm200_ibex:
                    return {
                        "decision": "NO_OPERAR",
                        "motivos": ["🚫 IBEX por debajo de MM200 - Mercado bajista general"],
                        "detalles": detalles
                    }
        except Exception as e:
            print(f"⚠️ Advertencia: No se pudo verificar mercado IBEX ({e}). Continuando análisis...")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 1: TENDENCIA ALCISTA FUERTE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_tendencia = detectar_tendencia_largo_plazo(precios, df)
    cond_tend = analisis_tendencia.get("condiciones", {})
    detalles.update({
        "tendencia":            analisis_tendencia["tendencia"],
        "mm50":                 round(analisis_tendencia["mm50"], 2) if analisis_tendencia.get("mm50") else None,
        "mm200":                round(analisis_tendencia["mm200"], 2) if analisis_tendencia.get("mm200") else None,
        "distancia_mm50_pct":   round(analisis_tendencia["distancia_mm50_pct"], 2) if analisis_tendencia.get("distancia_mm50_pct") else None,
        "pendiente_mm50":       round(analisis_tendencia["pendiente_mm50"], 2) if analisis_tendencia.get("pendiente_mm50") else None,
        # Condiciones individuales para el score
        "mm50_sobre_mm200":     cond_tend.get("mm50_sobre_mm200", False),
        "precio_sobre_mm50":    cond_tend.get("precio_sobre_mm50", False),
        "pendiente_positiva":   cond_tend.get("pendiente_positiva", False),
        "no_sobreextendido":    cond_tend.get("no_sobreextendido", True),
    })
    
    if not analisis_tendencia.get("cumple_criterios", False):
        if analisis_tendencia["tendencia"] != "ALCISTA":
            motivos_rechazo.append(f"Tendencia {analisis_tendencia['tendencia'].lower()}")
        else:
            condiciones = analisis_tendencia.get("condiciones", {})
            if not condiciones.get("distancia_suficiente"):
                motivos_rechazo.append(f"Precio muy cerca de MM50 ({detalles['distancia_mm50_pct']}%)")
            if not condiciones.get("pendiente_positiva"):
                motivos_rechazo.append("MM50 sin pendiente alcista")
    else:
        # Tendencia alcista — avisar si sobreextendido (no bloquea)
        condiciones = analisis_tendencia.get("condiciones", {})
        if not condiciones.get("no_sobreextendido"):
            dist = detalles.get("distancia_mm50_pct", 0)
            detalles["aviso_sobreextendido"] = f"Precio {dist:.1f}% sobre MM50 — entrada con precaución"
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 2: CONSOLIDACIÓN PREVIA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Buscar la MEJOR consolidación (no la primera)
    # Score interno: semanas largas + rango estrecho + posición alta en rango
    consolidacion_encontrada = False
    mejor_consolidacion = None
    mejor_score_consol = -1

    for lookback in range(CONSOLIDACION_MIN_SEMANAS, CONSOLIDACION_MAX_SEMANAS + 1, 4):
        if len(precios) < lookback:
            continue
        analisis_consol = detectar_consolidacion(precios, lookback_max=lookback)
        if analisis_consol["en_consolidacion"]:
            # Score interno: más semanas mejor, rango más estrecho mejor, posición alta
            s = (lookback / CONSOLIDACION_MAX_SEMANAS) * 40        # semanas
            s += max(0, (CONSOLIDACION_MAX_RANGO_PCT - analisis_consol["rango_pct"]) / CONSOLIDACION_MAX_RANGO_PCT) * 40  # estrechez
            s += (analisis_consol.get("posicion_en_rango", 50) / 100) * 20  # posición alta
            if s > mejor_score_consol:
                mejor_score_consol = s
                mejor_consolidacion = analisis_consol
                consolidacion_encontrada = True
    
    if mejor_consolidacion:
        detalles.update({
            "consolidacion": True,
            "consolidacion_semanas": mejor_consolidacion["semanas_consolidacion"],
            "consolidacion_rango_pct": round(mejor_consolidacion["rango_pct"], 1),
            "posicion_en_rango": round(mejor_consolidacion["posicion_en_rango"], 1)
        })
    else:
        detalles["consolidacion"] = False
        # No es requisito estricto, pero resta puntos
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 3: BREAKOUT DE MÁXIMOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_breakout = detectar_breakout(precios, volumenes, lookback=26)
    detalles.update({
        "breakout": analisis_breakout["hay_breakout"],
        "breakout_distancia_pct": round(analisis_breakout.get("distancia_breakout_pct", 0), 2),
        "breakout_volumen_ratio": round(analisis_breakout.get("ratio_volumen", 1), 2)
    })
    
    if not analisis_breakout["hay_breakout"]:
        motivos_rechazo.append("Sin breakout de máximos")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 4: VOLATILIDAD SUFICIENTE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    volatilidad = calcular_volatilidad(precios, periodo=52)
    detalles["volatilidad_pct"] = round(volatilidad, 1) if volatilidad else None

    if volatilidad and volatilidad < MIN_VOLATILIDAD_PCT:
        motivos_rechazo.append(f"Volatilidad baja ({volatilidad:.1f}%)")
    if volatilidad and volatilidad > MAX_VOLATILIDAD_PCT:
        motivos_rechazo.append(f"Volatilidad excesiva ({volatilidad:.1f}% > {MAX_VOLATILIDAD_PCT}%)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SI HAY RECHAZOS → NO OPERAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if motivos_rechazo:
        return {
            "decision": "NO_OPERAR",
            "motivos": motivos_rechazo,
            "detalles": detalles
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR TRIGGER DE ENTRADA Y STOP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Trigger = máximo de los últimos 26 semanas + 0.1%
    # Orden stop-limit que se activa al superar la resistencia
    maximo_26 = analisis_breakout.get("maximo_previo", precio_actual)
    trigger   = round(maximo_26 * 1.001, 4)   # +0.1% sobre el máximo

    # Si el precio ya superó el trigger (breakout en curso), entrada = precio actual
    # Si no, la entrada es el trigger (orden pendiente)
    if precio_actual >= trigger:
        entrada = precio_actual
    else:
        entrada = trigger

    detalles["trigger"]    = trigger
    detalles["maximo_26"]  = round(maximo_26, 4)

    stop = calcular_stop_inicial(entrada, precios, df)
    
    # Validar riesgo
    validacion_riesgo = validar_riesgo(entrada, stop)
    detalles.update({
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2)
    })
    
    if not validacion_riesgo["riesgo_valido"]:
        return {
            "decision": "NO_OPERAR",
            "motivos": [validacion_riesgo["motivo"]],
            "detalles": detalles
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ SEÑAL DE COMPRA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    motivos_compra = [
        "Tendencia alcista fuerte",
        f"Breakout confirmado (+{detalles['breakout_distancia_pct']}%)",
        f"Trigger entrada: {trigger:.2f}€ (máx. 26sem {maximo_26:.2f}€ +0.1%)"
    ]
    
    if mejor_consolidacion:
        motivos_compra.append(f"Consolidación previa ({mejor_consolidacion['semanas_consolidacion']} semanas)")
    
    if analisis_breakout.get("volumen_confirma"):
        motivos_compra.append(f"Volumen confirmación ({detalles['breakout_volumen_ratio']:.1f}x)")
    
    return {
        "decision": "COMPRA",
        "trigger":  round(trigger, 2),
        "entrada":  round(entrada, 2),
        "stop":     round(stop, 2),
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2),
        "detalles": detalles,
        "motivos": motivos_compra
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 EVALUADOR CON SCORING (para escáneres)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_fuerza_relativa_pos(precios_ticker, precios_ibex, semanas=26):
    """Fuerza relativa del ticker vs IBEX en últimas N semanas."""
    if precios_ibex is None or len(precios_ticker) < semanas or len(precios_ibex) < semanas:
        return 0, "SIN_DATOS"
    rend_tick = (precios_ticker[-1] / precios_ticker[-semanas] - 1) * 100
    rend_ibex = (precios_ibex[-1]   / precios_ibex[-semanas]   - 1) * 100
    diff = round(rend_tick - rend_ibex, 1)
    if diff >= 10:    cat = "LIDERA"
    elif diff >= -5:  cat = "NEUTRAL"
    else:             cat = "DÉBIL"
    return diff, cat


def calcular_score_posicional(detalles, fr_diff=0, fr_cat="SIN_DATOS"):
    """
    Score 0-100 para señales posicionales.

    25 — Tendencia de fondo
    25 — Calidad de consolidación  ⭐
    15 — Fuerza relativa vs IBEX   ⭐
    10 — Breakout / cercanía máximos
    10 — Volumen
    10 — Distancia a MM50
     5 — Volatilidad
    """
    score_desglose = {}

    # 1. TENDENCIA — 25 pts
    tend    = detalles.get("tendencia", "")
    pend    = detalles.get("pendiente_mm50", 0) or 0
    mm50_ok = detalles.get("mm50_sobre_mm200", False)
    if tend == "ALCISTA" and mm50_ok and abs(pend) >= 10:
        pts_t, desc_t = 25, f"MM50>MM200 + pendiente fuerte ({pend:+.1f}%)"
    elif tend == "ALCISTA" and mm50_ok:
        pts_t, desc_t = 15, f"MM50>MM200 + pendiente moderada ({pend:+.1f}%)"
    elif tend == "ALCISTA":
        pts_t, desc_t = 5, "Alineación débil"
    else:
        pts_t, desc_t = 0, "No cumple tendencia"
    score_desglose["tendencia"] = (pts_t, 25, desc_t)

    # 2. CONSOLIDACIÓN — 25 pts ⭐
    consol  = detalles.get("consolidacion", False)
    sem_c   = detalles.get("consolidacion_semanas", 0) or 0
    rango_c = detalles.get("consolidacion_rango_pct", 0) or 0
    if consol and sem_c >= 16 and rango_c <= 12:
        pts_c, desc_c = 25, f"Base sólida {sem_c}sem rango {rango_c}%"
    elif consol and sem_c >= 12 and rango_c <= 18:
        pts_c, desc_c = 18, f"Base aceptable {sem_c}sem rango {rango_c}%"
    elif consol:
        pts_c, desc_c = 10, f"Base amplia {sem_c}sem rango {rango_c}%"
    else:
        pts_c, desc_c = 0, "Sin consolidación previa"
    score_desglose["consolidacion"] = (pts_c, 25, desc_c)

    # 3. FUERZA RELATIVA — 15 pts ⭐
    if fr_cat == "LIDERA":
        pts_fr, desc_fr = 15, f"Lidera al IBEX ({fr_diff:+.1f}pp)"
    elif fr_cat == "NEUTRAL":
        pts_fr, desc_fr = 8,  f"Neutral vs IBEX ({fr_diff:+.1f}pp)"
    elif fr_cat == "DÉBIL":
        pts_fr, desc_fr = 0,  f"Rezagado vs IBEX ({fr_diff:+.1f}pp)"
    else:
        pts_fr, desc_fr = 4,  "Sin datos IBEX"
    score_desglose["fuerza_relativa"] = (pts_fr, 15, desc_fr)

    # 4. BREAKOUT / CERCANÍA MÁXIMOS — 10 pts
    hay_bk  = detalles.get("breakout", False)
    dist_bk = detalles.get("breakout_distancia_pct", -99) or -99
    if hay_bk and dist_bk >= 0:
        pts_bk, desc_bk = 10, f"Breakout limpio (+{dist_bk:.1f}%)"
    elif dist_bk >= -3:
        pts_bk, desc_bk = 6,  f"Muy cerca de máximos ({dist_bk:.1f}%)"
    elif dist_bk >= -8:
        pts_bk, desc_bk = 3,  f"Cerca de máximos ({dist_bk:.1f}%)"
    else:
        pts_bk, desc_bk = 0,  f"Lejos de máximos ({dist_bk:.1f}%)"
    score_desglose["breakout"] = (pts_bk, 10, desc_bk)

    # 5. VOLUMEN — 10 pts
    vol_r = detalles.get("breakout_volumen_ratio", 1) or 1
    if vol_r >= 1.5:
        pts_v, desc_v = 10, f"Volumen fuerte ({vol_r:.1f}x)"
    elif vol_r >= 1.0:
        pts_v, desc_v = 5,  f"Volumen normal ({vol_r:.1f}x)"
    else:
        pts_v, desc_v = 0,  f"Volumen débil ({vol_r:.1f}x)"
    score_desglose["volumen"] = (pts_v, 10, desc_v)

    # 6. DISTANCIA A MM50 — 10 pts
    dist_mm50 = detalles.get("distancia_mm50_pct", 0) or 0
    if 5 <= dist_mm50 <= 20:
        pts_d, desc_d = 10, f"Zona óptima ({dist_mm50:+.1f}%)"
    elif 20 < dist_mm50 <= 35:
        pts_d, desc_d = 5,  f"Algo extendido ({dist_mm50:+.1f}%)"
    elif dist_mm50 > 35:
        pts_d, desc_d = 0,  f"Muy extendido ({dist_mm50:+.1f}%)"
    else:
        pts_d, desc_d = 3,  f"Cerca o bajo MM50 ({dist_mm50:+.1f}%)"
    score_desglose["distancia_mm50"] = (pts_d, 10, desc_d)

    # 7. VOLATILIDAD — 5 pts
    vol_anual = detalles.get("volatilidad_pct", None)
    if vol_anual is None:
        pts_va, desc_va = 2, "Sin datos"
    elif 25 <= vol_anual <= 50:
        pts_va, desc_va = 5, f"Óptima ({vol_anual:.1f}%)"
    elif 20 <= vol_anual < 25:
        pts_va, desc_va = 3, f"Aceptable ({vol_anual:.1f}%)"
    elif vol_anual > 50:
        pts_va, desc_va = 2, f"Alta ({vol_anual:.1f}%)"
    else:
        pts_va, desc_va = 0, f"Baja ({vol_anual:.1f}%)"
    score_desglose["volatilidad"] = (pts_va, 5, desc_va)

    total = sum(v[0] for v in score_desglose.values())

    # Clasificación
    if total >= 80:   clasificacion = "EXCELENTE"
    elif total >= 60: clasificacion = "BUENO"
    elif total >= 40: clasificacion = "MEDIOCRE"
    else:             clasificacion = "DÉBIL"

    return total, 100, clasificacion, score_desglose


def evaluar_con_scoring(precios, volumenes=None, fechas=None, df=None,
                        precios_ibex=None):
    """
    Evaluador con score 0-100 (nuevo sistema).
    Incluye fuerza relativa si se pasa precios_ibex semanal.
    """
    resultado = evaluar_entrada_posicional(precios, volumenes, fechas, df)
    detalles  = resultado.get("detalles", {})

    # Calcular fuerza relativa
    fr_diff, fr_cat = calcular_fuerza_relativa_pos(precios, precios_ibex)
    detalles["fr_diff"] = fr_diff
    detalles["fr_cat"]  = fr_cat

    # Calcular score 0-100
    score, max_score, clasificacion, desglose = calcular_score_posicional(
        detalles, fr_diff, fr_cat
    )

    resultado["setup_score"]    = score
    resultado["setup_max"]      = max_score
    resultado["clasificacion"]  = clasificacion
    resultado["score_desglose"] = desglose

    # Umbral: solo COMPRA si score >= 60
    if resultado["decision"] == "COMPRA" and score < 60:
        resultado["decision"]    = "NO_OPERAR"
        resultado["clasificacion"] = "DÉBIL"
        resultado["motivos"]     = [f"Score insuficiente ({score}/100)"]

    # Preservar campos esperados por generar_reporte_completo
    if "entrada" not in resultado: resultado["entrada"]    = 0
    if "stop"    not in resultado: resultado["stop"]       = 0
    if "riesgo_pct" not in resultado:
        resultado["riesgo_pct"] = detalles.get("riesgo_pct", 0)

    return resultado


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 ANÁLISIS DETALLADO (para UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generar_reporte_completo(ticker, precios, volumenes=None, fechas=None, df=None):
    """
    Genera reporte completo para mostrar en UI.
    
    El precio mostrado es SIEMPRE el precio en tiempo real (intradía),
    no el último cierre semanal. El análisis técnico sigue usando
    los datos semanales históricos.
    
    Returns:
        dict con toda la información formateada
    """
    resultado = evaluar_con_scoring(precios, volumenes, fechas, df)
    
    # ─── Precio en tiempo real ────────────────────────────────
    precio_rt = obtener_precio_tiempo_real(ticker)
    
    if precio_rt:
        precio_mostrar   = precio_rt['precio']
        precio_hora      = precio_rt['hora']
        precio_fecha     = precio_rt['fecha']
        precio_variacion = precio_rt['variacion_pct']
        precio_anterior  = precio_rt['cierre_anterior']
        precio_fuente    = precio_rt['fuente']
    else:
        precio_mostrar   = round(float(precios[-1]), 2)
        precio_hora      = '--'
        precio_fecha     = '--'
        precio_variacion = 0.0
        precio_anterior  = precio_mostrar
        precio_fuente    = 'semanal'
    
    score       = resultado.get("setup_score", 0)
    score_max   = resultado.get("setup_max", 100)
    clasificacion = resultado.get("clasificacion", "N/A")
    desglose    = resultado.get("score_desglose", {})
    fr_diff     = resultado.get("detalles", {}).get("fr_diff", 0)
    fr_cat      = resultado.get("detalles", {}).get("fr_cat", "SIN_DATOS")

    # Etiqueta visual del score
    if score >= 80:   score_label = "🟢 EXCELENTE"
    elif score >= 60: score_label = "🟡 BUENO"
    elif score >= 40: score_label = "🟠 MEDIOCRE"
    else:             score_label = "🔴 DÉBIL"

    reporte = {
        "ticker":            ticker,
        "precio_actual":     precio_mostrar,
        "precio_hora":       precio_hora,
        "precio_fecha":      precio_fecha,
        "precio_variacion":  precio_variacion,
        "precio_anterior":   precio_anterior,
        "precio_fuente":     precio_fuente,
        "precio_semanal":    round(float(precios[-1]), 2),
        "decision":          resultado["decision"],
        "clasificacion":     clasificacion,
        "score":             score,
        "score_max":         score_max,
        "score_label":       score_label,
        "score_desglose":    desglose,
        "fuerza_relativa":   fr_cat,
        "fr_diferencial":    fr_diff,
    }
    
    # Si hay señal de compra
    if resultado["decision"] == "COMPRA":
        reporte.update({
            "trigger":           resultado.get("trigger", resultado["entrada"]),
            "entrada":           resultado["entrada"],
            "stop":              resultado["stop"],
            "riesgo_pct":        resultado["riesgo_pct"],
            "objetivo_r":        "10-30R",
            "duracion_estimada": "6-24 meses",
            "maximo_26":         resultado.get("detalles", {}).get("maximo_26", 0),
        })
    
    # Detalles técnicos
    reporte["detalles"] = resultado.get("detalles", {})
    reporte["motivos"]  = resultado.get("motivos", [])
    
    return reporte


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test sistema_trading_posicional.py")
    print("=" * 60)
    
    # Simular tendencia alcista con consolidación y breakout
    import numpy as np
    
    # 200 semanas tendencia alcista
    base = [100 + i*0.8 for i in range(200)]
    
    # 26 semanas consolidando
    consolidacion = [base[-1] + np.random.uniform(-3, 3) for _ in range(26)]
    
    # Breakout
    breakout = [consolidacion[-1] + i*2 for i in range(5)]
    
    precios_test = base + consolidacion + breakout
    volumenes_test = [1000000 + np.random.uniform(-200000, 400000) for _ in range(len(precios_test))]
    # Volumen mayor en breakout
    volumenes_test[-5:] = [v * 2 for v in volumenes_test[-5:]]
    
    print(f"\n📊 Datos simulados:")
    print(f"   Total semanas: {len(precios_test)}")
    print(f"   Precio actual: {precios_test[-1]:.2f}")
    print(f"   Precio hace 26 semanas: {precios_test[-26]:.2f}")
    print(f"   Precio hace 200 semanas: {precios_test[-200]:.2f}")
    
    print(f"\n🔍 Evaluando señal...")
    resultado = evaluar_entrada_posicional(precios_test, volumenes_test)
    
    print(f"\n🎯 RESULTADO:")
    print(f"   Decisión: {resultado['decision']}")
    
    if resultado['decision'] == 'COMPRA':
        print(f"   Entrada: {resultado['entrada']:.2f}")
        print(f"   Stop: {resultado['stop']:.2f}")
        print(f"   Riesgo: {resultado['riesgo_pct']:.1f}%")
        print(f"\n   Motivos:")
        for motivo in resultado['motivos']:
            print(f"   ✓ {motivo}")
    else:
        print(f"\n   Motivos rechazo:")
        for motivo in resultado['motivos']:
            print(f"   ✗ {motivo}")
    
    print(f"\n📋 Detalles:")
    for k, v in resultado.get('detalles', {}).items():
        print(f"   {k}: {v}")
    
    # Test scoring
    print(f"\n📊 Test con scoring:")
    resultado_scoring = evaluar_con_scoring(precios_test, volumenes_test)
    print(f"   Score: {resultado_scoring['setup_score']}/{resultado_scoring['setup_max']}")
    print(f"   Clasificación: {resultado_scoring['clasificacion']}")
    
    print("\n" + "=" * 60)
