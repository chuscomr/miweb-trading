# core/data_provider.py
# ══════════════════════════════════════════════════════════════
# PROVEEDOR DE DATOS — PUNTO ÚNICO DE DESCARGA
#
# REGLA: Ningún módulo llama a yf.download() o yf.Ticker() directamente.
# Todos usan get_df() o get_df_semanal() de aquí.
#
# Pipeline según entorno:
#   LOCAL      (ENTORNO=local):      yfinance directo (rápido, sin límites)
#   PRODUCCIÓN (ENTORNO=produccion): EODHD → FMP → yfinance
#
# Formato de salida: DataFrame OHLCV con columnas simples (no MultiIndex)
#   Index: DatetimeIndex (tz-naive)
#   Columnas: Open, High, Low, Close, Volume
# ══════════════════════════════════════════════════════════════

import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta, date
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

PERIODO_DEFAULT   = "1y"
MIN_VELAS         = 50
CACHE_TIMEOUT_SEG = 600
PARQUET_DIR       = os.path.join(os.path.dirname(__file__), "..", "data_cache")

_ENTORNO = os.getenv("ENTORNO", "local")   # "local" | "produccion"


# ─────────────────────────────────────────────────────────────
# LIMPIEZA DE DATAFRAME
# ─────────────────────────────────────────────────────────────

def _limpiar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza DataFrame OHLCV: aplana MultiIndex, columnas canónicas,
    elimina NaN en Close, filtra outliers >30%, ordena ascendente."""
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.strip().title() for c in df.columns]

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = df.get("Close", 0)

    df = df.dropna(subset=["Close"])
    variacion = df["Close"].pct_change().abs()
    df = df[variacion.isna() | (variacion < 0.50)]  # solo elimina errores claros (>50%)

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    return df.sort_index()


# ─────────────────────────────────────────────────────────────
# FUENTES INDIVIDUALES
# ─────────────────────────────────────────────────────────────

def _desde_eodhd(ticker: str, fecha_inicio: datetime, fecha_fin: datetime) -> Optional[pd.DataFrame]:
    """Histórico diario desde EODHD. Devuelve DataFrame o None."""
    token = os.getenv("EODHD_API_TOKEN")
    if not token or ticker.startswith("^"):
        return None
    try:
        r = requests.get(
            f"https://eodhd.com/api/eod/{ticker}",
            params={
                "api_token": token, "period": "d", "fmt": "json", "order": "a",
                "from": fecha_inicio.strftime("%Y-%m-%d"),
                "to":   fecha_fin.strftime("%Y-%m-%d"),
            },
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()

        if not isinstance(data, list) or len(data) < 50:
            raise ValueError(f"Pocos datos EODHD: {len(data) if isinstance(data, list) else 0}")

        df = pd.DataFrame({
            "Open":   [float(row.get("open")   or row["close"]) for row in data],
            "High":   [float(row.get("high")   or row["close"]) for row in data],
            "Low":    [float(row.get("low")    or row["close"]) for row in data],
            "Close":  [float(row.get("adjusted_close") or row["close"]) for row in data],
            "Volume": [float(row.get("volume") or 0) for row in data],
        }, index=pd.DatetimeIndex(
            [datetime.strptime(row["date"], "%Y-%m-%d") for row in data]
        ))
        logger.info(f"✅ EODHD OK: {len(df)} días para {ticker}")
        return df

    except Exception as e:
        logger.warning(f"⚠️  EODHD falló para {ticker}: {e}")
        return None


def _vela_hoy_fmp(ticker: str, ultima: date) -> Optional[pd.DataFrame]:
    """Vela de hoy desde FMP. Devuelve DataFrame 1 fila o None."""
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        return None
    try:
        hoy = date.today()
        r = requests.get(
            f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}",
            params={"apikey": fmp_key,
                    "from": hoy.strftime("%Y-%m-%d"),
                    "to":   hoy.strftime("%Y-%m-%d")},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        hist = r.json().get("historical", [])
        if not hist:
            return None
        row   = hist[0]
        fecha = datetime.strptime(row["date"], "%Y-%m-%d")
        if fecha.date() <= ultima:
            return None
        df = pd.DataFrame({
            "Open":   [float(row.get("open")   or row["close"])],
            "High":   [float(row.get("high")   or row["close"])],
            "Low":    [float(row.get("low")    or row["close"])],
            "Close":  [float(row["close"])],
            "Volume": [float(row.get("volume") or 0)],
        }, index=pd.DatetimeIndex([fecha]))
        logger.info(f"[FMP hoy] Vela añadida: {fecha.date()} Close={row['close']}")
        return df
    except Exception as e:
        logger.warning(f"[FMP hoy] Error {ticker}: {e}")
        return None


def _vela_hoy_yf(ticker: str, ultima: date) -> Optional[pd.DataFrame]:
    """Vela de hoy desde yfinance. Devuelve DataFrame 1 fila o None."""
    try:
        # Usar 5d para asegurar que capturamos hoy aunque sea lunes
        vela = yf.Ticker(ticker).history(period="5d", interval="1d")
        if vela.empty:
            return None
        if vela.index.tz is not None:
            vela.index = vela.index.tz_localize(None)
        # Filtrar solo velas con Close > 0
        vela = vela[vela["Close"] > 0].dropna(subset=["Close"])
        if vela.empty:
            return None
        # Solo añadir si la última vela es posterior a la última que tenemos
        if vela.index[-1].date() <= ultima:
            return None
        # Solo devolver la vela de hoy (o la más reciente disponible)
        vela_hoy = vela.iloc[[-1]]
        logger.info(f"[yfinance hoy] Vela añadida: {vela_hoy.index[-1].date()} Close={vela_hoy['Close'].iloc[-1]:.2f}")
        return vela_hoy[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as e:
        logger.warning(f"[yfinance hoy] Error {ticker}: {e}")
        return None


def _completar_con_hoy(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Añade velas que faltan desde el último día del df hasta hoy.
    Cubre el caso lunes: el histórico tiene el viernes, el lunes
    aún no está en el histórico pero sí en yfinance (period='5d').
    """
    try:
        ultima = df.index[-1].date()
        hoy    = date.today()
        if ultima >= hoy:
            return df

        # Descargar las últimas 5 velas y añadir las que faltan
        vela = yf.Ticker(ticker).history(period="5d", interval="1d")
        if vela.empty:
            return df
        # Normalizar MultiIndex y nombres de columnas
        vela = _limpiar_df(vela)
        if vela.empty:
            return df
        if vela.index.tz is not None:
            vela.index = vela.index.tz_localize(None)
        vela = vela[vela["Close"] > 0].dropna(subset=["Close"])
        # Filtrar solo las velas posteriores a la última que tenemos
        vela = vela[vela.index.date > ultima]
        if vela.empty:
            return df
        vela = vela[["Open", "High", "Low", "Close", "Volume"]]
        df = pd.concat([df, vela])
        df = df[~df.index.duplicated(keep="last")]
        df.sort_index(inplace=True)
        logger.info(f"[completar_hoy] {ticker}: +{len(vela)} vela(s) añadida(s) hasta {df.index[-1].date()}")
    except Exception as e:
        logger.warning(f"[completar_hoy] {ticker}: {e}")
    return df


def _desde_fmp(ticker: str, fecha_inicio: datetime, fecha_fin: datetime) -> Optional[pd.DataFrame]:
    """Descarga histórico completo desde FMP."""
    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        return None
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}",
            params={
                "apikey": fmp_key,
                "from": fecha_inicio.strftime("%Y-%m-%d"),
                "to":   fecha_fin.strftime("%Y-%m-%d"),
            },
            timeout=30,
        )
        if r.status_code != 200:
            logger.warning(f"⚠️  FMP {ticker}: HTTP {r.status_code}")
            return None
        hist = r.json().get("historical", [])
        if len(hist) < 50:
            logger.warning(f"⚠️  FMP {ticker}: solo {len(hist)} filas")
            return None
        hist = sorted(hist, key=lambda x: x["date"])
        df = pd.DataFrame({
            "Open":   [float(h.get("open")   or h["close"]) for h in hist],
            "High":   [float(h.get("high")   or h["close"]) for h in hist],
            "Low":    [float(h.get("low")    or h["close"]) for h in hist],
            "Close":  [float(h["close"]) for h in hist],
            "Volume": [float(h.get("volume") or 0) for h in hist],
        }, index=pd.DatetimeIndex(
            [datetime.strptime(h["date"], "%Y-%m-%d") for h in hist]
        ))
        logger.info(f"✅ FMP OK: {len(df)} días para {ticker}")
        return df
    except Exception as e:
        logger.warning(f"⚠️  FMP falló para {ticker}: {e}")
        return None
    """Histórico diario desde yfinance. Devuelve DataFrame o None."""
    try:
        # yfinance excluye el end — sumamos 1 día para incluir fecha_fin
        fecha_fin_yf = fecha_fin + timedelta(days=1)
        df = yf.Ticker(ticker).history(
            start=fecha_inicio.strftime("%Y-%m-%d"),
            end=fecha_fin_yf.strftime("%Y-%m-%d"),
            interval="1d",
        )
        if df is None or df.empty:
            logger.warning(f"⚠️  yfinance sin datos para {ticker}")
            return None
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        logger.info(f"✅ yfinance OK: {len(df)} días para {ticker}")
        return _limpiar_df(df)
    except Exception as e:
        logger.error(f"❌ yfinance falló para {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# DESCARGA DIARIA — PIPELINE COMPLETO
# ─────────────────────────────────────────────────────────────

def _descargar_diario(ticker: str, periodo_años: float = 1.0) -> Optional[pd.DataFrame]:
    """
    Descarga datos diarios aplicando el pipeline según ENTORNO:
      local:      yfinance directo
      produccion: EODHD → yfinance; completa hoy con FMP → yfinance
    """
    fecha_fin    = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=int(periodo_años * 365))

    logger.info(f"[{fecha_fin.strftime('%Y-%m-%d %H:%M:%S')}] Descargando {ticker}...")

    if _ENTORNO == "local":
        df = _desde_yfinance(ticker, fecha_inicio, fecha_fin)
        if df is not None:
            df = _completar_con_hoy(df, ticker)
        return df

    # Producción: FMP → EODHD → yfinance
    df = _desde_fmp(ticker, fecha_inicio, fecha_fin)
    if df is None:
        logger.warning(f"⚠️  FMP falló para {ticker} → intentando EODHD...")
        df = _desde_eodhd(ticker, fecha_inicio, fecha_fin)
    if df is None:
        logger.warning(f"⚠️  EODHD falló para {ticker} → intentando yfinance...")
        df = _desde_yfinance(ticker, fecha_inicio, fecha_fin)

    if df is not None:
        df = _completar_con_hoy(df, ticker)

    return df


# ─────────────────────────────────────────────────────────────
# API PÚBLICA — DATOS DIARIOS
# ─────────────────────────────────────────────────────────────

def get_df(
    ticker: str,
    periodo: str = PERIODO_DEFAULT,
    cache=None,
    min_velas: int = MIN_VELAS,
) -> Optional[pd.DataFrame]:
    """
    DataFrame OHLCV diario limpio para el ticker.

    Args:
        ticker:    Ticker (ej: "BBVA.MC", "^IBEX")
        periodo:   "1y", "2y", "5y", etc.
        cache:     Objeto Cache Flask (opcional).
        min_velas: Mínimo de filas requeridas.
    Returns:
        pd.DataFrame o None.
    """
    if cache is not None:
        cache_key = f"df_{ticker}_{periodo}"
        df = cache.get(cache_key)
        if df is not None and len(df) >= min_velas:
            # Aunque el cache tenga datos, completar con la vela de hoy si falta
            df = _completar_con_hoy(df, ticker)
            return df

    _mapa = {"1d": 0.01, "5d": 0.02, "1mo": 0.1, "3mo": 0.25, "6mo": 0.5,
             "1y": 1, "2y": 2, "5y": 5, "10y": 10, "max": 20}
    años = _mapa.get(periodo, 1)

    df = _descargar_diario(ticker, periodo_años=años)

    if df is None or df.empty or len(df) < min_velas:
        logger.warning(f"⚠️  {ticker}: datos insuficientes")
        return None

    if cache is not None:
        cache.set(cache_key, df, timeout=CACHE_TIMEOUT_SEG)

    return df


# ─────────────────────────────────────────────────────────────
# API PÚBLICA — DATOS SEMANALES
# ─────────────────────────────────────────────────────────────

def get_df_semanal(
    ticker: str,
    periodo_años: float = 1.0,
    cache=None,
    min_semanas: int = 40,
) -> tuple:
    """
    Descarga diario y resamplea a semanal W-FRI.
    Reemplaza obtener_datos_semanales() de datos_posicional.py.

    Returns:
        (df_semanal, validacion_dict)  —  df_semanal puede ser None.
    """
    if cache is not None:
        cache_key = f"df_semanal_{ticker}_{periodo_años}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    df_diario = _descargar_diario(ticker, periodo_años=periodo_años)

    if df_diario is None or df_diario.empty:
        return None, {"errores": [f"No hay datos para {ticker}"]}

    try:
        df_semanal = pd.DataFrame({
            "Open":   df_diario["Open"].resample("W-FRI").first(),
            "High":   df_diario["High"].resample("W-FRI").max(),
            "Low":    df_diario["Low"].resample("W-FRI").min(),
            "Close":  df_diario["Close"].resample("W-FRI").last(),
            "Volume": df_diario["Volume"].resample("W-FRI").sum(),
        }).dropna()
        # ✅ FIX: eliminar semanas con Close <= 0 (velas corruptas)
        df_semanal = df_semanal[df_semanal["Close"] > 0]
    except Exception as e:
        return None, {"errores": [f"Error convirtiendo a semanal: {e}"]}

    if len(df_semanal) < min_semanas:
        return None, {"errores": [
            f"Histórico insuficiente: {len(df_semanal)} semanas (mínimo {min_semanas})"
        ]}

    ultima_fecha    = df_semanal.index[-1]
    dias_antiguedad = (datetime.now() - ultima_fecha).days
    logger.info(f"✓ {len(df_semanal)} semanas | Última: {ultima_fecha.strftime('%Y-%m-%d')} ({dias_antiguedad}d)")

    validacion = {
        "ultima_actualizacion": ultima_fecha.strftime("%Y-%m-%d"),
        "dias_antiguedad":      dias_antiguedad,
        "n_semanas":            len(df_semanal),
        "errores":              [],
        "advertencias":         [],
    }

    resultado = (df_semanal, validacion)
    if cache is not None:
        cache.set(cache_key, resultado, timeout=CACHE_TIMEOUT_SEG)

    return resultado


# ─────────────────────────────────────────────────────────────
# API PÚBLICA — PRECIO EN TIEMPO REAL
# ─────────────────────────────────────────────────────────────

def get_precio_rt(ticker: str) -> Optional[dict]:
    """
    Precio actual. Pipeline: EODHD RT → yfinance.
    Devuelve dict con precio, variacion_pct, fecha, fuente — o None.
    """
    token = os.getenv("EODHD_API_TOKEN")

    if token and _ENTORNO != "local" and not ticker.startswith("^"):
        try:
            r = requests.get(
                f"https://eodhd.com/api/real-time/{ticker}",
                params={"api_token": token, "fmt": "json"},
                timeout=10,
            )
            r.raise_for_status()
            data   = r.json()
            precio = float(data.get("close") or data.get("last") or 0)
            if precio > 0:
                anterior = float(data.get("previousClose") or precio)
                var = ((precio - anterior) / anterior) * 100
                return {
                    "precio":          round(precio, 2),
                    "variacion_pct":   round(var, 2),
                    "cierre_anterior": round(anterior, 2),
                    "fecha":           str(date.today()),
                    "fuente":          "tiempo_real",
                }
        except Exception as e:
            logger.warning(f"⚠️  EODHD RT falló ({ticker}): {e}")

    # Fallback yfinance
    try:
        df_d = yf.Ticker(ticker).history(period="5d", interval="1d")
        if df_d is not None and not df_d.empty:
            if df_d.index.tz is not None:
                df_d.index = df_d.index.tz_localize(None)
            precio   = float(df_d["Close"].iloc[-1])
            anterior = float(df_d["Close"].iloc[-2]) if len(df_d) >= 2 else precio
            var      = ((precio - anterior) / anterior) * 100
            return {
                "precio":          round(precio, 2),
                "variacion_pct":   round(var, 2),
                "cierre_anterior": round(anterior, 2),
                "fecha":           df_d.index[-1].strftime("%Y-%m-%d"),
                "fuente":          "ultimo_cierre",
            }
    except Exception as e:
        logger.warning(f"⚠️  yfinance RT falló ({ticker}): {e}")

    return None


# ─────────────────────────────────────────────────────────────
# ATAJOS DE COMPATIBILIDAD
# ─────────────────────────────────────────────────────────────

def get_df_ibex(cache=None, periodo: str = "1y") -> Optional[pd.DataFrame]:
    """Atajo para obtener ^IBEX. Usado por contexto_mercado."""
    return get_df("^IBEX", periodo=periodo, cache=cache, min_velas=210)


def df_a_listas(df: pd.DataFrame) -> tuple:
    """Convierte DataFrame a (precios, volumenes, fechas, precio_actual)."""
    if df is None or df.empty:
        return None, None, None, None
    try:
        precios   = df["Close"].tolist()
        volumenes = df["Volume"].tolist()
        fechas    = df.index.to_pydatetime().tolist()
        return precios, volumenes, fechas, precios[-1] if precios else None
    except Exception as e:
        logger.error(f"❌ df_a_listas: {e}")
        return None, None, None, None


def get_precios(ticker: str, periodo: str = PERIODO_DEFAULT, cache=None) -> tuple:
    """Atajo: descarga y devuelve (precios, volumenes, fechas, precio_actual)."""
    return df_a_listas(get_df(ticker, periodo=periodo, cache=cache))


# ─────────────────────────────────────────────────────────────
# CACHE EN DISCO (parquet) — backtesting offline
# ─────────────────────────────────────────────────────────────

def guardar_parquet(ticker: str, df: pd.DataFrame) -> bool:
    try:
        os.makedirs(PARQUET_DIR, exist_ok=True)
        path = os.path.join(PARQUET_DIR, f"{ticker.replace('.', '_')}.parquet")
        df.to_parquet(path)
        return True
    except Exception as e:
        logger.error(f"❌ guardar_parquet {ticker}: {e}")
        return False


def cargar_parquet(ticker: str) -> Optional[pd.DataFrame]:
    try:
        path = os.path.join(PARQUET_DIR, f"{ticker.replace('.', '_')}.parquet")
        if not os.path.exists(path):
            return None
        return _limpiar_df(pd.read_parquet(path))
    except Exception as e:
        logger.error(f"❌ cargar_parquet {ticker}: {e}")
        return None


def get_df_con_fallback(ticker: str, periodo: str = PERIODO_DEFAULT, cache=None) -> Optional[pd.DataFrame]:
    """Cache Flask → Parquet local → Descarga fresca."""
    if cache is not None:
        df = get_df(ticker, periodo, cache)
        if df is not None:
            return df
    df = cargar_parquet(ticker)
    if df is not None and not df.empty:
        return df
    df = get_df(ticker, periodo, cache=None)
    if df is not None:
        guardar_parquet(ticker, df)
    return df
