# ==========================================================
# WEB/ROUTES/POSICIONAL_ROUTES.PY
# Blueprint sistema posicional — adaptado a nueva arquitectura
# ==========================================================

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import json
import os

from core.universos import IBEX35, CONTINUO
from core.contexto_mercado import evaluar_contexto_ibex
from estrategias.posicional.datos_posicional import obtener_datos_semanales, filtrar_universo_posicional
from estrategias.posicional.sistema_trading_posicional import evaluar_entrada_posicional, evaluar_con_scoring
from estrategias.posicional.backtest_sistema_posicional import ejecutar_backtest_sistema_completo
from estrategias.posicional.backtest_posicional import ejecutar_backtest_posicional

RESULTADOS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_cache", "posicional")
os.makedirs(RESULTADOS_DIR, exist_ok=True)


import math

def _serializar_analisis(resultado):
    """Convierte todos los valores del resultado a tipos JSON-serializables."""
    def _conv(v):
        if v is None:             return None
        if isinstance(v, bool):   return bool(v)
        try:
            import numpy as np
            if isinstance(v, np.bool_):    return bool(v)
            if isinstance(v, np.integer):  return int(v)
            if isinstance(v, np.floating):
                f = float(v)
                return None if (math.isnan(f) or math.isinf(f)) else f
            if isinstance(v, np.ndarray): return [_conv(i) for i in v.tolist()]
        except ImportError:
            pass
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
        if isinstance(v, (int, float)): return v
        if isinstance(v, str):    return v
        if isinstance(v, dict):   return {k: _conv(val) for k, val in v.items()}
        if isinstance(v, (list, tuple)): return [_conv(i) for i in v]
        return str(v)

    det = {k: _conv(v) for k, v in resultado.get("detalles", {}).items()}
    return {
        "decision":       resultado["decision"],
        "motivos":        resultado.get("motivos", []),
        "motivo":         ", ".join(resultado.get("motivos", [])),
        "entrada":        _conv(resultado.get("entrada", 0)),
        "trigger":        _conv(resultado.get("trigger", resultado.get("entrada", 0))),
        "stop":           _conv(resultado.get("stop", 0)),
        "riesgo_pct":     _conv(resultado.get("riesgo_pct", 0)),
        "detalles":       det,
        "score":          _conv(resultado.get("setup_score", 0)),
        "score_max":      100,
        "score_label":    resultado.get("clasificacion", ""),
        "score_desglose": {k: _conv(v) for k, v in resultado.get("score_desglose", {}).items()},
        "fuerza_relativa":det.get("fr_cat", ""),
        "fr_diferencial": _conv(det.get("fr_diff", 0)),
    }

posicional_bp = Blueprint("posicional", __name__, url_prefix="/posicional")


@posicional_bp.route("/")
def index():
    from estrategias.posicional.config_posicional import MIN_VOLATILIDAD_PCT, MIN_VOLUMEN_MEDIO_DIARIO, MIN_CAPITALIZACION, RIESGO_POR_TRADE_PCT
    contexto = {
        "sistema": "posicional",
        "titulo": "Sistema Posicional",
        "subtitulo": "Trading 6M-2Y · IBEX 35",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "universo": {"total": len(IBEX35), "aptos": len(IBEX35), "ratio": "100%"},
        "parametros": {
            "volatilidad_min": MIN_VOLATILIDAD_PCT,
            "volumen_min": f"{MIN_VOLUMEN_MEDIO_DIARIO/1_000_000:.1f}M€",
            "capitalizacion_min": f"{MIN_CAPITALIZACION/1_000_000_000:.1f}B€" if MIN_CAPITALIZACION > 0 else "Sin filtro",
            "duracion": "6 meses - 2 años",
            "riesgo_por_trade": f"{RIESGO_POR_TRADE_PCT}%"
        }
    }
    # Contexto IBEX para barra de estado
    from flask import current_app
    cache = current_app.config.get("CACHE_INSTANCE")
    contexto["contexto_mercado"] = evaluar_contexto_ibex(cache)
    return render_template("index_posicional.html", **contexto)


@posicional_bp.route("/analizar")
def analizar():
    return render_template("analizar_posicional.html",
                           titulo="Analizar Valor Posicional",
                           valores_ibex=IBEX35,
                           valores_continuo=CONTINUO,
                           sistema="posicional")


@posicional_bp.route("/api/analizar/<ticker>")
def api_analizar(ticker):
    try:
        if ticker not in IBEX35 and ticker not in CONTINUO:
            return jsonify({"success": False, "error": f"{ticker} no está en IBEX 35 ni Mercado Continuo"})
        df, validacion = obtener_datos_semanales(ticker, periodo_años=10, validar=True)
        if df is None:
            return jsonify({"success": False, "error": "No se pudieron obtener datos", "validacion": validacion})
        precios   = df["Close"].tolist()
        volumenes = df["Volume"].tolist() if "Volume" in df.columns else None

        # Obtener IBEX semanal para fuerza relativa
        precios_ibex = None
        try:
            from estrategias.posicional.datos_posicional import obtener_datos_semanales as _get_ibex
            df_ibex, _ = _get_ibex("^IBEX", periodo_años=10, validar=False)
            if df_ibex is not None and not df_ibex.empty:
                precios_ibex = df_ibex["Close"].tolist()
        except Exception:
            pass

        resultado = evaluar_con_scoring(precios, volumenes, df=df, precios_ibex=precios_ibex)

        # Calcular stats que espera el template JS
        try:
            ret = df["Close"].pct_change().dropna()
            volatilidad_anual = round(float(ret.std() * (52 ** 0.5) * 100), 1)
        except Exception:
            volatilidad_anual = None

        try:
            # Media 3 años = 156 semanas (estándar ADTV institucional)
            vol_medio_diario = float(df["Volume"].tail(156).mean() / 5)
            vol_medio_diario_eur = vol_medio_diario * float(df["Close"].iloc[-1])
        except Exception:
            vol_medio_diario_eur = None

        stats = {
            "volatilidad_anual":     volatilidad_anual,
            "volumen_medio_diario":  vol_medio_diario_eur,
        }

        return jsonify({
            "success": True, "ticker": ticker,
            "fecha_analisis": datetime.now().isoformat(),
            "datos": {"semanas": len(df), "desde": df.index[0].strftime("%Y-%m-%d"),
                      "hasta": df.index[-1].strftime("%Y-%m-%d"), "precio_actual": float(df["Close"].iloc[-1])},
            "validacion": stats,
            "analisis": _serializar_analisis(resultado)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/backtest-valor")
def backtest_valor():
    return render_template("backtest_valor_posicional.html",
                           titulo="Backtest Valor Individual", valores=IBEX35, sistema="posicional")


@posicional_bp.route("/api/backtest-valor/<ticker>")
def api_backtest_valor(ticker):
    try:
        if ticker not in IBEX35:
            return jsonify({"success": False, "error": f"{ticker} no está en IBEX 35"})
        df, _ = obtener_datos_semanales(ticker, periodo_años=10)
        if df is None or df.empty:
            return jsonify({"success": False, "error": "No se pudieron obtener datos"})
        resultado = ejecutar_backtest_posicional(df, ticker, verbose=False)
        return jsonify({"success": True, "ticker": ticker, "resultado": {
            "total_trades": resultado.get("total_trades", 0),
            "expectancy":   round(resultado.get("expectancy", 0), 2),
            "winrate":      round(resultado.get("winrate", 0), 1),
            "profit_factor": round(resultado.get("profit_factor", 0), 2),
            "equity_final": round(resultado.get("equity_final", 0), 2),
            "mejor_trade":  round(resultado.get("mejor_trade", 0), 2),
            "peor_trade":   round(resultado.get("peor_trade", 0), 2),
            "duracion_media": round(resultado.get("duracion_media", 0), 0)
        }})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/cartera")
def cartera():
    cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
    data = json.load(open(cartera_path)) if os.path.exists(cartera_path) else {"posiciones": []}
    return render_template("cartera_posicional.html", titulo="Cartera Posicional", sistema="posicional",
                           cartera=data, valores_ibex=IBEX35, valores_continuo=CONTINUO)


@posicional_bp.route("/api/cartera/agregar", methods=["POST"])
def api_agregar_posicion():
    try:
        data = request.get_json()
        for campo in ["ticker", "precio_entrada", "stop", "acciones"]:
            if campo not in data:
                return jsonify({"success": False, "error": f"Campo {campo} requerido"})
        ticker = data["ticker"]
        precio_entrada = float(data["precio_entrada"])
        stop     = float(data["stop"])
        acciones = int(data["acciones"])
        if precio_entrada <= 0 or stop <= 0 or acciones <= 0:
            return jsonify({"success": False, "error": "Valores deben ser positivos"})
        if stop >= precio_entrada:
            return jsonify({"success": False, "error": "Stop debe ser menor que entrada"})
        riesgo_pct   = ((precio_entrada - stop) / precio_entrada) * 100
        cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
        cartera = json.load(open(cartera_path)) if os.path.exists(cartera_path) else {"posiciones": []}
        if any(p["ticker"] == ticker for p in cartera["posiciones"]):
            return jsonify({"success": False, "error": f"{ticker} ya está en cartera"})
        nueva = {"ticker": ticker, "fecha_entrada": datetime.now().strftime("%Y-%m-%d"),
                 "precio_entrada": precio_entrada, "stop": stop, "acciones": acciones,
                 "riesgo_pct": round(riesgo_pct, 2), "R_actual": 0, "estado": "INICIAL",
                 "notas": data.get("notas", "")}
        cartera["posiciones"].append(nueva)
        json.dump(cartera, open(cartera_path, "w"), indent=2)
        return jsonify({"success": True, "mensaje": f"{ticker} agregado a cartera", "posicion": nueva})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/api/cartera/eliminar/<ticker>", methods=["POST"])
def api_eliminar_posicion(ticker):
    try:
        cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
        if not os.path.exists(cartera_path):
            return jsonify({"success": False, "error": "Cartera vacía"})
        cartera = json.load(open(cartera_path))
        antes = len(cartera["posiciones"])
        cartera["posiciones"] = [p for p in cartera["posiciones"] if p["ticker"] != ticker]
        if len(cartera["posiciones"]) == antes:
            return jsonify({"success": False, "error": f"{ticker} no está en cartera"})
        json.dump(cartera, open(cartera_path, "w"), indent=2)
        return jsonify({"success": True, "mensaje": f"{ticker} eliminado de cartera"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/historial")
def historial():
    historial_path = os.path.join(RESULTADOS_DIR, "historial_posicional.json")
    data = json.load(open(historial_path)) if os.path.exists(historial_path) else {"trades": []}
    return render_template("historial_posicional.html", titulo="Historial Posicional",
                           sistema="posicional", historial=data)


@posicional_bp.route("/backtest", methods=["GET", "POST"])
def backtest_sistema():
    if request.method == "POST":
        from estrategias.posicional.config_posicional import (IBEX_GRUPO_1, IBEX_GRUPO_2, IBEX_GRUPO_3,
                                     CONTINUO_GRUPO_1, CONTINUO_GRUPO_2, CONTINUO_GRUPO_3)
        grupo   = request.form.get("grupo", "todos")
        mercado = request.form.get("mercado", "ibex")
        universos = {
            "ibex":     {"grupo1": IBEX_GRUPO_1, "grupo2": IBEX_GRUPO_2, "grupo3": IBEX_GRUPO_3, "todos": IBEX35},
            "continuo": {"grupo1": CONTINUO_GRUPO_1, "grupo2": CONTINUO_GRUPO_2,
                         "grupo3": CONTINUO_GRUPO_3, "todos": CONTINUO}
        }
        universo  = universos.get(mercado, {}).get(grupo, IBEX35)
        resultado = ejecutar_backtest_sistema_completo(universo=universo)
        resultado["grupo"]   = grupo
        resultado["mercado"] = mercado
        return jsonify(resultado)
    return render_template("backtest_posicional.html", resultado=None)


@posicional_bp.route("/api/backtest/ejecutar")
def api_ejecutar_backtest():
    try:
        resultado_raw = ejecutar_backtest_sistema_completo(verbose=True)
        resultado     = _adaptar_resultado_backtest(resultado_raw)
        path = os.path.join(RESULTADOS_DIR, "ultimo_backtest_posicional.json")
        json.dump(resultado, open(path, "w"), indent=2, default=str)
        return jsonify({"success": True, "resultado": resultado, "mensaje": "Backtest ejecutado exitosamente"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/api/backtest/ultimo")
def api_ultimo_backtest():
    try:
        path = os.path.join(RESULTADOS_DIR, "ultimo_backtest_posicional.json")
        if os.path.exists(path):
            return jsonify({"success": True, "resultado": json.load(open(path))})
        return jsonify({"success": False, "error": "No hay backtest previo"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@posicional_bp.route("/config")
def config():
    from estrategias.posicional.config_posicional import (
        MIN_VOLATILIDAD_PCT, MAX_VOLATILIDAD_PCT,
        MIN_VOLUMEN_MEDIO_DIARIO, MIN_CAPITALIZACION,
        RIESGO_POR_TRADE_PCT, RIESGO_MIN_PCT, RIESGO_MAX_PCT,
        CONSOLIDACION_MIN_SEMANAS, CONSOLIDACION_MAX_SEMANAS, CONSOLIDACION_MAX_RANGO_PCT,
        BREAKOUT_VOLUMEN_MIN_RATIO,
        DISTANCIA_MIN_MM50_PCT, DISTANCIA_MAX_MM50_PCT,
        R_PARA_PROTEGER, R_PARA_TRAILING, TRAILING_R_MINIMO,
        TRAILING_LOOKBACK, TRAILING_LOOKBACK_FINAL,
        DURACION_MINIMA_SEMANAS,
    )
    return render_template("config_posicional.html", titulo="Configuración Sistema Posicional",
                           sistema="posicional", parametros={
                               "volatilidad_min":      MIN_VOLATILIDAD_PCT,
                               "volatilidad_max":      MAX_VOLATILIDAD_PCT,
                               "volumen_min":          MIN_VOLUMEN_MEDIO_DIARIO,
                               "capitalizacion_min":   MIN_CAPITALIZACION,
                               "riesgo_trade":         RIESGO_POR_TRADE_PCT,
                               "riesgo_min":           RIESGO_MIN_PCT,
                               "riesgo_max":           RIESGO_MAX_PCT,
                               "consolidacion_min":    CONSOLIDACION_MIN_SEMANAS,
                               "consolidacion_max":    CONSOLIDACION_MAX_SEMANAS,
                               "consolidacion_rango":  CONSOLIDACION_MAX_RANGO_PCT,
                               "breakout_volumen":     BREAKOUT_VOLUMEN_MIN_RATIO,
                               "distancia_min_mm50":   DISTANCIA_MIN_MM50_PCT,
                               "distancia_max_mm50":   DISTANCIA_MAX_MM50_PCT,
                               "r_proteger":           R_PARA_PROTEGER,
                               "r_trailing":           R_PARA_TRAILING,
                               "r_trailing_final":     TRAILING_R_MINIMO,
                               "trailing_semanas":     TRAILING_LOOKBACK,
                               "trailing_semanas_final": TRAILING_LOOKBACK_FINAL,
                               "duracion_min":         DURACION_MINIMA_SEMANAS,
                           })


def _escanear(universo, titulo, nombre_universo):
    resultados = []
    for ticker in universo:
        try:
            df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)
            if df is None or len(df) < 50:
                continue
            precios   = df["Close"].tolist()
            volumenes = df["Volume"].tolist() if "Volume" in df.columns else None
            analisis  = evaluar_entrada_posicional(precios, volumenes, df=df)
            resultados.append({
                "ticker": ticker, "nombre": ticker.replace(".MC", ""),
                "precio": float(df["Close"].iloc[-1]),
                "decision": analisis.get("decision", "ESPERAR"),
                "motivo":   ", ".join(analisis.get("motivos", [])),
                "entrada":  analisis.get("entrada", 0), "stop": analisis.get("stop", 0),
                "riesgo_pct": analisis.get("riesgo_pct", 0)
            })
        except Exception as e:
            print(f"⚠️ Error en {ticker}: {e}")
    compras = [r for r in resultados if r["decision"] == "COMPRA"]
    esperas = [r for r in resultados if r["decision"] != "COMPRA"]
    return render_template("escanear_posicional.html", titulo=titulo, universo=nombre_universo,
                           total=len(universo), analizados=len(resultados),
                           compras=compras, esperas=esperas, sistema="posicional")


@posicional_bp.route("/escanear/ibex")
def escanear_ibex():
    return _escanear(IBEX35, "Escáner IBEX 35", "IBEX 35")


@posicional_bp.route("/escanear/continuo")
def escanear_continuo():
    return _escanear(CONTINUO, "Escáner Mercado Continuo", "Mercado Continuo")


def _adaptar_resultado_backtest(resultado_raw):
    detallados = resultado_raw.get("resultados_detallados", [])
    con_trades = [r for r in detallados if r.get("total_trades", 0) > 0]
    mejores = sorted(con_trades, key=lambda x: x.get("expectancy", 0), reverse=True)[:5]
    peores  = sorted(con_trades, key=lambda x: x.get("expectancy", 0))[:5]
    def _fmt(lst):
        return [{"ticker": r.get("ticker", ""), "empresa": r.get("ticker", "").replace(".MC", ""),
                 "total_trades": r.get("total_trades", 0), "expectancy_R": r.get("expectancy", 0),
                 "winrate": r.get("winrate", 0), "equity_final_R": r.get("equity_final", 0)} for r in lst]
    return {
        "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "universo": {"total_tickers": resultado_raw.get("total_tickers", 0),
                     "analizados": resultado_raw.get("tickers_analizados", 0),
                     "sin_datos": 0, "con_error": resultado_raw.get("tickers_con_error", 0)},
        "metricas_globales": {
            "total_trades":   resultado_raw.get("total_trades", 0),
            "expectancy_R":   resultado_raw.get("expectancy_global", 0),
            "winrate":        resultado_raw.get("winrate_global", 0),
            "profit_factor":  resultado_raw.get("profit_factor_global", 0),
            "equity_final_R": resultado_raw.get("equity_total", 0),
            "mejor_trade":    max((r.get("mejor_trade", 0) for r in con_trades), default=0),
            "peor_trade":     min((r.get("peor_trade", 0) for r in con_trades), default=0),
            "max_drawdown_R": 0,
            "tickers_rentables":    resultado_raw.get("tickers_rentables", 0),
            "tickers_no_rentables": resultado_raw.get("tickers_no_rentables", 0)
        },
        "top_performers": {"mejores": _fmt(mejores), "peores": _fmt(peores)}
    }
