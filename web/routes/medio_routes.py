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

    return {
        "ticker":           ticker,
        "precio_actual":    señal.get("precio_actual") or entrada,
        "decision":         "COMPRA" if señal.get("valido") else "NO OPERAR",
        "score":            señal.get("setup_score", 3),
        "score_max":        señal.get("setup_max", 10),
        "semanas_historico": señal.get("semanas", 260),
        "entrada":          entrada,
        "stop":             stop,
        "riesgo_pct":       riesgo_pct,
        "motivos":          _normalizar_motivos(señal.get("motivos", [])),
        "detalles":         señal.get("detalles", {}),
        "advertencias":     señal.get("advertencias", []),
        "fecha_desde":      señal.get("fecha_desde", ""),
        "fecha_hasta":      señal.get("fecha_hasta", ""),
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
    señal           = _medio.evaluar(ticker, cache)
    contexto        = evaluar_contexto_ibex(cache)
    factor          = factor_riesgo_mercado(cache)
    resultado       = _construir_resultado(ticker, señal)

    operacion = None
    if señal.get("valido"):
        try:
            operacion = resumen_operacion(
                entrada        = señal["entrada"],
                stop           = señal["stop"],
                objetivo       = señal.get("objetivo"),
                capital_total  = capital,
                riesgo_pct     = riesgo,
                factor_mercado = factor,
            )
        except Exception:
            pass

    return render_template(
        "medio.html",
        resultado        = resultado,
        operacion        = operacion,
        capital_total    = capital,
        riesgo_pct       = riesgo,
        contexto_mercado = contexto,
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
    return render_template("medio.html", contexto_mercado=evaluar_contexto_ibex(_get_cache()))
