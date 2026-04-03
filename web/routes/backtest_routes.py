# web/routes/backtest_routes.py
# ══════════════════════════════════════════════════════════════
# RUTAS BACKTEST
# Solo lógica HTTP — sin cálculos, sin yfinance.
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, request, render_template, current_app, jsonify
from core.universos import normalizar_ticker, get_nombre, IBEX35, CONTINUO
from backtest.config_backtest import ConfigBacktest
from backtest.run_backtest import ejecutar_backtest, ejecutar_backtest_multiticker

backtest_bp = Blueprint("backtest", __name__, url_prefix="/backtest")


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _config_desde_form(form) -> ConfigBacktest:
    """Construye ConfigBacktest desde los parámetros del formulario."""
    estrategia = form.get("estrategia", "breakout")

    # Partir de la config predefinida según estrategia
    fabricas = {
        "breakout":  ConfigBacktest.para_breakout,
        "pullback":  ConfigBacktest.para_pullback,
        "medio":     ConfigBacktest.para_medio,
        "posicional": ConfigBacktest.para_posicional,
    }
    fabrica = fabricas.get(estrategia, ConfigBacktest.para_breakout)

    return fabrica(
        capital_inicial = float(form.get("capital", 10000)),
        riesgo_pct      = float(form.get("riesgo_pct", 1.0)),
        slippage_pct    = float(form.get("slippage_pct", 0.10)),
        comision_pct    = float(form.get("comision_pct", 0.10)),
        trailing_stop   = form.get("trailing_stop") == "on",
    )


# ─────────────────────────────────────────────────────────────
# PANEL PRINCIPAL
# ─────────────────────────────────────────────────────────────

@backtest_bp.route("/", methods=["GET"])
def panel():
    return render_template("backtest.html")


# ─────────────────────────────────────────────────────────────
# BACKTEST INDIVIDUAL
# ─────────────────────────────────────────────────────────────

@backtest_bp.route("/ejecutar", methods=["POST"])
def ejecutar():
    """Ejecuta backtest para un ticker individual."""
    ticker = normalizar_ticker(request.form.get("ticker", ""))
    if not ticker:
        return render_template("backtest.html", error="Introduce un ticker válido")

    try:
        config    = _config_desde_form(request.form)
        resultado = ejecutar_backtest(ticker, config, _get_cache())

        if resultado.get("error"):
            return render_template("backtest.html", error=resultado["error"])

        return render_template(
            "backtest.html",
            ticker       = ticker,
            nombre_valor = get_nombre(ticker),
            metricas     = resultado["metricas"],
            trades       = resultado["trades"],
            equity       = resultado["equity"],
            config       = resultado["config"],
        )

    except Exception as e:
        return render_template("backtest.html", error=f"Error inesperado: {str(e)}")


# ─────────────────────────────────────────────────────────────
# BACKTEST MULTI-TICKER (API JSON para el escáner)
# ─────────────────────────────────────────────────────────────

@backtest_bp.route("/multiticker", methods=["POST"])
def multiticker():
    """Ejecuta backtest sobre múltiples tickers. Devuelve JSON."""
    data       = request.get_json() or {}
    tickers    = data.get("tickers", IBEX35)
    estrategia = data.get("estrategia", "breakout")
    capital    = float(data.get("capital", 10000))
    riesgo_pct = float(data.get("riesgo_pct", 1.0))
    top_n      = int(data.get("top_n", 10))

    fabricas = {
        "breakout":   ConfigBacktest.para_breakout,
        "pullback":   ConfigBacktest.para_pullback,
        "medio":      ConfigBacktest.para_medio,
        "posicional": ConfigBacktest.para_posicional,
    }
    config = fabricas.get(estrategia, ConfigBacktest.para_breakout)(
        capital_inicial=capital,
        riesgo_pct=riesgo_pct,
    )

    resultado = ejecutar_backtest_multiticker(
        tickers=tickers,
        config=config,
        cache=_get_cache(),
        top_n=top_n,
    )

    return jsonify(resultado)


# ─────────────────────────────────────────────────────────────
# API BACKTEST SISTEMA COMPLETO (GET /backtest/api/ejecutar)
# Llamado desde el modal JS de swing.html
# Usa la MISMA lógica que el backtest_api.py original:
#   obtener_precios → construir_df → MarketData → StrategyLogic
#   → BacktestEngine → Portfolio → calcular_metricas
# ─────────────────────────────────────────────────────────────

@backtest_bp.route("/api/ejecutar", methods=["GET"])
def api_ejecutar_sistema():
    """
    Backtest sistema completo usando el pipeline original:
    get_df → MarketData → StrategyLogic → BacktestEngineLegacy
           → Portfolio(legacy) → calcular_metricas
    Devuelve JSON para el modal JS de swing.html.
    """
    import io
    from contextlib import redirect_stdout

    universo_param  = request.args.get("universo", "ibex")
    tickers         = IBEX35 if universo_param != "continuo" else CONTINUO
    nombre_universo = "Mercado Continuo" if universo_param == "continuo" else "IBEX 35"

    CAPITAL_INICIAL  = 10_000
    RIESGO_PCT       = 0.01
    MIN_VOLATILIDAD  = 9.0
    PERIODO          = "5y"

    try:
        from core.data_provider       import get_df
        from backtest.datos           import MarketData
        from backtest.strategy        import StrategyLogic
        from backtest.execution       import ExecutionModel
        from backtest.risk            import RiskManager
        from backtest.portfolio_legacy import Portfolio
        from backtest.engine_legacy   import BacktestEngineLegacy, calcular_atr
        from backtest.metrics         import calcular_metricas

        cache = _get_cache()

        # ── Filtro de mercado: cargar IBEX una vez ────────────
        from backtest.backtest_f1 import _cargar_ibex_mm200, _estado_mercado
        filtro_ibex = _cargar_ibex_mm200(periodo=PERIODO)
        print(f"Filtro IBEX: {len(filtro_ibex)} barras cargadas" if filtro_ibex else "Filtro IBEX: no disponible")

        tickers_operados  = []
        tickers_excluidos = []
        todos_trades      = []
        todas_equities    = []
        tickers           = list(dict.fromkeys(tickers))  # deduplicar manteniendo orden

        for ticker in tickers:
            try:
                df = get_df(ticker, periodo=PERIODO, cache=None)  # sin cache → datos frescos
                print(f"📊 {ticker}: {len(df) if df is not None else 'NONE'} barras")
                if df is None or len(df) < 60:
                    print(f"  ⚠️ {ticker}: datos insuficientes, saltando")
                    continue

                # ✅ REPLICAR SISTEMA ANTIGUO: construir_df_desde_listas usaba High=Low=Close
                # El sistema original trabajaba SOLO con precios de cierre.
                # Usar High/Low reales cambia cuándo se activan TARGET/STOP y rompe la equivalencia.
                import pandas as _pd
                df = _pd.DataFrame({
                    "Open":   df["Close"].values,
                    "High":   df["Close"].values,
                    "Low":    df["Close"].values,
                    "Close":  df["Close"].values,
                    "Volume": df["Volume"].values,
                }, index=df.index)

                # Filtro volatilidad (ventana último año)
                ventana_vol = min(252, len(df))
                vol_reciente = (df["Close"].tail(ventana_vol).std() /
                                df["Close"].tail(ventana_vol).mean()) * 100

                if vol_reciente < MIN_VOLATILIDAD:
                    tickers_excluidos.append({
                        "ticker": ticker,
                        "vol":    round(vol_reciente, 1)
                    })
                    continue

                # Pipeline completo original
                with redirect_stdout(io.StringIO()):
                    data      = MarketData(df)
                    strategy  = StrategyLogic(modo_test=False,
                                              min_volatilidad_pct=0,
                                              modo_backtest=True)
                    execution = ExecutionModel(comision_pct=0.0005,
                                              slippage_atr_pct=0.01,
                                              slippage_min_pct=0.0003)
                    risk      = RiskManager(CAPITAL_INICIAL, RIESGO_PCT)
                    portfolio = Portfolio(CAPITAL_INICIAL)
                    engine    = BacktestEngineLegacy(data, strategy, execution,
                                                    risk, portfolio,
                                                    filtro_ibex=filtro_ibex)
                    engine.run()

                if portfolio.trades:
                    todos_trades.extend(portfolio.trades)
                    todas_equities.extend(portfolio.equity_curve)

                    capital_final = portfolio.equity_curve[-1]
                    retorno = ((capital_final - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
                    Rs = [t.R for t in portfolio.trades]
                    wrs = [t for t in portfolio.trades if t.R > 0]
                    import numpy as _np
                    print(f"  ✅ {ticker}: {len(portfolio.trades)} trades WR={len(wrs)/len(portfolio.trades)*100:.0f}% exp={_np.mean(Rs):.2f}R ret={retorno:.1f}%")

                    tickers_operados.append({
                        "ticker":     ticker,
                        "trades":     len(portfolio.trades),
                        "retorno":    round(retorno, 1),
                        "volatilidad": round(vol_reciente, 1),
                    })
                else:
                    print(f"  ⛔ {ticker}: 0 trades (vol={vol_reciente:.1f}%)")
                    tickers_excluidos.append({
                        "ticker": ticker,
                        "vol":    round(vol_reciente, 1),
                        "motivo": "sin señales en 5 años"
                    })

            except Exception as e_ticker:
                import traceback
                print(f"⚠️ {ticker}: {e_ticker}")
                traceback.print_exc()
                continue

        if not todos_trades:
            return jsonify({"success": False, "error": "No se ejecutaron trades"}), 400

        # Métricas globales
        metricas   = calcular_metricas(todos_trades, todas_equities,
                                       capital_inicial=CAPITAL_INICIAL)
        expectancy = metricas.get("expectancy_R", metricas.get("expectancy", 0))
        winrate    = metricas.get("winrate", 0)
        max_dd     = metricas.get("max_drawdown_pct", 0)
        n_trades   = metricas.get("trades", len(todos_trades))

        # Estado
        if expectancy >= 0.40:
            estado = {"texto": "EXCELENTE",  "color": "success"}
        elif expectancy >= 0.20:
            estado = {"texto": "RENTABLE",   "color": "success"}
        elif expectancy > 0:
            estado = {"texto": "MARGINAL",   "color": "warning"}
        else:
            estado = {"texto": "NO RENTABLE", "color": "danger"}

        # Clasificar tickers
        aprobados  = sorted([t for t in tickers_operados if t["retorno"] >= 2.0],
                             key=lambda x: x["retorno"], reverse=True)
        neutros    = sorted([t for t in tickers_operados if -2.0 <= t["retorno"] < 2.0],
                             key=lambda x: x["retorno"], reverse=True)
        rechazados = sorted([t for t in tickers_operados if t["retorno"] < -2.0],
                             key=lambda x: x["retorno"])

        def _fmt(lst):
            return [{"nombre":  t["ticker"].replace(".MC", ""),
                     "empresa": get_nombre(t["ticker"]),
                     "retorno": t["retorno"],
                     "trades":  t["trades"]} for t in lst]

        # Recomendación
        if expectancy >= 0.20 and len(aprobados) >= 5:
            recomendacion = {"titulo": "Sistema listo para operar",
                             "acciones": [f"Operar SOLO los {len(aprobados)} tickers aprobados",
                                           "Mantener configuración actual"]}
        elif expectancy >= 0.20:
            recomendacion = {"titulo": "Pocos tickers aprobados",
                             "acciones": ["Considerar reducir filtro volatilidad",
                                           "O incluir tickers neutros en watchlist"]}
        else:
            recomendacion = {"titulo": "Sistema requiere optimización",
                             "acciones": ["Revisar parámetros de entrada",
                                           "NO operar hasta expectancy > 0.20R"]}

        return jsonify({
            "success":  True,
            "universo": nombre_universo,
            "estado":   estado,
            "metricas": {
                "expectancy":      round(expectancy, 2),
                "winrate":         round(winrate, 1),
                "max_dd":          round(max_dd, 1),
                "total_trades":    n_trades,
                "tickers_activos": len(tickers_operados),
            },
            "tickers": {
                "aprobados":  _fmt(aprobados),
                "neutros":    _fmt(neutros),
                "rechazados": _fmt(rechazados),
                "excluidos":  [{"nombre":  t["ticker"].replace(".MC", ""),
                                  "empresa": get_nombre(t["ticker"]),
                                  "vol":     t["vol"],
                                  "motivo":  t.get("motivo", "")}
                                 for t in tickers_excluidos],
            },
            "recomendacion": recomendacion,
            "config": {"target": "3R", "breakeven": "1R",
                        "riesgo": "1.0%", "filtro_vol": ">9%"},
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# API BACKTEST SISTEMA — BREAKOUT / PULLBACK / AMBOS
# GET /backtest/api/sistema?universo=ibex&estrategia=breakout
# ─────────────────────────────────────────────────────────────

@backtest_bp.route("/api/sistema", methods=["GET"])
def api_sistema_estrategia():
    """
    Backtest sistema usando PullbackSwing / BreakoutSwing reales.
    Parámetros:
        universo     = ibex | continuo
        estrategia   = breakout | pullback | ambos
        entrada_modo = zona | trigger  (solo afecta a pullback)
    """
    from core.data_provider  import get_df
    from core.universos      import get_nombre, IBEX35, CONTINUO
    from backtest.backtest_f1 import _cargar_ibex_mm200, _estado_mercado
    import pandas as pd
    import numpy as np

    universo_param  = request.args.get("universo", "ibex")
    estrategia_param = request.args.get("estrategia", "breakout")
    entrada_modo    = request.args.get("entrada_modo", "zona")  # zona | trigger
    tickers         = IBEX35 if universo_param != "continuo" else CONTINUO
    nombre_universo = "Mercado Continuo" if universo_param == "continuo" else "IBEX 35"
    PERIODO         = "5y"
    CAPITAL         = 10_000
    RIESGO_PCT      = 0.01
    MIN_VOL         = 9.0

    try:
        # Cargar estrategia(s)
        from estrategias.swing.breakout import BreakoutSwing
        from estrategias.swing.pullback import PullbackSwing

        estrategias = []
        if estrategia_param in ("breakout", "ambos"):
            estrategias.append(("BREAKOUT", BreakoutSwing()))
        if estrategia_param in ("pullback", "ambos"):
            estrategias.append(("PULLBACK", PullbackSwing()))

        # Filtro IBEX
        filtro_ibex = _cargar_ibex_mm200(periodo=PERIODO)
        print(f"Filtro IBEX: {len(filtro_ibex)} barras" if filtro_ibex else "Filtro IBEX: no disponible")

        tickers_operados  = []
        tickers_excluidos = []
        todos_trades      = []
        todas_equities    = []

        for ticker in tickers:
            try:
                df = get_df(ticker, periodo=PERIODO, cache=None)
                if df is None or len(df) < 60:
                    tickers_excluidos.append({"ticker": ticker, "vol": "sin datos"})
                    continue

                # Filtro volatilidad
                ventana = min(252, len(df))
                vol = (df["Close"].tail(ventana).std() / df["Close"].tail(ventana).mean()) * 100
                if vol < MIN_VOL:
                    tickers_excluidos.append({"ticker": ticker, "vol": round(vol, 1)})
                    continue

                # ── Precalcular DataFrame con indicadores (una sola vez) ──
                # Añadir columnas al df para que _evaluar_df no las recalcule
                df_pre = df.copy()
                df_pre["MM20"]  = df_pre["Close"].rolling(20).mean()
                df_pre["MM50"]  = df_pre["Close"].rolling(50).mean()
                df_pre["MM200"] = df_pre["Close"].rolling(200).mean()
                df_pre["ATR"]   = (pd.Series(
                    pd.concat([df_pre["High"]-df_pre["Low"],
                               (df_pre["High"]-df_pre["Close"].shift()).abs(),
                               (df_pre["Low"]-df_pre["Close"].shift()).abs()], axis=1
                    ).max(axis=1)).rolling(14).mean())
                delta = df_pre["Close"].diff()
                avg_g = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
                avg_p = (-delta).clip(lower=0).ewm(com=13, adjust=False).mean()
                df_pre["RSI"] = 100 - 100 / (1 + avg_g / avg_p)

                close_arr = df_pre["Close"].values.astype(float)
                high_arr  = df_pre["High"].values.astype(float)
                low_arr   = df_pre["Low"].values.astype(float)
                fechas_arr = df_pre.index
                n = len(df_pre)

                trades_ticker = []
                capital  = CAPITAL
                max_cap  = CAPITAL
                equity   = []
                pos      = None
                pending_trigger = None  # solo en modo trigger: {trigger, stop, R_unit, acciones, tipo, score}

                for i in range(200, n):
                    fecha = fechas_arr[i]
                    high  = high_arr[i]
                    low   = low_arr[i]

                    # ── Gestionar posición abierta ────────────
                    if pos:
                        R_u = pos["R_unit"]
                        pos["max"] = max(pos["max"], high)
                        if R_u > 0 and (high - pos["entrada"]) / R_u >= 1.0:
                            if pos["stop"] < pos["entrada"]:
                                pos["stop"] = pos["entrada"]
                        target = pos["entrada"] + 2.0 * R_u if R_u > 0 else None
                        salida = None; motivo = None
                        if target and high >= target:
                            salida = target; motivo = "TARGET"
                        elif low <= pos["stop"]:
                            salida = pos["stop"]; motivo = "STOP"
                        if salida:
                            R = (salida - pos["entrada"]) / R_u if R_u > 0 else 0
                            beneficio = (salida - pos["entrada"]) * pos["acciones"]
                            capital  += beneficio; max_cap = max(max_cap, capital)
                            trades_ticker.append({
                                "entrada": pos["entrada"], "salida": salida,
                                "beneficio": beneficio, "R": round(R, 2),
                                "motivo": motivo, "estrategia": pos["tipo"],
                                "score": pos.get("score", 0),
                            })
                            pos = None
                        equity.append(capital)
                        continue

                    # ── Modo trigger: comprobar si se activa trigger pendiente ──
                    if entrada_modo == "trigger" and pending_trigger and not pos:
                        trig = pending_trigger["trigger"]
                        if high >= trig:
                            # Trigger activado — entrar a ese precio
                            R_unit   = trig - pending_trigger["stop"]
                            if R_unit > 0 and 0.5 <= R_unit/trig*100 <= 10.0:
                                acciones = int((capital * RIESGO_PCT) / R_unit)
                                if acciones > 0 and acciones * trig <= capital:
                                    pos = {
                                        "entrada": trig,
                                        "stop":    pending_trigger["stop"],
                                        "R_unit":  R_unit,
                                        "acciones": acciones,
                                        "max":     trig,
                                        "tipo":    pending_trigger["tipo"],
                                        "score":   pending_trigger["score"],
                                    }
                        # Trigger expiró (solo válido 1 sesión)
                        pending_trigger = None
                        equity.append(capital)
                        continue

                    pending_trigger = None  # limpiar si no había pendiente

                    # ── Buscar entrada ────────────────────────
                    if not pos:
                        estado_mkt = _estado_mercado(fecha, filtro_ibex) if filtro_ibex else "ALCISTA"
                        if estado_mkt == "BAJISTA":
                            equity.append(capital); continue

                        # Evaluar TODAS las estrategias y elegir la de mayor score
                        candidatas = []
                        for nombre_est, est in estrategias:
                            if estado_mkt == "TRANSICION" and nombre_est == "BREAKOUT":
                                continue
                            try:
                                señal = est._evaluar_df(df_pre.iloc[:i+1], ticker)
                            except Exception:
                                continue
                            if not señal.get("valido"): continue
                            entrada_p = float(señal.get("entrada", 0))
                            stop_p    = float(señal.get("stop", 0))
                            score     = float(señal.get("setup_score", 0))
                            if estado_mkt == "TRANSICION" and score < 7.0: continue
                            if not entrada_p or not stop_p or stop_p >= entrada_p: continue
                            R_unit = entrada_p - stop_p
                            riesgo_pct_op = R_unit / entrada_p * 100
                            if not (0.5 <= riesgo_pct_op <= 10.0): continue
                            acciones = int((capital * RIESGO_PCT) / R_unit)
                            if acciones <= 0 or acciones * entrada_p > capital: continue
                            candidatas.append({
                                "tipo": nombre_est, "entrada": entrada_p,
                                "stop": stop_p, "score": score,
                                "R_unit": R_unit, "acciones": acciones,
                            })

                        if candidatas:
                            candidatas.sort(
                                key=lambda x: (x["score"], x["tipo"] == "PULLBACK"),
                                reverse=True
                            )
                            mejor = candidatas[0]

                            # Modo trigger solo para PULLBACK — BREAKOUT siempre entra zona
                            if entrada_modo == "trigger" and mejor["tipo"] == "PULLBACK":
                                # Guardar trigger para el día siguiente
                                pending_trigger = {
                                    "trigger": round(high * 1.001, 2),
                                    "stop":    mejor["stop"],
                                    "tipo":    mejor["tipo"],
                                    "score":   mejor["score"],
                                }
                            else:
                                pos = {
                                    "entrada": mejor["entrada"], "stop": mejor["stop"],
                                    "R_unit": mejor["R_unit"], "acciones": mejor["acciones"],
                                    "max": mejor["entrada"], "tipo": mejor["tipo"],
                                    "score": mejor["score"],
                                }

                    equity.append(capital)

                # Cierre final
                if pos:
                    R_u = pos["R_unit"]
                    R = (close_arr[-1] - pos["entrada"]) / R_u if R_u > 0 else 0
                    beneficio = (close_arr[-1] - pos["entrada"]) * pos["acciones"]
                    capital += beneficio
                    trades_ticker.append({
                        "entrada": pos["entrada"], "salida": round(float(close_arr[-1]),2),
                        "beneficio": beneficio, "R": round(R,2),
                        "motivo": "FIN", "estrategia": pos["tipo"],
                        "score": pos.get("score", 0),
                    })

                if not trades_ticker:
                    tickers_excluidos.append({"ticker": ticker, "vol": round(vol, 1)})
                    continue

                retorno = (capital - CAPITAL) / CAPITAL * 100
                todos_trades.extend(trades_ticker)
                todas_equities.extend(equity)
                Rs  = [t["R"] for t in trades_ticker]
                wrs = [t for t in trades_ticker if t["R"] > 0]
                print(f"  ✅ {ticker}: {len(trades_ticker)} trades WR={len(wrs)/len(trades_ticker)*100:.0f}% exp={np.mean(Rs):.2f}R ret={retorno:.1f}%")
                tickers_operados.append({"ticker": ticker, "retorno": round(retorno, 1), "trades": len(trades_ticker)})

            except Exception as e_t:
                print(f"⚠️ {ticker}: {e_t}")
                continue

        if not todos_trades:
            return jsonify({"success": False, "error": "Sin trades"}), 400

        # Métricas
        Rs_all  = [t["R"] for t in todos_trades]
        wrs_all = [r for r in Rs_all if r > 0]
        expectancy = float(np.mean(Rs_all))
        winrate    = len(wrs_all) / len(Rs_all) * 100

        max_dd = 0
        if todas_equities:
            peak = todas_equities[0]
            for v in todas_equities:
                if v > peak: peak = v
                dd = (peak - v) / peak * 100 if peak > 0 else 0
                if dd > max_dd: max_dd = dd

        if expectancy >= 0.40: estado = {"texto": "EXCELENTE",   "color": "success"}
        elif expectancy >= 0.20: estado = {"texto": "RENTABLE",  "color": "success"}
        elif expectancy > 0:    estado = {"texto": "MARGINAL",   "color": "warning"}
        else:                   estado = {"texto": "NO RENTABLE","color": "danger"}

        aprobados  = sorted([t for t in tickers_operados if t["retorno"] >= 2.0],  key=lambda x: x["retorno"], reverse=True)
        neutros    = sorted([t for t in tickers_operados if -2.0 <= t["retorno"] < 2.0], key=lambda x: x["retorno"], reverse=True)
        rechazados = sorted([t for t in tickers_operados if t["retorno"] < -2.0],  key=lambda x: x["retorno"])

        def _fmt(lst):
            return [{"nombre": t["ticker"].replace(".MC",""), "empresa": get_nombre(t["ticker"]),
                     "retorno": t["retorno"], "trades": t["trades"]} for t in lst]

        excl_fmt = [{"nombre": t["ticker"].replace(".MC",""), "empresa": get_nombre(t["ticker"]),
                     "vol": str(t.get("vol",""))} for t in tickers_excluidos]

        if expectancy >= 0.20 and len(aprobados) >= 5:
            rec = {"titulo": "Sistema listo para operar",
                   "acciones": [f"Operar SOLO los {len(aprobados)} tickers aprobados", "Mantener configuración actual"]}
        elif expectancy >= 0.20:
            rec = {"titulo": "Pocos tickers aprobados", "acciones": ["Considerar reducir filtro volatilidad"]}
        else:
            rec = {"titulo": "Sistema requiere optimización", "acciones": ["NO operar hasta expectancy > 0.20R"]}

        return jsonify({
            "success": True,
            "universo": nombre_universo,
            "estrategia": estrategia_param,
            "estado": estado,
            "metricas": {
                "expectancy": round(expectancy, 2),
                "winrate":    round(winrate, 1),
                "max_dd":     round(max_dd, 1),
                "total_trades": len(todos_trades),
                "tickers_activos": len(tickers_operados),
            },
            "tickers": {
                "aprobados":  _fmt(aprobados),
                "neutros":    _fmt(neutros),
                "rechazados": _fmt(rechazados),
                "excluidos":  excl_fmt,
            },
            "recomendacion": rec,
            "config": {
                "target": "2.5", "breakeven": "1",
                "riesgo": f"{RIESGO_PCT*100:.1f}", "filtro_vol": f">{MIN_VOL:.0f}%",
                "estrategia": estrategia_param,
                "entrada_modo": entrada_modo,
            },
            "periodo": "5 años",
            "entrada_modo": entrada_modo,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
