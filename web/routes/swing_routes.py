# web/routes/swing_routes.py
# ══════════════════════════════════════════════════════════════
# RUTAS SWING TRADING
#
# REGLA: Aquí solo vive lógica de HTTP.
#   - Leer parámetros del request
#   - Llamar a la capa de estrategias
#   - Pasar el resultado a la template
#
# Sin cálculos de riesgo, sin yfinance, sin indicadores.
# ══════════════════════════════════════════════════════════════

import numpy as np
from flask import Blueprint, current_app, redirect, render_template, request, url_for

from analisis.fundamental.proveedor import obtener_datos_fundamentales
from analisis.fundamental.rating import calcular_rating_fundamental
from core.contexto_mercado import evaluar_contexto_ibex, factor_riesgo_mercado
from core.riesgo import resumen_operacion
from core.sizing import calcular_sizing_recomendado
from core.universos import CONTINUO, IBEX35, get_nombre, normalizar_ticker
from estrategias.swing import BreakoutSwing, PullbackSwing, ScannerSwing


swing_bp = Blueprint("swing", __name__, url_prefix="/swing")

# Instancias únicas (stateless — se pueden reutilizar)
_breakout = BreakoutSwing()
_pullback = PullbackSwing()
_scanner  = ScannerSwing()


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _nivel_calidad(score):
    """Clasifica el setup en 3 niveles de calidad para mostrar en el análisis individual."""
    score = float(score or 0)
    if score >= 8.0:
        return {"nivel": "alta_probabilidad", "label": "Alta Probabilidad", "emoji": "⭐"}
    if score >= 6.5:
        return {"nivel": "confirmada",        "label": "Compra Confirmada", "emoji": "🔵"}
    if score >= 5.5:
        return {"nivel": "compra",            "label": "Compra",            "emoji": "🟢"}
    return {"nivel": "sin_nivel",         "label": "",                  "emoji": ""}


def _params_capital(form):
    """Extrae y valida parámetros de capital del formulario."""
    try:
        capital_total = float(form.get("capital_total", 10000))
        riesgo_pct    = float(form.get("riesgo_pct", 1.0))
    except (ValueError, TypeError):
        capital_total = 10000.0
        riesgo_pct    = 1.0
    return capital_total, riesgo_pct


def _stats_y_grafico(ticker, cache, evaluacion=None):
    """Calcula max/min/mm20 recientes y genera gráfico Plotly."""
    try:
        import pandas as pd
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        from core.data_provider import get_df
        from core.indicadores import calcular_rsi

        df = get_df(ticker, periodo="1y", cache=cache)
        if df is None or len(df) < 20:
            return {}, None

        closes  = df["Close"].tolist()
        fechas  = list(df.index)
        precio  = closes[-1]

        max_rec = max(closes[-20:])
        min_rec = min(closes[-20:])
        mm20    = sum(closes[-20:]) / 20

        high_hoy = float(df["High"].iloc[-1])

        # Trigger: si hay vela de giro en la evaluación, usar su high
        # Si no, usar el high de la última vela (high_hoy)
        vela_ok     = evaluacion.get("vela_ok", False) if evaluacion else False
        vela_nombre = evaluacion.get("vela_nombre", "") if evaluacion else ""
        trigger = round(high_hoy * 1.001, 2)  # default: high previo + 0.1%

        stats = {
            "max_reciente":  round(max_rec, 4),
            "min_reciente":  round(min_rec, 4),
            "mm_actual":     round(mm20, 4),
            "dist_max":      round((precio - max_rec) / max_rec * 100, 2),
            "dist_min":      round((precio - min_rec) / min_rec * 100, 2),
            "dist_mm":       round((precio - mm20) / mm20 * 100, 2),
            "trigger":       trigger,
            "trigger_tipo":  f"Vela de giro ({vela_nombre})" if vela_ok else "Máximo sesión anterior",
        }

        # ── Gráfico Plotly ──
        serie = pd.Series(closes, index=pd.DatetimeIndex(fechas))
        mm20s = serie.rolling(20).mean()

        # RSI — usando implementación canónica de core/indicadores.py (Wilder EWM)
        rsi = calcular_rsi(serie, 14)

        señal = evaluacion.get("valido", False) if evaluacion else False
        color_titulo = "green" if señal else "red"
        titulo = f"{ticker} – {'COMPRA' if señal else 'NO OPERAR'}"

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7, 0.3], vertical_spacing=0.05)

        fig.add_trace(go.Scatter(x=serie.index, y=serie.values,
            name="Precio", line=dict(color="black", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=mm20s.index, y=mm20s.values,
            name="MM20", line=dict(color="blue", width=1, dash="dash")), row=1, col=1)

        if evaluacion:
            entrada = evaluacion.get("entrada")
            stop    = evaluacion.get("stop")
            if entrada:
                fig.add_hline(y=entrada, line_color="green", line_dash="dash",
                              line_width=1.5, annotation_text="Entrada",
                              annotation_position="right", row=1, col=1)
            if stop:
                fig.add_hline(y=stop, line_color="red", line_dash="dash",
                              line_width=1.5, annotation_text="Stop",
                              annotation_position="right", row=1, col=1)

        fig.add_trace(go.Scatter(x=rsi.index, y=rsi.values,
            name="RSI", line=dict(color="orange", width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_color="red",   line_dash="dash", row=2, col=1)
        fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)

        fig.update_layout(
            title=dict(text=titulo, font=dict(color=color_titulo, size=14)),
            height=450,
            margin=dict(l=40, r=40, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        fig.update_yaxes(range=[0, 100], row=2, col=1)
        fig.update_xaxes(showgrid=True, gridcolor="lightgrey")
        fig.update_yaxes(showgrid=True, gridcolor="lightgrey")

        grafico_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
        return stats, grafico_html

    except Exception as e:
        print(f"⚠️ _stats_y_grafico error: {e}")
        return {}, None



# ─────────────────────────────────────────────────────────────
# PANEL PRINCIPAL
# ─────────────────────────────────────────────────────────────


def _render_swing(ticker, evaluacion, capital, riesgo, cache, tipo="BREAKOUT"):
    """Construye el contexto de template con variables planas."""
    contexto  = evaluar_contexto_ibex(cache)
    factor    = factor_riesgo_mercado(cache)
    stats, grafico_html = _stats_y_grafico(ticker, cache, evaluacion)

    # Trigger = high * 1.001 (ya calculado en stats)
    trigger = stats.get("trigger", evaluacion.get("entrada", 0))

    # Sizing calculado desde el trigger, no desde precio actual
    sizing = resumen_operacion(
        trigger, evaluacion.get("stop", 0),
        evaluacion.get("objetivo", 0), capital, riesgo, factor
    ) if evaluacion.get("valido") else {}

    return render_template("swing.html",
        contexto_mercado = contexto,
        ticker           = ticker,
        nombre           = get_nombre(ticker),
        nombre_valor     = get_nombre(ticker),
        señal            = "COMPRA" if evaluacion.get("valido") else "NO OPERAR",
        tipo_estrategia  = tipo,
        precio_actual    = evaluacion.get("precio_actual", 0),
        entrada          = evaluacion.get("entrada", 0),
        stop             = evaluacion.get("stop", 0),
        objetivo         = evaluacion.get("objetivo", 0),
        rr               = evaluacion.get("rr", 0),
        setup_score      = evaluacion.get("setup_score", 0),
        nivel_calidad    = _nivel_calidad(evaluacion.get("setup_score", 0)),
        motivos          = evaluacion.get("motivos", []),
        sizing           = sizing,
        capital_total    = capital,
        riesgo_pct       = riesgo,
        grafico_file     = grafico_html,
        **stats,
    )

@swing_bp.route("/", methods=["GET", "POST"])
def panel():
    """Panel principal de swing trading."""
    cache    = _get_cache()
    contexto = evaluar_contexto_ibex(cache)

    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip()
        if not ticker:
            return render_template("swing.html", contexto_mercado=contexto,
                                   error="Selecciona un ticker")

        ticker = normalizar_ticker(ticker)
        capital, riesgo = _params_capital(request.form)
        factor = factor_riesgo_mercado(cache)
        # Precio broker — si el usuario introduce precio real de ejecución,
        # se usa para el sizing en vez del trigger técnico
        try:
            precio_broker = float(request.form.get("precio_broker", 0) or 0)
        except (ValueError, TypeError):
            precio_broker = 0.0

        # ── BACKTEST F1 ──────────────────────────────────
        if request.form.get("backtest"):
            try:
                from backtest.backtest_f1 import ejecutar_backtest_f1
                from core.data_provider import get_df
                df_bt = get_df(ticker, periodo="2y", cache=cache)
                precios   = df_bt["Close"].tolist()  if df_bt is not None else None
                volumenes = df_bt["Volume"].tolist() if df_bt is not None else None
                fechas    = list(df_bt.index)        if df_bt is not None else None
                highs     = df_bt["High"].tolist()   if df_bt is not None else None
                lows      = df_bt["Low"].tolist()    if df_bt is not None else None
                estrategia_bt = request.form.get("estrategia_bt", "breakout")
                print(f"🧪 BACKTEST F1: ticker={ticker} estrategia={estrategia_bt}")
                if precios and len(precios) >= 60:
                    resultado = ejecutar_backtest_f1(
                        precios, volumenes, fechas,
                        capital_inicial=capital,
                        riesgo_pct_trade=riesgo / 100,
                        highs=highs, lows=lows,
                        estrategia=estrategia_bt,
                    )
                    print(f"🧪 RESULTADO: trades={resultado['metricas']['total_trades']} r_acumulado={resultado.get('r_acumulado',0)}")
                    return render_template("swing.html",
                        contexto_mercado      = contexto,
                        ticker                = ticker,
                        nombre                = get_nombre(ticker),
                        modo                  = "backtest",
                        backtest_metricas     = resultado["metricas"],
                        backtest_trades       = resultado["trades"],
                        backtest_r_acumulado  = resultado.get("r_acumulado", 0),
                        backtest_estrategia   = estrategia_bt,
                    )
                return render_template("swing.html",
                    contexto_mercado = contexto,
                    error            = f"Datos insuficientes para backtest de {ticker}",
                )
            except Exception as e:
                return render_template("swing.html",
                    contexto_mercado = contexto,
                    error            = f"Error en backtest: {e}",
                )

        # ── ANÁLISIS NORMAL — evalúa BREAKOUT y PULLBACK ────────────────
        eval_breakout = _breakout.evaluar(ticker, cache)
        eval_pullback = _pullback.evaluar(ticker, cache)

        # Elegir la señal válida con mayor score (breakout tiene preferencia si empatan)
        if eval_breakout.get("valido") and eval_pullback.get("valido"):
            evaluacion = eval_breakout if eval_breakout.get("setup_score", 0) >= eval_pullback.get("setup_score", 0) else eval_pullback
        elif eval_breakout.get("valido"):
            evaluacion = eval_breakout
        elif eval_pullback.get("valido"):
            evaluacion = eval_pullback
        else:
            # Ninguno válido — mostrar el de mayor score pero combinar motivos de ambos
            score_b = eval_breakout.get("setup_score", 0)
            score_p = eval_pullback.get("setup_score", 0)
            evaluacion = eval_breakout if score_b >= score_p else eval_pullback
            # Combinar motivos de ambas estrategias para dar contexto completo
            motivos_b = eval_breakout.get("motivos", [])
            motivos_p = eval_pullback.get("motivos", [])
            evaluacion["_motivos_breakout"] = motivos_b
            evaluacion["_motivos_pullback"]  = motivos_p
            evaluacion["_score_breakout"]    = score_b
            evaluacion["_score_pullback"]    = score_p
            evaluacion["tipo"] = "BREAKOUT + PULLBACK"
        # Si hay precio broker, usarlo como precio real de entrada
        entrada_real = precio_broker if precio_broker > 0 else evaluacion.get("entrada", 0)
        sizing     = resumen_operacion(
            entrada_real, evaluacion.get("stop", 0),
            evaluacion.get("objetivo", 0), capital,
            riesgo, factor
        ) if evaluacion.get("valido") else {}

        decision = "COMPRA" if evaluacion.get("valido") else "NO OPERAR"
        stats, grafico_html = _stats_y_grafico(ticker, cache, evaluacion)
        # Rating fundamental + sizing multiplicativo
        try:
            datos_fund = obtener_datos_fundamentales(ticker)
            rating_fund = calcular_rating_fundamental(datos_fund)
        except Exception:
            rating_fund = {"color": "sin_datos", "emoji": "⚪", "etiqueta": "Sin datos",
                           "tamaño_pct": 100, "criterios": [], "disponible": False}
        try:
            sizing_rec = calcular_sizing_recomendado(
                rating_fund     = rating_fund,
                contexto_mercado= contexto,
                setup_score     = float(evaluacion.get("setup_score", 0) or 0),
                score_max       = 10.0,
                sistema         = "swing",
            )
        except Exception:
            sizing_rec = None
        return render_template("swing.html",
            contexto_mercado = contexto,
            ticker           = ticker,
            nombre           = get_nombre(ticker),
            señal            = decision,
            tipo_estrategia  = evaluacion.get("tipo", "BREAKOUT"),
            precio_actual    = evaluacion.get("precio_actual", 0),
            entrada          = evaluacion.get("entrada", 0),
            precio_broker    = precio_broker if precio_broker > 0 else None,
            entrada_real     = entrada_real,
            stop             = evaluacion.get("stop", 0),
            objetivo         = evaluacion.get("objetivo", 0),
            rr               = evaluacion.get("rr", 0),
            setup_score      = evaluacion.get("setup_score", 0),
            nivel_calidad    = _nivel_calidad(evaluacion.get("setup_score", 0)),
            score_breakout          = round(float(eval_breakout.get("setup_score", 0)), 1),
            score_pullback          = round(float(eval_pullback.get("setup_score", 0)), 1),
            motivo_bloqueo_breakout = eval_breakout.get("motivo_bloqueo", ""),
            motivo_bloqueo_pullback = eval_pullback.get("motivo_bloqueo", ""),
            motivos          = evaluacion.get("motivos", []),
            sizing           = sizing,
            capital_total    = capital,
            riesgo_pct       = riesgo,
            acciones           = sizing.get("acciones", 0),
            capital_invertido  = sizing.get("capital_invertido", 0),
            riesgo_por_accion  = sizing.get("riesgo_por_accion", 0),
            riesgo_operacion   = sizing.get("riesgo_operacion", 0),
            beneficio_potencial= sizing.get("beneficio_potencial", 0),
            precio_activacion  = evaluacion.get("precio_activacion"),
            vcp                = evaluacion.get("vcp", False),
            modo             = "analisis",
            grafico_file     = grafico_html,
            rating_fund      = rating_fund,
            sizing_rec       = sizing_rec,
            **stats,
        )

    return render_template("swing.html", contexto_mercado=contexto)


# ─────────────────────────────────────────────────────────────
# ANÁLISIS INDIVIDUAL
# ─────────────────────────────────────────────────────────────

@swing_bp.route("/breakout", methods=["POST"])
def breakout():
    """Analiza un ticker con estrategia BREAKOUT."""
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return redirect(url_for("swing.panel"))
    cache           = _get_cache()
    capital, riesgo = _params_capital(request.form)
    return _render_swing(ticker, _breakout.evaluar(ticker, cache), capital, riesgo, cache, "BREAKOUT")


@swing_bp.route("/pullback", methods=["POST"])
def pullback():
    """Analiza un ticker con estrategia PULLBACK."""
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return redirect(url_for("swing.panel"))
    cache           = _get_cache()
    capital, riesgo = _params_capital(request.form)
    return _render_swing(ticker, _pullback.evaluar(ticker, cache), capital, riesgo, cache, "PULLBACK")


@swing_bp.route("/analizar", methods=["POST"])
def analizar():
    """Evalúa un ticker con AMBAS estrategias simultáneamente."""
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return redirect(url_for("swing.panel"))

    cache           = _get_cache()
    capital, riesgo = _params_capital(request.form)
    factor          = factor_riesgo_mercado(cache)

    resultado = _scanner.evaluar_ticker(ticker, cache)

    # Calcular operación para la señal válida (breakout tiene preferencia)
    operacion = None
    señal_activa = None

    for tipo in ("breakout", "pullback"):
        s = resultado.get(tipo, {})
        if s.get("valido"):
            señal_activa = s
            operacion = resumen_operacion(
                entrada        = s["entrada"],
                stop           = s["stop"],
                objetivo       = s["objetivo"],
                capital_total  = capital,
                riesgo_pct     = riesgo,
                factor_mercado = factor,
            )
            break

    return render_template(
        "swing.html",
        ticker           = ticker,
        nombre_valor     = get_nombre(ticker),
        señal_breakout   = resultado["breakout"],
        señal_pullback   = resultado["pullback"],
        señal            = señal_activa,
        operacion        = operacion,
        capital_total    = capital,
        riesgo_pct       = riesgo,
        contexto_mercado = resultado["contexto"],
        tipo_estrategia  = "DUAL",
    )


# ─────────────────────────────────────────────────────────────
# ESCÁNER
# ─────────────────────────────────────────────────────────────

@swing_bp.route("/scanner", methods=["GET"])
def scanner():
    """Ejecuta el escáner completo sobre IBEX + Continuo."""
    cache = _get_cache()

    universo = request.args.get("universo", "todo")
    tickers  = {"ibex": IBEX35, "continuo": CONTINUO}.get(universo)

    resultados = _scanner.escanear_todo(tickers=tickers, cache=cache, top_n=20)

    return render_template(
        "swing_scanner.html",
        **resultados,
        universo=universo,
    )


# ─────────────────────────────────────────────────────────────
# API ESCÁNER JSON — llamado desde el modal JS de swing.html
# GET /swing/scanner/breakouts?mercado=ibex35&tf=1d&tipo=breakouts
# ─────────────────────────────────────────────────────────────

@swing_bp.route("/scanner/breakouts", methods=["GET"])
def scanner_api():
    """Escáner de señales. Devuelve JSON para el modal JS."""
    try:
        mercado = request.args.get("mercado", "ibex35")
        tipo    = request.args.get("tipo", "breakouts")
        cache   = _get_cache()

        tickers = IBEX35 if mercado == "ibex35" else CONTINUO

        resultados = _scanner.escanear_todo(tickers=tickers, cache=cache, top_n=20)

        señales = resultados.get("señales", [])

        # Filtrar por tipo si se pide
        if tipo == "breakouts":
            señales = [s for s in señales if s.get("tipo", "").upper() == "BREAKOUT"]
        elif tipo == "pullbacks":
            señales = [s for s in señales if s.get("tipo", "").upper() == "PULLBACK"]
        # "ambos" → no filtrar, devolver todos

        breakouts = sum(1 for s in señales if s.get("tipo", "").upper() == "BREAKOUT")
        pullbacks = sum(1 for s in señales if s.get("tipo", "").upper() == "PULLBACK")

        def _safe(obj):
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return obj

        import json
        payload = {
            "resultados":   señales,
            "total":        len(señales),
            "breakouts":    breakouts,
            "pullbacks":    pullbacks,
            "from_cache":   resultados.get("from_cache", False),
            "cache_age_minutes": resultados.get("cache_age_minutes", 0),
        }
        # Serializar con manejo de numpy
        return current_app.response_class(
            json.dumps(payload, default=_safe),
            mimetype="application/json"
        )

    except Exception as e:
        return jsonify({"error": str(e), "resultados": [], "total": 0}), 500


@swing_bp.route("/config", methods=["GET"])
def config():
    """Página de configuración del sistema Swing Trading."""
    return render_template("config_swing.html")
