# web/routes/cartera_routes.py
from flask import Blueprint, request, redirect, url_for, render_template, current_app, jsonify, flash
from datetime import datetime, date
from core.universos import normalizar_ticker, get_nombre, IBEX35, CONTINUO
from cartera.cartera_db import CarteraDB
from cartera.cartera_logica import CarteraLogica
from core.contexto_mercado import evaluar_contexto_ibex
from analytics.integrador import registrar_apertura, registrar_cierre
import logging


logger = logging.getLogger(__name__)
cartera_bp = Blueprint("cartera", __name__, url_prefix="/cartera")
_db     = CarteraDB()
_logica = CarteraLogica()

TODOS_TICKERS = sorted(set(IBEX35 + CONTINUO))

def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")

def _resumen_completo():
    cfg             = _db.get_config()
    abiertas        = _db.obtener_posiciones_abiertas()
    hoy             = date.today()
    cerradas_mes    = _db.obtener_cerradas_mes(hoy.year, hoy.month)
    pos_enriquecidas = [_logica.calcular_metricas_posicion(p) for p in abiertas]
    resumen         = _logica.calcular_resumen(pos_enriquecidas, cfg, cerradas_mes)
    return pos_enriquecidas, resumen, cfg

# ── DASHBOARD ─────────────────────────────────────────────────

@cartera_bp.route("/", methods=["GET"])
def ver_cartera():
    try:
        cache    = _get_cache()
        contexto = evaluar_contexto_ibex(cache)
        pos, resumen, cfg = _resumen_completo()
        
        return render_template("cartera.html",
            posiciones       = pos,
            resumen          = resumen,
            config           = cfg,
            contexto_mercado = contexto,
        )
    except Exception as e:
        return render_template("cartera.html",
            posiciones=[], resumen=None, config={},
            contexto_mercado=None, error=str(e))


# ── NUEVA POSICIÓN ─────────────────────────────────────────────

@cartera_bp.route("/nueva", methods=["GET"])
def nueva_form():
    cfg      = _db.get_config()
    cache    = _get_cache()
    contexto = evaluar_contexto_ibex(cache)
    pos_abiertas = _db.obtener_posiciones_abiertas()
    n_pos    = len(pos_abiertas)
    max_pos  = cfg.get("max_posiciones", 99)
    return render_template("cartera_nueva.html",
        tickers   = TODOS_TICKERS,
        config    = cfg,
        n_pos     = n_pos,
        max_pos   = max_pos,
        excepcion = False,
        contexto_mercado = contexto,
        hoy       = date.today().isoformat(),
    )

@cartera_bp.route("/nueva", methods=["POST"])
def nueva_guardar():
    try:
        f = request.form
        ticker        = normalizar_ticker(f.get("ticker", ""))
        sistema       = f.get("sistema", "SWING").upper()
        fecha_entrada = f.get("fecha_entrada", date.today().isoformat())
        precio_entrada= float(f.get("precio_entrada", 0))
        stop_inicial  = float(f.get("stop_inicial")) if f.get("stop_inicial") else None
        objetivo      = float(f.get("objetivo")) if f.get("objetivo") else None
        acciones      = int(f.get("acciones", 0))
        score_nivel   = f.get("score_nivel") or None
        notas         = f.get("notas") or None
        es_excepcion  = f.get("es_excepcion") == "1"

        if not ticker or precio_entrada <= 0 or acciones <= 0:
            raise ValueError("Datos incompletos")
        
        # ─────────────────────────────────────────────────────────
        # v88.1 — VALIDACIÓN DE RISK MANAGER (MODO ADVERTENCIA)
        # Avisa pero NO bloquea — el usuario decide
        # ─────────────────────────────────────────────────────────
        from cartera.risk_manager import RiskManager
        
        cfg = _db.get_config()
        capital = float(cfg.get("capital_total") or 30000)
        
        # Calcular riesgo y tamaño de la posición
        R_unit = (precio_entrada - stop_inicial) if stop_inicial else 0
        riesgo_eur = R_unit * acciones if R_unit > 0 else 0
        tamano_eur = precio_entrada * acciones
        
        # Obtener posiciones abiertas actuales
        posiciones_abiertas = _db.obtener_posiciones_abiertas()
        
        # Validar con Risk Manager
        rm = RiskManager(capital=capital)
        validacion = rm.validar_nueva_posicion(
            ticker=ticker,
            riesgo_eur=riesgo_eur,
            tamano_eur=tamano_eur,
            posiciones_abiertas=posiciones_abiertas
        )
        
        # Mostrar advertencias pero SIEMPRE continuar
        if not validacion['aprobada']:
            flash(f"⚠️ ADVERTENCIA: {validacion['razon']}", 'warning')
            logger.warning(f"⚠️ Advertencia Risk Manager: {ticker} - {validacion['razon']}")
        
        for alerta in validacion.get('alertas', []):
            flash(alerta, 'info')
        # ─────────────────────────────────────────────────────────

        cache    = _get_cache()
        contexto = evaluar_contexto_ibex(cache)
        estado   = contexto.get("estado", "TRANSICION") if contexto else "TRANSICION"

        # 1. Registrar en Analytics PRIMERO
        analytics_id = None
        try:
            analytics_id = registrar_apertura(
                ticker=ticker,
                sistema=sistema,
                tipo_setup=score_nivel or "MANUAL",
                precio_entrada=precio_entrada,
                stop=stop_inicial or 0,
                contexto_mercado=estado,
                score_fundamental=None,
                notas=notas
            )
            logger.info(f"✅ Analytics: trade_id={analytics_id} para {ticker}")
        except Exception as e:
            logger.warning(f"⚠️ Analytics falló (continuando): {e}")
            # Continuar sin analytics_id

        # 2. Crear posición en cartera
        pid = _db.agregar_posicion(
            ticker        = ticker,
            nombre        = f.get("nombre") or get_nombre(ticker) or ticker.replace(".MC",""),
            sistema       = sistema,
            fecha_entrada = fecha_entrada,
            precio_entrada= precio_entrada,
            stop_inicial  = stop_inicial,
            objetivo      = objetivo,
            acciones      = acciones,
            score_nivel   = score_nivel,
            contexto_ibex = estado,
            es_excepcion  = es_excepcion,
            notas         = notas,
            analytics_id  = analytics_id,
        )
        logger.info(f"✅ Posición creada: pid={pid}, analytics_id={analytics_id}")
        
        return redirect(url_for("cartera.ver_cartera"))
    except Exception as e:
        logger.error(f"❌ Error creando posición: {e}", exc_info=True)
        return redirect(url_for("cartera.nueva_form"))


# ── EDITAR STOP / FASE ─────────────────────────────────────────

@cartera_bp.route("/editar/<int:pid>", methods=["GET"])
def editar_form(pid):
    pos = _db.obtener_posicion_por_id(pid)
    if not pos:
        return redirect(url_for("cartera.ver_cartera"))
    cfg = _db.get_config()
    return render_template("cartera_editar.html", pos=pos, config=cfg, hoy=date.today().isoformat())

@cartera_bp.route("/editar/<int:pid>", methods=["POST"])
def editar_guardar(pid):
    f = request.form
    accion = f.get("accion", "stop")

    if accion == "stop_fase":
        stop_actual = float(f.get("stop_actual", 0))
        fase        = f.get("fase", "INICIAL")
        _db.actualizar_stop_fase(pid, stop_actual, fase)

    elif accion == "mitad":
        precio_mitad = float(f.get("precio_mitad", 0))
        fecha_mitad  = f.get("fecha_mitad", date.today().isoformat())
        _db.registrar_mitad(pid, precio_mitad, fecha_mitad)

    elif accion == "editar":
        # Actualizar stop y fase también
        fase = f.get("fase") or "INICIAL"
        stop = float(f.get("stop_actual", 0))
        _db.actualizar_stop_fase(pid, stop, fase)
        _db.actualizar_posicion(
            pid,
            float(f.get("precio_entrada", 0)),
            stop,
            float(f.get("objetivo")) if f.get("objetivo") else None,
            int(f.get("acciones", 0)),
            f.get("notas") or None,
            nombre        = f.get("nombre") if f.get("nombre") is not None else None,
            es_excepcion  = (f.get("es_excepcion") == "1"),
            ticker        = f.get("ticker") or None,
            fecha_entrada = f.get("fecha_entrada") or None,
        )
        # Actualizar score, contexto y sistema si la DB los soporta
        try:
            with _db._conexion() as con:
                if f.get("score_nivel"):
                    con.execute("UPDATE posiciones SET score_nivel=? WHERE id=?",
                               (f.get("score_nivel"), pid))
                if f.get("contexto_ibex"):
                    con.execute("UPDATE posiciones SET contexto_ibex=? WHERE id=?",
                               (f.get("contexto_ibex"), pid))
                if f.get("sistema"):
                    con.execute("UPDATE posiciones SET sistema=? WHERE id=?",
                               (f.get("sistema", "SWING").upper(), pid))
        except Exception:
            pass
    return redirect(url_for("cartera.ver_cartera"))


# ── CERRAR POSICIÓN ────────────────────────────────────────────

@cartera_bp.route("/cerrar/<int:pid>", methods=["GET"])
def cerrar_form(pid):
    pos = _db.obtener_posicion_por_id(pid)
    if not pos:
        return redirect(url_for("cartera.ver_cartera"))
    return render_template("cartera_cerrar.html",
        pos  = pos,
        hoy  = date.today().isoformat(),
    )

@cartera_bp.route("/cerrar/<int:pid>", methods=["POST"])
def cerrar_guardar(pid):
    f             = request.form
    fecha_cierre  = f.get("fecha_cierre", date.today().isoformat())
    precio_cierre = float(f.get("precio_cierre", 0))
    motivo_cierre = f.get("motivo_cierre", "Manual")

    pos = _db.obtener_posicion_por_id(pid)
    if not pos:
        logger.error(f"❌ Posición {pid} no encontrada")
        return redirect(url_for("cartera.ver_cartera"))

    # Calcular R
    r_final = None
    entrada  = float(pos.get("precio_entrada", 0))
    stop_ini = float(pos.get("stop_inicial") or pos.get("stop_actual") or entrada)
    R_unit   = entrada - stop_ini
    if R_unit > 0:
        r_final = round((precio_cierre - entrada) / R_unit, 2)

    # 1. Cerrar en BD cartera
    _db.cerrar_posicion(pid, fecha_cierre, precio_cierre, motivo_cierre, r_final)
    
    # 2. Actualizar Analytics si existe analytics_id
    analytics_id = pos.get("analytics_id")
    if analytics_id:
        try:
            registrar_cierre(
                trade_id=analytics_id,
                precio_salida=precio_cierre,
                precio_entrada=entrada,
                stop=stop_ini,
                tipo_salida=motivo_cierre,
                r_multiple=r_final
            )
            logger.info(f"✅ Analytics actualizado: trade_id={analytics_id}, R={r_final}")
        except Exception as e:
            logger.warning(f"⚠️ Error actualizando Analytics: {e}")
    else:
        logger.info(f"ℹ️ Posición {pid} sin analytics_id (posición antigua, OK)")
    
    return redirect(url_for("cartera.ver_cartera"))


# ── EDITAR TRADE CERRADO ────────────────────────────────────────

@cartera_bp.route("/editar-cerrado/<int:pid>", methods=["GET"])
def editar_cerrado_form(pid):
    pos = _db.obtener_posicion_por_id(pid)
    if not pos or pos.get("estado") != "CERRADA":
        return redirect(url_for("cartera.historial"))
    return render_template("cartera_editar_cerrado.html", pos=pos)

@cartera_bp.route("/editar-cerrado/<int:pid>", methods=["POST"])
def editar_cerrado_guardar(pid):
    f             = request.form
    fecha_cierre  = f.get("fecha_cierre", "")
    precio_cierre = float(f.get("precio_cierre") or 0)
    motivo_cierre = f.get("motivo_cierre", "Manual")
    notas         = f.get("notas") or None

    # Recalcular R si se cambia precio_cierre
    pos    = _db.obtener_posicion_por_id(pid)
    r_final = None
    if pos:
        entrada  = float(pos.get("precio_entrada", 0))
        stop_ini = float(pos.get("stop_inicial") or pos.get("stop_actual") or entrada)
        R_unit   = entrada - stop_ini
        if R_unit > 0:
            r_final = round((precio_cierre - entrada) / R_unit, 2)

    _db.actualizar_posicion_cerrada(pid, fecha_cierre, precio_cierre, motivo_cierre, r_final, notas)
    return redirect(url_for("cartera.historial"))


# ── HISTORIAL ──────────────────────────────────────────────────

@cartera_bp.route("/historial", methods=["GET"])
def historial():
    cerradas = _db.obtener_posiciones_cerradas(limit=200)
    cfg      = _db.get_config()

    # Métricas globales historial
    Rs = [float(p.get("r_final") or 0) for p in cerradas if p.get("r_final") is not None]
    n_win    = sum(1 for r in Rs if r > 0)
    wr       = round(n_win / len(Rs) * 100, 1) if Rs else 0
    exp      = round(sum(Rs) / len(Rs), 2) if Rs else 0
    pnl_total= 0
    for p in cerradas:
        r     = p.get("r_final") or 0
        r_unit= float(p.get("precio_entrada", 0)) - float(p.get("stop_inicial", 0) or 0)
        acc   = int(p.get("acciones", 0))
        if r_unit > 0: pnl_total += r * r_unit * acc

    return render_template("cartera_historial.html",
        cerradas  = cerradas,
        metricas  = {
            "total":    len(Rs),
            "wr":       wr,
            "exp":      exp,
            "pnl_eur":  round(pnl_total, 2),
        },
        config    = cfg,
    )


# ── REVISIÓN DOMINGO ───────────────────────────────────────────

@cartera_bp.route("/domingo", methods=["GET"])
def domingo():
    hoy    = date.today()
    # Semana actual: lunes a domingo
    lunes  = hoy.toordinal() - hoy.weekday()
    dom    = date.fromordinal(lunes + 6)
    lun    = date.fromordinal(lunes)

    cfg              = _db.get_config()
    todas_cerradas   = _db.obtener_posiciones_cerradas(limit=500)
    abiertas         = _db.obtener_posiciones_abiertas()
    pos_enriquecidas = [_logica.calcular_metricas_posicion(p) for p in abiertas]

    # Filtrar cerradas esta semana
    cerradas_semana = [
        p for p in todas_cerradas
        if p.get("fecha_cierre") and
           lun.isoformat() <= p["fecha_cierre"][:10] <= dom.isoformat()
    ]

    revision = _logica.calcular_revision_domingo(
        cerradas_semana, todas_cerradas, pos_enriquecidas, cfg
    )

    return render_template("cartera_domingo.html",
        revision         = revision,
        cerradas_semana  = cerradas_semana,
        posiciones       = pos_enriquecidas,
        config           = cfg,
        semana_inicio    = lun.isoformat(),
        semana_fin       = dom.isoformat(),
    )


# ── CONFIG ─────────────────────────────────────────────────────

@cartera_bp.route("/config", methods=["GET"])
def config_form():
    return render_template("cartera_config.html", config=_db.get_config())

@cartera_bp.route("/config", methods=["POST"])
def config_guardar():
    f = request.form
    for clave in ["capital_total", "riesgo_pct", "limite_mensual_pct",
                  "riesgo_swing_pct", "riesgo_medio_pct", "riesgo_posicional_pct"]:
        if f.get(clave):
            _db.set_config(clave, f.get(clave))
    return redirect(url_for("cartera.ver_cartera"))


# ── DASHBOARD DE RIESGO (v88.1) ────────────────────────────────

@cartera_bp.route("/riesgo", methods=["GET"])
def dashboard_riesgo():
    """Vista de exposición por sector y límites de riesgo."""
    from cartera.risk_manager import RiskManager
    
    cfg = _db.get_config()
    capital = float(cfg.get("capital_total") or 30000)
    
    posiciones = _db.obtener_posiciones_abiertas()
    logica = CarteraLogica()
    
    # Enriquecer posiciones con métricas
    posiciones_enriquecidas = [
        logica.calcular_metricas_posicion(p) 
        for p in posiciones
    ]
    
    # Obtener exposición detallada
    rm = RiskManager(capital=capital)
    exposicion = rm.obtener_exposicion_detallada(posiciones_enriquecidas)
    
    return render_template(
        "cartera_riesgo.html",
        exposicion=exposicion,
        posiciones=posiciones_enriquecidas,
        config=cfg
    )


# ── TRAILING STOPS AUTOMÁTICO (v88.2) ──────────────────────────

@cartera_bp.route("/trailing/<int:pid>", methods=["POST"])
def aplicar_trailing_auto(pid):
    """Aplica trailing stop automático a una posición."""
    from cartera.trailing_stops import get_trailing_stop_manager
    
    pos = _db.obtener_posicion_por_id(pid)
    if not pos:
        flash("Posición no encontrada", "error")
        return redirect(url_for("cartera.ver_cartera"))
    
    # Enriquecer con precio actual
    logica = CarteraLogica()
    pos_enriquecida = logica.calcular_metricas_posicion(pos)
    
    # Calcular nuevo stop
    tsm = get_trailing_stop_manager()
    nuevo_stop, nueva_fase = tsm.calcular_nuevo_stop(
        precio_entrada=float(pos_enriquecida['precio_entrada']),
        stop_inicial=float(pos_enriquecida['stop_inicial'] or 0),
        stop_actual=float(pos_enriquecida['stop_actual'] or pos_enriquecida['stop_inicial'] or 0),
        precio_actual=float(pos_enriquecida['precio_actual']),
        fase_actual=pos.get('fase', 'INICIAL')
    )
    
    # Verificar si hay cambio
    stop_previo = float(pos_enriquecida['stop_actual'] or pos_enriquecida['stop_inicial'] or 0)
    if abs(nuevo_stop - stop_previo) < 0.01:
        flash(f"ℹ️ {pos['ticker'].replace('.MC', '')}: Stop ya está ajustado ({nuevo_stop:.2f}€)", "info")
    else:
        # Aplicar cambio
        _db.actualizar_stop_fase(pid, nuevo_stop, nueva_fase)
        flash(f"✅ {pos['ticker'].replace('.MC', '')}: Stop → {nuevo_stop:.2f}€ (Fase: {nueva_fase})", "success")
        logger.info(f"Trailing aplicado: {pos['ticker']} stop {stop_previo:.2f} → {nuevo_stop:.2f}, fase {nueva_fase}")
    
    return redirect(url_for("cartera.ver_cartera"))


@cartera_bp.route("/trailing/todas", methods=["POST"])
def aplicar_trailing_todas():
    """Aplica trailing stop automático a TODAS las posiciones abiertas."""
    from cartera.trailing_stops import get_trailing_stop_manager
    
    posiciones = _db.obtener_posiciones_abiertas()
    logica = CarteraLogica()
    tsm = get_trailing_stop_manager()
    
    cambios = 0
    sin_cambios = 0
    
    for pos in posiciones:
        pos_enriquecida = logica.calcular_metricas_posicion(pos)
        
        nuevo_stop, nueva_fase = tsm.calcular_nuevo_stop(
            precio_entrada=float(pos_enriquecida['precio_entrada']),
            stop_inicial=float(pos_enriquecida['stop_inicial'] or 0),
            stop_actual=float(pos_enriquecida['stop_actual'] or pos_enriquecida['stop_inicial'] or 0),
            precio_actual=float(pos_enriquecida['precio_actual']),
            fase_actual=pos.get('fase', 'INICIAL')
        )
        
        stop_previo = float(pos_enriquecida['stop_actual'] or pos_enriquecida['stop_inicial'] or 0)
        
        if abs(nuevo_stop - stop_previo) >= 0.01:
            _db.actualizar_stop_fase(pos['id'], nuevo_stop, nueva_fase)
            cambios += 1
            logger.info(f"Trailing: {pos['ticker']} {stop_previo:.2f} → {nuevo_stop:.2f}, fase {nueva_fase}")
        else:
            sin_cambios += 1
    
    if cambios > 0:
        flash(f"✅ Trailing aplicado a {cambios} posición(es)", "success")
    if sin_cambios > 0:
        flash(f"ℹ️ {sin_cambios} posición(es) sin cambios", "info")
    
    return redirect(url_for("cartera.ver_cartera"))


@cartera_bp.route("/eliminar/<int:pid>")
def eliminar_posicion(pid):
    _db.eliminar_posicion(pid)
    return redirect(url_for("cartera.ver_cartera"))
