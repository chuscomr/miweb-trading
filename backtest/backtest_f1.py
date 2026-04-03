# backtest/backtest_f1.py
# ══════════════════════════════════════════════════════════════
# BACKTEST FASE 1 — Motor original portado de sistema_trading.py
# ══════════════════════════════════════════════════════════════

import logging
import datetime
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# FILTRO DE MERCADO — IBEX MM200 barra a barra
# ─────────────────────────────────────────────────────────────

def _cargar_ibex_mm200(periodo="5y"):
    """
    Descarga el IBEX35 para el filtro de mercado barra a barra.
    Pipeline: yfinance → FMP → desactivado
    EODHD rechaza tickers con '^', por eso se bypasea get_df.
    Devuelve dict {fecha: {close, mm200, mm50}}.
    """
    df_ibex = None

    # ── 1. yfinance (siempre disponible, gratuito) ────────
    try:
        import yfinance as yf
        df_raw = yf.download("^IBEX", period=periodo, progress=False, auto_adjust=True)
        if df_raw is None or df_raw.empty or len(df_raw) < 50:
            raise ValueError("yfinance devolvió datos insuficientes para ^IBEX")
        # Aplanar MultiIndex si yfinance lo genera
        if isinstance(df_raw.columns, pd.MultiIndex):
            df_raw.columns = df_raw.columns.get_level_values(0)
        # Verificar que tiene columna Close
        if "Close" not in df_raw.columns:
            raise ValueError(f"Columnas disponibles: {list(df_raw.columns)}")
        df_ibex = df_raw.copy()
        logger.info(f"IBEX cargado via yfinance: {len(df_ibex)} barras")
    except Exception as e:
        logger.warning(f"yfinance IBEX falló: {e}")

    # ── 2. yfinance con ticker alternativo ───────────────
    if df_ibex is None:
        try:
            import yfinance as yf
            # EWP es el ETF del IBEX35, muy correlacionado y más estable en yfinance
            for ticker_alt in ["EWP", "SX5E=F"]:
                df_raw = yf.download(ticker_alt, period=periodo, progress=False, auto_adjust=True)
                if df_raw is not None and not df_raw.empty and len(df_raw) >= 50:
                    if isinstance(df_raw.columns, pd.MultiIndex):
                        df_raw.columns = df_raw.columns.get_level_values(0)
                    if "Close" in df_raw.columns:
                        df_ibex = df_raw.copy()
                        logger.info(f"IBEX proxy cargado via {ticker_alt}: {len(df_ibex)} barras")
                        break
        except Exception as e:
            logger.warning(f"yfinance proxy IBEX falló: {e}")

    # ── 3. FMP (fallback para producción / Render) ────────
    if df_ibex is None or df_ibex.empty:
        try:
            import os, requests
            from datetime import datetime as _dt, timedelta
            fmp_key = os.getenv("FMP_API_KEY")
            if fmp_key:
                # Calcular fecha inicio según periodo
                anos = int(periodo.replace("y", "")) if "y" in periodo else 2
                fecha_ini = (_dt.today() - timedelta(days=anos * 365)).strftime("%Y-%m-%d")
                fecha_fin = _dt.today().strftime("%Y-%m-%d")
                r = requests.get(
                    "https://financialmodelingprep.com/api/v3/historical-price-full/%5EIBEX",
                    params={"apikey": fmp_key, "from": fecha_ini, "to": fecha_fin},
                    timeout=30,
                )
                if r.status_code == 200:
                    hist = r.json().get("historical", [])
                    if len(hist) >= 50:
                        hist = sorted(hist, key=lambda x: x["date"])
                        df_ibex = pd.DataFrame({
                            "Close":  [float(h["close"])  for h in hist],
                            "High":   [float(h.get("high",  h["close"])) for h in hist],
                            "Low":    [float(h.get("low",   h["close"])) for h in hist],
                            "Volume": [float(h.get("volume", 0)) for h in hist],
                        }, index=pd.DatetimeIndex(
                            [_dt.strptime(h["date"], "%Y-%m-%d") for h in hist]
                        ))
                        logger.info(f"IBEX cargado via FMP: {len(df_ibex)} barras")
        except Exception as e:
            logger.warning(f"FMP IBEX falló: {e}")

    # ── Sin datos → filtro desactivado ───────────────────
    if df_ibex is None or df_ibex.empty or len(df_ibex) < 50:
        logger.warning("No se pudo cargar IBEX (yfinance ni FMP) — filtro desactivado")
        return {}

    df_ibex["MM200"] = df_ibex["Close"].rolling(200).mean()
    df_ibex["MM50"]  = df_ibex["Close"].rolling(50).mean()

    filtro = {}
    for fecha, row in df_ibex.iterrows():
        fecha_d = fecha.date() if hasattr(fecha, "date") else fecha
        filtro[fecha_d] = {
            "close": float(row["Close"]),
            "mm200": float(row["MM200"]) if pd.notna(row["MM200"]) else None,
            "mm50":  float(row["MM50"])  if pd.notna(row["MM50"])  else None,
        }
    logger.info(f"Filtro IBEX listo: {len(filtro)} barras")
    return filtro


def _estado_mercado(fecha, filtro_ibex):
    """
    Devuelve el estado del mercado en esa fecha:
      'ALCISTA'    → IBEX > MM200              → breakout + pullback
      'TRANSICION' → IBEX entre MM200 y -5%    → solo pullback
      'BAJISTA'    → IBEX < MM200 * 0.95       → no operar

    Sin datos → 'ALCISTA' (no bloquea).
    """
    if not filtro_ibex:
        return "ALCISTA"

    fecha_d = fecha.date() if hasattr(fecha, "date") else fecha
    datos = filtro_ibex.get(fecha_d)
    if datos is None:
        for delta in range(1, 6):
            fecha_ant = fecha_d - datetime.timedelta(days=delta)
            datos = filtro_ibex.get(fecha_ant)
            if datos:
                break

    if datos is None:
        return "ALCISTA"

    close = datos["close"]
    mm200 = datos["mm200"]
    mm50  = datos["mm50"]

    # Usar MM50 como fallback si MM200 no disponible aún
    referencia = mm200 if mm200 is not None else mm50
    if referencia is None:
        return "ALCISTA"

    ratio = close / referencia

    if ratio >= 1.0:
        return "ALCISTA"       # IBEX sobre MM200 → todo permitido
    elif ratio >= 0.95:
        return "TRANSICION"    # IBEX hasta -5% bajo MM200 → solo pullback
    else:
        return "BAJISTA"       # IBEX > -5% bajo MM200 → no operar


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
    mm50     = sum(precios[-50:]) / 50 if len(precios) >= 50 else None
    mm20_ant = sum(precios[-25:-5]) / 20
    pendiente_mm20 = mm20 - mm20_ant

    # Mejora 1: máximo 52 días en vez de 20
    max52    = max(precios[-52:]) if len(precios) >= 52 else max(precios[-20:])
    max20    = max(precios[-20:])
    min20    = min(precios[-20:])
    volatilidad = (max20 - min20) / min20 * 100 if min20 > 0 else 999

    # OBLIGATORIO 1: precio sobre MM50 con pendiente MM20 positiva
    # (Mejora 2: relajar estructura — precio>MM50 + MM20 pendiente alcista)
    if mm50 is not None:
        estructura_ok = precio > mm50 and pendiente_mm20 > 0
    else:
        estructura_ok = precio > mm20 and pendiente_mm20 > 0
    if not estructura_ok:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    rsi = _calcular_rsi(precios)
    if rsi is None:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    # OBLIGATORIO 2: RSI en rango momentum
    if not (45 < rsi < 82):
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    if volatilidad > 10:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    dist_mm   = abs(precio - mm20) / mm20 * 100
    # Mejora 1: distancia al máximo 52d (antes max20)
    dist_max52 = (max52 - precio) / max52 * 100

    eval_vol = _evaluar_volumen(volumenes)

    # Volumen obligatorio
    if not eval_vol["permitir_normal"] and not eval_vol["permitir_impulso"]:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": 0}

    # Score ponderado (sincronizado con breakout.py)
    setup_score = 0.0
    if dist_max52 <= 3.0:                        setup_score += 2.0
    if precio > mm20:                            setup_score += 2.5
    if 55 <= rsi <= 70:                          setup_score += 2.5
    if volatilidad <= 6:                         setup_score += 3.0
    if eval_vol.get("bonus_score", 0) > 0:       setup_score += 0.5
    setup_score = round(min(setup_score, 10.0), 1)

    SCORE_MINIMO = 5.0

    if setup_score < SCORE_MINIMO:
        return {"decision": "NO OPERAR", "entrada_tecnica": None, "setup_score": setup_score}

    # Entrada calculada sobre máximo 52d
    if setup_score >= 7.0 and eval_vol["permitir_impulso"]:
        return {
            "decision":        "COMPRA",
            "entrada_tecnica": _calcular_entrada(precio, max52, dist_max52),
            "setup_score":     setup_score,
        }

    if eval_vol["permitir_normal"]:
        return {
            "decision":        "COMPRA",
            "entrada_tecnica": _calcular_entrada(precio, max52, dist_max52),
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
                         highs=None, lows=None,
                         filtro_ibex=None):
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
            R_unit     = pos_actual["entrada"] - pos_actual["stop_inicial"]
            R_actual   = (high_hoy - pos_actual["entrada"]) / R_unit if R_unit > 0 else 0
            atr        = pos_actual.get("atr")
            R_unit_pos = R_unit  # alias legible

            # ── Break-even en +1R
            if R_actual >= 1.0 and pos_actual["stop_actual"] < pos_actual["entrada"]:
                pos_actual["stop_actual"] = pos_actual["entrada"]
                pos_actual["gestion"]     = "BE (+1R)"

            # ── Salida parcial 50% en +2R (si aún no se ejecutó)
            target_parcial = pos_actual["entrada"] + 2.0 * R_unit_pos if R_unit_pos > 0 else None
            if (target_parcial
                    and not pos_actual.get("parcial_ejecutada")
                    and high_hoy >= target_parcial):
                acc_parcial = max(1, pos_actual["acciones"] // 2)
                beneficio_parcial = (target_parcial - pos_actual["entrada"]) * acc_parcial
                capital    += beneficio_parcial
                max_capital = max(max_capital, capital)
                pos_actual["acciones"]         -= acc_parcial
                pos_actual["parcial_ejecutada"] = True
                pos_actual["gestion"]           = "PARCIAL 50%@2R"
                # Mover stop a break-even tras salida parcial
                if pos_actual["stop_actual"] < pos_actual["entrada"]:
                    pos_actual["stop_actual"] = pos_actual["entrada"]
                trades.append({
                    "fecha_entrada": pos_actual["fecha_entrada"].strftime("%Y-%m-%d"),
                    "fecha_salida":  fecha_hoy.strftime("%Y-%m-%d"),
                    "entrada":       round(pos_actual["entrada"], 2),
                    "salida":        round(target_parcial, 2),
                    "beneficio":     round(beneficio_parcial, 2),
                    "R_alcanzado":   2.0,
                    "gestion":       "PARCIAL +2R",
                    "setup_score":   pos_actual["setup_score"],
                })

            # ── Trailing stop ATR en el 50% restante (tras salida parcial)
            if pos_actual.get("parcial_ejecutada") and atr:
                trailing_nivel = pos_actual["max_precio"] - 1.5 * atr
                if trailing_nivel > pos_actual["stop_actual"]:
                    pos_actual["stop_actual"] = trailing_nivel
                    pos_actual["gestion"]     = "TRAILING ATR"

            # ── Target final +3R (50% restante) o STOP
            target_final  = pos_actual["entrada"] + 3.0 * R_unit_pos if R_unit_pos > 0 else None
            precio_salida = None
            motivo_salida = None

            if target_final and high_hoy >= target_final:
                precio_salida = target_final
                motivo_salida = "TARGET +3R"
            elif low_hoy <= pos_actual["stop_actual"]:
                precio_salida = pos_actual["stop_actual"]
                motivo_salida = "STOP" if not pos_actual.get("parcial_ejecutada") else "STOP (trailing)"

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
            # Filtro de mercado:
            #   ALCISTA    → breakout + pullback
            #   TRANSICION → solo pullback (score >= 7 exigido)
            #   BAJISTA    → no operar
            estado_mkt = _estado_mercado(fecha_hoy, filtro_ibex) if filtro_ibex else "ALCISTA"

            if estado_mkt == "BAJISTA":
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            señal = _evaluar_señal(precios[:i+1], volumenes[:i+1])
            if señal["decision"] != "COMPRA":
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

            entrada     = señal["entrada_tecnica"]
            setup_score = señal.get("setup_score", 3)

            # En TRANSICION solo permitir setups de alta calidad (score >= 7)
            if estado_mkt == "TRANSICION" and setup_score < 7.0:
                dd = (max_capital - capital) / max_capital if max_capital > 0 else 0
                equity_curve.append({"fecha": fecha_hoy.strftime("%Y-%m-%d"),
                                     "capital": round(capital, 2), "drawdown": round(dd*100, 2)})
                continue

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
            if not (1.0 <= riesgo_pct <= 10.0):
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

    # ── Filtro de mercado: cargar IBEX una sola vez ──────────
    print(">>> Cargando filtro IBEX MM200...")
    filtro_ibex = _cargar_ibex_mm200(periodo=periodo)
    if filtro_ibex:
        fechas_muestra = sorted(filtro_ibex.keys())
        primera = fechas_muestra[0]
        ultima  = fechas_muestra[-1]
        dato_ej = filtro_ibex[ultima]
        print(f">>> Filtro IBEX OK: {len(filtro_ibex)} barras ({primera} → {ultima})")
        print(f">>> Último dato IBEX: close={dato_ej['close']:.0f} MM200={dato_ej['mm200']}")
        alcista = dato_ej['mm200'] and dato_ej['close'] >= dato_ej['mm200']
        print(f">>> Estado hoy: {'ALCISTA' if alcista else 'BAJISTA/TRANSICION'}")
    else:
        print(">>> ADVERTENCIA: Filtro IBEX vacío — backtest SIN filtro de mercado")

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
                filtro_ibex=filtro_ibex,
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
