# ==========================================================
# LÓGICA TÉCNICA - SISTEMA MEDIO PLAZO
# Indicadores y análisis técnico para timeframe semanal
# ==========================================================

import numpy as np
import pandas as pd
from .config_medio import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 INDICADORES TÉCNICOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_atr_semanal(df, periodo=ATR_PERIODO):
    """
    Calcula ATR (Average True Range) sobre datos semanales.
    
    Args:
        df: DataFrame con OHLC
        periodo: ventana para el ATR (default: 14 semanas)
    
    Returns:
        float: ATR actual o None si no hay suficientes datos
    """
    if df is None or len(df) < periodo + 1:
        return None
    
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    # True Range
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR = media del TR
    atr = tr.rolling(periodo).mean()
    
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else None


def calcular_atr_desde_listas(precios, periodo=ATR_PERIODO):
    """
    Versión simplificada de ATR solo con cierres (para listas).
    Menos preciso pero funcional.
    
    Args:
        precios: lista de precios de cierre semanales
        periodo: ventana para el ATR
    
    Returns:
        float: ATR aproximado
    """
    if len(precios) < periodo + 1:
        return None
    
    precios = np.array(precios, dtype=float)
    
    # Rangos semanales (aproximación)
    rangos = np.abs(np.diff(precios))
    
    # Media de rangos
    atr = np.mean(rangos[-periodo:])
    
    return atr


def calcular_mm(precios, periodo):
    """
    Calcula media móvil simple.
    
    Args:
        precios: array/lista de precios
        periodo: ventana
    
    Returns:
        float: MM actual o None
    """
    if len(precios) < periodo:
        return None
    
    return np.mean(precios[-periodo:])


def calcular_volatilidad(precios, ventana=52):
    """
    Calcula volatilidad anualizada en %.
    
    Args:
        precios: lista/array de precios semanales
        ventana: semanas a considerar (default: 52 = 1 año)
    
    Returns:
        float: volatilidad en %
    """
    if len(precios) < ventana:
        ventana = len(precios)
    
    if ventana < 10:
        return None
    
    precios = np.array(precios[-ventana:])
    
    # Desviación estándar / media
    volatilidad = (np.std(precios) / np.mean(precios)) * 100
    
    return volatilidad


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 ANÁLISIS DE TENDENCIA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_tendencia_semanal(precios):
    """
    Detecta tendencia usando medias móviles semanales.
    Doble confirmación: MM20↑ + MM50 > MM200

    Returns:
        dict con:
        - tendencia: "ALCISTA", "BAJISTA", "NEUTRAL"
        - mm10, mm20, mm40, mm50, mm200: valores de las MMs
        - precio_vs_mm20: relación precio/MM20 en %
        - mm50_sobre_mm200: bool — filtro de calidad de tendencia
    """
    if len(precios) < MM_TENDENCIA_LARGA:
        return {"tendencia": "INSUFICIENTE"}

    precio = precios[-1]
    mm10 = calcular_mm(precios, MM_TENDENCIA_CORTA)
    mm20 = calcular_mm(precios, MM_TENDENCIA_MEDIA)
    mm40 = calcular_mm(precios, MM_TENDENCIA_LARGA)

    # Calcular pendiente MM20 (últimas 4 semanas vs anteriores)
    mm20_actual = np.mean(precios[-20:])
    mm20_previa = np.mean(precios[-24:-4])
    pendiente_mm20 = mm20_actual - mm20_previa

    # Filtro calidad tendencia: MM50 > MM200
    mm50 = calcular_mm(precios, MM_FILTRO_TENDENCIA) if len(precios) >= MM_FILTRO_TENDENCIA else None
    mm200 = calcular_mm(precios, MM_FILTRO_LARGO) if len(precios) >= MM_FILTRO_LARGO else None
    mm50_sobre_mm200 = (mm50 is not None and mm200 is not None and mm50 > mm200)

    # Determinar tendencia — estructura alcista aunque precio esté en pullback bajo MM20
    # Clave: durante un pullback válido el precio PUEDE estar bajo MM20
    # Lo que importa es la estructura macro: MM20↑ + MM50 > MM200
    if pendiente_mm20 > 0 and mm50_sobre_mm200:
        tendencia = "ALCISTA"   # estructura alcista, precio puede estar en pullback
    elif precio < mm20 and pendiente_mm20 < 0:
        tendencia = "BAJISTA"
    else:
        tendencia = "NEUTRAL"

    precio_vs_mm20 = ((precio - mm20) / mm20) * 100 if mm20 else None

    return {
        "tendencia":        tendencia,
        "mm10":             mm10,
        "mm20":             mm20,
        "mm40":             mm40,
        "mm50":             mm50,
        "mm200":            mm200,
        "precio_vs_mm20":   precio_vs_mm20,
        "pendiente_mm20":   pendiente_mm20,
        "mm50_sobre_mm200": mm50_sobre_mm200,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 DETECCIÓN DE PULLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_pullback(precios, lookback=LOOKBACK_MAXIMO):
    """
    Detecta si hay un pullback válido.
    Rango 5-8%: evita ruido (3%) y correcciones profundas (12%).

    Returns:
        dict con:
        - es_pullback: bool
        - maximo_reciente: float
        - retroceso_pct: float
        - semanas_desde_max: int
    """
    if len(precios) < lookback:
        return {"es_pullback": False, "motivo": "Histórico insuficiente"}

    precio_actual = precios[-1]
    ultimos_precios = precios[-lookback:]

    maximo_reciente = max(ultimos_precios)
    indice_max = len(ultimos_precios) - 1 - list(reversed(ultimos_precios)).index(maximo_reciente)
    semanas_desde_max = len(ultimos_precios) - 1 - indice_max

    retroceso_pct = ((maximo_reciente - precio_actual) / maximo_reciente) * 100

    es_pullback = PULLBACK_MIN_PCT <= retroceso_pct <= PULLBACK_MAX_PCT

    if retroceso_pct < PULLBACK_MIN_PCT:
        motivo = f"Retroceso insuficiente ({retroceso_pct:.1f}%) — mínimo {PULLBACK_MIN_PCT}%"
    elif retroceso_pct > PULLBACK_MAX_PCT:
        motivo = f"Retroceso excesivo ({retroceso_pct:.1f}%) — máximo {PULLBACK_MAX_PCT}%"
    else:
        motivo = f"Pullback válido ({retroceso_pct:.1f}%)"

    return {
        "es_pullback":      es_pullback,
        "maximo_reciente":  maximo_reciente,
        "retroceso_pct":    retroceso_pct,
        "semanas_desde_max": semanas_desde_max,
        "motivo":           motivo
    }


def detectar_giro_semanal(precios, highs=None):
    """
    Calcula el trigger de entrada para la sesión siguiente.

    Trigger = high de la semana actual × 1.001
    Si el precio supera ese nivel la semana siguiente → giro confirmado.

    Returns:
        dict con:
        - hay_giro: bool (precio actual ya superó el high anterior)
        - trigger: float (nivel Buy Stop para broker)
        - variacion_pct: float
    """
    if len(precios) < 2:
        return {"hay_giro": False, "trigger": None}

    precio_actual  = precios[-1]
    precio_anterior = precios[-2]
    variacion_pct  = ((precio_actual - precio_anterior) / precio_anterior) * 100

    # Trigger = high semana actual × 1.001
    high_actual = highs[-1] if highs is not None and len(highs) > 0 else precio_actual
    trigger = round(high_actual * 1.001, 2)

    return {
        "hay_giro":      precio_actual > precio_anterior,
        "trigger":       trigger,
        "variacion_pct": variacion_pct,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ CÁLCULO DE STOPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_stop_inicial(precio_entrada, precios, df=None, stop_atr_mult=None):
    """
    Stop = max(mínimo estructura × 0.98, entrada - ATR × 2)
    En semanal el stop por estructura tiende a quedar muy lejos —
    el ATR lo acerca y hace el riesgo más manejable.
    """
    lookback = min(STOP_ESTRUCTURA_LOOKBACK, len(precios))
    stop_estructura = min(precios[-lookback:]) * 0.98

    if df is not None:
        atr = calcular_atr_semanal(df)
    else:
        atr = calcular_atr_desde_listas(precios)

    if stop_atr_mult is None:
        stop_atr_mult = STOP_ATR_MULTIPLICADOR

    if atr:
        stop_atr = precio_entrada - (atr * stop_atr_mult)
        return max(stop_estructura, stop_atr)

    return stop_estructura


def validar_riesgo(entrada, stop):
    """
    Valida que el riesgo está en el rango aceptable.
    
    Returns:
        dict con:
        - riesgo_valido: bool
        - riesgo_pct: float
        - motivo: str
    """
    if stop >= entrada:
        return {
            "riesgo_valido": False,
            "riesgo_pct": 0,
            "motivo": "Stop >= entrada"
        }
    
    riesgo_pct = ((entrada - stop) / entrada) * 100
    
    if riesgo_pct < RIESGO_MIN_PCT:
        return {
            "riesgo_valido": False,
            "riesgo_pct": riesgo_pct,
            "motivo": f"Riesgo muy bajo ({riesgo_pct:.2f}%)"
        }
    
    if riesgo_pct > RIESGO_MAX_PCT:
        return {
            "riesgo_valido": False,
            "riesgo_pct": riesgo_pct,
            "motivo": f"Riesgo muy alto ({riesgo_pct:.2f}%)"
        }
    
    return {
        "riesgo_valido": True,
        "riesgo_pct": riesgo_pct,
        "motivo": "Riesgo dentro de rango"
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test logica_medio.py")
    print("=" * 50)
    
    # Datos de prueba
    precios_test = [10, 10.5, 11, 11.5, 12, 12.5, 13, 12, 11.5, 11, 10.8, 11.2]
    
    print("\n1️⃣ Tendencia:")
    tendencia = detectar_tendencia_semanal(precios_test + [0]*30)
    print(f"   {tendencia}")
    
    print("\n2️⃣ Pullback:")
    pullback = detectar_pullback(precios_test)
    print(f"   {pullback}")
    
    print("\n3️⃣ Giro:")
    giro = detectar_giro_semanal(precios_test)
    print(f"   {giro}")
    
    print("\n4️⃣ Stop:")
    stop = calcular_stop_inicial(11.2, precios_test)
    print(f"   Stop: {stop:.2f}")
    
    validacion = validar_riesgo(11.2, stop)
    print(f"   {validacion}")

# ══════════════════════════════════════════════════════════════
# CLASE WRAPPER — para compatibilidad con medio_routes.py
# ══════════════════════════════════════════════════════════════


def calcular_score_medio(precios, tendencia, pullback, df=None):
    """
    Score 0-10 alineado con los filtros reales del sistema.

    Criterios:
    - MM50 > MM200 (tendencia macro):        +3.0  obligatorio ya filtrado
    - MM20 pendiente positiva:               +1.0
    - Pullback 5-8% (óptimo):               +2.0  |  4-5% (válido): +1.0
    - RSI semanal 40-55 (zona pullback):     +1.5
    - Precio cerca MM20 ≤2% (+1.5) | ≤3% (+0.5)
    - Volumen decreciente en pullback:       +1.0
    Total máximo: 10.0
    """
    score = 0
    score_max = 10

    precio    = precios[-1] if precios else 0
    mm20      = tendencia.get("mm20", 0) or 0
    mm50      = tendencia.get("mm50", 0) or 0
    mm200     = tendencia.get("mm200", 0) or 0
    pendiente = tendencia.get("pendiente_mm20", 0) or 0
    mm50_ok   = tendencia.get("mm50_sobre_mm200", False)

    # 1. MM50 > MM200 — tendencia macro (+3.0)
    if mm50_ok:
        score += 3.0

    # 2. MM20 pendiente positiva (+1.0)
    if pendiente > 0:
        score += 1.0

    # 3. Calidad del pullback — variable escalonada (+0, +1, +2)
    retroceso = pullback.get("retroceso_pct", 0)
    if 5.0 <= retroceso <= 8.0:
        score += 2.0   # rango óptimo
    elif 4.0 <= retroceso < 5.0:
        score += 1.0   # válido pero zona baja

    # 4. RSI semanal 40-55 zona pullback sano (+1.5)
    rsi_val = None
    if len(precios) >= 15:
        try:
            deltas    = [precios[i]-precios[i-1] for i in range(1, min(15, len(precios)))]
            ganancias = [d for d in deltas if d > 0]
            perdidas  = [-d for d in deltas if d < 0]
            avg_g     = sum(ganancias)/14 if ganancias else 0
            avg_p     = sum(perdidas)/14  if perdidas  else 0.001
            rsi_val   = round(100-(100/(1+avg_g/avg_p)), 1)
            if 40 <= rsi_val <= 55:
                score += 1.5
        except Exception:
            pass

    # 5. Precio cerca de MM20 — timing de entrada
    #    ≤2% → muy buen timing (+1.5) | 2-3% → aceptable (+0.5)
    if mm20 > 0:
        dist_mm20 = abs(precio - mm20) / mm20 * 100
        if dist_mm20 <= 2.0:
            score += 1.5
        elif dist_mm20 <= 3.0:
            score += 0.5

    # 6. Volumen decreciente en pullback — confirma corrección sana (+1.0)
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            import numpy as _np
            vol_media  = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            if vol_actual < vol_media * 0.85:
                score += 1.0
        except Exception:
            pass

    return round(min(score, score_max), 1), score_max


def calcular_semaforo_medio(precios, tendencia, pullback, df=None):
    """
    Semáforo de prioridad para señales de medio plazo.
    No es un filtro — es un ranking de calidad cuando hay varias señales.

    Confirmaciones evaluadas:
    - RSI semanal 40-55
    - Volumen decreciente en pullback
    - Precio cerca MM20 (≤3%)

    🟢 Operar    — 3/3 confirmaciones
    🟡 En radar  — 2/3 confirmaciones
    🔴 Esperar   — 1/3 o menos
    """
    confirmaciones = []

    # RSI 40-55
    rsi_ok = False
    if len(precios) >= 15:
        try:
            deltas    = [precios[i]-precios[i-1] for i in range(1, min(15, len(precios)))]
            ganancias = [d for d in deltas if d > 0]
            perdidas  = [-d for d in deltas if d < 0]
            avg_g     = sum(ganancias)/14 if ganancias else 0
            avg_p     = sum(perdidas)/14  if perdidas  else 0.001
            rsi       = 100-(100/(1+avg_g/avg_p))
            rsi_ok    = 40 <= rsi <= 55
        except Exception:
            pass
    confirmaciones.append(("RSI 40-55 (zona pullback sano)", rsi_ok))

    # Volumen decreciente
    vol_ok = False
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            import numpy as _np
            vol_media  = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            vol_ok     = vol_actual < vol_media * 0.85
        except Exception:
            pass
    confirmaciones.append(("Volumen decreciente en pullback", vol_ok))

    # Precio cerca MM20 ≤3%
    mm20   = tendencia.get("mm20", 0) or 0
    precio = precios[-1] if precios else 0
    dist_ok = (mm20 > 0 and abs(precio - mm20) / mm20 * 100 <= 3.0)
    confirmaciones.append(("Precio cerca MM20 (≤3%)", dist_ok))

    n_ok = sum(1 for _, ok in confirmaciones if ok)

    if n_ok == 3:
        semaforo = {"color": "verde",    "emoji": "🟢", "texto": "Operar",   "n": n_ok}
    elif n_ok == 2:
        semaforo = {"color": "amarillo", "emoji": "🟡", "texto": "En radar", "n": n_ok}
    else:
        semaforo = {"color": "rojo",     "emoji": "🔴", "texto": "Esperar",  "n": n_ok}

    semaforo["confirmaciones"] = [{"texto": t, "ok": ok} for t, ok in confirmaciones]
    return semaforo


class MedioPlazo:
    """
    Wrapper OOP sobre las funciones de logica_medio.py.
    medio_routes.py llama: señal = _medio.evaluar(ticker, cache)
    """

    def evaluar(self, ticker: str, cache=None) -> dict:
        """
        Evalúa señal de medio plazo:
          1. Tendencia macro: MM20↑ + MM50 > MM200
          2. Pullback válido 5-8% en últimas 10 semanas
          3. RSI semanal > 45
          4. Volatilidad mínima 8%
          5. Riesgo controlado 1.5-8%
          6. Trigger: high semana × 1.001
        """
        from estrategias.posicional.datos_posicional import obtener_datos_semanales
        from core.riesgo import calcular_objetivo, calcular_rr
        from core.utilidades import respuesta_invalida

        # Intentar con get_df_semanal primero, fallback a get_df + resample
        df = None
        try:
            from estrategias.posicional.datos_posicional import obtener_datos_semanales
            df, _ = obtener_datos_semanales(ticker, periodo_años=5, validar=False)
        except Exception:
            pass

        # Fallback: get_df diario + resamplear
        if df is None or df.empty:
            try:
                from core.data_provider import get_df_semanal
                df, _ = get_df_semanal(ticker, periodo_años=5)
            except Exception:
                pass

        if df is None or df.empty:
            try:
                import pandas as pd
                from core.data_provider import get_df
                df_d = get_df(ticker, periodo="5y", cache=cache)
                if df_d is not None and not df_d.empty:
                    df = pd.DataFrame({
                        "Open":   df_d["Open"].resample("W-FRI").first(),
                        "High":   df_d["High"].resample("W-FRI").max(),
                        "Low":    df_d["Low"].resample("W-FRI").min(),
                        "Close":  df_d["Close"].resample("W-FRI").last(),
                        "Volume": df_d["Volume"].resample("W-FRI").sum(),
                    }).dropna()
                    df = df[df["Close"] > 0]
            except Exception:
                pass

        if df is None or df.empty or len(df) < MM_TENDENCIA_LARGA:
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": 0, "entrada": 0, "stop": 0,
                "objetivo": None, "setup_score": 0, "setup_max": 10,
                "motivos": [{"ok": False, "texto": f"Histórico insuficiente ({len(df) if df is not None else 0} semanas)"}],
                "advertencias": [], "fecha_desde": "", "fecha_hasta": "", "semanas": 0,
                "detalles": {},
            }

        precios       = df["Close"].tolist()
        highs         = df["High"].tolist()
        precio_actual = round(precios[-1], 2)
        fecha_desde   = str(df.index[0].date())
        fecha_hasta   = str(df.index[-1].date())
        semanas       = len(df)

        # ── Indicadores ───────────────────────────────────────────────────────
        tendencia = detectar_tendencia_semanal(precios)
        pullback  = detectar_pullback(precios)
        giro      = detectar_giro_semanal(precios, highs=highs)
        vol_anual = calcular_volatilidad(precios, ventana=52)
        score, score_max = calcular_score_medio(precios, tendencia, pullback, df=df)
        semaforo         = calcular_semaforo_medio(precios, tendencia, pullback, df=df)

        # Valores de MMs
        mm20  = round(tendencia.get("mm20", 0) or 0, 2)
        mm50  = round(tendencia.get("mm50", 0) or 0, 2)
        mm200 = round(tendencia.get("mm200", 0) or 0, 2)
        mm50_sobre_mm200 = tendencia.get("mm50_sobre_mm200", False)
        tendencia_str    = tendencia.get("tendencia", "NEUTRAL")
        retroceso        = pullback.get("retroceso_pct", 0)
        trigger          = giro.get("trigger", round(precio_actual * 1.001, 2))

        # RSI semanal aproximado
        rsi_val = None
        if len(precios) >= 15:
            try:
                deltas    = [precios[i]-precios[i-1] for i in range(1, min(15, len(precios)))]
                ganancias = [d for d in deltas if d > 0]
                perdidas  = [-d for d in deltas if d < 0]
                avg_g     = sum(ganancias)/14 if ganancias else 0
                avg_p     = sum(perdidas)/14  if perdidas  else 0.001
                rsi_val   = round(100 - (100 / (1 + avg_g / avg_p)), 1)
            except Exception:
                pass

        # ── Detalles para el template ─────────────────────────────────────────
        detalles_base = {
            "tendencia":        tendencia_str,
            "retroceso_pct":    round(retroceso, 1),
            "volatilidad_pct":  round(vol_anual, 1) if vol_anual else None,
            "mm20":             mm20,
            "mm50":             mm50,
            "mm200":            mm200,
            "mm50_sobre_mm200": mm50_sobre_mm200,
            "rsi":              rsi_val,
            "giro_semanal":     giro.get("hay_giro", False),
            "trigger":          trigger,
        }

        # ── Construir motivos completos (siempre, compra o no) ────────────────
        motivos = []

        # 1. Tendencia macro
        tendencia_ok = (tendencia_str == "ALCISTA")
        if mm200 > 0:
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Tendencia macro: precio {precio_actual}€ vs MM200 {mm200}€ | MM50 {mm50}€ {'>' if mm50_sobre_mm200 else '<'} MM200"
            })
        else:
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Tendencia: {tendencia_str.lower()} (precio {precio_actual}€ vs MM20 {mm20}€)"
            })

        # 2. Pullback
        motivos.append({
            "ok":    pullback.get("es_pullback", False),
            "texto": pullback.get("motivo", f"Pullback: {retroceso:.1f}%")
        })

        # 3. RSI — zona pullback sano 40-55 (alineado con score y semáforo)
        if rsi_val is not None:
            rsi_ok = 40 <= rsi_val <= 55
            motivos.append({
                "ok":    rsi_ok,
                "texto": f"RSI semanal {rsi_val} ({'zona pullback' if rsi_ok else 'fuera de zona 40-55'})"
            })

        # 4. Volatilidad
        if vol_anual is not None:
            vol_ok = vol_anual >= VOL_MIN_PCT
            motivos.append({
                "ok":    vol_ok,
                "texto": f"Volatilidad anual {vol_anual:.1f}% (mínimo {VOL_MIN_PCT}%)"
            })

        # 5. MM50 > MM200
        if mm50 > 0 and mm200 > 0:
            motivos.append({
                "ok":    mm50_sobre_mm200,
                "texto": f"MM50 {'>' if mm50_sobre_mm200 else '<'} MM200 ({mm50}€ vs {mm200}€)"
            })

        # ── Filtros eliminatorios ─────────────────────────────────────────────
        rechazos = []
        if not tendencia_ok:
            rechazos.append("Tendencia no alcista")
        if not pullback.get("es_pullback"):
            rechazos.append(pullback.get("motivo", "Sin pullback válido"))
        if vol_anual is not None and vol_anual < VOL_MIN_PCT:
            rechazos.append(f"Volatilidad baja ({vol_anual:.1f}%)")

        if rechazos:
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": precio_actual,
                "entrada": 0, "stop": 0, "objetivo": None, "trigger": trigger,
                "setup_score": score, "setup_max": score_max,
                "motivos": motivos,
                "advertencias": [], "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta, "semanas": semanas,
                "detalles": detalles_base,
            }

        # ── Stop y riesgo ─────────────────────────────────────────────────────
        entrada    = precio_actual
        stop       = calcular_stop_inicial(entrada, precios, df=df)
        if stop is None or stop <= 0:
            stop = entrada * (1 - RIESGO_MAX_PCT / 100)

        val_riesgo = validar_riesgo(trigger, stop)
        riesgo_pct = val_riesgo.get("riesgo_pct", 0)

        if not val_riesgo["riesgo_valido"]:
            motivos.append({"ok": False, "texto": f"Riesgo fuera de rango: {val_riesgo['motivo']}"})
            return {
                "valido": False, "decision": "NO_OPERAR", "ticker": ticker,
                "tipo": "MEDIO", "precio_actual": precio_actual,
                "entrada": entrada, "stop": round(stop, 2), "objetivo": None,
                "trigger": trigger, "setup_score": score, "setup_max": score_max,
                "motivos": motivos, "advertencias": [],
                "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta,
                "semanas": semanas, "detalles": detalles_base,
            }

        # ── COMPRA ────────────────────────────────────────────────────────────
        atr      = calcular_atr_semanal(df)
        R_unit   = trigger - stop
        objetivo = round(trigger + 6.0 * R_unit, 2) if R_unit > 0 else None
        rr       = round(6.0, 1) if objetivo else None

        return {
            "valido":      True,
            "decision":    "COMPRA",
            "ticker":      ticker,
            "tipo":        "MEDIO",
            "precio_actual": precio_actual,
            "entrada":     round(entrada, 2),
            "trigger":     trigger,
            "stop":        round(stop, 2),
            "objetivo":    objetivo,
            "rr":          rr,
            "riesgo_pct":  round(riesgo_pct, 1),
            "setup_score": score,
            "setup_max":   score_max,
            "semaforo":    semaforo,
            "motivos":     motivos,
            "advertencias": [],
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "semanas":     semanas,
            "detalles":    detalles_base,
        }

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        filtrar_mercado: bool = True,
        top_n: int = None,
    ) -> list:
        """
        Escanea una lista de tickers y devuelve señales ordenadas por score.
        """
        from core.universos import TODOS
        lista = tickers or TODOS
        señales = []

        for ticker in lista:
            try:
                señal = self.evaluar(ticker, cache)
                señal["ticker"] = ticker
                señales.append(señal)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"ScannerMedio: error en {ticker}: {e}")

        # Ordenar: primero válidas, luego por score descendente
        señales.sort(key=lambda s: (s.get("valido", False), s.get("setup_score", 0)), reverse=True)

        if top_n:
            señales = señales[:top_n]

        return señales
