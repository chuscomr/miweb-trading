# web/routes/medio_routes.py

from flask import Blueprint, request, redirect, url_for, render_template, current_app
from core.universos import get_nombre, normalizar_ticker, IBEX35, CONTINUO
from core.contexto_mercado import evaluar_contexto_ibex, factor_riesgo_mercado
from core.riesgo import resumen_operacion
from estrategias.medio import MedioPlazo, ScannerMedio
from estrategias.medio.backtest_medio import ejecutar_backtest_medio_plazo
from estrategias.medio.backtest_sistema_medio import ejecutar_backtest_sistema_completo
from estrategias.posicional.datos_posicional import obtener_datos_semanales

medio_bp = Blueprint("medio", __name__, url_prefix="/medio")

_medio   = MedioPlazo()
_scanner = ScannerMedio()


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _grafico_semanal(ticker, señal):
    """Genera gráfico Plotly semanal con precio + MM20 + MM50 + RSI."""
    try:
        import pandas as pd
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import numpy as np
        from core.data_provider import get_df

        df_d = get_df(ticker, periodo="3y")
        if df_d is None or df_d.empty:
            return None

        df = pd.DataFrame({
            "Open":   df_d["Open"].resample("W-FRI").first(),
            "High":   df_d["High"].resample("W-FRI").max(),
            "Low":    df_d["Low"].resample("W-FRI").min(),
            "Close":  df_d["Close"].resample("W-FRI").last(),
            "Volume": df_d["Volume"].resample("W-FRI").sum(),
        }).dropna()
        df = df[df["Close"] > 0]
        if len(df) < 30:
            return None

        serie  = df["Close"]
        fechas = df.index
        mm20   = serie.rolling(20).mean()
        mm50   = serie.rolling(50).mean()

        # RSI semanal
        delta = serie.diff()
        gain  = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
        rsi   = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

        valido = señal.get("valido", False)
        titulo = f"{ticker} – {'COMPRA' if valido else 'NO OPERAR'}"
        color_titulo = "green" if valido else "red"

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7, 0.3], vertical_spacing=0.05)

        fig.add_trace(go.Scatter(x=fechas, y=serie.values,
            name="Precio", line=dict(color="black", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=fechas, y=mm20.values,
            name="MM20", line=dict(color="blue", width=1, dash="dash")), row=1, col=1)
        fig.add_trace(go.Scatter(x=fechas, y=mm50.values,
            name="MM50", line=dict(color="purple", width=1, dash="dot")), row=1, col=1)

        # Líneas trigger y stop si hay compra
        if valido:
            trigger = señal.get("trigger") or señal.get("entrada")
            stop    = señal.get("stop")
            if trigger:
                fig.add_hline(y=trigger, line_color="green", line_dash="dash",
                              line_width=1.5, annotation_text="Trigger",
                              annotation_position="right", row=1, col=1)
            if stop:
                fig.add_hline(y=stop, line_color="red", line_dash="dash",
                              line_width=1.5, annotation_text="Stop",
                              annotation_position="right", row=1, col=1)

        fig.add_trace(go.Scatter(x=fechas, y=rsi.values,
            name="RSI", line=dict(color="orange", width=1.5)), row=2, col=1)
        fig.add_hline(y=55, line_color="red",   line_dash="dash", line_width=0.8, row=2, col=1)
        fig.add_hline(y=40, line_color="green", line_dash="dash", line_width=0.8, row=2, col=1)

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

        return fig.to_html(full_html=False, include_plotlyjs="cdn")
    except Exception as e:
        print(f"⚠️ _grafico_semanal error: {e}")
        return None


def _params_capital(form):
    try:
        capital_total = float(form.get("capital_total", 10000))
        riesgo_pct    = float(form.get("riesgo_pct", 1.0))
    except (ValueError, TypeError):
        capital_total = 10000.0
        riesgo_pct    = 1.0
    return capital_total, riesgo_pct


def _normalizar_motivos(motivos_raw):
    """Convierte cualquier formato de motivo al dict {ok, texto} que espera el template."""
    result = []
    for m in (motivos_raw or []):
        if isinstance(m, dict) and "ok" in m and "texto" in m:
            texto_limpio = m["texto"].replace("❌ ", "").replace("✅ ", "").strip()
            result.append({"ok": m["ok"], "texto": texto_limpio})
        else:
            texto = str(m)
            ok    = not any(x in texto for x in ["❌", "False", "NO", "Sin"])
            result.append({"ok": ok, "texto": texto.replace("❌ ", "").replace("✅ ", "")})
    return result


def _construir_resultado(ticker, señal):
    """Convierte la señal al dict que espera medio.html."""
    entrada    = float(señal.get("entrada") or 0)
    stop       = float(señal.get("stop")    or 0)
    riesgo_pct = round((entrada - stop) / max(entrada, 0.01) * 100, 2) if entrada else 0

    # Trigger — viene directamente de la señal o se calcula
    trigger = señal.get("trigger") or (round(entrada * 1.001, 2) if entrada else 0)

    # Objetivo = 6R desde trigger
    objetivo = señal.get("objetivo")
    if not objetivo and trigger and stop and trigger > stop:
        R_unit  = trigger - stop
        objetivo = round(trigger + 6.0 * R_unit, 2)

    # Detalles técnicos — incluye MM50, MM200 del nuevo evaluar()
    detalles = señal.get("detalles", {})

    return {
        "ticker":            ticker,
        "precio_actual":     señal.get("precio_actual") or entrada,
        "decision":          "COMPRA" if señal.get("valido") else "NO OPERAR",
        "score":             señal.get("setup_score", 0),
        "score_max":         señal.get("setup_max", 10),
        "semanas_historico": señal.get("semanas", 260),
        "entrada":           entrada,
        "trigger":           trigger,
        "stop":              stop,
        "objetivo":          objetivo,
        "riesgo_pct":        riesgo_pct,
        "semaforo":          señal.get("semaforo"),
        "motivos":           _normalizar_motivos(señal.get("motivos", [])),
        "detalles":          detalles,
        "advertencias":      señal.get("advertencias", []),
        "fecha_desde":       señal.get("fecha_desde", ""),
        "fecha_hasta":       señal.get("fecha_hasta", ""),
    }


# ── PANEL PRINCIPAL ───────────────────────────────────────────

@medio_bp.route("/", methods=["GET"])
def panel():
    contexto = evaluar_contexto_ibex(_get_cache())
    return render_template("medio.html", contexto_mercado=contexto)


# ── ANÁLISIS INDIVIDUAL ───────────────────────────────────────

@medio_bp.route("/analizar", methods=["POST"])
def analizar():
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return redirect(url_for("medio.panel"))

    cache           = _get_cache()
    capital, riesgo = _params_capital(request.form)
    contexto        = evaluar_contexto_ibex(cache)

    # ── BACKTEST TICKER ───────────────────────────────────────
    if request.form.get("backtest"):
        try:
            from estrategias.posicional.datos_posicional import obtener_datos_semanales
            df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)
            if df is None or df.empty:
                return render_template("medio.html",
                    contexto_mercado=contexto,
                    resultado={"ticker": ticker, "decision": "NO OPERAR", "motivos": [], "score": 0, "score_max": 10},
                    modo="backtest",
                    resultado_bt={"ticker": ticker, "total_trades": 0, "metricas": {}, "trades": []},
                )
            from estrategias.medio.backtest_medio import ejecutar_backtest_medio_plazo
            res    = ejecutar_backtest_medio_plazo(df, ticker)
            trades = res.get("trades", [])
            for t in trades:
                for k in ("fecha_entrada", "fecha_salida"):
                    v = t.get(k)
                    if hasattr(v, "date"):
                        t[k] = v.date()
            m   = res.get("metricas", {})
            exp = m.get("expectancy_R", 0)
            resultado_bt = {
                "ticker":       ticker,
                "total_trades": len(trades),
                "metricas":     m,
                "trades":       trades,
                "color":        "verde" if exp >= 0.2 else "amarillo" if exp > 0 else "rojo",
            }
        except Exception as e:
            resultado_bt = {"ticker": ticker, "total_trades": 0, "metricas": {}, "trades": [], "error": str(e)}

        return render_template("medio.html",
            contexto_mercado = contexto,
            resultado        = {"ticker": ticker, "decision": "NO OPERAR", "motivos": [], "score": 0, "score_max": 10},
            modo             = "backtest",
            resultado_bt     = resultado_bt,
        )
    señal           = _medio.evaluar(ticker, cache)
    contexto        = evaluar_contexto_ibex(cache)
    factor          = factor_riesgo_mercado(cache)
    resultado       = _construir_resultado(ticker, señal)

    # Determinar tier del ticker
    from estrategias.medio.config_medio import TIER_1_RIESGO_PCT, TIER_2_RIESGO_PCT
    tier        = 1 if ticker in IBEX35 else 2
    riesgo_tier = TIER_1_RIESGO_PCT if tier == 1 else TIER_2_RIESGO_PCT
    # Si el usuario especifica riesgo manual, respetar solo para tier 1
    riesgo_efectivo = riesgo if tier == 1 else min(riesgo * 0.5, TIER_2_RIESGO_PCT)

    operacion = None
    if señal.get("valido"):
        try:
            trigger_val = resultado.get("trigger") or resultado.get("entrada") or 0
            operacion = resumen_operacion(
                entrada        = trigger_val,
                stop           = señal["stop"],
                objetivo       = señal.get("objetivo"),
                capital_total  = capital,
                riesgo_pct     = riesgo_efectivo,
                factor_mercado = factor,
            )
        except Exception:
            pass

    # Stats semanales para presentación (estilo swing)
    stats_semanales = {}
    try:
        import pandas as pd
        from core.data_provider import get_df
        df_d = get_df(ticker, periodo="2y", cache=cache)
        df_w = None
        if df_d is not None and not df_d.empty:
            df_w = pd.DataFrame({
                "Open":   df_d["Open"].resample("W-FRI").first(),
                "High":   df_d["High"].resample("W-FRI").max(),
                "Low":    df_d["Low"].resample("W-FRI").min(),
                "Close":  df_d["Close"].resample("W-FRI").last(),
                "Volume": df_d["Volume"].resample("W-FRI").sum(),
            }).dropna()
            df_w = df_w[df_w["Close"] > 0]
        if df_w is not None and len(df_w) >= 20:
            precio = resultado["precio_actual"]
            max10  = round(float(df_w["High"].tail(10).max()), 2)
            min10  = round(float(df_w["Low"].tail(10).min()), 2)
            mm20   = round(float(df_w["Close"].rolling(20).mean().iloc[-1]), 2)
            stats_semanales = {
                "max_reciente": max10,
                "min_reciente": min10,
                "mm20s":        mm20,
                "dist_max":     round((precio - max10) / max10 * 100, 2) if max10 else 0,
                "dist_min":     round((precio - min10) / min10 * 100, 2) if min10 else 0,
                "dist_mm20":    round((precio - mm20)  / mm20  * 100, 2) if mm20  else 0,
            }
    except Exception:
        pass

    # Gráfico semanal — solo si hay compra
    grafico_html = _grafico_semanal(ticker, señal) if señal.get("valido") else None

    return render_template(
        "medio.html",
        resultado        = resultado,
        operacion        = operacion,
        capital_total    = capital,
        riesgo_pct       = riesgo_efectivo,
        tier             = tier,
        grafico_html     = grafico_html,
        contexto_mercado = contexto,
        **stats_semanales,
    )


# ── BACKTEST INDIVIDUAL ───────────────────────────────────────

@medio_bp.route("/backtest", methods=["GET", "POST"])
def backtest():
    resultado = None
    error     = None
    ticker    = ""

    if request.method == "POST":
        ticker = normalizar_ticker(request.form.get("ticker", ""))
        if ticker:
            try:
                df, _ = obtener_datos_semanales(ticker, periodo_años=5, validar=False)
                if df is None or df.empty:
                    error = f"Sin datos para {ticker}"
                else:
                    res      = ejecutar_backtest_medio_plazo(df, ticker)
                    trades   = res.get("trades", [])
                    metricas = res.get("metricas", {})
                    exp      = metricas.get("expectancy_R", 0)
                    color    = "verde" if exp >= 0.2 else "amarillo" if exp > 0 else "rojo"
                    # Formatear fechas para el template
                    for t in trades:
                        for k in ("fecha_entrada", "fecha_salida"):
                            v = t.get(k)
                            if hasattr(v, "date"):
                                t[k] = v.date()
                    resultado = {
                        "ticker":       ticker,
                        "total_trades": len(trades),
                        "metricas":     metricas,
                        "trades":       trades,
                        "color":        color,
                        "evaluacion":   "RENTABLE" if color == "verde" else
                                        "MARGINAL" if color == "amarillo" else "NO RENTABLE",
                    }
            except Exception as e:
                error = str(e)

    return render_template(
        "backtest_medio.html",
        resultado = resultado,
        error     = error,
        ticker    = ticker,
    )


# ── ESCÁNER ───────────────────────────────────────────────────

@medio_bp.route("/escaner", methods=["GET", "POST"])
def escaner():
    cache    = _get_cache()
    universo = request.form.get("universo") or request.args.get("universo", "")

    # Sin universo seleccionado → mostrar selector
    if not universo:
        return render_template("escaner_medio.html", resultado=None, universo=None)

    tickers = {"ibex": IBEX35, "continuo": CONTINUO}.get(universo, IBEX35)

    # Escanear SOLO el universo seleccionado
    señales_raw = _scanner.estrategia.escanear(tickers=tickers, cache=cache)

    def _normalizar(s):
        ticker    = s.get("ticker", "")
        nombre    = ticker.replace(".MC", "")
        entrada   = float(s.get("entrada")       or 0)
        stop      = float(s.get("stop")          or 0)
        precio    = float(s.get("precio_actual") or entrada or 0)
        riesgo    = round((entrada - stop) / max(entrada, 0.01) * 100, 1) if entrada and stop else 0
        score     = s.get("setup_score", 0)
        score_max = s.get("setup_max", 10)
        return {
            **s,
            "empresa":    nombre,
            "nombre":     nombre,
            "precio":     precio,
            "entrada":    entrada,
            "stop":       stop,
            "riesgo_pct": riesgo,
            "score":      f"{score}/{score_max}",
            "setup_score": score,
        }

    señales     = [_normalizar(s) for s in señales_raw]
    compras     = [s for s in señales if s.get("decision") == "COMPRA"]
    vigilancia  = [s for s in señales if s.get("decision") == "VIGILANCIA"]
    descartados = [s for s in señales if s.get("decision") not in ("COMPRA", "VIGILANCIA")]

    # Para vigilancia: extraer motivo legible
    for s in vigilancia:
        motivos = s.get("motivos", [])
        if motivos:
            m = motivos[0]
            s["motivo"] = m.get("texto", str(m)) if isinstance(m, dict) else str(m)
        else:
            s["motivo"] = "En vigilancia"

    compras.sort(key=lambda x: x.get("setup_score", 0), reverse=True)
    vigilancia.sort(key=lambda x: x.get("setup_score", 0), reverse=True)

    resultado = {
        "universo":          universo,
        "compras":           compras,
        "vigilancia":        vigilancia,
        "descartados":       descartados,
        "total_analizados":  len(señales),
        "total_compras":     len(compras),
        "total_vigilancia":  len(vigilancia),
        "total_descartados": len(descartados),
        "total_errores":     0,
        "contexto":          {},
        "cancelado":         False,
    }

    return render_template("escaner_medio.html", resultado=resultado, universo=universo)


# ── BACKTEST SISTEMA ──────────────────────────────────────────

@medio_bp.route("/backtest-sistema", methods=["GET", "POST"])
def backtest_sistema():
    resultado = None
    if request.method == "POST":
        usar_continuo = request.form.get("usar_continuo") == "1"
        try:
            resultado = ejecutar_backtest_sistema_completo(
                universo=None,
                verbose=True,
                usar_continuo=usar_continuo,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            resultado = None
    return render_template("backtest_sistema_medio.html", resultado=resultado)


# ── CONFIGURACIÓN ─────────────────────────────────────────────

@medio_bp.route("/config", methods=["GET"])
def config():
    from estrategias.medio import config_medio as cfg
    config_data = {
        "timeframe":       "Semanal",
        "estrategia":      "Pullback en tendencia alcista",
        "min_semanas":     cfg.MIN_SEMANAS_HISTORICO,
        "volatilidad_min": f"{cfg.VOL_MIN_PCT}%",
        "pullback_min":    f"{cfg.PULLBACK_MIN_PCT}%",
        "pullback_max":    f"{cfg.PULLBACK_MAX_PCT}%",
        "riesgo_min":      f"{cfg.RIESGO_MIN_PCT}%",
        "riesgo_max":      f"{cfg.RIESGO_MAX_PCT}%",
        "r_proteger":      f"+{cfg.R_PARA_PROTEGER}R",
        "r_trailing":      f"+{cfg.R_PARA_TRAILING}R",
        "capital_inicial": f"{cfg.CAPITAL_INICIAL:,} €",
        "riesgo_trade":    f"{cfg.RIESGO_POR_TRADE_PCT}%",
        "tier1_riesgo":    f"{cfg.TIER_1_RIESGO_PCT}%",
        "tier2_riesgo":    f"{cfg.TIER_2_RIESGO_PCT}%",
    }
    return render_template("config_medio.html", config=config_data)
