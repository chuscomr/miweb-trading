# web/routes/ibex_live_routes.py
# ══════════════════════════════════════════════════════════════
# MERCADO LIVE — IBEX 35 + Mercado Continuo en tiempo real
# Ruta:  /ibex-live/              → página HTML (2 tablas)
# Ruta:  /ibex-live/api/datos     → JSON ambos mercados (polling)
# ══════════════════════════════════════════════════════════════

import logging
from datetime import datetime

import pytz
import yfinance as yf
from flask import Blueprint, jsonify, render_template

from core.universos import CONTINUO, IBEX35, get_nombre

logger = logging.getLogger(__name__)

ibex_live_bp = Blueprint("ibex_live", __name__, url_prefix="/ibex-live")

# ─────────────────────────────────────────────────────────────
# Horario de mercado (Madrid)
# ─────────────────────────────────────────────────────────────

_TZ_MADRID = pytz.timezone("Europe/Madrid")


def _mercado_abierto() -> bool:
    """True si el mercado español está en horario de negociación."""
    ahora = datetime.now(_TZ_MADRID)
    if ahora.weekday() >= 5:
        return False
    hora = ahora.hour * 60 + ahora.minute
    return 9 * 60 <= hora <= 17 * 60 + 35


# ─────────────────────────────────────────────────────────────
# Sectores
# ─────────────────────────────────────────────────────────────

SECTORES = {
    # IBEX 35
    "ACS.MC":  "Construcción",      "ACX.MC":  "Materiales",
    "AENA.MC": "Transporte",        "AMS.MC":  "Tecnología",
    "ANA.MC":  "Construcción",      "ANE.MC":  "Energía",
    "BBVA.MC": "Banca",             "BKT.MC":  "Banca",
    "CABK.MC": "Banca",             "CLNX.MC": "Telecomunicaciones",
    "COL.MC":  "Inmobiliario",      "ELE.MC":  "Energía",
    "ENG.MC":  "Energía",           "FDR.MC":  "Consumo",
    "FER.MC":  "Infraestructuras",  "GRF.MC":  "Salud",
    "IAG.MC":  "Transporte",        "IBE.MC":  "Energía",
    "IDR.MC":  "Tecnología",        "ITX.MC":  "Consumo",
    "LOG.MC":  "Distribución",      "MAP.MC":  "Seguros",
    "MRL.MC":  "Inmobiliario",      "MTS.MC":  "Materiales",
    "NTGY.MC": "Energía",           "PUIG.MC": "Consumo",
    "RED.MC":  "Energía",           "REP.MC":  "Energía",
    "ROVI.MC": "Salud",             "SAB.MC":  "Banca",
    "SAN.MC":  "Banca",             "SCYR.MC": "Construcción",
    "SLR.MC":  "Energía",           "TEF.MC":  "Telecomunicaciones",
    "UNI.MC":  "Banca",
    # Mercado Continuo
    "A3M.MC":   "Medios",           "AEDAS.MC": "Inmobiliario",
    "APAM.MC":  "Servicios",        "ATRY.MC":  "Salud",
    "AZK.MC":   "Industria",        "CAF.MC":   "Industria",
    "CIE.MC":   "Automoción",       "CIRSA.MC": "Ocio",
    "DIA.MC":   "Distribución",     "DOM.MC":   "Tecnología",
    "EBROM.MC": "Alimentación",     "ENC.MC":   "Materiales",
    "ENO.MC":   "Energía",          "FAE.MC":   "Salud",
    "FCC.MC":   "Construcción",     "GEST.MC":  "Automoción",
    "GRE.MC":   "Energía",          "HBX.MC":   "Turismo",
    "HOME.MC":  "Inmobiliario",     "LDA.MC":   "Seguros",
    "MEL.MC":   "Turismo",          "MVC.MC":   "Inmobiliario",
    "OHLA.MC":  "Construcción",     "PHM.MC":   "Salud",
    "PSG.MC":   "Seguridad",        "R4.MC":    "Financiero",
    "RLIA.MC":  "Inmobiliario",     "TRE.MC":   "Ingeniería",
    "TUB.MC":   "Materiales",       "VID.MC":   "Alimentación",
    "VIS.MC":   "Alimentación",
}


# ─────────────────────────────────────────────────────────────
# Descarga batch (reutilizable para cualquier lista de tickers)
# ─────────────────────────────────────────────────────────────

def _batch_download(tickers: list[str], label: str) -> list[dict]:
    """
    Descarga todos los tickers en un único batch yfinance.
    Fallback individual si el batch falla.
    """
    resultados = []
    tickers_str = " ".join(tickers)

    try:
        datos = yf.download(
            tickers_str,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        for ticker in tickers:
            try:
                df = datos[ticker] if ticker in datos.columns.get_level_values(0) else None

                if df is None or df.empty:
                    resultados.append(_placeholder(ticker))
                    continue

                precio   = round(float(df["Close"].iloc[-1]), 3)
                anterior = round(float(df["Close"].iloc[-2]) if len(df) >= 2 else precio, 3)
                apertura = round(float(df["Open"].iloc[-1]), 3)
                maximo   = round(float(df["High"].iloc[-1]), 3)
                minimo   = round(float(df["Low"].iloc[-1]), 3)
                volumen  = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0

                var_abs = round(precio - anterior, 3)
                var_pct = round((var_abs / anterior) * 100, 2) if anterior else 0.0

                resultados.append({
                    "ticker":   ticker,
                    "nombre":   get_nombre(ticker),
                    "sector":   SECTORES.get(ticker, "—"),
                    "precio":   precio,
                    "apertura": apertura,
                    "maximo":   maximo,
                    "minimo":   minimo,
                    "var_abs":  var_abs,
                    "var_pct":  var_pct,
                    "volumen":  volumen,
                    "anterior": anterior,
                })
            except Exception as e:
                logger.warning(f"⚠️  {label} batch — error {ticker}: {e}")
                resultados.append(_placeholder(ticker))

    except Exception as e:
        logger.error(f"❌ {label} batch download falló: {e} — usando fallback individual")
        for ticker in tickers:
            dato = _descarga_individual(ticker)
            resultados.append(dato if dato else _placeholder(ticker))

    return resultados


def _descarga_individual(ticker: str) -> dict | None:
    """Fallback: descarga un único ticker via fast_info."""
    try:
        t    = yf.Ticker(ticker)
        info = t.fast_info

        precio   = round(float(info.last_price or 0), 3)
        anterior = round(float(info.previous_close or precio), 3)
        apertura = round(float(info.open or 0), 3)
        maximo   = round(float(info.day_high or 0), 3)
        minimo   = round(float(info.day_low or 0), 3)
        volumen  = 0

        try:
            df_hoy = t.history(period="1d", interval="1m")
            if df_hoy is not None and not df_hoy.empty:
                volumen  = int(df_hoy["Volume"].sum())
                apertura = apertura or round(float(df_hoy["Open"].iloc[0]), 3)
                maximo   = maximo   or round(float(df_hoy["High"].max()), 3)
                minimo   = minimo   or round(float(df_hoy["Low"].min()), 3)
        except Exception:
            pass

        if precio == 0:
            return None

        var_abs = round(precio - anterior, 3)
        var_pct = round((var_abs / anterior) * 100, 2) if anterior else 0.0

        return {
            "ticker":   ticker,
            "nombre":   get_nombre(ticker),
            "sector":   SECTORES.get(ticker, "—"),
            "precio":   precio,
            "apertura": apertura,
            "maximo":   maximo,
            "minimo":   minimo,
            "var_abs":  var_abs,
            "var_pct":  var_pct,
            "volumen":  volumen,
            "anterior": anterior,
        }
    except Exception as e:
        logger.warning(f"⚠️  Fallback individual — error {ticker}: {e}")
        return None


def _placeholder(ticker: str) -> dict:
    return {
        "ticker":   ticker,
        "nombre":   get_nombre(ticker),
        "sector":   SECTORES.get(ticker, "—"),
        "precio":   None, "apertura": None, "maximo":  None,
        "minimo":   None, "var_abs":  None, "var_pct": None,
        "volumen":  None, "anterior": None,
    }


def _obtener_indice() -> dict:
    """Descarga el valor del índice IBEX 35 (^IBEX)."""
    try:
        t    = yf.Ticker("^IBEX")
        df   = t.history(period="2d", interval="1d")
        if df is None or df.empty:
            return None
        precio   = round(float(df["Close"].iloc[-1]), 2)
        anterior = round(float(df["Close"].iloc[-2]) if len(df) >= 2 else precio, 2)
        apertura = round(float(df["Open"].iloc[-1]), 2)
        maximo   = round(float(df["High"].iloc[-1]), 2)
        minimo   = round(float(df["Low"].iloc[-1]), 2)
        volumen  = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
        var_abs  = round(precio - anterior, 2)
        var_pct  = round((var_abs / anterior) * 100, 2) if anterior else 0.0
        return {
            "ticker":   "^IBEX",
            "nombre":   "IBEX 35 Índice",
            "sector":   "Índice",
            "precio":   precio,
            "apertura": apertura,
            "maximo":   maximo,
            "minimo":   minimo,
            "var_abs":  var_abs,
            "var_pct":  var_pct,
            "volumen":  volumen,
            "anterior": anterior,
            "es_indice": True,
        }
    except Exception as e:
        logger.warning(f"⚠️  IBEX Index — error: {e}")
        return None


def _resumen(datos: list[dict]) -> dict:
    """Calcula stats de subidas/bajadas/mejor/peor para un bloque de datos."""
    validos   = [d for d in datos if d["var_pct"] is not None]
    n_subidas = sum(1 for d in validos if d["var_pct"] > 0)
    n_bajadas = sum(1 for d in validos if d["var_pct"] < 0)
    n_planas  = len(validos) - n_subidas - n_bajadas
    mejor     = max(validos, key=lambda x: x["var_pct"], default=None)
    peor      = min(validos, key=lambda x: x["var_pct"], default=None)
    return {
        "subidas": n_subidas,
        "bajadas": n_bajadas,
        "planas":  n_planas,
        "mejor":   {"ticker": mejor["ticker"], "var_pct": mejor["var_pct"]} if mejor else None,
        "peor":    {"ticker": peor["ticker"],  "var_pct": peor["var_pct"]}  if peor  else None,
    }


# ─────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────

@ibex_live_bp.route("/")
def panel():
    """Página principal — dos tablas: IBEX 35 + Mercado Continuo."""
    return render_template("ibex_live.html")


@ibex_live_bp.route("/api/datos")
def api_datos():
    """
    Endpoint JSON con los datos de ambos mercados.
    El frontend hace polling cada 30 segundos.
    """
    mercado_abierto = _mercado_abierto()
    ahora_madrid    = datetime.now(_TZ_MADRID)

    datos_ibex     = _batch_download(IBEX35,   "IBEX35")
    datos_continuo = _batch_download(CONTINUO, "Continuo")

    # Añadir el índice como fila normal dentro de la tabla IBEX
    indice = _obtener_indice()
    if indice:
        datos_ibex.append(indice)

    return jsonify({
        "ok":                True,
        "mercado_abierto":   mercado_abierto,
        "hora_actualizacion": ahora_madrid.strftime("%H:%M:%S"),
        "ibex":     {"datos": datos_ibex,     "resumen": _resumen(datos_ibex)},
        "continuo": {"datos": datos_continuo, "resumen": _resumen(datos_continuo)},
    })
