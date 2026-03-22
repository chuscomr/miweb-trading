# web/routes/analisis_routes.py
# ══════════════════════════════════════════════════════════════
# RUTAS ANÁLISIS (técnico + fundamental)
# Solo lógica HTTP.
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, request, render_template, current_app, jsonify
from core.universos import normalizar_ticker, get_nombre
from core.data_provider import get_df
from core.indicadores import calcular_rsi, calcular_atr, calcular_macd
from analisis.tecnico import (
    detectar_soportes_resistencias, calcular_confirmaciones,
    detectar_patrones_velas, analizar_confluencia_velas_sr,
    crear_grafico_analisis_tecnico, obtener_sr_mas_cercanos,
)
from analisis.fundamental import (
    obtener_datos_fundamentales, calcular_score_fundamental,
    obtener_noticias_del_dia,
)

analisis_bp = Blueprint("analisis", __name__, url_prefix="/analisis")


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _enriquecer_df(df):
    """Añade indicadores al df para que confirmaciones los encuentre."""
    import pandas as pd
    df = df.copy()
    df["MM20"]       = df["Close"].rolling(20).mean()
    df["MM50"]       = df["Close"].rolling(50).mean()
    df["MM200"]      = df["Close"].rolling(200).mean()
    df["ATR"]        = calcular_atr(df, 14)
    df["RSI"]        = calcular_rsi(df["Close"], 14)
    macd = calcular_macd(df["Close"])
    df["MACD"]       = macd["macd"]
    df["MACD_SEÑAL"] = macd["señal"]
    df["MACD_HIST"]  = macd["histograma"]
    return df


# ─────────────────────────────────────────────────────────────
# ANÁLISIS TÉCNICO
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/tecnico", methods=["GET"])
def tecnico_panel():
    return render_template("analisis_tecnico.html")


@analisis_bp.route("/tecnico", methods=["POST"])
def tecnico_analizar():
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return render_template("analisis_tecnico.html",
                               error="Introduce un ticker válido")

    cache = _get_cache()
    df    = get_df(ticker, periodo="1y", cache=cache)

    if df is None or len(df) < 60:
        return render_template("analisis_tecnico.html",
                               ticker=ticker,
                               error=f"Datos insuficientes para {ticker}")

    df_enriquecido = _enriquecer_df(df)

    sr = detectar_soportes_resistencias(df_enriquecido)

    precio_actual = sr["precio_actual"]
    rsi_val = float(df_enriquecido["RSI"].iloc[-1])

    señal_dummy = {
        "tipo":             "BREAKOUT",
        "ticker":           ticker,
        "precio_actual":    precio_actual,
        "rsi":              rsi_val,
        "volumen_ruptura":  1.0,
        "resistencia_rota": sr["resistencias"][0]["nivel"] if sr["resistencias"] else 0,
        "dist_maximo_pct":  0,
        "consolidacion_dias": 0,
        "setup_score":      0,
    }
    confirmaciones = calcular_confirmaciones(df_enriquecido, señal_dummy)

    # Patrones de velas
    patron     = detectar_patrones_velas(df_enriquecido, ultimas_n=2)
    sr_cercanos = obtener_sr_mas_cercanos(precio_actual, sr["soportes"], sr["resistencias"])
    confluencia = analizar_confluencia_velas_sr(patron, sr_cercanos.get("distancia_soporte_pct"))

    # Gráfico interactivo (últimos 90 días)
    grafico_html = crear_grafico_analisis_tecnico(
        df            = df_enriquecido.tail(90),
        soportes      = sr["soportes"],
        resistencias  = sr["resistencias"],
        patron        = patron,
        precio_actual = precio_actual,
    )

    return render_template(
        "analisis_tecnico.html",
        ticker         = ticker,
        nombre_valor   = get_nombre(ticker),
        soportes       = sr["soportes"],
        resistencias   = sr["resistencias"],
        analisis_sr    = sr["analisis"],
        precio_actual  = precio_actual,
        confirmaciones = confirmaciones,
        patron         = patron,
        confluencia    = confluencia,
        grafico_html   = grafico_html,
    )


# ─────────────────────────────────────────────────────────────
# ANÁLISIS FUNDAMENTAL
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/fundamental", methods=["GET"])
def fundamental_panel():
    return render_template("analisis_fundamental.html")


@analisis_bp.route("/fundamental", methods=["POST"])
def fundamental_analizar():
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return render_template("analisis_fundamental.html",
                               error="Introduce un ticker válido")

    cache  = _get_cache()
    datos  = obtener_datos_fundamentales(ticker, cache)
    score  = calcular_score_fundamental(datos)

    return render_template(
        "analisis_fundamental.html",
        ticker       = ticker,
        nombre_valor = get_nombre(ticker),
        datos        = datos,
        score        = score,
    )


# ─────────────────────────────────────────────────────────────
# ANÁLISIS COMPLETO (técnico + fundamental)
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/completo", methods=["POST"])
def completo():
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return render_template("analisis_completo.html",
                               error="Introduce un ticker válido")

    cache = _get_cache()

    df = get_df(ticker, periodo="1y", cache=cache)
    df_enriquecido = _enriquecer_df(df) if df is not None and len(df) >= 60 else None

    sr             = detectar_soportes_resistencias(df_enriquecido) if df_enriquecido is not None else None
    datos_fund     = obtener_datos_fundamentales(ticker, cache)
    score_fund     = calcular_score_fundamental(datos_fund)

    # Garantizar campos opcionales
    for campo in ["cagr_ingresos_3y","cagr_beneficios_3y","aceleracion_ingresos",
                  "aceleracion_beneficios","momentum_score","momentum_nivel",
                  "momentum_detalles","fcf_positivo_anos","fcf_ultimo_ano",
                  "deuda_neta","deuda_ebitda"]:
        if campo not in datos_fund:
            datos_fund[campo] = None

    return render_template(
        "analisis_completo.html",
        ticker       = ticker,
        nombre_valor = get_nombre(ticker),
        sr           = sr,
        score_fund   = score_fund,
        datos_fund   = datos_fund,
    )


# ─────────────────────────────────────────────────────────────
# API JSON — para llamadas AJAX desde el frontend
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/api/sr/<ticker>")
def api_sr(ticker):
    ticker = normalizar_ticker(ticker)
    cache  = _get_cache()
    df     = get_df(ticker, periodo="1y", cache=cache)
    if df is None:
        return jsonify({"error": "Sin datos"}), 404
    return jsonify(detectar_soportes_resistencias(df))


@analisis_bp.route("/api/fundamental/<ticker>")
def api_fundamental(ticker):
    ticker = normalizar_ticker(ticker)
    cache  = _get_cache()
    datos  = obtener_datos_fundamentales(ticker, cache)
    score  = calcular_score_fundamental(datos)
    return jsonify({"datos": datos, "score": score})


# ─────────────────────────────────────────────────────────────
# NOTICIAS DEL DÍA
# GET  /analisis/noticias         → página HTML
# GET  /analisis/api/noticias     → JSON para fetch()
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/noticias", methods=["GET"])
def noticias_panel():
    """Página de noticias financieras del día."""
    cache = _get_cache()
    noticias = cache.get("noticias_del_dia") if cache else None
    if noticias is None:
        noticias = obtener_noticias_del_dia()
        if cache:
            cache.set("noticias_del_dia", noticias, timeout=1800)
    return render_template("noticias.html", noticias=noticias)


@analisis_bp.route("/api/noticias", methods=["GET"])
def api_noticias():
    """JSON con noticias del día. Cache 30 min."""
    cache = _get_cache()
    noticias = cache.get("noticias_del_dia") if cache else None
    if noticias is None:
        try:
            noticias = obtener_noticias_del_dia()
            if cache:
                cache.set("noticias_del_dia", noticias, timeout=1800)
        except Exception as e:
            return jsonify({"noticias": [], "error": str(e)}), 500
    return jsonify({"noticias": noticias, "total": len(noticias)})


# ─────────────────────────────────────────────────────────────
# MODAL FUNDAMENTAL — fragmento HTML para fetch() desde swing.html
# GET /analisis/modal/fundamental/<ticker>
# ─────────────────────────────────────────────────────────────

@analisis_bp.route("/modal/fundamental/<ticker>")
def modal_fundamental(ticker):
    """Devuelve fragmento HTML con análisis fundamental para el modal JS."""
    ticker = normalizar_ticker(ticker)
    cache  = _get_cache()
    try:
        datos = obtener_datos_fundamentales(ticker, cache)
        score = calcular_score_fundamental(datos)

        # Garantizar que todos los campos opcionales existen en el dict
        # (pueden faltar si _enriquecer_con_financials falla a mitad)
        campos_opcionales = [
            "cagr_ingresos_3y", "cagr_beneficios_3y",
            "aceleracion_ingresos", "aceleracion_beneficios",
            "momentum_score", "momentum_nivel", "momentum_detalles",
            "fcf_positivo_anos", "fcf_ultimo_ano",
            "deuda_neta", "deuda_ebitda",
        ]
        for campo in campos_opcionales:
            if campo not in datos:
                datos[campo] = None

        return render_template("_modal_fundamental.html", ticker=ticker, datos=datos, score=score)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"❌ modal_fundamental error para {ticker}:\n{tb}")
        return f'''<div style="padding:32px;text-align:center;color:#f06060;background:#1a1f2e;border-radius:10px;">
            <div style="font-size:1.2rem;margin-bottom:8px;">❌ Error al cargar datos</div>
            <div style="font-size:0.85rem;color:#94a3b8;">{str(e)}</div>
            <pre style="font-size:0.7rem;color:#64748b;text-align:left;margin-top:12px;overflow:auto;max-height:200px;">{tb}</pre>
        </div>''', 500
