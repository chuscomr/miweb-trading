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
    
    Returns:
        dict con:
        - tendencia: "ALCISTA", "BAJISTA", "NEUTRAL"
        - mm10, mm20, mm40: valores de las MMs
        - precio_vs_mm20: relación precio/MM20 en %
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
    
    # Determinar tendencia
    if precio > mm20 and pendiente_mm20 > 0:
        tendencia = "ALCISTA"
    elif precio < mm20 and pendiente_mm20 < 0:
        tendencia = "BAJISTA"
    else:
        tendencia = "NEUTRAL"
    
    # Distancia precio vs MM20
    precio_vs_mm20 = ((precio - mm20) / mm20) * 100 if mm20 else None
    
    return {
        "tendencia": tendencia,
        "mm10": mm10,
        "mm20": mm20,
        "mm40": mm40,
        "precio_vs_mm20": precio_vs_mm20,
        "pendiente_mm20": pendiente_mm20
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 DETECCIÓN DE PULLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detectar_pullback(precios, lookback=LOOKBACK_MAXIMO):
    """
    Detecta si hay un pullback válido.
    
    Pullback = retroceso desde máximo reciente dentro del rango permitido.
    
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
    
    # Máximo reciente
    maximo_reciente = max(ultimos_precios)
    indice_max = len(ultimos_precios) - 1 - list(reversed(ultimos_precios)).index(maximo_reciente)
    semanas_desde_max = len(ultimos_precios) - 1 - indice_max
    
    # Retroceso actual
    retroceso_pct = ((maximo_reciente - precio_actual) / maximo_reciente) * 100
    
    # Validar rango
    es_pullback = PULLBACK_MIN_PCT <= retroceso_pct <= PULLBACK_MAX_PCT
    
    if retroceso_pct < PULLBACK_MIN_PCT:
        motivo = f"Retroceso insuficiente ({retroceso_pct:.1f}%)"
    elif retroceso_pct > PULLBACK_MAX_PCT:
        motivo = f"Retroceso excesivo ({retroceso_pct:.1f}%)"
    else:
        motivo = "Pullback válido"
    
    return {
        "es_pullback": es_pullback,
        "maximo_reciente": maximo_reciente,
        "retroceso_pct": retroceso_pct,
        "semanas_desde_max": semanas_desde_max,
        "motivo": motivo
    }


def detectar_giro_semanal(precios):
    """
    Detecta si hay confirmación de giro alcista.
    
    Giro = precio actual > precio semana anterior
    
    Returns:
        dict con:
        - hay_giro: bool
        - variacion_pct: float
    """
    if len(precios) < 2:
        return {"hay_giro": False}
    
    precio_actual = precios[-1]
    precio_anterior = precios[-2]
    
    variacion_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
    
    return {
        "hay_giro": precio_actual > precio_anterior,
        "variacion_pct": variacion_pct
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ CÁLCULO DE STOPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_stop_inicial(precio_entrada, precios, df=None, stop_atr_mult=None):
    lookback = min(STOP_ESTRUCTURA_LOOKBACK, len(precios))
    stop_estructura = min(precios[-lookback:])

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
    Score 0-10 específico para sistema medio plazo (pullback en tendencia alcista semanal).

    Criterios:
    - Tendencia alcista confirmada (MM20 > MM40, pendiente positiva): +3
    - Pullback en rango óptimo (5-8%): +2  | aceptable (8-12%): +1
    - Precio cerca de soporte MM20 (distancia ≤ 3%): +2  | ≤ 5%: +1
    - Volatilidad útil (10-35%): +1
    - Volumen en retroceso menor que media (pullback sin pánico): +1
    - RSI en zona de soporte (40-55): +1
    """
    score = 0
    score_max = 10

    precio = precios[-1] if precios else 0

    # ── 1. Tendencia alcista: MM20 > MM40, pendiente positiva, precio > MM40 (+3) ──
    mm20 = tendencia.get("mm20", 0)
    mm40 = tendencia.get("mm40", 0)
    pendiente = tendencia.get("pendiente_mm20", 0)
    # Durante pullback el precio cae bajo MM20 → tendencia="NEUTRAL"
    # La estructura alcista real requiere: MM20 > MM40, pendiente + y precio > MM40
    estructura_alcista = (mm20 > 0 and mm40 > 0
                          and mm20 > mm40
                          and pendiente > 0
                          and precio > mm40)
    if estructura_alcista:
        score += 3
    elif (mm20 > mm40 and pendiente > 0) or (precio > mm40 and pendiente > 0):
        score += 1  # tendencia parcial

    # ── 2. Calidad del pullback ───────────────────────────────────────────────
    retroceso = pullback.get("retroceso_pct", 0)
    if 5.0 <= retroceso <= 8.0:
        score += 2   # rango óptimo
    elif 8.0 < retroceso <= 12.0:
        score += 1   # aceptable pero extendido

    # ── 3. Precio cerca de MM20 (soporte dinámico) ───────────────────────────
    if mm20 > 0:
        dist_mm20 = abs(precio - mm20) / mm20 * 100
        if dist_mm20 <= 3.0:
            score += 2
        elif dist_mm20 <= 5.0:
            score += 1

    # ── 4. Volatilidad útil (10-35%) ─────────────────────────────────────────
    vol = calcular_volatilidad(precios, ventana=52)
    if vol and 10.0 <= vol <= 35.0:
        score += 1

    # ── 5. Volumen en pullback menor que media (corrección sana) ─────────────
    if df is not None and "Volume" in df.columns and len(df) >= 10:
        try:
            import numpy as _np
            vol_media = float(df["Volume"].iloc[-20:].mean())
            vol_actual = float(df["Volume"].iloc[-1])
            if vol_actual < vol_media * 0.85:
                score += 1
        except Exception:
            pass

    # ── 6. RSI semanal en zona de soporte (40-55) ────────────────────────────
    if len(precios) >= 15:
        try:
            deltas = [precios[i] - precios[i-1] for i in range(1, min(15, len(precios)))]
            ganancias = [d for d in deltas if d > 0]
            perdidas  = [-d for d in deltas if d < 0]
            avg_g = sum(ganancias) / 14 if ganancias else 0
            avg_p = sum(perdidas)  / 14 if perdidas  else 0.001
            rsi = 100 - (100 / (1 + avg_g / avg_p))
            if 40 <= rsi <= 55:
                score += 1
        except Exception:
            pass

    return min(score, score_max), score_max


class MedioPlazo:
    """
    Wrapper OOP sobre las funciones de logica_medio.py.
    medio_routes.py llama: señal = _medio.evaluar(ticker, cache)
    """

    def evaluar(self, ticker: str, cache=None) -> dict:
        """
        Evalúa señal de medio plazo siguiendo el sistema antiguo:
          1. Tendencia alcista (precio > MM20, pendiente +)
          2. Pullback válido 3-12% en últimas 10 semanas
          3. Giro semanal confirmado (cierre > cierre semana anterior)
          4. Volatilidad mínima 8%
          5. Riesgo controlado 1.5-4%

        Decisiones: COMPRA | VIGILANCIA (ok pero sin giro) | NO_OPERAR
        """
        from estrategias.posicional.datos_posicional import obtener_datos_semanales
        from core.riesgo import calcular_objetivo, calcular_rr
        from core.utilidades import respuesta_invalida, respuesta_valida

        df, _ = obtener_datos_semanales(ticker, periodo_años=1, validar=False)
        if df is None or df.empty or len(df) < MM_TENDENCIA_LARGA:
            r = respuesta_invalida(ticker=ticker, tipo="MEDIO", motivo="Sin datos suficientes")
            r["decision"] = "NO_OPERAR"
            return r

        precios       = df["Close"].tolist()
        precio_actual = round(precios[-1], 2)
        fecha_desde   = str(df.index[0].date())
        fecha_hasta   = str(df.index[-1].date())
        semanas       = len(df)

        tendencia = detectar_tendencia_semanal(precios)
        pullback  = detectar_pullback(precios)
        giro      = detectar_giro_semanal(precios)
        vol_anual = calcular_volatilidad(precios, ventana=52)
        score, score_max = calcular_score_medio(precios, tendencia, pullback, df=df)

        detalles_base = {
            "tendencia":       tendencia.get("tendencia"),
            "retroceso_pct":   round(pullback.get("retroceso_pct", 0), 1),
            "volatilidad_pct": round(vol_anual, 1) if vol_anual else None,
            "mm20":            round(tendencia.get("mm20", 0), 2),
            "giro_semanal":    giro.get("hay_giro", False),
        }

        # ── Filtros eliminatorios (igual que antiguo) ──────────────────────────
        motivos_rechazo = []

        if tendencia.get("tendencia") != "ALCISTA":
            motivos_rechazo.append(f"Tendencia {tendencia.get('tendencia', 'desconocida').lower()}")

        if not pullback.get("es_pullback"):
            motivos_rechazo.append(pullback.get("motivo", "Sin pullback válido"))

        if vol_anual is not None and vol_anual < VOL_MIN_PCT:
            motivos_rechazo.append(f"Volatilidad baja ({vol_anual:.1f}%)")

        if motivos_rechazo:
            return {
                "valido":        False,
                "decision":      "NO_OPERAR",
                "ticker":        ticker,
                "tipo":          "MEDIO",
                "precio_actual": precio_actual,
                "entrada":       0,
                "stop":          0,
                "objetivo":      None,
                "setup_score":   score,
                "setup_max":     score_max,
                "motivos":       [{"ok": False, "texto": m} for m in motivos_rechazo],
                "advertencias":  [],
                "fecha_desde":   fecha_desde,
                "fecha_hasta":   fecha_hasta,
                "semanas":       semanas,
                "detalles":      detalles_base,
            }

        # ── Calcular stop y riesgo ─────────────────────────────────────────────
        entrada = precio_actual
        stop    = calcular_stop_inicial(entrada, precios, df=df)
        if stop is None or stop <= 0:
            stop = entrada * (1 - RIESGO_MAX_PCT / 100)

        val_riesgo = validar_riesgo(entrada, stop)
        riesgo_pct = val_riesgo.get("riesgo_pct", 0)

        if not val_riesgo["riesgo_valido"]:
            return {
                "valido":        False,
                "decision":      "NO_OPERAR",
                "ticker":        ticker,
                "tipo":          "MEDIO",
                "precio_actual": precio_actual,
                "entrada":       0,
                "stop":          0,
                "objetivo":      None,
                "setup_score":   score,
                "setup_max":     score_max,
                "motivos":       [{"ok": False, "texto": val_riesgo["motivo"]}],
                "advertencias":  [],
                "fecha_desde":   fecha_desde,
                "fecha_hasta":   fecha_hasta,
                "semanas":       semanas,
                "detalles":      detalles_base,
            }

        # ── VIGILANCIA: todo ok pero sin giro semanal ──────────────────────────
        if not giro.get("hay_giro"):
            return {
                "valido":        False,
                "decision":      "VIGILANCIA",
                "ticker":        ticker,
                "tipo":          "MEDIO",
                "precio_actual": precio_actual,
                "entrada":       round(entrada, 2),
                "stop":          round(stop, 2),
                "objetivo":      None,
                "riesgo_pct":    round(riesgo_pct, 1),
                "setup_score":   score,
                "setup_max":     score_max,
                "motivos":       [{"ok": False, "texto": "Sin giro semanal"}],
                "advertencias":  [],
                "fecha_desde":   fecha_desde,
                "fecha_hasta":   fecha_hasta,
                "semanas":       semanas,
                "detalles":      detalles_base,
            }

        # ── COMPRA: todos los filtros superados ────────────────────────────────
        atr      = calcular_atr_desde_listas(precios)
        objetivo = calcular_objetivo(entrada, stop, atr=atr, setup_score=score)
        rr       = calcular_rr(entrada, stop, objetivo) if objetivo else None

        r = respuesta_valida(
            ticker        = ticker,
            tipo          = "MEDIO",
            entrada       = round(entrada, 2),
            stop          = round(stop, 2),
            objetivo      = round(objetivo, 2) if objetivo else None,
            rr            = rr,
            setup_score   = score,
            motivos       = [
                "Tendencia alcista confirmada",
                f"Pullback {pullback.get('retroceso_pct', 0):.1f}% (válido)",
                "Giro semanal confirmado",
            ],
            precio_actual = precio_actual,
        )
        r["decision"]   = "COMPRA"
        r["riesgo_pct"] = round(riesgo_pct, 1)
        r["setup_max"]  = score_max
        r["fecha_desde"]= fecha_desde
        r["fecha_hasta"]= fecha_hasta
        r["semanas"]    = semanas
        r["detalles"]   = detalles_base
        return r

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
