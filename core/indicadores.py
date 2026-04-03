# core/indicadores.py
# ══════════════════════════════════════════════════════════════
# INDICADORES TÉCNICOS — IMPLEMENTACIÓN ÚNICA Y CANÓNICA
#
# REGLA: Ningún otro módulo implementa RSI, ATR, MACD, Bollinger.
# Todos importan desde aquí.
#
# RSI usa método Wilder (EWM alpha=1/periodo) — estándar de mercado.
# ATR usa High/Low/Close previo — fórmula correcta (no solo diff).
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
from typing import Optional


# ─────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────

def _to_series(data) -> pd.Series:
    """Convierte lista, array, Series o DataFrame 1-col a pd.Series float limpia."""
    if isinstance(data, pd.DataFrame):
        data = data.squeeze()  # DataFrame de 1 columna (yfinance MultiIndex) → Series
    if isinstance(data, pd.Series):
        return data.astype(float)  # preservar índice original
    return pd.Series(data, dtype=float)


def _scalar(val) -> float:
    """Extrae float de un valor que puede ser numpy scalar, Series o float."""
    if hasattr(val, "item"):
        return val.item()
    return float(val)


# ─────────────────────────────────────────────────────────────
# RSI  (Wilder / EWM — método estándar)
# ─────────────────────────────────────────────────────────────

def calcular_rsi(close, periodo: int = 14) -> pd.Series:
    """
    RSI de Wilder sobre una serie de cierres.
    Robusto ante divisiones por cero (solo subidas o solo bajadas).

    Returns:
        pd.Series con valores RSI (0-100). NaN en las primeras `periodo` velas.
    """
    s = _to_series(close)
    delta = s.diff()
    ganancias = delta.clip(lower=0)
    perdidas  = (-delta).clip(lower=0)

    avg_g = ganancias.ewm(alpha=1 / periodo, adjust=False).mean()
    avg_p = perdidas.ewm(alpha=1 / periodo, adjust=False).mean()

    # avg_p == 0 → solo subidas → RSI = 100
    with np.errstate(divide='ignore', invalid='ignore'):
        rs  = np.where(avg_p == 0, np.inf, avg_g / avg_p)
        rsi = 100 - (100 / (1 + rs))

    return pd.Series(rsi, index=s.index)


def rsi_actual(close, periodo: int = 14) -> Optional[float]:
    """Devuelve solo el último valor RSI como float. None si no hay datos."""
    try:
        serie = calcular_rsi(close, periodo)
        val = serie.iloc[-1]
        return round(_scalar(val), 2) if not np.isnan(val) else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# ATR  (True Range completo: High/Low/Close previo)
# ─────────────────────────────────────────────────────────────

def calcular_atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """
    ATR sobre un DataFrame OHLCV.

    Args:
        df: DataFrame con columnas ['High', 'Low', 'Close']
        periodo: ventana (default 14)

    Returns:
        pd.Series con ATR. NaN en las primeras velas.
    """
    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(window=periodo).mean()


def atr_actual(df: pd.DataFrame, periodo: int = 14) -> Optional[float]:
    """Devuelve solo el último valor ATR como float. None si no hay datos."""
    try:
        serie = calcular_atr(df, periodo)
        val = serie.iloc[-1]
        return round(_scalar(val), 4) if not np.isnan(val) else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# MEDIAS MÓVILES
# ─────────────────────────────────────────────────────────────

def calcular_medias(df: pd.DataFrame, periodos: list = None) -> pd.DataFrame:
    """
    Añade columnas MM{n} al DataFrame para cada periodo solicitado.

    Args:
        df: DataFrame con columna 'Close'
        periodos: lista de periodos, default [20, 50, 200]

    Returns:
        DataFrame con nuevas columnas MM20, MM50, MM200 (o las pedidas)
    """
    if periodos is None:
        periodos = [20, 50, 200]

    resultado = df.copy()
    for n in periodos:
        resultado[f"MM{n}"] = resultado["Close"].rolling(n).mean()
    return resultado


def mm_actual(close, periodo: int) -> Optional[float]:
    """Último valor de la media móvil simple. None si datos insuficientes."""
    s = _to_series(close)
    if len(s) < periodo:
        return None
    val = s.rolling(periodo).mean().iloc[-1]
    return round(_scalar(val), 4) if not np.isnan(val) else None


# ─────────────────────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────────────────────

def calcular_macd(
    close,
    rapida: int = 12,
    lenta: int = 26,
    señal: int = 9,
) -> dict:
    """
    MACD estándar.

    Returns:
        dict con claves:
            'macd'      pd.Series — línea MACD
            'señal'     pd.Series — línea de señal
            'histograma' pd.Series — diferencia
    """
    s = _to_series(close)
    ema_r = s.ewm(span=rapida, adjust=False).mean()
    ema_l = s.ewm(span=lenta,  adjust=False).mean()
    macd_line = ema_r - ema_l
    signal_line = macd_line.ewm(span=señal, adjust=False).mean()
    histograma = macd_line - signal_line

    return {
        "macd":       macd_line,
        "señal":      signal_line,
        "histograma": histograma,
    }


def macd_actual(close, rapida=12, lenta=26, señal=9) -> dict:
    """Devuelve los últimos valores de MACD como floats."""
    try:
        m = calcular_macd(close, rapida, lenta, señal)
        return {
            "macd":       round(_scalar(m["macd"].iloc[-1]), 4),
            "señal":      round(_scalar(m["señal"].iloc[-1]), 4),
            "histograma": round(_scalar(m["histograma"].iloc[-1]), 4),
        }
    except Exception:
        return {"macd": None, "señal": None, "histograma": None}


# ─────────────────────────────────────────────────────────────
# BOLLINGER BANDS
# ─────────────────────────────────────────────────────────────

def calcular_bollinger(close, periodo: int = 20, desviaciones: float = 2.0) -> dict:
    """
    Bandas de Bollinger.

    Returns:
        dict con:
            'media'     pd.Series — SMA central
            'superior'  pd.Series — banda superior
            'inferior'  pd.Series — banda inferior
            'ancho'     pd.Series — (superior - inferior) / media * 100
    """
    s = _to_series(close)
    media = s.rolling(periodo).mean()
    std   = s.rolling(periodo).std()

    superior = media + (desviaciones * std)
    inferior = media - (desviaciones * std)
    ancho = (superior - inferior) / media * 100

    return {
        "media":    media,
        "superior": superior,
        "inferior": inferior,
        "ancho":    ancho,
    }


def bollinger_actual(close, periodo=20, desviaciones=2.0) -> dict:
    """Devuelve los últimos valores de Bollinger como floats."""
    try:
        b = calcular_bollinger(close, periodo, desviaciones)
        return {k: round(_scalar(v.iloc[-1]), 4) for k, v in b.items()}
    except Exception:
        return {"media": None, "superior": None, "inferior": None, "ancho": None}


# ─────────────────────────────────────────────────────────────
# VOLUMEN
# ─────────────────────────────────────────────────────────────

def evaluar_volumen(volumenes: list) -> dict:
    """
    Clasifica el volumen actual respecto a medias recientes.

    Returns:
        dict con 'nivel', 'ratio', 'mensaje', 'permite_entrada'
    """
    if len(volumenes) < 21:
        return {
            "nivel": "NO_VALIDADO",
            "ratio": None,
            "mensaje": "ℹ️ Histórico de volumen insuficiente",
            "permite_entrada": True,
        }

    vol_actual   = volumenes[-2]       # penúltima (ayer) — el de hoy puede estar incompleto
    media_10     = sum(volumenes[-11:-1]) / 10
    media_20     = sum(volumenes[-21:-1]) / 20

    if media_20 < 50_000:
        return {
            "nivel": "ILIQUIDO",
            "ratio": 0,
            "mensaje": f"❌ Ilíquido ({int(media_20):,} acc/día)",
            "permite_entrada": False,
        }

    ratio     = vol_actual / media_10 if media_10 > 0 else 0
    tendencia = media_10  / media_20  if media_20 > 0 else 1.0

    if ratio >= 1.5:
        return {"nivel": "EXPLOSIVO",       "ratio": ratio, "mensaje": f"🔥 Volumen explosivo ({ratio:.2f}x)",    "permite_entrada": True}
    if ratio >= 1.05:
        return {"nivel": "FUERTE",          "ratio": ratio, "mensaje": f"✅ Volumen fuerte ({ratio:.2f}x)",       "permite_entrada": True}
    if ratio >= 0.85 and tendencia >= 1.1:
        return {"nivel": "NORMAL_CRECIENTE","ratio": ratio, "mensaje": "📊 Volumen en crecimiento",               "permite_entrada": True}
    if tendencia >= 1.0:
        return {"nivel": "SECO_SANO",       "ratio": ratio, "mensaje": "🤫 Volumen seco saludable",               "permite_entrada": True}
    if ratio >= 0.75:
        return {"nivel": "ACEPTABLE",       "ratio": ratio, "mensaje": f"⚠️ Volumen aceptable ({ratio:.2f}x)",   "permite_entrada": True}

    return {"nivel": "INSUFICIENTE",        "ratio": ratio, "mensaje": f"❌ Volumen insuficiente ({ratio:.2f}x)", "permite_entrada": False}


# ─────────────────────────────────────────────────────────────
# VOLATILIDAD
# ─────────────────────────────────────────────────────────────

def calcular_volatilidad(close, periodo: int = 20) -> Optional[float]:
    """Volatilidad relativa: rango(periodo) / media(periodo) * 100."""
    s = _to_series(close)
    if len(s) < periodo:
        return None
    ventana = s.iloc[-periodo:]
    media = ventana.mean()
    if media == 0:
        return None
    return round(float((ventana.max() - ventana.min()) / media * 100), 2)


def clasificar_volatilidad(vol: Optional[float]) -> str:
    if vol is None:
        return "media"
    if vol < 2:
        return "baja"
    if vol < 4:
        return "media"
    return "alta"
