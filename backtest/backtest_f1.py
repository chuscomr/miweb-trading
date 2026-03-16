# backtest/backtest_f1.py
# ══════════════════════════════════════════════════════════════
# BACKTEST FASE 1 — Motor original portado de sistema_trading.py
# ══════════════════════════════════════════════════════════════

import logging
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# INDICADORES (portados de sistema_trading.py)
# ─────────────────────────────────────────────────────────────

def _calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return None
    deltas = [precios[i] - precios[i-1] for i in range(1, len(precios))]
    ganancias = [max(d, 0) for d in deltas]
    perdidas  = [abs(min(d, 0)) for d in deltas]
    # EMA suavizada
    avg_g = sum(ganancias[:periodo]) / periodo
    avg_p = sum(perdidas[:periodo]) / periodo
    for i in range(periodo, len(ganancias)):
        avg_g = (avg_g * (periodo - 1) + ganancias[i]) / periodo
        avg_p = (avg_p * (periodo - 1) + perdidas[i]) / periodo
    if avg_p == 0:
        return 100.0
    rs = avg_g / avg_p
    return round(100 - (100 / (1 + rs)), 2)


def _evaluar_volumen(volumenes):
    if len(volumenes) < 21:
        return {"permitir_normal": True, "permitir_impulso": False,
                "bonus_score": 0, "penalizacion_score": -1}
    vol_actual   = volumenes[-2]
    media_10     = sum(volumenes[-11:-1]) / 10
    media_20     = sum(volumenes[-21:-1]) / 20
    if media_20 < 50_000:
        return {"permitir_normal": False, "permitir_impulso": False,
                "bonus_score": 0, "penalizacion_score": -3}
    ratio    = vol_actual / media_10 if media_10 > 0 else 0
    tendencia = media_10 / media_20 if media_20 > 0 else 1.0
    if ratio >= 1.5:
        return {"permitir_normal": True,  "permitir_impulso": True,
                "bonus_score": 1,  "penalizacion_score": 0}
    if ratio >= 1.05:
        return {"permitir_normal": True,  "permitir_impulso": True,
                "bonus_score": 0,  "penalizacion_score": 0}
    if ratio >= 0.85 and tendencia >= 1.1:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": 0}
    if tendencia >= 1.0:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": 0}
    if ratio >= 0.75:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": -1}
    return {"permitir_normal": False, "permitir_impulso": False,
            "bonus_score": 0,  "penalizacion_score": -2}


def _calcular_entrada(precio, max20, dist_max):
    if dist_max <= 0.5:
        return round(max20 * 1.001, 2)
    elif dist_max <= 1.5:
        return round(precio * 1.005, 2)
    else:
        return round(((precio + max20) / 2) * 1.002, 2)


def _evaluar_señal(precios, volumenes):
    """
    Lógica original de sistema_trading: MM20, RSI, volumen, distancia máximo.
    """
    if len(precios) < 50:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    precio   = precios[-1]
    mm20     = sum(precios[-20:]) / 20
    mm20_ant = sum(precios[-25:-5]) / 20
    pendiente = mm20 - mm20_ant
    max20    = max(precios[-20:])
    min20    = min(precios[-20:])
    volatilidad = (max20 - min20) / min20 * 100 if min20 > 0 else 999

    # Condiciones básicas
    if precio <= mm20 or pendiente <= 0:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    rsi = _calcular_rsi(precios)
    if rsi is None:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    if volatilidad > 10:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    dist_mm  = abs(precio - mm20) / mm20 * 100
    dist_max = (max20 - precio) / max20 * 100

    eval_vol = _evaluar_volumen(volumenes)

    # Setup score (igual que el original)
    setup_score = 0
    if rsi >= 55:          setup_score += 1
    if 60 <= rsi <= 68:    setup_score += 1
    if dist_max <= 1:      setup_score += 1
    if dist_mm <= 3:       setup_score += 1
    if pendiente > 0:
        setup_score += 1
        setup_score += eval_vol.get("bonus_score", 0)
        setup_score += eval_vol.get("penalizacion_score", 0)
        setup_score = max(0, min(setup_score, 5))

    # Compra normal
    if (45 < rsi < 70 and dist_mm <= 4 and dist_max <= 3
            and setup_score >= 3 and eval_vol["permitir_normal"]):
        return {
            "decision":        "COMPRA",
            "entrada_tecnica": _calcular_entrada(precio, max20, dist_max),
            "setup_score":     setup_score,
        }

    # Compra impulso
    if (60 <= rsi <= 73 and dist_mm <= 6 and dist_max <= 3
            and setup_score >= 4 and eval_vol["permitir_impulso"]):
        return {
            "decision":        "COMPRA",
            "entrada_tecnica": _calcular_entrada(precio, max20, dist_max),
            "setup_score":     setup_score,
        }

    return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": setup_score}


# ─────────────────────────────────────────────────────────────
# ATR
# ─────────────────────────────────────────────────────────────

def _calcular_atr(precios, periodo=14):
    if len(precios) < periodo + 1:
        return None
    trs = [abs(precios[i] - precios[i-1]) for i in range(1, len(precios))]
    return sum(trs[-periodo:]) / periodo


# ─────────────────────────────────────────────────────────────
# ALINEAMIENTO
# ─────────────────────────────────────────────────────────────

def _alinear(precios, volumenes, fechas):
    n = min(len(precios), len(volumenes), len(fechas))
    datos = [(fechas[i], precios[i], volumenes[i])
             for i in range(n) if precios[i] is not None and volumenes[i] is not None]
    datos.sort(key=lambda x: x[0])
    return ([d[1] for d in datos], [d[2] for d in datos], [d[0] for d in datos])


# ─────────────────────────────────────────────────────────────
# MÉTRICAS
# ─────────────────────────────────────────────────────────────

def _calcular_metricas(trades, equity_curve, capital_inicial, capital_final):
    if not trades:
        return {"total_trades": 0, "win_rate_pct": 0, "profit_factor": 0,
                "expectancy": 0, "expectancy_R": 0, "max_drawdown_pct": 0,
                "retorno_pct": 0, "avg_win": 0, "avg_loss": 0,
                "payoff_ratio": 0, "r_promedio": 0}
    beneficios = [t["beneficio"] for t in trades]
    R_trades   = [t.get("R_alcanzado", 0) for t in trades]
    ganadores  = [b for b in beneficios if b > 0]
    perdedores = [b for b in beneficios if b < 0]
    total      = len(trades)
    win_rate   = len(ganadores) / total * 100
    suma_g     = sum(ganadores)
    suma_p     = abs(sum(perdedores))
    pf         = suma_g / suma_p if suma_p > 0 else (99 if suma_g > 0 else 0)
    expectancy = sum(beneficios) / total
    exp_R      = sum(R_trades) / total
    max_dd     = max((e.get("drawdown", 0) for e in equity_curve), default=0)
    retorno    = (capital_final - capital_inicial) / capital_inicial * 100
    avg_win    = sum(ganadores) / len(ganadores) if ganadores else 0
    avg_loss   = abs(sum(perdedores) / len(perdedores)) if perdedores else 0
    return {
        "total_trades":     total,
        "win_rate_pct":     round(win_rate, 2),
        "profit_factor":    round(pf, 2),
        "expectancy":       round(expectancy, 2),
        "expectancy_R":     round(exp_R, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "retorno_pct":      round(retorno, 2),
        "avg_win":          round(avg_win, 2),
        "avg_loss":         round(avg_loss, 2),
        "payoff_ratio":     round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        "r_promedio":       round(exp_R, 2),
    }


# ─────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

def ejecutar_backtest_f1(precios, volumenes, fechas,
                         capital_inicial=10_000,
                         riesgo_pct_trade=0.01,
                         highs=None, lows=None):
    if not precios or len(precios) < 50:
        return {"capital_inicial": capital_inicial, "capital_final": capital_inicial,
                "trades": [], "equity_curve": [],
                "metricas": _calcular_metricas([], [], capital_inicial, capital_inicial)}

    precios, volumenes, fechas = _alinear(precios, volumenes, fechas)
    if len(precios) < 50:
        return {"capital_inicial": capital_inicial, "capital_final": capital_inicial,
                "trades": [], "equity_curve": [],
                "metricas": _calcular_metricas([], [], capital_inicial, capital_inicial)}

    capital     = capital_inicial
    max_capital = capital_inicial
    equity_curve = []
    trades      = []
    en_posicion = False
    pos_actual  = None
    ultimo_max  = None

    for i in range(50, len(precios)):
        precio_hoy = precios[i]
        fecha_hoy  = fechas[i]
        high_hoy   = highs[i] if highs and len(highs) > i else precio_hoy
        low_hoy    = lows[i]  if lows  and len(lows)  > i else precio_hoy

        # ── Gestión posición abierta ─────────────────────
        if en_posicion and pos_actual:
            pos_actual["max_precio"] = max(pos_actual["max_precio"], high_hoy)
            R_unit   = pos_actual["entrada"] - pos_actual["stop_inicial"]
            R_actual = (high_hoy - pos_actual["entrada"]) / R_unit if R_unit > 0 else 0
            atr      = pos_actual.get("atr")

            # Break-even en +1R (igual que position.py original)
            if R_actual >= 1.0 and pos_actual["stop_actual"] < pos_actual["entrada"]:
                pos_actual["stop_actual"] = pos_actual["entrada"]
                pos_actual["gestion"]     = "BE (+1R)"

            # TARGET en +3R usando high (igual que position.py original)
            R_unit_pos = pos_actual["entrada"] - pos_actual["stop_inicial"]
            target     = pos_actual["entrada"] + 3.0 * R_unit_pos if R_unit_pos > 0 else None

            precio_salida = None
            motivo_salida = None

            if target and high_hoy >= target:
                precio_salida = target
                motivo_salida = "TARGET +3R"
            elif low_hoy <= pos_actual["stop_actual"]:
                precio_salida = pos_actual["stop_actual"]
                motivo_salida = "STOP"

            if precio_salida is not None:
                R_cerrado = (precio_salida - pos_actual["entrada"]) / R_unit_pos if R_unit_pos > 0 else 0
                beneficio = (precio_salida - pos_actual["entrada"]) * pos_actual["acciones"]
                capital  += beneficio
                max_capital = max(max_capital, capital)
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                trades.append({
                    "fecha_entrada": pos_actual["fecha_entrada"].strftime("%Y-%m-%d"),
                    "fecha_salida":  fecha_hoy.strftime("%Y-%m-%d"),
                    "entrada":       round(pos_actual["entrada"], 2),
                    "salida":        round(precio_salida, 2),
                    "beneficio":     round(beneficio, 2),
                    "R_alcanzado":   round(R_cerrado, 2),
                    "gestion":       motivo_salida,
                    "setup_score":   pos_actual["setup_score"],
                })
                ultimo_max  = pos_actual["max_precio"]
                en_posicion = False
                pos_actual  = None

        # ── Buscar entrada ───────────────────────────────
        if not en_posicion:
            señal = _evaluar_señal(precios[:i+1], volumenes[:i+1])
            if señal["decision"] != "COMPRA":
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            entrada     = señal["entrada_tecnica"]
            setup_score = señal.get("setup_score", 3)

            if ultimo_max and entrada <= ultimo_max:
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            atr  = _calcular_atr(precios[:i+1])
            mult = 2.5 if setup_score >= 4 else 1.8
            stop = (entrada - atr * mult) if atr else entrada * 0.96

            if not stop or stop <= 0 or stop >= entrada:
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            riesgo_acc = entrada - stop
            riesgo_pct = riesgo_acc / entrada * 100
            if not (1.0 <= riesgo_pct <= 3.0):
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            acciones = int(capital * riesgo_pct_trade / riesgo_acc)
            if acciones <= 0:
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            exp_max = 35.0 if setup_score >= 5 else 25.0
            if acciones * entrada > capital * (exp_max / 100):
                acciones = int(capital * (exp_max / 100) / entrada)
            if acciones <= 0 or acciones * entrada > capital:
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            en_posicion = True
            pos_actual  = {
                "fecha_entrada": fecha_hoy,
                "entrada":       entrada,
                "stop_inicial":  stop,
                "stop_actual":   stop,
                "acciones":      acciones,
                "max_precio":    entrada,
                "setup_score":   setup_score,
                "gestion":       "Inicial",
                "atr":           atr,
            }

        dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
        equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                              "capital": round(capital, 2),
                              "drawdown": round(dd*100, 2),
                              "en_posicion": en_posicion})

    # Cierre final
    if en_posicion and pos_actual:
        precio_f  = precios[-1]
        beneficio = (precio_f - pos_actual["entrada"]) * pos_actual["acciones"]
        capital  += beneficio
        R_unit    = pos_actual["entrada"] - pos_actual["stop_inicial"]
        R_final   = (precio_f - pos_actual["entrada"]) / R_unit if R_unit > 0 else 0
        trades.append({
            "fecha_entrada": pos_actual["fecha_entrada"].strftime("%Y-%m-%d"),
            "fecha_salida":  fechas[-1].strftime("%Y-%m-%d"),
            "entrada":       round(pos_actual["entrada"], 2),
            "salida":        round(precio_f, 2),
            "beneficio":     round(beneficio, 2),
            "R_alcanzado":   round(R_final, 2),
            "gestion":       "Cierre final",
            "setup_score":   pos_actual["setup_score"],
        })

    metricas = _calcular_metricas(trades, equity_curve, capital_inicial, capital)
    logger.info(f"✅ Backtest F1: {len(trades)} trades, {metricas['retorno_pct']}%")

    return {
        "capital_inicial": capital_inicial,
        "capital_final":   round(capital, 2),
        "trades":          trades,
        "equity_curve":    equity_curve,
        "metricas":        metricas,
    }


# ─────────────────────────────────────────────────────────────
# BACKTEST MULTI-TICKER (para el modal "Sistema Completo")
# ─────────────────────────────────────────────────────────────

def ejecutar_backtest_f1_sistema(tickers, cache=None, capital_inicial=10_000,
                                  riesgo_pct_trade=0.01, periodo="5y"):
    """
    Ejecuta backtest_f1 sobre una lista de tickers y devuelve la estructura
    JSON exacta que espera el modal JS de swing.html:
      estado, metricas, tickers {aprobados, neutros, rechazados, excluidos},
      recomendacion, config
    """
    from core.data_provider import get_df
    from core.universos import get_nombre

    tickers_operados = []
    tickers_excluidos = []
    todos_trades = []
    todas_equities = []

    MIN_VOLATILIDAD = 9.0

    for ticker in tickers:
        try:
            df = get_df(ticker, periodo=periodo, cache=cache, min_velas=60)
            if df is None or df.empty or len(df) < 60:
                tickers_excluidos.append({
                    "nombre":  ticker.replace(".MC", ""),
                    "empresa": get_nombre(ticker),
                    "vol":     "sin datos",
                })
                continue

            precios   = df["Close"].tolist()
            volumenes = df["Volume"].tolist()
            fechas    = list(df.index)
            highs     = df["High"].tolist()  if "High"   in df.columns else None
            lows      = df["Low"].tolist()   if "Low"    in df.columns else None

            # Filtro volatilidad (último año)
            ventana = min(252, len(precios))
            import statistics
            media = sum(precios[-ventana:]) / ventana
            std   = statistics.stdev(precios[-ventana:]) if ventana > 1 else 0
            vol   = (std / media * 100) if media > 0 else 0

            if vol < MIN_VOLATILIDAD:
                tickers_excluidos.append({
                    "nombre":  ticker.replace(".MC", ""),
                    "empresa": get_nombre(ticker),
                    "vol":     f"{vol:.1f}",
                })
                continue

            resultado = ejecutar_backtest_f1(
                precios, volumenes, fechas,
                capital_inicial=capital_inicial,
                riesgo_pct_trade=riesgo_pct_trade,
                highs=highs, lows=lows,
            )

            trades = resultado.get("trades", [])
            if not trades:
                tickers_excluidos.append({
                    "nombre":  ticker.replace(".MC", ""),
                    "empresa": get_nombre(ticker),
                    "vol":     f"{vol:.1f} (0 trades)",
                })
                continue

            todos_trades.extend(trades)
            equity = resultado.get("equity_curve", [])
            todas_equities.extend([e.get("capital", capital_inicial) for e in equity])

            capital_final = resultado["capital_final"]
            retorno = (capital_final - capital_inicial) / capital_inicial * 100

            tickers_operados.append({
                "ticker":  ticker,
                "retorno": round(retorno, 1),
                "trades":  len(trades),
                "vol":     round(vol, 1),
            })

        except Exception as e:
            logger.warning(f"Error en {ticker}: {e}")
            tickers_excluidos.append({
                "nombre":  ticker.replace(".MC", ""),
                "empresa": get_nombre(ticker),
                "vol":     str(e)[:30],
            })

    # ── Métricas globales ─────────────────────────────────────
    if not todos_trades:
        return {
            "estado":    {"color": "danger", "texto": "SIN TRADES"},
            "metricas":  {"expectancy": 0, "winrate": 0, "max_dd": 0,
                          "total_trades": 0, "tickers_activos": 0},
            "tickers":   {"aprobados": [], "neutros": [], "rechazados": [],
                          "excluidos": tickers_excluidos},
            "recomendacion": {"titulo": "Sin datos suficientes",
                              "acciones": ["Revisa la conexión de datos"]},
            "config":    {"target": "3", "breakeven": "1",
                          "riesgo": "1.0", "filtro_vol": ">9"},
            "periodo":   "5 años",
            "universo":  f"IBEX 35 ({len(tickers_operados)} tickers)",
        }

    beneficios  = [t["beneficio"] for t in todos_trades]
    ganadores   = [b for b in beneficios if b > 0]
    perdedores  = [b for b in beneficios if b < 0]
    total       = len(todos_trades)
    winrate     = len(ganadores) / total * 100
    expectancy  = sum(beneficios) / total
    suma_g      = sum(ganadores)
    suma_p      = abs(sum(perdedores)) if perdedores else 1
    pf          = suma_g / suma_p

    # Max DD sobre equity global
    max_dd = 0
    if todas_equities:
        peak = todas_equities[0]
        for v in todas_equities:
            if v > peak: peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            if dd > max_dd: max_dd = dd

    # Expectancy en R (normalizado al riesgo medio por trade)
    r_values = [t.get("R_alcanzado", 0) for t in todos_trades]
    expectancy_R = sum(r_values) / total if total > 0 else 0

    # ── Clasificar tickers ────────────────────────────────────
    aprobados, neutros, rechazados = [], [], []
    for t in tickers_operados:
        entry = {
            "nombre":  t["ticker"].replace(".MC", ""),
            "empresa": get_nombre(t["ticker"]),
            "retorno": t["retorno"],
            "trades":  t["trades"],
        }
        if t["retorno"] >= 2.0:
            aprobados.append(entry)
        elif t["retorno"] >= -2.0:
            neutros.append(entry)
        else:
            rechazados.append(entry)

    aprobados.sort(key=lambda x: x["retorno"], reverse=True)
    rechazados.sort(key=lambda x: x["retorno"])

    # ── Estado ───────────────────────────────────────────────
    if expectancy_R >= 0.40:
        estado = {"color": "success", "texto": "EXCELENTE"}
    elif expectancy_R >= 0.20:
        estado = {"color": "success", "texto": "RENTABLE"}
    elif expectancy_R > 0:
        estado = {"color": "warning", "texto": "MARGINAL"}
    else:
        estado = {"color": "danger",  "texto": "NO RENTABLE"}

    # ── Recomendación ─────────────────────────────────────────
    if expectancy_R >= 0.20 and len(aprobados) >= 5:
        recomendacion = {
            "titulo":   "Sistema listo para operar",
            "acciones": [f"Operar SOLO los {len(aprobados)} tickers aprobados",
                         "Mantener configuración actual"],
        }
    elif expectancy_R >= 0.20:
        recomendacion = {
            "titulo":   "Pocos tickers aprobados",
            "acciones": ["Considerar reducir filtro de volatilidad",
                         "O incluir tickers neutros en watchlist"],
        }
    else:
        recomendacion = {
            "titulo":   "Sistema requiere optimización",
            "acciones": ["Revisar parámetros de entrada",
                         "NO operar hasta expectancy > 0.20R"],
        }

    return {
        "estado":   estado,
        "metricas": {
            "expectancy":      round(expectancy_R, 2),
            "winrate":         round(winrate, 1),
            "max_dd":          round(max_dd, 1),
            "total_trades":    total,
            "tickers_activos": len(tickers_operados),
        },
        "tickers": {
            "aprobados":  aprobados,
            "neutros":    neutros,
            "rechazados": rechazados,
            "excluidos":  tickers_excluidos,
        },
        "recomendacion": recomendacion,
        "config": {
            "target":     "3",
            "breakeven":  "1",
            "riesgo":     f"{riesgo_pct_trade*100:.1f}",
            "filtro_vol": ">9",
        },
        "periodo":  "5 años",
        "universo": f"IBEX 35 ({len(tickers_operados)} tickers)",
    }
