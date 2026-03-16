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

        tickers_operados  = []
        tickers_excluidos = []
        todos_trades      = []
        todas_equities    = []

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
                                                    risk, portfolio)
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
                                  "vol":     t["vol"]}
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
