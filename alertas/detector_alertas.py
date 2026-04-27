"""
detector_alertas.py — MiWeb Swing Trading
Detecta patrones técnicos sobre los DataFrames que ya genera tu sistema.
Compatible con los indicadores calculados en logica_breakout.py y logica_pullback.py
"""

import pandas as pd
import numpy as np
from datetime import datetime


# ─────────────────────────────────────────────
# CONSTANTES — ajusta según tus thresholds
# ─────────────────────────────────────────────
VOLATILIDAD_MULTIPLICADOR = 1.8   # ATR actual > media * X → pico
VOLUMEN_MULTIPLICADOR     = 2.0   # Vol actual > media * X → anómalo
RSI_SOBRECOMPRA           = 72
RSI_SOBREVENTA            = 28
MA_CORTA                  = 50
MA_LARGA                  = 200
VENTANA_MEDIA             = 20    # sesiones para calcular medias de ATR/Vol


def detectar_alertas(df: pd.DataFrame, ticker: str) -> list[dict]:
    """
    Entrada : DataFrame con columnas OHLCV + indicadores de tu sistema.
              Columnas esperadas (las que ya calculas):
              close, volume, high, low,
              ma50, ma200 (o sma50, sma200),
              rsi, atr, bb_upper, bb_lower  (opcionales si no todas están)

    Salida  : Lista de dicts con estructura estándar de alerta.
    """
    alertas = []

    if df is None or len(df) < 30:
        return alertas

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # ── Normalizar nombres de columnas (tu sistema puede usar distintos nombres) ──
    _renombrar = {
        'sma50': 'ma50', 'sma200': 'ma200',
        'sma_50': 'ma50', 'sma_200': 'ma200',
        'vol': 'volume', 'adj_close': 'close',
    }
    df.rename(columns=_renombrar, inplace=True)

    curr = df.iloc[-1]
    precio_actual = curr['close']

    # ─────────────────────────────────────────
    # 1. CRUCE DE MEDIAS MÓVILES
    # ─────────────────────────────────────────
    if 'ma50' in df.columns and 'ma200' in df.columns:
        alertas += _cruce_medias(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 2. PICO DE VOLATILIDAD (ATR)
    # ─────────────────────────────────────────
    if 'atr' in df.columns:
        alertas += _pico_volatilidad_atr(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 3. BANDAS DE BOLLINGER
    # ─────────────────────────────────────────
    if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
        alertas += _bollinger_squeeze(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 4. RSI EXTREMOS
    # ─────────────────────────────────────────
    if 'rsi' in df.columns:
        alertas += _rsi_extremo(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 5. VOLUMEN ANÓMALO
    # ─────────────────────────────────────────
    if 'volume' in df.columns:
        alertas += _volumen_anomalo(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 6. PRECIO EN ZONA DE RESISTENCIA/SOPORTE
    #    (usa los pivots semanales que ya tienes)
    # ─────────────────────────────────────────
    if all(c in df.columns for c in ['pivot', 'r1', 's1']):
        alertas += _zona_pivot(df, ticker, precio_actual)

    # ─────────────────────────────────────────
    # 7. ADX — TENDENCIA FUERTE EMERGENTE
    # ─────────────────────────────────────────
    if 'adx' in df.columns:
        alertas += _adx_tendencia(df, ticker, precio_actual)

    return alertas


# ══════════════════════════════════════════════
# DETECTORES INDIVIDUALES
# ══════════════════════════════════════════════

def _fecha_indice(df, pos=-1):
    """Devuelve la fecha del índice en la posición dada, o None si falla."""
    try:
        return df.index[pos]
    except Exception:
        return None


def _fecha_cruce_ma(df, col_rapida, col_lenta, alcista=True, ventana=20):
    """
    Busca hacia atrás la última vela donde se produjo el cruce entre dos MAs.
    alcista=True → busca cruce al alza (rapida cruza lenta por arriba).
    """
    try:
        for i in range(1, min(ventana, len(df))):
            curr = df.iloc[-i]
            prev = df.iloc[-i - 1]
            if alcista:
                if prev[col_rapida] < prev[col_lenta] and curr[col_rapida] >= curr[col_lenta]:
                    return df.index[-i]
            else:
                if prev[col_rapida] > prev[col_lenta] and curr[col_rapida] <= curr[col_lenta]:
                    return df.index[-i]
    except Exception:
        pass
    return df.index[-1]  # fallback: última vela


def _fecha_primer_extremo_rsi(df, umbral, sobreventa=False, ventana=10):
    """
    Busca la vela más reciente donde el RSI entró en zona extrema (cruzó el umbral).
    """
    try:
        for i in range(1, min(ventana, len(df))):
            curr_rsi = df['rsi'].iloc[-i]
            prev_rsi = df['rsi'].iloc[-i - 1]
            if sobreventa:  # RSI bajó del umbral
                if prev_rsi >= umbral and curr_rsi < umbral:
                    return df.index[-i]
            else:  # RSI subió del umbral
                if prev_rsi <= umbral and curr_rsi > umbral:
                    return df.index[-i]
    except Exception:
        pass
    return df.index[-1]


def _fecha_pico_vol_atr(df, col, multiplicador, ventana=10):
    """
    Busca la vela más reciente donde la columna (vol o atr) superó su media * multiplicador.
    """
    try:
        media = df[col].rolling(20).mean()
        for i in range(1, min(ventana, len(df))):
            val   = df[col].iloc[-i]
            med   = media.iloc[-i]
            if not pd.isna(med) and med > 0 and val / med >= multiplicador:
                return df.index[-i]
    except Exception:
        pass
    return df.index[-1]


def _cruce_medias(df, ticker, precio):
    alertas = []
    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # Golden Cross — busca la fecha real del cruce (hasta 30 velas atrás)
    if prev['ma50'] < prev['ma200'] and curr['ma50'] >= curr['ma200']:
        fecha = _fecha_cruce_ma(df, 'ma50', 'ma200', alcista=True, ventana=30)
        alertas.append(_alerta(
            tipo       = "GOLDEN_CROSS",
            ticker     = ticker,
            severidad  = "ALTA",
            icono      = "🟢",
            titulo     = f"Golden Cross MA{MA_CORTA}/MA{MA_LARGA}",
            detalle    = (f"MA{MA_CORTA} ({curr['ma50']:.2f}) acaba de cruzar al alza "
                          f"la MA{MA_LARGA} ({curr['ma200']:.2f}). "
                          f"Señal alcista de largo plazo."),
            accion     = "Buscar entrada larga si el sistema swing confirma setup.",
            precio     = precio,
            fecha_vela = fecha,
        ))

    # Death Cross
    elif prev['ma50'] > prev['ma200'] and curr['ma50'] <= curr['ma200']:
        fecha = _fecha_cruce_ma(df, 'ma50', 'ma200', alcista=False, ventana=30)
        alertas.append(_alerta(
            tipo       = "DEATH_CROSS",
            ticker     = ticker,
            severidad  = "ALTA",
            icono      = "🔴",
            titulo     = f"Death Cross MA{MA_CORTA}/MA{MA_LARGA}",
            detalle    = (f"MA{MA_CORTA} ({curr['ma50']:.2f}) ha cruzado por debajo "
                          f"de MA{MA_LARGA} ({curr['ma200']:.2f}). "
                          f"Señal bajista estructural."),
            accion     = "Evitar entradas largas. Revisar posiciones abiertas.",
            precio     = precio,
            fecha_vela = fecha,
        ))

    # Precio cruza MA50
    prev_close = df.iloc[-2]['close']
    if prev_close < prev['ma50'] and precio >= curr['ma50']:
        fecha = _fecha_cruce_ma(df, 'close', 'ma50', alcista=True, ventana=15)
        alertas.append(_alerta(
            tipo      = "PRECIO_CRUZA_MA50",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "📈",
            titulo    = f"Precio cruza MA50 al alza",
            detalle   = f"Precio ({precio:.2f}) supera la MA50 ({curr['ma50']:.2f}). Posible inicio de impulso.",
            accion    = "Confirmar con volumen y RSI. Revisar setup pullback.",
            precio    = precio,
            fecha_vela = fecha,
        ))

    return alertas


def _pico_volatilidad_atr(df, ticker, precio):
    alertas = []
    atr_actual = df['atr'].iloc[-1]
    atr_media  = df['atr'].rolling(VENTANA_MEDIA).mean().iloc[-1]

    if pd.isna(atr_media) or atr_media == 0:
        return alertas

    ratio = atr_actual / atr_media

    if ratio >= VOLATILIDAD_MULTIPLICADOR:
        severidad = "ALTA" if ratio >= 2.5 else "MEDIA"
        fecha = _fecha_pico_vol_atr(df, 'atr', VOLATILIDAD_MULTIPLICADOR, ventana=10)
        alertas.append(_alerta(
            tipo      = "ATR_SPIKE",
            ticker    = ticker,
            severidad = severidad,
            icono     = "⚡",
            titulo    = f"Pico de volatilidad ATR x{ratio:.1f}",
            detalle   = (f"ATR actual ({atr_actual:.3f}) es {ratio:.1f}x "
                         f"la media de {VENTANA_MEDIA} sesiones ({atr_media:.3f})."),
            accion    = (f"Ampliar stops en {ratio:.1f}x o reducir tamaño de posición. "
                         f"Stop mínimo sugerido: {atr_actual * 1.5:.2f}€ por acción."),
            precio    = precio,
            fecha_vela = fecha,
            extra     = {"atr_actual": round(atr_actual, 4), "atr_media": round(atr_media, 4), "ratio": round(ratio, 2)},
        ))

    return alertas


def _bollinger_squeeze(df, ticker, precio):
    alertas = []
    bb_up  = df['bb_upper'].iloc[-1]
    bb_low = df['bb_lower'].iloc[-1]

    if pd.isna(bb_up) or pd.isna(bb_low):
        return alertas

    ancho_actual = (bb_up - bb_low) / precio
    ancho_hist   = ((df['bb_upper'] - df['bb_lower']) / df['close']).rolling(50).mean().iloc[-1]

    if not pd.isna(ancho_hist) and ancho_actual < ancho_hist * 0.7:
        alertas.append(_alerta(
            tipo      = "BB_SQUEEZE",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "🔔",
            titulo    = "Bollinger Squeeze — Explosión inminente",
            detalle   = (f"Bandas de Bollinger muy estrechas ({ancho_actual*100:.1f}% del precio vs "
                         f"media histórica {ancho_hist*100:.1f}%). Baja volatilidad previa a movimiento fuerte."),
            accion    = "Preparar orden en ambas direcciones o esperar la rotura para entrar en la dirección del movimiento.",
            precio    = precio,
            fecha_vela = _fecha_indice(df, -1),
        ))

    if precio >= bb_up:
        alertas.append(_alerta(
            tipo      = "BB_UPPER_TOUCH",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "↑",
            titulo    = "Precio en banda superior de Bollinger",
            detalle   = f"Precio ({precio:.2f}) en o por encima de BB superior ({bb_up:.2f}).",
            accion    = "En tendencia alcista: señal de fortaleza. Sin tendencia: posible sobreextensión.",
            precio    = precio,
            fecha_vela = _fecha_indice(df, -1),
        ))

    return alertas


def _rsi_extremo(df, ticker, precio):
    alertas = []
    rsi     = df['rsi'].iloc[-1]
    rsi_ant = df['rsi'].iloc[-2]

    if pd.isna(rsi):
        return alertas

    if rsi > RSI_SOBRECOMPRA:
        div_bajista = bool(precio > df['close'].iloc[-2] and rsi < rsi_ant)
        fecha = _fecha_primer_extremo_rsi(df, RSI_SOBRECOMPRA, sobreventa=False, ventana=15)
        alertas.append(_alerta(
            tipo      = "RSI_OVERBOUGHT",
            ticker    = ticker,
            severidad = "ALTA" if rsi > 80 else "MEDIA",
            icono     = "🔴" if div_bajista else "⚠️",
            titulo    = f"RSI sobrecomprado ({rsi:.1f})" + (" + Divergencia bajista" if div_bajista else ""),
            detalle   = (f"RSI en {rsi:.1f}, por encima de {RSI_SOBRECOMPRA}. "
                         + ("DIVERGENCIA BAJISTA detectada: precio sube pero RSI cae." if div_bajista else
                            "Posible agotamiento del movimiento alcista.")),
            accion    = "Vigilar señal de salida o take-profit parcial. No añadir a posición.",
            precio    = precio,
            fecha_vela = fecha,
            extra     = {"rsi": round(float(rsi), 1), "divergencia": div_bajista},
        ))

    elif rsi < RSI_SOBREVENTA:
        div_alcista = bool(precio < df['close'].iloc[-2] and rsi > rsi_ant)
        fecha = _fecha_primer_extremo_rsi(df, RSI_SOBREVENTA, sobreventa=True, ventana=15)
        alertas.append(_alerta(
            tipo      = "RSI_OVERSOLD",
            ticker    = ticker,
            severidad = "ALTA" if rsi < 20 else "MEDIA",
            icono     = "🟢" if div_alcista else "⚠️",
            titulo    = f"RSI sobrevendido ({rsi:.1f})" + (" + Divergencia alcista" if div_alcista else ""),
            detalle   = (f"RSI en {rsi:.1f}, por debajo de {RSI_SOBREVENTA}. "
                         + ("DIVERGENCIA ALCISTA detectada: precio cae pero RSI sube." if div_alcista else
                            "Posible rebote técnico en zona de sobreventa.")),
            accion    = "Esperar confirmación de giro (vela alcista + volumen). No anticipar.",
            precio    = precio,
            fecha_vela = fecha,
            extra     = {"rsi": round(float(rsi), 1), "divergencia": div_alcista},
        ))

    return alertas


def _volumen_anomalo(df, ticker, precio):
    alertas = []
    vol_actual = df['volume'].iloc[-1]
    vol_media  = df['volume'].rolling(VENTANA_MEDIA).mean().iloc[-1]

    if pd.isna(vol_media) or vol_media == 0:
        return alertas

    ratio = vol_actual / vol_media

    if ratio >= VOLUMEN_MULTIPLICADOR:
        close_ant = df['close'].iloc[-2]
        direccion = "ALCISTA" if precio > close_ant else "BAJISTA"
        icono     = "📈" if direccion == "ALCISTA" else "📉"
        fecha = _fecha_pico_vol_atr(df, 'volume', VOLUMEN_MULTIPLICADOR, ventana=10)
        alertas.append(_alerta(
            tipo      = "VOLUMEN_ANOMALO",
            ticker    = ticker,
            severidad = "ALTA" if ratio >= 3.0 else "MEDIA",
            icono     = icono,
            titulo    = f"Volumen anómalo {direccion} x{ratio:.1f}",
            detalle   = (f"Volumen {ratio:.1f}x la media de {VENTANA_MEDIA} sesiones. "
                         f"Movimiento de precio: {((precio/close_ant)-1)*100:+.2f}%. "
                         f"Señal {direccion}."),
            accion    = (f"Alta probabilidad de movimiento sostenido {direccion.lower()}. "
                         f"Confirmar con indicadores de tendencia."),
            precio    = precio,
            fecha_vela = fecha,
            extra     = {"vol_ratio": round(ratio, 2), "direccion": direccion},
        ))

    return alertas


def _zona_pivot(df, ticker, precio):
    alertas = []
    r1    = df['r1'].iloc[-1]
    s1    = df['s1'].iloc[-1]
    margen = 0.005

    if abs(precio - r1) / r1 < margen:
        alertas.append(_alerta(
            tipo      = "EN_RESISTENCIA_R1",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "🎯",
            titulo    = f"Precio en Resistencia R1 ({r1:.2f})",
            detalle   = f"Precio ({precio:.2f}) dentro del {margen*100:.1f}% de la resistencia semanal R1 ({r1:.2f}).",
            accion    = "Zona de posible rechazo. Vigilar velas de vuelta. Si rompe con volumen → continuación.",
            precio    = precio,
            fecha_vela = _fecha_indice(df, -1),
            extra     = {"nivel": "R1", "valor": round(r1, 2)},
        ))

    if abs(precio - s1) / s1 < margen:
        alertas.append(_alerta(
            tipo      = "EN_SOPORTE_S1",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "🛡️",
            titulo    = f"Precio en Soporte S1 ({s1:.2f})",
            detalle   = f"Precio ({precio:.2f}) dentro del {margen*100:.1f}% del soporte semanal S1 ({s1:.2f}).",
            accion    = "Zona de posible rebote. Buscar señal de entrada en largo con confirmación.",
            precio    = precio,
            fecha_vela = _fecha_indice(df, -1),
            extra     = {"nivel": "S1", "valor": round(s1, 2)},
        ))

    return alertas


def _adx_tendencia(df, ticker, precio):
    alertas = []
    adx      = df['adx'].iloc[-1]
    adx_ant  = df['adx'].iloc[-3] if len(df) >= 4 else df['adx'].iloc[-2]

    if pd.isna(adx):
        return alertas

    if adx_ant < 25 and adx >= 25:
        # Busca la vela donde ADX cruzó 25
        fecha = _fecha_indice(df, -1)
        try:
            for i in range(1, min(20, len(df))):
                if df['adx'].iloc[-i-1] < 25 and df['adx'].iloc[-i] >= 25:
                    fecha = df.index[-i]
                    break
        except Exception:
            pass
        alertas.append(_alerta(
            tipo      = "ADX_TENDENCIA_FUERTE",
            ticker    = ticker,
            severidad = "MEDIA",
            icono     = "💪",
            titulo    = f"ADX cruza 25 — Tendencia fuerte emergente ({adx:.1f})",
            detalle   = f"ADX ha superado 25 ({adx:.1f}), indicando que se está estableciendo una tendencia clara.",
            accion    = "Momento favorable para entradas en la dirección de la tendencia. Evitar contratendencia.",
            precio    = precio,
            fecha_vela = fecha,
            extra     = {"adx": round(adx, 1)},
        ))

    elif adx >= 45:
        alertas.append(_alerta(
            tipo      = "ADX_SOBREEXTENDIDO",
            ticker    = ticker,
            severidad = "BAJA",
            icono     = "⚠️",
            titulo    = f"ADX sobreextendido ({adx:.1f}) — Tendencia madura",
            detalle   = f"ADX en {adx:.1f}, nivel muy alto. La tendencia puede estar en fase final.",
            accion    = "Ajustar stop a break-even o subir trailing stop. Reducir exposición.",
            precio    = precio,
            fecha_vela = _fecha_indice(df, -1),
            extra     = {"adx": round(adx, 1)},
        ))

    return alertas


# ══════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════

def _alerta(tipo, ticker, severidad, icono, titulo, detalle, accion, precio, fecha_vela=None, extra=None):
    """Estructura estándar de alerta para MiWeb."""
    # Usar la fecha de la vela que disparó la alerta, no la hora del sistema
    if fecha_vela is not None:
        try:
            ts = pd.Timestamp(fecha_vela)
            timestamp = ts.strftime('%Y-%m-%dT%H:%M:%S')
        except Exception:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    else:
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    return {
        "tipo":      tipo,
        "ticker":    ticker,
        "severidad": severidad,   # ALTA / MEDIA / BAJA
        "icono":     icono,
        "titulo":    titulo,
        "detalle":   detalle,
        "accion":    accion,
        "precio":    round(float(precio), 2),
        "timestamp": timestamp,
        "extra":     extra or {},
    }


def priorizar_alertas(alertas: list[dict]) -> list[dict]:
    """Ordena las alertas por severidad para mostrar primero las más importantes."""
    orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    return sorted(alertas, key=lambda x: orden.get(x.get('severidad', 'BAJA'), 3))


def alertas_por_ticker(alertas: list[dict]) -> dict:
    """Agrupa una lista plana de alertas por ticker."""
    resultado = {}
    for a in alertas:
        t = a['ticker']
        resultado.setdefault(t, []).append(a)
    return resultado
