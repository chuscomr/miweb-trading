import os
import sys
from dotenv import load_dotenv
load_dotenv()

# ════════════════════════════════════════════════════════════════
# 1️⃣ PATH
# ════════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ════════════════════════════════════════════════════════════════
# 2️⃣ IMPORTS
# ════════════════════════════════════════════════════════════════
import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_caching import Cache

# ════════════════════════════════════════════════════════════════
# 3️⃣ BLUEPRINTS
# ════════════════════════════════════════════════════════════════
from web.routes.swing_routes      import swing_bp
from web.routes.medio_routes      import medio_bp
from web.routes.posicional_routes import posicional_bp
from web.routes.backtest_routes   import backtest_bp
from web.routes.cartera_routes    import cartera_bp
from web.routes.analisis_routes   import analisis_bp
from web.routes.alertas_routes    import alertas_bp
from indicadores                  import indicadores_bp
from fundamentales.routes         import fundamentales_bp

# ════════════════════════════════════════════════════════════════
# 4️⃣ APLICACIÓN
# ════════════════════════════════════════════════════════════════
application = Flask(__name__)
application.secret_key = os.environ.get("SECRET_KEY", "dev-key-temporal")

# ════════════════════════════════════════════════════════════════
# 5️⃣ CACHE
# ════════════════════════════════════════════════════════════════
cache = Cache(application, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
})

# Inyectar cache para que los blueprints la recuperen via:
#   current_app.config["CACHE_INSTANCE"]
application.config["CACHE_INSTANCE"] = cache

# ════════════════════════════════════════════════════════════════
# 6️⃣ REGISTRAR BLUEPRINTS
# ════════════════════════════════════════════════════════════════
application.register_blueprint(swing_bp)        # /swing/
application.register_blueprint(medio_bp)        # /medio/
application.register_blueprint(posicional_bp)   # /posicional/
application.register_blueprint(backtest_bp)     # /backtest/
application.register_blueprint(cartera_bp)      # /cartera/
application.register_blueprint(analisis_bp)     # /analisis/
application.register_blueprint(alertas_bp)      # /alertas/
application.register_blueprint(indicadores_bp)  # /indicadores/
application.register_blueprint(fundamentales_bp, url_prefix="/fundamentales")  # /fundamentales/

print(">>> APP.PY CARGADO <<<")

# ════════════════════════════════════════════════════════════════
# RUTA RAÍZ — Hub selector de sistemas
# ════════════════════════════════════════════════════════════════

@application.route("/", methods=["GET"])
def inicio():
    """Hub principal - selector de sistemas"""
    return render_template("hub.html")


# ════════════════════════════════════════════════════════════════
# POPUPS ESCÁNER (iframes en index_swing.html)
# ════════════════════════════════════════════════════════════════

@application.route("/popup/ibex")
def popup_ibex():
    from estrategias.swing.scanner_swing import escanear_mercado
    from core.universos import IBEX35
    escaneo = cache.get("escaneo_ibex")
    if not escaneo:
        escaneo = escanear_mercado(IBEX35, tipo_scan="ambos")
        cache.set("escaneo_ibex", escaneo, timeout=600)
    return render_template("ibex.html", escaneo_ibex=escaneo)


@application.route("/popup/continuo")
def popup_continuo():
    from estrategias.swing.scanner_swing import escanear_mercado
    from core.universos import CONTINUO
    escaneo = cache.get("escaneo_continuo")
    if not escaneo:
        escaneo = escanear_mercado(CONTINUO, tipo_scan="ambos")
        cache.set("escaneo_continuo", escaneo, timeout=600)
    return render_template("continuo.html", escaneo_continuo=escaneo)


# ════════════════════════════════════════════════════════════════
# SWING — Breakout y Pullback (rutas POST con sizing)
# ════════════════════════════════════════════════════════════════

@application.route("/swing/breakout", methods=["POST"])
def swing_breakout():
    """Estrategia BREAKOUT con cálculo de sizing"""
    ticker = request.form.get("ticker", "").upper()
    if not ticker:
        return redirect(url_for("swing_sistema"))

    try:
        from estrategias.swing.breakout import BreakoutSwing
        from core.universos import get_nombre
        from core.contexto_mercado import obtener_contexto_mercado

        capital_total    = float(request.form.get("capital_total", 10000))
        riesgo_pct       = float(request.form.get("riesgo_pct", 1))
        estrategia       = BreakoutSwing()
        resultado        = estrategia.evaluar(ticker, cache)
        contexto_mercado = obtener_contexto_mercado(cache)

        contexto = {
            "ticker":           ticker,
            "nombre_valor":     get_nombre(ticker),
            "tipo_estrategia":  "BREAKOUT",
            "precio_actual":    resultado.get("precio_actual"),
            "contexto_mercado": contexto_mercado,
        }

        if resultado.get("valido"):
            riesgo_por_accion = resultado["entrada"] - resultado["stop"]
            acciones = int((capital_total * riesgo_pct / 100) / riesgo_por_accion) if riesgo_por_accion > 0 else 0
            contexto.update({
                "señal":               "COMPRA",
                "entrada":             resultado["entrada"],
                "stop":                resultado["stop"],
                "objetivo":            resultado["objetivo"],
                "rr":                  resultado.get("rr"),
                "setup_score":         resultado.get("setup_score"),
                "acciones":            max(acciones, 0),
                "capital_total":       capital_total,
                "riesgo_pct":          riesgo_pct,
                "riesgo_por_accion":   round(riesgo_por_accion, 2),
                "riesgo_operacion":    round(acciones * riesgo_por_accion, 2),
                "capital_invertido":   round(acciones * resultado["entrada"], 2),
                "beneficio_potencial": round(resultado["objetivo"] - resultado["entrada"], 2),
                "motivos":             resultado.get("motivos", []),
            })
        else:
            contexto.update({
                "señal":   "NO OPERAR",
                "motivos": resultado.get("motivos") or [{"ok": False, "texto": "❌ No cumple condiciones técnicas"}],
            })

        return render_template("swing.html", **contexto)

    except Exception as e:
        print(f"❌ Error BREAKOUT: {e}")
        return redirect(url_for("swing_sistema"))


@application.route("/swing/pullback", methods=["POST"])
def swing_pullback():
    """Estrategia PULLBACK con cálculo de sizing"""
    ticker = request.form.get("ticker", "").upper()
    if not ticker:
        return redirect(url_for("swing_sistema"))

    try:
        from estrategias.swing.pullback import PullbackSwing
        from core.universos import get_nombre
        from core.contexto_mercado import obtener_contexto_mercado

        capital_total    = float(request.form.get("capital_total", 10000))
        riesgo_pct       = float(request.form.get("riesgo_pct", 1))
        estrategia       = PullbackSwing()
        resultado        = estrategia.evaluar(ticker, cache)
        contexto_mercado = obtener_contexto_mercado(cache)

        contexto = {
            "ticker":           ticker,
            "nombre_valor":     get_nombre(ticker),
            "tipo_estrategia":  "PULLBACK",
            "precio_actual":    resultado.get("precio_actual"),
            "contexto_mercado": contexto_mercado,
        }

        if resultado.get("valido"):
            riesgo_por_accion = resultado["entrada"] - resultado["stop"]
            acciones = int((capital_total * riesgo_pct / 100) / riesgo_por_accion) if riesgo_por_accion > 0 else 0
            contexto.update({
                "señal":               "COMPRA",
                "entrada":             resultado["entrada"],
                "stop":                resultado["stop"],
                "objetivo":            resultado["objetivo"],
                "rr":                  resultado.get("rr"),
                "setup_score":         resultado.get("setup_score"),
                "acciones":            max(acciones, 0),
                "capital_total":       capital_total,
                "riesgo_pct":          riesgo_pct,
                "riesgo_por_accion":   round(riesgo_por_accion, 2),
                "riesgo_operacion":    round(acciones * riesgo_por_accion, 2),
                "capital_invertido":   round(acciones * resultado["entrada"], 2),
                "beneficio_potencial": round(resultado["objetivo"] - resultado["entrada"], 2),
                "motivos":             resultado.get("motivos", []),
            })
        else:
            contexto.update({
                "señal":   "NO OPERAR",
                "motivos": resultado.get("motivos") or [{"ok": False, "texto": "❌ No cumple condiciones técnicas"}],
            })

        return render_template("swing.html", **contexto)

    except Exception as e:
        print(f"❌ Error PULLBACK: {e}")
        return redirect(url_for("swing_sistema"))


# ════════════════════════════════════════════════════════════════
# SWING — Scanner API JSON
# ════════════════════════════════════════════════════════════════

@application.route("/swing/scanner/breakouts")
def scanner_breakouts():
    from estrategias.swing.scanner_swing import escanear_mercado
    from core.universos import IBEX35, CONTINUO

    mercado = request.args.get("mercado", "ibex35")
    tipo    = request.args.get("tipo", "breakout")
    if tipo not in ("breakout", "pullback"):
        tipo = "breakout"

    tickers    = IBEX35 if mercado == "ibex35" else CONTINUO
    resultados = escanear_mercado(tickers, tipo_scan=tipo)

    return jsonify({
        "ok":        True,
        "resultados": resultados,
        "total":     len(resultados),
        "breakouts": sum(1 for r in resultados if r.get("tipo_señal") == "BREAKOUT"),
        "pullbacks": sum(1 for r in resultados if r.get("tipo_señal") == "PULLBACK"),
        "mercado":   mercado,
        "tipo":      tipo,
    })


# ════════════════════════════════════════════════════════════════
# SENTIMIENTO IBEX 35
# ════════════════════════════════════════════════════════════════

@application.route("/api/sentimiento_rss", methods=["GET"])
@cache.cached(timeout=1800, key_prefix="sentimiento_ibex")
def api_sentimiento_rss():
    """Sentimiento IBEX 35 via RSS. Cache 30 min."""
    try:
        from sentimiento_ibex import analizar_sentimiento_ibex
        resultado = analizar_sentimiento_ibex(delay=0.25)
        return jsonify({"ok": True, **resultado})
    except Exception as e:
        print(f"❌ Error en /api/sentimiento_rss: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@application.route("/api/sentimiento", methods=["POST"])
def api_sentimiento_profundo():
    """Análisis profundo con Claude Haiku."""
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            return jsonify({"error": "Falta el campo 'prompt'"}), 400

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"error": "ANTHROPIC_API_KEY no configurada"}), 500

        import anthropic
        client  = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": data["prompt"]}],
        )
        return jsonify({"text": message.content[0].text})

    except Exception as e:
        print(f"❌ Error en /api/sentimiento: {e}")
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# GUARDAR PANTALLAZO
# ════════════════════════════════════════════════════════════════

@application.route("/guardar_pantallazo", methods=["POST"])
def guardar_pantallazo():
    from controlador import guardar_pantallazo_controlador
    ok, resultado = guardar_pantallazo_controlador(request.get_json())
    if not ok:
        return resultado, 400
    return jsonify({"ok": True, "archivo": resultado})


# ════════════════════════════════════════════════════════════════
# ARRANQUE LOCAL
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🚀  MiWeb — servidor Flask")
    print("=" * 65)
    print("  /                        ← Hub principal")
    print("  /swing/                  ← Swing Trading")
    print("  /swing/breakout          ← Breakout (POST)")
    print("  /swing/pullback          ← Pullback (POST)")
    print("  /swing/scanner/breakouts ← Scanner API JSON")
    print("  /medio/                  ← Medio Plazo")
    print("  /posicional/             ← Posicional")
    print("  /backtest/               ← Backtest")
    print("  /cartera/                ← Cartera")
    print("  /analisis/               ← Análisis técnico + fundamental")
    print("  /alertas/                ← Alertas")
    print("  /popup/ibex              ← Escáner IBEX (iframe)")
    print("  /popup/continuo          ← Escáner Continuo (iframe)")
    print("  /api/sentimiento_rss     ← Sentimiento IBEX (RSS)")
    print("  /api/sentimiento         ← Sentimiento profundo (Claude)")
    print("=" * 65 + "\n")

    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port, debug=True)
