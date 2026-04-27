# alertas/detector.py
# ══════════════════════════════════════════════════════════════
# DETECTOR DE ALERTAS TÉCNICAS
#
# Migrado desde detector_alertas.py del proyecto original.
# Cambios:
#   - Usa core/data_provider.get_df() en lugar de yfinance directo
#   - Usa core/indicadores para calcular los que falten
#   - Sin cambios en la lógica de detección (7 detectores intactos)
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
from datetime import datetime
import logging

from core.data_provider import get_df
from core.indicadores import calcular_rsi, calcular_atr

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
VOLATILIDAD_MULTIPLICADOR = 1.8
VOLUMEN_MULTIPLICADOR     = 2.0
RSI_SOBRECOMPRA           = 72
RSI_SOBREVENTA            = 28
MA_CORTA                  = 50
MA_LARGA                  = 200
VENTANA_MEDIA             = 20


# ══════════════════════════════════════════════
# API PÚBLICA
# ══════════════════════════════════════════════

def detectar_alertas_ticker(ticker: str, cache=None) -> list:
    """Obtiene datos y detecta alertas para un ticker. Punto de entrada principal."""
    df = get_df(ticker, periodo="1y", cache=cache)
    if df is None or len(df) < 30:
        return []
    df = _preparar_df(df)
    return detectar_alertas(df, ticker)


def detectar_alertas(df: pd.DataFrame, ticker: str) -> list:
    """
    Detecta alertas técnicas sobre un DataFrame ya preparado.
    Compatible con DataFrames de cualquier fuente (EODHD, yfinance, FMP).
    """
    alertas = []
    if df is None or len(df) < 30:
        return alertas

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df.rename(columns={
        'sma50': 'ma50', 'sma200': 'ma200',
        'sma_50': 'ma50', 'sma_200': 'ma200',
        'mm50': 'ma50', 'mm200': 'ma200',
        'vol': 'volume', 'adj_close': 'close',
    }, inplace=True)

    precio_actual = float(df['close'].iloc[-1])

    if 'ma50' in df.columns and 'ma200' in df.columns:
        alertas += _cruce_medias(df, ticker, precio_actual)
    if 'atr' in df.columns:
        alertas += _pico_volatilidad_atr(df, ticker, precio_actual)
    if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
        alertas += _bollinger_squeeze(df, ticker, precio_actual)
    if 'rsi' in df.columns:
        alertas += _rsi_extremo(df, ticker, precio_actual)
    if 'volume' in df.columns:
        alertas += _volumen_anomalo(df, ticker, precio_actual)
    if all(c in df.columns for c in ['pivot', 'r1', 's1']):
        alertas += _zona_pivot(df, ticker, precio_actual)
    if 'adx' in df.columns:
        alertas += _adx_tendencia(df, ticker, precio_actual)

    return alertas


def priorizar_alertas(alertas: list) -> list:
    orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    return sorted(alertas, key=lambda x: orden.get(x.get('severidad', 'BAJA'), 3))


def alertas_por_ticker(alertas: list) -> dict:
    resultado = {}
    for a in alertas:
        resultado.setdefault(a['ticker'], []).append(a)
    return resultado


# ══════════════════════════════════════════════
# PREPARACIÓN DE DATOS
# ══════════════════════════════════════════════

def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores que falten en el df."""
    df = df.copy()
    cols = [c.lower() for c in df.columns]

    if 'mm50' not in cols and 'ma50' not in cols:
        df['MM50']  = df['Close'].rolling(50).mean()
        df['MM200'] = df['Close'].rolling(200).mean()
    if 'rsi' not in cols:
        df['RSI'] = calcular_rsi(df['Close'], 14)
    if 'atr' not in cols:
        df['ATR'] = calcular_atr(df, 14)
    if 'bb_upper' not in cols:
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['BB_UPPER'] = sma + 2 * std
        df['BB_LOWER'] = sma - 2 * std
    if 'adx' not in cols:
        df['ADX'] = _calcular_adx(df, 14)

    return df


def _calcular_adx(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    try:
        hl  = df['High'] - df['Low']
        hpc = (df['High'] - df['Close'].shift()).abs()
        lpc = (df['Low']  - df['Close'].shift()).abs()
        tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        dm_plus  = df['High'].diff().clip(lower=0)
        dm_minus = (-df['Low'].diff()).clip(lower=0)
        atr14    = tr.rolling(periodo).mean()
        di_plus  = 100 * (dm_plus.rolling(periodo).mean()  / atr14.replace(0, np.nan))
        di_minus = 100 * (dm_minus.rolling(periodo).mean() / atr14.replace(0, np.nan))
        dx       = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
        return dx.rolling(periodo).mean()
    except Exception:
        return pd.Series(np.nan, index=df.index)


# ══════════════════════════════════════════════
# DETECTORES INDIVIDUALES (lógica original intacta)
# ══════════════════════════════════════════════

def _cruce_medias(df, ticker, precio):
    alertas = []
    prev = df.iloc[-2]
    curr = df.iloc[-1]

    if prev['ma50'] < prev['ma200'] and curr['ma50'] >= curr['ma200']:
        fecha = _fecha_cruce_ma(df, 'ma50', 'ma200', alcista=True)
        alertas.append(_alerta(
            tipo="GOLDEN_CROSS", ticker=ticker, severidad="ALTA", icono="🟢",
            titulo=f"Golden Cross MA{MA_CORTA}/MA{MA_LARGA}",
            detalle=(f"MA{MA_CORTA} ({curr['ma50']:.2f}) acaba de cruzar al alza "
                     f"la MA{MA_LARGA} ({curr['ma200']:.2f}). Señal alcista de largo plazo."),
            accion="Buscar entrada larga si el sistema swing confirma setup.",
            precio=precio, fecha_vela=fecha,
        ))
    elif prev['ma50'] > prev['ma200'] and curr['ma50'] <= curr['ma200']:
        fecha = _fecha_cruce_ma(df, 'ma50', 'ma200', alcista=False)
        alertas.append(_alerta(
            tipo="DEATH_CROSS", ticker=ticker, severidad="ALTA", icono="🔴",
            titulo=f"Death Cross MA{MA_CORTA}/MA{MA_LARGA}",
            detalle=(f"MA{MA_CORTA} ({curr['ma50']:.2f}) ha cruzado por debajo "
                     f"de MA{MA_LARGA} ({curr['ma200']:.2f}). Señal bajista estructural."),
            accion="Evitar entradas largas. Revisar posiciones abiertas.",
            precio=precio, fecha_vela=fecha,
        ))

    prev_close = float(df.iloc[-2]['close'])
    if prev_close < float(prev['ma50']) and precio >= float(curr['ma50']):
        alertas.append(_alerta(
            tipo="PRECIO_CRUZA_MA50_ALZA", ticker=ticker, severidad="MEDIA", icono="📈",
            titulo=f"Precio cruza MA{MA_CORTA} al alza",
            detalle=f"Precio ({precio:.2f}) ha superado la MA{MA_CORTA} ({curr['ma50']:.2f}).",
            accion="Posible inicio alcista. Confirmar con volumen y RSI.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
        ))
    elif prev_close > float(prev['ma50']) and precio <= float(curr['ma50']):
        alertas.append(_alerta(
            tipo="PRECIO_CRUZA_MA50_BAJA", ticker=ticker, severidad="MEDIA", icono="📉",
            titulo=f"Precio pierde MA{MA_CORTA}",
            detalle=f"Precio ({precio:.2f}) ha perdido la MA{MA_CORTA} ({curr['ma50']:.2f}).",
            accion="Señal de debilidad. Revisar stop-loss si hay posición abierta.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
        ))
    return alertas


def _pico_volatilidad_atr(df, ticker, precio):
    alertas = []
    atr_actual = float(df['atr'].iloc[-1])
    atr_media  = float(df['atr'].rolling(VENTANA_MEDIA).mean().iloc[-1])
    if pd.isna(atr_media) or atr_media == 0:
        return alertas
    ratio = atr_actual / atr_media
    if ratio >= VOLATILIDAD_MULTIPLICADOR:
        fecha = _fecha_pico_vol_atr(df, 'atr', VOLATILIDAD_MULTIPLICADOR)
        alertas.append(_alerta(
            tipo="PICO_VOLATILIDAD", ticker=ticker,
            severidad="ALTA" if ratio >= 2.5 else "MEDIA", icono="⚡",
            titulo=f"Pico de volatilidad ATR x{ratio:.1f}",
            detalle=(f"ATR actual ({atr_actual:.3f}) es {ratio:.1f}x la media de "
                     f"{VENTANA_MEDIA} sesiones ({atr_media:.3f})."),
            accion="Ampliar stop o reducir tamaño de posición.",
            precio=precio, fecha_vela=fecha,
            extra={"atr_ratio": round(ratio, 2)},
        ))
    return alertas


def _bollinger_squeeze(df, ticker, precio):
    alertas = []
    ancho_actual = float(df['bb_upper'].iloc[-1]) - float(df['bb_lower'].iloc[-1])
    ancho_medio  = float((df['bb_upper'] - df['bb_lower']).rolling(VENTANA_MEDIA).mean().iloc[-1])
    if pd.isna(ancho_medio) or ancho_medio == 0:
        return alertas
    ratio_ancho = ancho_actual / ancho_medio

    if ratio_ancho < 0.5:
        alertas.append(_alerta(
            tipo="BOLLINGER_SQUEEZE", ticker=ticker, severidad="MEDIA", icono="🔄",
            titulo=f"Squeeze Bollinger — Compresión extrema ({ratio_ancho:.2f}x)",
            detalle=(f"Ancho de bandas es solo el {ratio_ancho*100:.0f}% de la media. "
                     "Alta probabilidad de movimiento brusco próximo."),
            accion="Preparar alerta en ambas direcciones. No anticipar dirección.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
            extra={"ratio_ancho": round(ratio_ancho, 2)},
        ))
    if precio >= float(df['bb_upper'].iloc[-1]) * 0.998:
        alertas.append(_alerta(
            tipo="PRECIO_BANDA_SUPERIOR", ticker=ticker, severidad="MEDIA", icono="🔴",
            titulo="Precio en banda superior Bollinger",
            detalle=f"Precio ({precio:.2f}) en banda superior ({df['bb_upper'].iloc[-1]:.2f}).",
            accion="Posible sobreextensión. Vigilar señal de vuelta.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
        ))
    elif precio <= float(df['bb_lower'].iloc[-1]) * 1.002:
        alertas.append(_alerta(
            tipo="PRECIO_BANDA_INFERIOR", ticker=ticker, severidad="MEDIA", icono="🟢",
            titulo="Precio en banda inferior Bollinger",
            detalle=f"Precio ({precio:.2f}) en banda inferior ({df['bb_lower'].iloc[-1]:.2f}).",
            accion="Posible rebote técnico. Esperar confirmación alcista.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
        ))
    return alertas


def _rsi_extremo(df, ticker, precio):
    alertas = []
    rsi     = float(df['rsi'].iloc[-1])
    rsi_ant = float(df['rsi'].iloc[-2])
    if pd.isna(rsi):
        return alertas

    if rsi > RSI_SOBRECOMPRA:
        div_bajista = precio > float(df['close'].iloc[-2]) and rsi < rsi_ant
        fecha = _fecha_primer_extremo_rsi(df, RSI_SOBRECOMPRA, sobreventa=False)
        alertas.append(_alerta(
            tipo="RSI_OVERBOUGHT", ticker=ticker,
            severidad="ALTA" if rsi > 80 else "MEDIA",
            icono="🔴" if div_bajista else "⚠️",
            titulo=f"RSI sobrecomprado ({rsi:.1f})" + (" + Divergencia bajista" if div_bajista else ""),
            detalle=(f"RSI en {rsi:.1f}, sobre {RSI_SOBRECOMPRA}. "
                     + ("DIVERGENCIA BAJISTA: precio sube pero RSI cae." if div_bajista
                        else "Posible agotamiento alcista.")),
            accion="Vigilar señal de salida o take-profit parcial.",
            precio=precio, fecha_vela=fecha,
            extra={"rsi": round(rsi, 1), "divergencia": div_bajista},
        ))
    elif rsi < RSI_SOBREVENTA:
        div_alcista = precio < float(df['close'].iloc[-2]) and rsi > rsi_ant
        fecha = _fecha_primer_extremo_rsi(df, RSI_SOBREVENTA, sobreventa=True)
        alertas.append(_alerta(
            tipo="RSI_OVERSOLD", ticker=ticker,
            severidad="ALTA" if rsi < 20 else "MEDIA",
            icono="🟢" if div_alcista else "⚠️",
            titulo=f"RSI sobrevendido ({rsi:.1f})" + (" + Divergencia alcista" if div_alcista else ""),
            detalle=(f"RSI en {rsi:.1f}, bajo {RSI_SOBREVENTA}. "
                     + ("DIVERGENCIA ALCISTA: precio cae pero RSI sube." if div_alcista
                        else "Posible rebote técnico en sobreventa.")),
            accion="Esperar confirmación de giro. No anticipar.",
            precio=precio, fecha_vela=fecha,
            extra={"rsi": round(rsi, 1), "divergencia": div_alcista},
        ))
    return alertas


def _volumen_anomalo(df, ticker, precio):
    alertas = []
    vol_actual = float(df['volume'].iloc[-1])
    vol_media  = float(df['volume'].rolling(VENTANA_MEDIA).mean().iloc[-1])
    if pd.isna(vol_media) or vol_media == 0:
        return alertas
    ratio = vol_actual / vol_media
    if ratio >= VOLUMEN_MULTIPLICADOR:
        close_ant = float(df['close'].iloc[-2])
        direccion = "ALCISTA" if precio > close_ant else "BAJISTA"
        fecha = _fecha_pico_vol_atr(df, 'volume', VOLUMEN_MULTIPLICADOR)
        alertas.append(_alerta(
            tipo="VOLUMEN_ANOMALO", ticker=ticker,
            severidad="ALTA" if ratio >= 3.0 else "MEDIA",
            icono="📈" if direccion == "ALCISTA" else "📉",
            titulo=f"Volumen anómalo {direccion} x{ratio:.1f}",
            detalle=(f"Volumen {ratio:.1f}x la media de {VENTANA_MEDIA} sesiones. "
                     f"Movimiento precio: {((precio/close_ant)-1)*100:+.2f}%."),
            accion=f"Alta probabilidad de movimiento sostenido {direccion.lower()}.",
            precio=precio, fecha_vela=fecha,
            extra={"vol_ratio": round(ratio, 2), "direccion": direccion},
        ))
    return alertas


def _zona_pivot(df, ticker, precio):
    alertas = []
    r1 = float(df['r1'].iloc[-1])
    s1 = float(df['s1'].iloc[-1])
    margen = 0.005
    if abs(precio - r1) / r1 < margen:
        alertas.append(_alerta(
            tipo="EN_RESISTENCIA_R1", ticker=ticker, severidad="MEDIA", icono="🎯",
            titulo=f"Precio en Resistencia R1 ({r1:.2f})",
            detalle=f"Precio ({precio:.2f}) dentro del {margen*100:.1f}% de R1 ({r1:.2f}).",
            accion="Posible rechazo. Si rompe con volumen → continuación.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
            extra={"nivel": "R1", "valor": round(r1, 2)},
        ))
    if abs(precio - s1) / s1 < margen:
        alertas.append(_alerta(
            tipo="EN_SOPORTE_S1", ticker=ticker, severidad="MEDIA", icono="🛡️",
            titulo=f"Precio en Soporte S1 ({s1:.2f})",
            detalle=f"Precio ({precio:.2f}) dentro del {margen*100:.1f}% de S1 ({s1:.2f}).",
            accion="Posible rebote. Buscar señal de entrada en largo con confirmación.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
            extra={"nivel": "S1", "valor": round(s1, 2)},
        ))
    return alertas


def _adx_tendencia(df, ticker, precio):
    alertas = []
    adx     = float(df['adx'].iloc[-1])
    adx_ant = float(df['adx'].iloc[-3] if len(df) >= 4 else df['adx'].iloc[-2])
    if pd.isna(adx):
        return alertas

    if adx_ant < 25 and adx >= 25:
        fecha = _fecha_indice(df, -1)
        try:
            for i in range(1, min(20, len(df))):
                if float(df['adx'].iloc[-i-1]) < 25 and float(df['adx'].iloc[-i]) >= 25:
                    fecha = df.index[-i]
                    break
        except Exception:
            pass
        alertas.append(_alerta(
            tipo="ADX_TENDENCIA_FUERTE", ticker=ticker, severidad="MEDIA", icono="💪",
            titulo=f"ADX cruza 25 — Tendencia fuerte emergente ({adx:.1f})",
            detalle=f"ADX ha superado 25 ({adx:.1f}), tendencia clara estableciéndose.",
            accion="Momento favorable para entradas en la dirección de la tendencia.",
            precio=precio, fecha_vela=fecha,
            extra={"adx": round(adx, 1)},
        ))
    elif adx >= 45:
        alertas.append(_alerta(
            tipo="ADX_SOBREEXTENDIDO", ticker=ticker, severidad="BAJA", icono="⚠️",
            titulo=f"ADX sobreextendido ({adx:.1f}) — Tendencia madura",
            detalle=f"ADX en {adx:.1f}. La tendencia puede estar en fase final.",
            accion="Subir trailing stop. Considerar reducir exposición.",
            precio=precio, fecha_vela=_fecha_indice(df, -1),
            extra={"adx": round(adx, 1)},
        ))
    return alertas


# ══════════════════════════════════════════════
# HELPERS DE FECHAS
# ══════════════════════════════════════════════

def _fecha_indice(df, pos=-1):
    try:
        return df.index[pos]
    except Exception:
        return None


def _fecha_cruce_ma(df, col_rapida, col_lenta, alcista=True, ventana=30):
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
    return df.index[-1]


def _fecha_primer_extremo_rsi(df, umbral, sobreventa=False, ventana=15):
    try:
        for i in range(1, min(ventana, len(df))):
            c = float(df['rsi'].iloc[-i])
            p = float(df['rsi'].iloc[-i - 1])
            if sobreventa:
                if p >= umbral and c < umbral:
                    return df.index[-i]
            else:
                if p <= umbral and c > umbral:
                    return df.index[-i]
    except Exception:
        pass
    return df.index[-1]


def _fecha_pico_vol_atr(df, col, multiplicador, ventana=10):
    try:
        media = df[col].rolling(20).mean()
        for i in range(1, min(ventana, len(df))):
            val = float(df[col].iloc[-i])
            med = float(media.iloc[-i])
            if not pd.isna(med) and med > 0 and val / med >= multiplicador:
                return df.index[-i]
    except Exception:
        pass
    return df.index[-1]


# ══════════════════════════════════════════════
# ESTRUCTURA ESTÁNDAR
# ══════════════════════════════════════════════

def _alerta(tipo, ticker, severidad, icono, titulo, detalle, accion,
            precio, fecha_vela=None, extra=None):
    if fecha_vela is not None:
        try:
            timestamp = pd.Timestamp(fecha_vela).strftime('%Y-%m-%dT%H:%M:%S')
        except Exception:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    else:
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    return {
        "tipo":      tipo,
        "ticker":    ticker,
        "severidad": severidad,
        "icono":     icono,
        "titulo":    titulo,
        "detalle":   detalle,
        "accion":    accion,
        "precio":    round(float(precio), 2),
        "timestamp": timestamp,
        "extra":     extra or {},
    }
