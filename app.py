import os
import sys
from dotenv import load_dotenv
load_dotenv()

# ════════════════════════════════════════════════════════════════
# 1️⃣  PATH
# ════════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ════════════════════════════════════════════════════════════════
# 2️⃣  IMPORTS
# ════════════════════════════════════════════════════════════════
import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, jsonify, request
from flask_caching import Cache

# ════════════════════════════════════════════════════════════════
# 3️⃣  BLUEPRINTS
# ════════════════════════════════════════════════════════════════
from web.routes.swing_routes       import swing_bp
from web.routes.medio_routes       import medio_bp
from web.routes.posicional_routes  import posicional_bp
from web.routes.backtest_routes    import backtest_bp
from web.routes.cartera_routes     import cartera_bp
from web.routes.analisis_routes    import analisis_bp
from web.routes.alertas_routes     import alertas_bp
from web.routes.indicadores_routes import indicadores_bp
from contexto_bp                   import contexto_bp

# ════════════════════════════════════════════════════════════════
# 4️⃣  APLICACIÓN
# ════════════════════════════════════════════════════════════════
application = Flask(__name__)
application.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
application.secret_key = os.environ.get("SECRET_KEY", "dev-key-temporal")

# ════════════════════════════════════════════════════════════════
# 5️⃣  CACHE
# ════════════════════════════════════════════════════════════════
cache = Cache(application, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
})
application.config["CACHE_INSTANCE"] = cache

# ════════════════════════════════════════════════════════════════
# 6️⃣  REGISTRAR BLUEPRINTS
# ════════════════════════════════════════════════════════════════
application.register_blueprint(swing_bp)        # /swing/
application.register_blueprint(medio_bp)        # /medio/
application.register_blueprint(posicional_bp)   # /posicional/
application.register_blueprint(backtest_bp)     # /backtest/
application.register_blueprint(cartera_bp)      # /cartera/
application.register_blueprint(analisis_bp)     # /analisis/
application.register_blueprint(alertas_bp)      # /alertas/
application.register_blueprint(indicadores_bp)  # /indicadores/
application.register_blueprint(contexto_bp)     # /contexto/

print(">>> APP.PY CARGADO <<<")

# ════════════════════════════════════════════════════════════════
# 7️⃣  RUTAS RAÍZ (no pertenecen a ningún blueprint)
# ════════════════════════════════════════════════════════════════

@application.route("/", methods=["GET"])
def inicio():
    """Hub principal — selector de sistemas."""
    return render_template("hub.html")


@application.route("/debug/fechas/<ticker>")
def debug_fechas(ticker):
    """Diagnóstico: muestra RSI y datos del df para un ticker."""
    from core.data_provider import get_df
    from core.indicadores import calcular_rsi
    from datetime import date
    import math
    resultado = {}
    try:
        df = get_df(ticker.upper(), periodo="1y", cache=None)
        if df is not None:
            resultado["filas"] = len(df)
            resultado["columnas"] = list(df.columns)
            resultado["ultima_fecha"] = str(df.index[-1].date())
            resultado["close_tipo"] = str(type(df["Close"]))
            resultado["close_shape"] = str(df["Close"].shape)

            # Calcular RSI manualmente
            rsi_serie = calcular_rsi(df["Close"], 14)
            resultado["rsi_serie_tipo"] = str(type(rsi_serie))
            resultado["rsi_serie_len"] = len(rsi_serie)
            resultado["rsi_nan_count"] = int(rsi_serie.isna().sum())
            resultado["rsi_dropna_len"] = len(rsi_serie.dropna())
            resultado["rsi_ultimo"] = float(rsi_serie.iloc[-1]) if not rsi_serie.empty else None
            resultado["rsi_ultimo_isnan"] = math.isnan(float(rsi_serie.iloc[-1])) if resultado["rsi_ultimo"] is not None else True

            # Añadir al df y ver
            df["RSI"] = rsi_serie
            resultado["df_rsi_ultimo"] = float(df["RSI"].iloc[-1])
            resultado["df_rsi_isnan"] = math.isnan(float(df["RSI"].iloc[-1]))
        else:
            resultado["error"] = "df es None"
    except Exception as e:
        import traceback
        resultado["error"] = str(e)
        resultado["traceback"] = traceback.format_exc()
    return jsonify(resultado)


@application.route("/admin/clear-cache")
def clear_cache():
    """Limpia la caché Flask de datos de mercado."""
    try:
        cache.clear()
        return jsonify({"ok": True, "msg": "Caché limpiada correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@application.route("/popup/ibex")
def popup_ibex():
    from estrategias.swing.scanner_swing import escanear_mercado
    from core.universos import IBEX35
    from core.contexto_mercado import evaluar_contexto_ibex

    escaneo = cache.get("escaneo_ibex")
    if not escaneo:
        contexto = evaluar_contexto_ibex(cache)
        estado   = contexto.get("estado", "TRANSICION") if contexto else "TRANSICION"

        señales = escanear_mercado(IBEX35, tipo_scan="ambos")
        # Todas las señales válidas (umbral 5.5) — clasificadas por nivel
        validas = [s for s in señales if s.get("score", 0) >= 5.5]
        alta_prob  = [s for s in validas if s.get("nivel") == "alta_probabilidad"]
        confirmada = [s for s in validas if s.get("nivel") == "confirmada"]
        compra     = [s for s in validas if s.get("nivel") == "compra"]

        # Aviso operativo según contexto
        if estado == "ALCISTA":
            aviso = None
        elif estado == "BAJISTA":
            aviso = "⚠️ Mercado bajista — operar solo Alta Probabilidad"
        else:
            aviso = "⚠️ Mercado en transición — preferir Confirmada o Alta Probabilidad"

        escaneo = {
            "total_analizados": len(IBEX35),
            "total_señales":    len(validas),
            "alta_prob":        alta_prob,
            "confirmada":       confirmada,
            "compra":           compra,
            "contexto":         estado,
            "aviso":            aviso,
            # Legacy para compatibilidad
            "compras":          validas,
            "vigilancia":       [],
            "total_compras":    len(validas),
            "total_vigilancia": 0,
        }
        cache.set("escaneo_ibex", escaneo, timeout=600)
    return render_template("ibex.html", escaneo_ibex=escaneo)


@application.route("/popup/continuo")
def popup_continuo():
    from estrategias.swing.scanner_swing import escanear_mercado
    from core.universos import CONTINUO
    from core.contexto_mercado import evaluar_contexto_ibex

    escaneo = cache.get("escaneo_continuo")
    if not escaneo:
        contexto = evaluar_contexto_ibex(cache)
        estado   = contexto.get("estado", "TRANSICION") if contexto else "TRANSICION"

        señales = escanear_mercado(CONTINUO, tipo_scan="ambos")
        validas    = [s for s in señales if s.get("score", 0) >= 5.5]
        alta_prob  = [s for s in validas if s.get("nivel") == "alta_probabilidad"]
        confirmada = [s for s in validas if s.get("nivel") == "confirmada"]
        compra     = [s for s in validas if s.get("nivel") == "compra"]

        if estado == "ALCISTA":
            aviso = None
        elif estado == "BAJISTA":
            aviso = "⚠️ Mercado bajista — operar solo Alta Probabilidad"
        else:
            aviso = "⚠️ Mercado en transición — preferir Confirmada o Alta Probabilidad"

        escaneo = {
            "total_analizados": len(CONTINUO),
            "total_señales":    len(validas),
            "alta_prob":        alta_prob,
            "confirmada":       confirmada,
            "compra":           compra,
            "contexto":         estado,
            "aviso":            aviso,
            "compras":          validas,
            "vigilancia":       [],
            "total_compras":    len(validas),
            "total_vigilancia": 0,
        }
        cache.set("escaneo_continuo", escaneo, timeout=600)
    return render_template("continuo.html", escaneo_continuo=escaneo)


@application.route("/popup/medio_ibex")
def popup_medio_ibex():
    from estrategias.medio import MedioPlazo
    from core.universos import IBEX35
    from core.contexto_mercado import evaluar_contexto_ibex

    escaneo_cache = cache.get("escaneo_medio_ibex")
    if not escaneo_cache:
        contexto = evaluar_contexto_ibex(cache)
        estado   = contexto.get("estado", "TRANSICION") if contexto else "TRANSICION"

        _medio   = MedioPlazo()
        señales  = _medio.escanear(tickers=IBEX35, cache=cache)
        validas  = [s for s in señales if s.get("valido")]

        def _nivel(s):
            score = s.get("setup_score", 0)
            if score >= 8.5: return "excelente"
            if score >= 7.0: return "solido"
            return "basico"

        def _fmt(s):
            det = s.get("detalles", {})
            return {
                "ticker":    s.get("ticker",""),
                "score":     s.get("setup_score", 0),
                "retroceso": det.get("retroceso_pct") or "",
            }

        excelente = [_fmt(s) for s in validas if _nivel(s) == "excelente"]
        solido    = [_fmt(s) for s in validas if _nivel(s) == "solido"]
        basico    = [_fmt(s) for s in validas if _nivel(s) == "basico"]

        if estado == "ALCISTA":    aviso = None
        elif estado == "BAJISTA":  aviso = "⚠️ Mercado bajista — operar solo Setup Excelente"
        else:                      aviso = "⚠️ Mercado en transición — preferir Sólido o Excelente"

        escaneo_cache = {
            "total_analizados": len(IBEX35),
            "total_señales":    len(validas),
            "excelente":        excelente,
            "solido":           solido,
            "basico":           basico,
            "contexto":         estado,
            "aviso":            aviso,
        }
        cache.set("escaneo_medio_ibex", escaneo_cache, timeout=600)
    return render_template("medio_ibex.html", escaneo=escaneo_cache)


@application.route("/popup/medio_continuo")
def popup_medio_continuo():
    from estrategias.medio import MedioPlazo
    from core.universos import CONTINUO
    from core.contexto_mercado import evaluar_contexto_ibex

    escaneo_cache = cache.get("escaneo_medio_continuo")
    if not escaneo_cache:
        contexto = evaluar_contexto_ibex(cache)
        estado   = contexto.get("estado", "TRANSICION") if contexto else "TRANSICION"

        _medio   = MedioPlazo()
        señales  = _medio.escanear(tickers=CONTINUO, cache=cache)
        validas  = [s for s in señales if s.get("valido")]

        def _nivel(s):
            score = s.get("setup_score", 0)
            if score >= 8.5: return "excelente"
            if score >= 7.0: return "solido"
            return "basico"

        def _fmt(s):
            det = s.get("detalles", {})
            return {
                "ticker":    s.get("ticker",""),
                "score":     s.get("setup_score", 0),
                "retroceso": det.get("retroceso_pct") or "",
            }

        excelente = [_fmt(s) for s in validas if _nivel(s) == "excelente"]
        solido    = [_fmt(s) for s in validas if _nivel(s) == "solido"]
        basico    = [_fmt(s) for s in validas if _nivel(s) == "basico"]

        if estado == "ALCISTA":    aviso = None
        elif estado == "BAJISTA":  aviso = "⚠️ Mercado bajista — operar solo Setup Excelente"
        else:                      aviso = "⚠️ Mercado en transición — preferir Sólido o Excelente"

        escaneo_cache = {
            "total_analizados": len(CONTINUO),
            "total_señales":    len(validas),
            "excelente":        excelente,
            "solido":           solido,
            "basico":           basico,
            "contexto":         estado,
            "aviso":            aviso,
        }
        cache.set("escaneo_medio_continuo", escaneo_cache, timeout=600)
    return render_template("medio_continuo.html", escaneo=escaneo_cache)


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
    """Análisis profundo con Claude."""
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


@application.route("/guardar_pantallazo", methods=["POST"])
def guardar_pantallazo():
    from controlador import guardar_pantallazo_controlador
    ok, resultado = guardar_pantallazo_controlador(request.get_json())
    if not ok:
        return resultado, 400
    return jsonify({"ok": True, "archivo": resultado})


# ════════════════════════════════════════════════════════════════
# 8️⃣  ARRANQUE LOCAL
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🚀  MiWeb — servidor Flask")
    print("=" * 65)
    print("  /                        ← Hub principal")
    print("  /swing/                  ← Swing Trading")
    print("  /medio/                  ← Medio Plazo")
    print("  /posicional/             ← Posicional")
    print("  /backtest/               ← Backtest")
    print("  /cartera/                ← Cartera")
    print("  /analisis/tecnico        ← Análisis técnico")
    print("  /analisis/fundamental    ← Análisis fundamental")
    print("  /alertas/                ← Alertas")
    print("  /indicadores/            ← Indicadores")
    print("  /popup/ibex              ← Escáner IBEX (iframe)")
    print("  /popup/continuo          ← Escáner Continuo (iframe)")
    print("  /api/sentimiento_rss     ← Sentimiento IBEX (RSS)")
    print("  /api/sentimiento         ← Sentimiento profundo (Claude)")
    print("  /analisis/noticias       ← Noticias del día")
    print("=" * 65 + "\n")
    port = int(os.environ.get("PORT", 5001))
    application.run(host="0.0.0.0", port=port, debug=True)
