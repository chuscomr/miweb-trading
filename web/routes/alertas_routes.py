# web/routes/alertas_routes.py
# ══════════════════════════════════════════════════════════════
# RUTAS ALERTAS
# Unifica la versión original (alertas_routes.py) con el nuevo
# sistema de persistencia en BD.
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import logging

from flask import Blueprint, request, redirect, url_for, render_template, jsonify, current_app
from core.universos import normalizar_ticker, get_nombre, IBEX35, CONTINUO
from alertas.detector import (
    detectar_alertas_ticker, detectar_alertas,
    priorizar_alertas, alertas_por_ticker,
)
from alertas.alertas_ia import interpretar_alertas, interpretar_cartera
from alertas.alertas_db import AlertasDB

logger = logging.getLogger(__name__)

alertas_bp = Blueprint("alertas", __name__, url_prefix="/alertas")
_db = AlertasDB()


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _sanitizar(obj):
    """Convierte tipos numpy a tipos Python nativos para jsonify."""
    if isinstance(obj, dict):
        return {k: _sanitizar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitizar(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


# ─────────────────────────────────────────────────────────────
# PANEL PRINCIPAL (HTML)
# ─────────────────────────────────────────────────────────────

@alertas_bp.route("/", methods=["GET"])
def panel():
    activas    = _db.obtener_activas()
    disparadas = _db.obtener_disparadas(limit=20)
    return render_template(
        "alertas.html",
        activas    = activas,
        disparadas = disparadas,
    )


# ─────────────────────────────────────────────────────────────
# API JSON — un ticker
# GET /alertas/api/SAN
# GET /alertas/api/SAN?ia=1
# GET /alertas/api/SAN?sistema=medio
# ─────────────────────────────────────────────────────────────

@alertas_bp.route("/api/<ticker>")
def api_ticker(ticker: str):
    ticker    = normalizar_ticker(ticker.upper())
    usar_ia   = request.args.get("ia", "0") == "1"
    sistema   = request.args.get("sistema", "swing")
    cache     = _get_cache()

    alertas = detectar_alertas_ticker(ticker, cache)
    alertas = priorizar_alertas(alertas)

    analisis_ia = None
    if usar_ia and alertas:
        analisis_ia = interpretar_alertas(alertas, ticker, sistema=sistema)

    return jsonify(_sanitizar({
        "ticker":      ticker,
        "total":       len(alertas),
        "alertas":     alertas,
        "analisis_ia": analisis_ia,
    }))


# ─────────────────────────────────────────────────────────────
# API JSON — scanner de universo
# GET /alertas/api/scanner?universo=ibex35
# GET /alertas/api/scanner?universo=continuo&solo_altas=1
# ─────────────────────────────────────────────────────────────

@alertas_bp.route("/api/scanner")
def api_scanner():
    universo_key = request.args.get("universo", "ibex35")
    solo_altas   = request.args.get("solo_altas", "0") == "1"
    cache        = _get_cache()

    universos = {
        "ibex35":   IBEX35,
        "continuo": CONTINUO,
        "ambos":    IBEX35 + CONTINUO,
    }
    tickers = universos.get(universo_key, IBEX35)

    todas_alertas = []
    errores       = []

    for ticker in tickers:
        try:
            alertas = detectar_alertas_ticker(ticker, cache)
            todas_alertas.extend(alertas)
        except Exception as e:
            errores.append({"ticker": ticker, "error": str(e)})

    todas_alertas = priorizar_alertas(todas_alertas)

    if solo_altas:
        todas_alertas = [a for a in todas_alertas if a["severidad"] == "ALTA"]

    return jsonify(_sanitizar({
        "universo":       universo_key,
        "tickers_ok":    len(tickers) - len(errores),
        "total_alertas": len(todas_alertas),
        "alertas":        todas_alertas,
        "errores":        errores,
    }))


# ─────────────────────────────────────────────────────────────
# API JSON — alertas de cartera
# POST /alertas/api/cartera
# Body: {"posiciones": [{"ticker": "SAN", "lado": "largo", "entrada": 4.20, "stop": 3.90}], "ia": true}
# ─────────────────────────────────────────────────────────────

@alertas_bp.route("/api/cartera", methods=["POST"])
def api_cartera():
    data       = request.get_json()
    posiciones = data.get("posiciones", [])
    usar_ia    = data.get("ia", False)

    if not posiciones:
        return jsonify({"error": "No se enviaron posiciones"}), 400

    cache         = _get_cache()
    todas_alertas = []

    for pos in posiciones:
        ticker = normalizar_ticker(pos.get("ticker", "").upper())
        try:
            alertas = detectar_alertas_ticker(ticker, cache)
            todas_alertas.extend(alertas)
        except Exception as e:
            logger.warning(f"⚠️ Error alertas cartera {ticker}: {e}")

    agrupadas        = alertas_por_ticker(todas_alertas)
    priorizadas      = priorizar_alertas(todas_alertas)
    analisis_cartera = None

    if usar_ia and todas_alertas:
        analisis_cartera = interpretar_cartera(posiciones, agrupadas)

    return jsonify(_sanitizar({
        "total_alertas":     len(priorizadas),
        "alertas":           priorizadas,
        "por_ticker":        agrupadas,
        "analisis_cartera":  analisis_cartera,
    }))


# ─────────────────────────────────────────────────────────────
# PERSISTENCIA — crear / gestionar alertas guardadas
# ─────────────────────────────────────────────────────────────

@alertas_bp.route("/nueva", methods=["GET"])
def nueva_form():
    return render_template("alertas_nueva.html")


@alertas_bp.route("/nueva", methods=["POST"])
def nueva_guardar():
    try:
        ticker      = normalizar_ticker(request.form.get("ticker", ""))
        tipo        = request.form.get("tipo", "").upper()
        nivel_raw   = request.form.get("nivel", "").strip()
        umbral_raw  = request.form.get("umbral", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        notas       = request.form.get("notas", "").strip()

        nivel  = float(nivel_raw)  if nivel_raw  else None
        umbral = float(umbral_raw) if umbral_raw else None

        errores = _validar_alerta(ticker, tipo, nivel, umbral)
        if errores:
            return render_template("alertas_nueva.html",
                                   errores=errores, datos=request.form)

        _db.crear_alerta(
            ticker=ticker, tipo=tipo, nivel=nivel, umbral=umbral,
            descripcion=descripcion, nombre=get_nombre(ticker), notas=notas,
        )
        return redirect(url_for("alertas.panel"))

    except Exception as e:
        return render_template("alertas_nueva.html",
                               errores=[str(e)], datos=request.form)


@alertas_bp.route("/desactivar/<int:alerta_id>", methods=["POST"])
def desactivar(alerta_id):
    _db.desactivar(alerta_id)
    return redirect(url_for("alertas.panel"))


@alertas_bp.route("/reactivar/<int:alerta_id>", methods=["POST"])
def reactivar(alerta_id):
    _db.reactivar(alerta_id)
    return redirect(url_for("alertas.panel"))


@alertas_bp.route("/eliminar/<int:alerta_id>", methods=["POST"])
def eliminar(alerta_id):
    _db.eliminar(alerta_id)
    return redirect(url_for("alertas.panel"))


# ─────────────────────────────────────────────────────────────
# VALIDACIÓN
# ─────────────────────────────────────────────────────────────

_TIPOS_PRECIO  = {"PRECIO_SOBRE", "PRECIO_BAJO", "STOP_LOSS", "OBJETIVO"}
_TIPOS_RSI     = {"RSI_ALTO", "RSI_BAJO"}
_TODOS_TIPOS   = _TIPOS_PRECIO | _TIPOS_RSI


def _validar_alerta(ticker, tipo, nivel, umbral) -> list:
    errores = []
    if not ticker:
        errores.append("El ticker es obligatorio")
    if tipo not in _TODOS_TIPOS:
        errores.append(f"Tipo no válido: {tipo}")
    if tipo in _TIPOS_PRECIO and nivel is None:
        errores.append("Este tipo requiere un nivel de precio")
    if tipo in _TIPOS_RSI and umbral is None:
        errores.append("Este tipo requiere un umbral RSI")
    if nivel is not None and nivel <= 0:
        errores.append("El nivel debe ser mayor que 0")
    if umbral is not None and not (0 <= umbral <= 100):
        errores.append("El umbral RSI debe estar entre 0 y 100")
    return errores
