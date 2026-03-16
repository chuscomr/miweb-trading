# web/routes/cartera_routes.py
# ══════════════════════════════════════════════════════════════
# RUTAS CARTERA
# Solo lógica HTTP — sin cálculos, sin yfinance.
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, request, redirect, url_for, render_template, current_app
from datetime import datetime
from core.universos import normalizar_ticker, get_nombre
from cartera.cartera_db import CarteraDB
from cartera.cartera_logica import CarteraLogica

cartera_bp = Blueprint("cartera", __name__, url_prefix="/cartera")

_db     = CarteraDB()
_logica = CarteraLogica()


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


# ─────────────────────────────────────────────────────────────
# PANEL PRINCIPAL
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/", methods=["GET"])
def ver_cartera():
    try:
        cache     = _get_cache()
        posiciones = _db.obtener_posiciones_abiertas()
        posiciones_con_metricas = [
            _logica.calcular_metricas_posicion(p, cache)
            for p in posiciones
        ]
        posiciones_con_metricas = [p for p in posiciones_con_metricas if p]
        resumen = _logica.calcular_resumen_cartera(posiciones_con_metricas)

        return render_template(
            "cartera.html",
            posiciones = posiciones_con_metricas,
            resumen    = resumen,
        )
    except Exception as e:
        return render_template(
            "cartera.html",
            posiciones     = [],
            resumen        = None,
            mensaje_error  = f"Error al cargar cartera: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────
# NUEVA POSICIÓN
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/nueva", methods=["GET"])
def nueva_posicion_form():
    return render_template("cartera_nueva.html")


@cartera_bp.route("/nueva", methods=["POST"])
def nueva_posicion_guardar():
    try:
        ticker         = normalizar_ticker(request.form.get("ticker", ""))
        nombre         = request.form.get("nombre", "").strip() or get_nombre(ticker)
        fecha_entrada  = request.form.get("fecha_entrada")
        precio_entrada = float(request.form.get("precio_entrada", 0))
        stop_loss      = float(request.form.get("stop_loss", 0))
        objetivo       = float(request.form.get("objetivo", 0))
        acciones       = int(request.form.get("acciones", 0))
        setup_score    = request.form.get("setup_score")
        contexto_ibex  = request.form.get("contexto_ibex")
        notas          = request.form.get("notas", "").strip()

        setup_score = int(setup_score) if setup_score else None

        errores = _logica.validar_nueva_posicion(
            ticker, precio_entrada, stop_loss, objetivo, acciones
        )

        if errores:
            return render_template("cartera_nueva.html",
                                   errores=errores, datos=request.form)

        _db.agregar_posicion(
            ticker=ticker, nombre=nombre, fecha_entrada=fecha_entrada,
            precio_entrada=precio_entrada, stop_loss=stop_loss,
            objetivo=objetivo, acciones=acciones, setup_score=setup_score,
            contexto_ibex=contexto_ibex, notas=notas,
        )
        return redirect(url_for("cartera.ver_cartera"))

    except ValueError as e:
        return render_template("cartera_nueva.html",
                               errores=[f"Error en los datos: {str(e)}"],
                               datos=request.form)
    except Exception as e:
        return render_template("cartera_nueva.html",
                               errores=[f"Error inesperado: {str(e)}"],
                               datos=request.form)


# ─────────────────────────────────────────────────────────────
# CERRAR POSICIÓN
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/cerrar/<int:posicion_id>", methods=["POST"])
def cerrar_posicion(posicion_id):
    try:
        posicion = _db.obtener_posicion_por_id(posicion_id)
        if not posicion:
            return redirect(url_for("cartera.ver_cartera"))

        precio_actual = _logica.obtener_precio_actual(posicion["ticker"], _get_cache())
        if not precio_actual:
            return redirect(url_for("cartera.ver_cartera"))

        _db.cerrar_posicion(
            posicion_id   = posicion_id,
            fecha_cierre  = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            precio_cierre = precio_actual,
            motivo_cierre = request.form.get("motivo", "Cierre manual"),
        )
        return redirect(url_for("cartera.ver_cartera"))

    except Exception as e:
        return redirect(url_for("cartera.ver_cartera"))


# ─────────────────────────────────────────────────────────────
# EDITAR POSICIÓN
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/editar/<int:posicion_id>", methods=["GET"])
def editar_posicion_form(posicion_id):
    posicion = _db.obtener_posicion_por_id(posicion_id)
    if not posicion:
        return redirect(url_for("cartera.ver_cartera"))
    return render_template("cartera_editar.html", posicion=posicion)


@cartera_bp.route("/editar/<int:posicion_id>", methods=["POST"])
def editar_posicion_guardar(posicion_id):
    try:
        posicion = _db.obtener_posicion_por_id(posicion_id)
        if not posicion:
            return redirect(url_for("cartera.ver_cartera"))

        ticker         = normalizar_ticker(request.form.get("ticker", ""))
        nombre         = request.form.get("nombre", "").strip() or get_nombre(ticker)
        precio_entrada = float(request.form.get("precio_entrada", 0))
        stop_loss      = float(request.form.get("stop_loss", 0))
        objetivo       = float(request.form.get("objetivo", 0))
        acciones       = int(request.form.get("acciones", 0))
        setup_score    = request.form.get("setup_score")
        contexto_ibex  = request.form.get("contexto_ibex")
        notas          = request.form.get("notas", "").strip()

        setup_score = int(setup_score) if setup_score else None

        errores = _logica.validar_edicion_posicion(
            ticker, precio_entrada, stop_loss, objetivo, acciones
        )

        if errores:
            posicion.update(request.form)
            return render_template("cartera_editar.html",
                                   posicion=posicion, errores=errores)

        _db.actualizar_posicion(
            posicion_id=posicion_id, ticker=ticker, nombre=nombre,
            precio_entrada=precio_entrada, stop_loss=stop_loss,
            objetivo=objetivo, acciones=acciones, setup_score=setup_score,
            contexto_ibex=contexto_ibex, notas=notas,
        )
        return redirect(url_for("cartera.ver_cartera"))

    except ValueError as e:
        posicion = _db.obtener_posicion_por_id(posicion_id)
        return render_template("cartera_editar.html",
                               posicion=posicion,
                               errores=[f"Error en los datos: {str(e)}"])
    except Exception as e:
        posicion = _db.obtener_posicion_por_id(posicion_id)
        return render_template("cartera_editar.html",
                               posicion=posicion,
                               errores=[f"Error inesperado: {str(e)}"])


# ─────────────────────────────────────────────────────────────
# ELIMINAR POSICIÓN
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/eliminar/<int:posicion_id>", methods=["POST"])
def eliminar_posicion(posicion_id):
    try:
        _db.eliminar_posicion(posicion_id)
    except Exception as e:
        pass
    return redirect(url_for("cartera.ver_cartera"))


# ─────────────────────────────────────────────────────────────
# HISTORIAL
# ─────────────────────────────────────────────────────────────

@cartera_bp.route("/historial", methods=["GET"])
def historial():
    try:
        posiciones = _db.obtener_posiciones_cerradas(limit=100)
        return render_template("cartera_historial.html", posiciones=posiciones)
    except Exception as e:
        return render_template("cartera_historial.html",
                               posiciones=[],
                               mensaje_error=str(e))
