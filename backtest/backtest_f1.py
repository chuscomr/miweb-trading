# backtest/backtest_f1.py
# ══════════════════════════════════════════════════════════════
# BACKTEST F1 — Sincronizado con breakout.py y pullback.py
#
# BREAKOUT (alineado con breakout.py):
#   Obligatorios: RSI 55-70 · Volumen ≥1.2x · Resistencia
#   Score:        Máx52d(1.5) + Consol(2.0) + VCP(1.5)
#                 + Estructura(2.5) + Estructura2(2.5) ≥ 5.0
#   Stop:         mín consolidación × 0.98
#
# PULLBACK (alineado con pullback.py):
#   Obligatorios: Tendencia macro (precio>MM200×0.95 + MM50>MM200)
#                 · Retroceso 5-15% desde máx 60d
#   Score:        RSI(1.5) + Soporte(2.0) + Vela(1.5)
#                 + Estructura(5.0) + bonus RSI(0.5) ≥ 5.5
#   Stop:         mín(5 velas, soporte 30d) × 0.98
#
# Gestión: BE(+1R) → Parcial 50%@+2R → Trailing ATR → Target +3R
# ══════════════════════════════════════════════════════════════

import logging
import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# FILTRO DE MERCADO — IBEX MM200 barra a barra
# ─────────────────────────────────────────────────────────────

def _cargar_ibex_mm200(periodo="5y"):
    df_ibex = None
    try:
        import yfinance as yf
        df_raw = yf.download("^IBEX", period=periodo, progress=False, auto_adjust=True)
        if df_raw is not None and not df_raw.empty and len(df_raw) >= 50:
            if isinstance(df_raw.columns, pd.MultiIndex):
                df_raw.columns = df_raw.columns.get_level_values(0)
            if "Close" in df_raw.columns:
                df_ibex = df_raw.copy()
    except Exception as e:
        logger.warning(f"yfinance IBEX falló: {e}")

    if df_ibex is None:
        try:
            import yfinance as yf
            for alt in ["EWP", "SX5E=F"]:
                df_raw = yf.download(alt, period=periodo, progress=False, auto_adjust=True)
                if df_raw is not None and not df_raw.empty and len(df_raw) >= 50:
                    if isinstance(df_raw.columns, pd.MultiIndex):
                        df_raw.columns = df_raw.columns.get_level_values(0)
                    if "Close" in df_raw.columns:
                        df_ibex = df_raw.copy()
                        break
        except Exception:
            pass

    if df_ibex is None or df_ibex.empty:
        try:
            import os, requests
            from datetime import datetime as _dt, timedelta
            fmp_key = os.getenv("FMP_API_KEY")
            if fmp_key:
                anos = int(periodo.replace("y","")) if "y" in periodo else 2
                fecha_ini = (_dt.today() - timedelta(days=anos*365)).strftime("%Y-%m-%d")
                r = requests.get(
                    "https://financialmodelingprep.com/api/v3/historical-price-full/%5EIBEX",
                    params={"apikey": fmp_key, "from": fecha_ini,
                            "to": _dt.today().strftime("%Y-%m-%d")}, timeout=30)
                if r.status_code == 200:
                    hist = sorted(r.json().get("historical",[]), key=lambda x: x["date"])
                    if len(hist) >= 50:
                        df_ibex = pd.DataFrame({
                            "Close": [float(h["close"]) for h in hist],
                            "High":  [float(h.get("high", h["close"])) for h in hist],
                            "Low":   [float(h.get("low",  h["close"])) for h in hist],
                        }, index=pd.DatetimeIndex([
                            datetime.datetime.strptime(h["date"],"%Y-%m-%d") for h in hist]))
        except Exception as e:
            logger.warning(f"FMP IBEX falló: {e}")

    if df_ibex is None or df_ibex.empty or len(df_ibex) < 50:
        logger.warning("IBEX no disponible — filtro desactivado")
        return {}

    df_ibex["MM200"] = df_ibex["Close"].rolling(200).mean()
    df_ibex["MM50"]  = df_ibex["Close"].rolling(50).mean()

    filtro = {}
    for fecha, row in df_ibex.iterrows():
        fd = fecha.date() if hasattr(fecha, "date") else fecha
        filtro[fd] = {
            "close": float(row["Close"]),
            "mm200": float(row["MM200"]) if pd.notna(row["MM200"]) else None,
            "mm50":  float(row["MM50"])  if pd.notna(row["MM50"])  else None,
        }
    return filtro


def _estado_mercado(fecha, filtro_ibex):
    if not filtro_ibex:
        return "ALCISTA"
    fd = fecha.date() if hasattr(fecha, "date") else fecha
    datos = filtro_ibex.get(fd)
    if datos is None:
        for d in range(1, 6):
            datos = filtro_ibex.get(fd - datetime.timedelta(days=d))
            if datos: break
    if datos is None:
        return "ALCISTA"
    ref = datos["mm200"] or datos["mm50"]
    if ref is None:
        return "ALCISTA"
    ratio = datos["close"] / ref
    if ratio >= 1.0:    return "ALCISTA"
    elif ratio >= 0.95: return "TRANSICION"
    else:               return "BAJISTA"


# ─────────────────────────────────────────────────────────────
# INDICADORES (vectorizados sobre listas — rápido)
# ─────────────────────────────────────────────────────────────

def _rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return None
    d = [precios[i] - precios[i-1] for i in range(1, len(precios))]
    g = [max(x,0) for x in d]
    p = [abs(min(x,0)) for x in d]
    ag = sum(g[:periodo]) / periodo
    ap = sum(p[:periodo]) / periodo
    for i in range(periodo, len(g)):
        ag = (ag*(periodo-1) + g[i]) / periodo
        ap = (ap*(periodo-1) + p[i]) / periodo
    return round(100 - (100/(1 + ag/ap)), 2) if ap > 0 else 100.0


def _atr(precios, highs, lows, periodo=14):
    n = min(len(precios), len(highs), len(lows))
    if n < periodo + 1:
        return None
    trs = [max(highs[i]-lows[i],
               abs(highs[i]-precios[i-1]),
               abs(lows[i] -precios[i-1]))
           for i in range(max(1,n-periodo-5), n)]
    return sum(trs[-periodo:]) / periodo if len(trs) >= periodo else sum(trs)/len(trs)


# ─────────────────────────────────────────────────────────────
# SEÑAL BREAKOUT — alineada con breakout.py
# ─────────────────────────────────────────────────────────────

def _señal_breakout(precios, volumenes, highs, lows):
    """
    Obligatorios: RSI 55-70 · Volumen ≥1.2x media3/media20 · Resistencia implícita
    Score (máx 10): máx52d(1.5) + consol(2.0) + VCP(1.5) + est(2.5) + est2(2.5)
    Umbral: ≥5.0
    Stop: mín consolidación × 0.98
    """
    n = len(precios)
    if n < 52:
        return None

    precio = precios[-1]

    # MMs
    mm20  = sum(precios[-20:]) / 20
    mm50  = sum(precios[-50:]) / 50 if n >= 50 else None

    # RSI — OBLIGATORIO 55-70
    rsi = _rsi(precios)
    if rsi is None or not (55 <= rsi <= 70):
        return None

    # Volumen — OBLIGATORIO ≥1.2x (alineado con breakout.py IBEX)
    if len(volumenes) >= 20:
        vol_media20 = sum(volumenes[-21:-1]) / 20
        vol_3v      = sum(volumenes[-3:]) / 3
        ratio_vol   = vol_3v / vol_media20 if vol_media20 > 0 else 0
        if ratio_vol < 1.2:
            return None
    else:
        return None

    # Máximo 52d — distancia
    max52     = max(precios[-52:])
    dist_max  = (max52 - precio) / max52 * 100

    # Resistencia implícita: precio debe estar cerca del máximo 52d (≤3%)
    # equivale a "resistencia identificada" del sistema real
    if dist_max > 3.0:
        return None

    # Consolidación: rango ≤10% en últimas N velas
    consol_dias = 0
    for k in range(5, min(41, n)):
        rango = (max(precios[-k:]) - min(precios[-k:])) / min(precios[-k:]) * 100
        if rango <= 10.0:
            consol_dias = k
        else:
            break

    # VCP: volumen decreciente durante consolidación
    vcp_ok = False
    if consol_dias >= 5 and len(volumenes) >= consol_dias + 1:
        vc = volumenes[-(consol_dias+1):-1]
        if len(vc) >= 4:
            primera = sum(vc[:len(vc)//2]) / max(1, len(vc)//2)
            segunda = sum(vc[len(vc)//2:]) / max(1, len(vc) - len(vc)//2)
            vcp_ok = segunda < primera * 0.85

    # Estructura alcista
    est_ok  = mm50 is not None and precio >= mm20 * 0.98
    est2_ok = mm50 is not None and mm20 >= mm50 * 0.98

    # Score opcionales (alineado con breakout.py)
    score = 0.0
    if dist_max <= 3.0:   score += 1.5
    if consol_dias >= 8:  score += 2.0
    if vcp_ok:            score += 1.5
    if est_ok:            score += 2.5
    if est2_ok:           score += 2.5

    if score < 5.0:
        return None

    # Stop: mínimo consolidación × 0.98 (alineado con breakout.py)
    lookback  = max(consol_dias, 5)
    min_l     = min(lows[-lookback:]) if lows and len(lows) >= lookback else min(precios[-lookback:])
    stop      = round(min_l * 0.98, 4)
    atr_val   = _atr(precios, highs if highs else precios, lows if lows else precios)

    if stop <= 0 or stop >= precio:
        if atr_val:
            stop = round(precio - atr_val * 2, 4)
        else:
            return None

    riesgo_pct = (precio - stop) / precio * 100
    if not (0.5 <= riesgo_pct <= 10.0):
        return None

    return {"decision": "COMPRA", "tipo": "BREAKOUT",
            "entrada": round(precio, 4), "stop": round(stop, 4),
            "setup_score": round(score, 1), "rsi": rsi,
            "consol_dias": consol_dias, "vcp": vcp_ok}


# ─────────────────────────────────────────────────────────────
# SEÑAL PULLBACK — alineada con pullback.py
# ─────────────────────────────────────────────────────────────

def _señal_pullback(precios, volumenes, highs, lows):
    """
    Obligatorios: Tendencia macro (precio>MM200×0.95 + MM50>MM200)
                  · Retroceso 5-15% desde máx 60d
    Score (máx 10): RSI(1.5) + Soporte(2.0) + Estructura(5.0) + bonus(0.5)
    Umbral: ≥5.5
    Stop: mín(5 velas, 30d) × 0.98
    """
    n = len(precios)
    if n < 60:
        return None

    precio = precios[-1]
    mm20   = sum(precios[-20:]) / 20
    mm50   = sum(precios[-50:]) / 50 if n >= 50 else None
    mm200  = sum(precios[-200:]) / 200 if n >= 200 else None
    mm20_ant = sum(precios[-25:-5]) / 20
    pendiente = mm20 - mm20_ant

    # OBLIGATORIO 1: Tendencia macro (alineado con pullback.py)
    if mm200 is not None:
        precio_ok = precio > mm200 * 0.95
        mm50_ok   = mm50 > mm200 if mm50 else False
        if not (precio_ok and mm50_ok):
            return None
    elif mm50:
        if precio < mm50 * 0.95:
            return None
    else:
        return None

    # OBLIGATORIO 2: Retroceso 5-15% desde máx 60d (alineado con pullback.py)
    max60     = max(precios[-60:])
    retroceso = (max60 - precio) / max60 * 100
    if not (5.0 <= retroceso <= 15.0):
        return None

    # RSI — zona pullback sano 38-57
    rsi    = _rsi(precios)
    rsi_ok = rsi is not None and 38 <= rsi <= 57

    # Bonus RSI rebotando (últimas 3 lecturas)
    bonus_rsi = 0.0
    if rsi_ok and n >= 18:
        r1 = _rsi(precios[:-3])
        r2 = _rsi(precios[:-2])
        r3 = _rsi(precios[:-1])
        if r1 and r2 and r3 and r3 > r2 > r1:
            bonus_rsi = 0.5

    # Soporte cercano 2-8% (mínimo 30d) — alineado con pullback.py
    min30    = min(lows[-30:]) if lows and len(lows) >= 30 else min(precios[-30:])
    dist_sop = (precio - min30) / precio * 100
    sop_ok   = 2.0 <= dist_sop <= 8.0

    # Estructura: precio>MM50 + MM20 pendiente positiva
    est_ok = (mm50 is not None and precio > mm50 and pendiente > 0)

    # Score (alineado con pullback.py actualizado)
    score = 0.0
    if rsi_ok:  score += 1.5
    if sop_ok:  score += 2.0
    if est_ok:  score += 5.0
    score += bonus_rsi

    if score < 5.5:
        return None

    # Stop: mín(5 velas, 30d) × 0.98 (alineado con pullback.py)
    min5  = min(lows[-5:]) if lows and len(lows) >= 5 else min(precios[-5:])
    stop  = round(min(min5, min30) * 0.98, 4)
    atr_v = _atr(precios, highs if highs else precios, lows if lows else precios)

    if stop <= 0 or stop >= precio:
        if atr_v:
            stop = round(precio - atr_v * 2, 4)
        else:
            return None

    # Validación ATR: stop no puede estar a más de 3×ATR (alineado con pullback.py)
    if atr_v and (precio - stop) > 3.0 * atr_v:
        return None

    riesgo_pct = (precio - stop) / precio * 100
    if not (0.5 <= riesgo_pct <= 10.0):
        return None

    return {"decision": "COMPRA", "tipo": "PULLBACK",
            "entrada": round(precio, 4), "stop": round(stop, 4),
            "setup_score": round(score, 1), "rsi": rsi,
            "retroceso": round(retroceso, 1)}


# ─────────────────────────────────────────────────────────────
# MÉTRICAS
# ─────────────────────────────────────────────────────────────

def _calcular_metricas(trades, equity_curve=None, capital_inicial=None, capital_final=None):
    """Métricas en R puro — sin capital, sin euros."""
    if not trades:
        return {"total_trades": 0, "win_rate_pct": 0, "profit_factor": 0,
                "expectancy_R": 0, "max_drawdown_R": 0,
                "avg_win_R": 0, "avg_loss_R": 0,
                "payoff_ratio": 0, "r_promedio": 0,
                "r_acumulado": 0, "r_maximo": 0, "r_minimo": 0}
    Rs     = [t.get("R_alcanzado", 0) for t in trades]
    g_R    = [r for r in Rs if r > 0]
    p_R    = [r for r in Rs if r < 0]
    total  = len(trades)
    pf     = sum(g_R) / abs(sum(p_R)) if p_R else (99 if g_R else 0)
    avg_wR = sum(g_R)/len(g_R) if g_R else 0
    avg_lR = abs(sum(p_R)/len(p_R)) if p_R else 0

    # Max Drawdown en R (equity curve en R)
    max_dd_R = 0.0
    peak_R   = 0.0
    acum_R   = 0.0
    for r in Rs:
        acum_R += r
        if acum_R > peak_R: peak_R = acum_R
        dd = peak_R - acum_R
        if dd > max_dd_R: max_dd_R = dd

    return {
        "total_trades":   total,
        "win_rate_pct":   round(len(g_R)/total*100, 1),
        "profit_factor":  round(pf, 2),
        "expectancy_R":   round(sum(Rs)/total, 2),
        "max_drawdown_R": round(max_dd_R, 2),
        "avg_win_R":      round(avg_wR, 2),
        "avg_loss_R":     round(avg_lR, 2),
        "payoff_ratio":   round(avg_wR/avg_lR, 2) if avg_lR > 0 else 0,
        "r_promedio":     round(sum(Rs)/total, 2),
        "r_acumulado":    round(sum(Rs), 2),
        "r_maximo":       round(max(Rs), 2),
        "r_minimo":       round(min(Rs), 2),
    }


# ─────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

def ejecutar_backtest_f1(precios, volumenes, fechas,
                         capital_inicial=None,   # ignorado — backtest en R puro
                         riesgo_pct_trade=None,  # ignorado — backtest en R puro
                         highs=None, lows=None,
                         filtro_ibex=None,
                         estrategia="breakout"):
    """
    Backtest en R puro — sin capital, sin euros, sin acciones.
    Mide exclusivamente la calidad estadística del sistema:
    Win Rate, Profit Factor, Expectancy R, Max Drawdown R.
    estrategia: "breakout" | "pullback" | "ambos"
    """
    if not precios or len(precios) < 60:
        return {"trades": [], "equity_curve_R": [], "estrategia": estrategia,
                "metricas": _calcular_metricas([])}

    # Alinear
    n = min(len(precios), len(volumenes), len(fechas))
    if highs and len(highs) < n: highs = None
    if lows  and len(lows)  < n: lows  = None

    datos = sorted(zip(fechas[:n], precios[:n], volumenes[:n],
                       (highs[:n] if highs else [None]*n),
                       (lows[:n]  if lows  else [None]*n)),
                   key=lambda x: x[0])
    fs = [d[0] for d in datos]
    ps = [d[1] for d in datos]
    vs = [d[2] for d in datos]
    hs = [d[3] for d in datos]
    ls = [d[4] for d in datos]

    def _h(i): return hs[i] if hs[i] is not None else ps[i]
    def _l(i): return ls[i] if ls[i] is not None else ps[i]

    # ── R acumulado — equity curve en R puro
    r_acum      = 0.0
    equity_R    = []   # [{fecha, r_acum, en_posicion}]
    trades      = []
    en_pos      = False
    pos         = None

    for i in range(60, len(ps)):
        precio_hoy = ps[i]
        fecha_hoy  = fs[i]
        high_hoy   = _h(i)
        low_hoy    = _l(i)

        # ── Gestión posición abierta ──────────────────────
        if en_pos and pos:
            pos["max_precio"] = max(pos["max_precio"], high_hoy)
            R_unit   = pos["entrada"] - pos["stop_inicial"]
            R_actual = (high_hoy - pos["entrada"]) / R_unit if R_unit > 0 else 0
            atr_pos  = pos.get("atr", 0)

            # Break-even en +1R
            if R_actual >= 1.0 and pos["stop_actual"] < pos["entrada"]:
                pos["stop_actual"] = pos["entrada"]
                pos["gestion"]     = "BE (+1R)"

            # Salida parcial 50% en +2R
            tgt_parcial = pos["entrada"] + 2.0 * R_unit if R_unit > 0 else None
            if tgt_parcial and not pos.get("parcial") and high_hoy >= tgt_parcial:
                pos["parcial"]  = True
                pos["gestion"]  = "PARCIAL 50%@2R"
                r_acum += 1.0   # +1R por la mitad cerrada a +2R
                if pos["stop_actual"] < pos["entrada"]:
                    pos["stop_actual"] = pos["entrada"]
                trades.append({
                    "fecha_entrada": str(pos["fecha_entrada"])[:10],
                    "fecha_salida":  str(fecha_hoy)[:10],
                    "entrada":       round(pos["entrada"], 2),
                    "salida":        round(tgt_parcial, 2),
                    "R_alcanzado":   1.0,   # 50% de posición × 2R = 1R total
                    "gestion":       "PARCIAL +2R",
                    "setup_score":   pos["setup_score"],
                    "tipo":          pos.get("tipo", ""),
                })

            # Trailing ATR tras parcial
            if pos.get("parcial") and atr_pos:
                trailing = pos["max_precio"] - 1.5 * atr_pos
                if trailing > pos["stop_actual"]:
                    pos["stop_actual"] = trailing
                    pos["gestion"]     = "TRAILING ATR"

            # Target +3R o STOP — sobre el 50% restante
            tgt_final = pos["entrada"] + 3.0 * R_unit if R_unit > 0 else None
            salida = motivo = None
            if tgt_final and high_hoy >= tgt_final:
                salida = tgt_final
                motivo = "TARGET +3R"
            elif low_hoy <= pos["stop_actual"]:
                salida = pos["stop_actual"]
                motivo = "STOP" if not pos.get("parcial") else "STOP (trailing)"

            if salida is not None:
                R_c = (salida - pos["entrada"]) / R_unit if R_unit > 0 else 0
                # Si hubo parcial, este R_c es del 50% restante → peso 0.5
                R_efectivo = R_c * 0.5 if pos.get("parcial") else R_c
                r_acum += R_efectivo
                trades.append({
                    "fecha_entrada": str(pos["fecha_entrada"])[:10],
                    "fecha_salida":  str(fecha_hoy)[:10],
                    "entrada":       round(pos["entrada"], 2),
                    "salida":        round(salida, 2),
                    "R_alcanzado":   round(R_efectivo, 2),
                    "gestion":       motivo,
                    "setup_score":   pos["setup_score"],
                    "tipo":          pos.get("tipo", ""),
                })
                en_pos = False
                pos    = None

        # ── Buscar entrada ───────────────────────────────
        if not en_pos:
            estado_mkt = _estado_mercado(fecha_hoy, filtro_ibex) if filtro_ibex else "ALCISTA"
            if estado_mkt == "BAJISTA":
                equity_R.append({"fecha": str(fecha_hoy)[:10],
                                  "r_acum": round(r_acum,2), "en_posicion": False})
                continue

            p_s = ps[:i+1]
            v_s = vs[:i+1]
            h_s = [_h(j) for j in range(i+1)]
            l_s = [_l(j) for j in range(i+1)]

            señal = None
            if estrategia in ("breakout", "ambos"):
                señal = _señal_breakout(p_s, v_s, h_s, l_s)
            if señal is None and estrategia in ("pullback", "ambos"):
                señal = _señal_pullback(p_s, v_s, h_s, l_s)

            if señal is None:
                equity_R.append({"fecha": str(fecha_hoy)[:10],
                                  "r_acum": round(r_acum,2), "en_posicion": False})
                continue

            if estado_mkt == "TRANSICION" and señal.get("setup_score",0) < 7.0:
                equity_R.append({"fecha": str(fecha_hoy)[:10],
                                  "r_acum": round(r_acum,2), "en_posicion": False})
                continue

            entrada     = float(señal["entrada"])
            stop        = float(señal["stop"])
            setup_score = float(señal.get("setup_score", 5.0))
            tipo_s      = señal.get("tipo", estrategia.upper())

            riesgo_pct = (entrada - stop) / entrada * 100
            if not (0.5 <= riesgo_pct <= 10.0):
                equity_R.append({"fecha": str(fecha_hoy)[:10],
                                  "r_acum": round(r_acum,2), "en_posicion": False})
                continue

            atr_v = _atr(p_s, h_s, l_s) or 0
            en_pos = True
            pos = {
                "fecha_entrada": fecha_hoy,
                "entrada":       entrada,
                "stop_inicial":  stop,
                "stop_actual":   stop,
                "max_precio":    entrada,
                "setup_score":   setup_score,
                "gestion":       "Inicial",
                "atr":           atr_v,
                "tipo":          tipo_s,
            }

        equity_R.append({"fecha": str(fecha_hoy)[:10],
                          "r_acum": round(r_acum,2), "en_posicion": en_pos})

    # Cierre final
    if en_pos and pos:
        precio_f = ps[-1]
        R_unit   = pos["entrada"] - pos["stop_inicial"]
        R_f      = (precio_f - pos["entrada"]) / R_unit if R_unit > 0 else 0
        R_ef     = R_f * 0.5 if pos.get("parcial") else R_f
        r_acum  += R_ef
        trades.append({
            "fecha_entrada": str(pos["fecha_entrada"])[:10],
            "fecha_salida":  str(fs[-1])[:10],
            "entrada":       round(pos["entrada"], 2),
            "salida":        round(precio_f, 2),
            "R_alcanzado":   round(R_ef, 2),
            "gestion":       "Cierre final",
            "setup_score":   pos["setup_score"],
            "tipo":          pos.get("tipo",""),
        })

    metricas = _calcular_metricas(trades)
    logger.info(f"✅ Backtest F1 ({estrategia}): {len(trades)} trades, exp={metricas['expectancy_R']}R")
    return {"trades": trades, "equity_curve_R": equity_R,
            "r_acumulado": round(r_acum, 2),
            "metricas": metricas, "estrategia": estrategia}


# ─────────────────────────────────────────────────────────────
# BACKTEST MULTI-TICKER
# ─────────────────────────────────────────────────────────────

def ejecutar_backtest_f1_sistema(tickers, cache=None, capital_inicial=10_000,
                                  riesgo_pct_trade=0.01, periodo="5y",
                                  estrategia="breakout"):
    from core.data_provider import get_df
    from core.universos import get_nombre

    print(">>> Cargando filtro IBEX MM200...")
    filtro_ibex = _cargar_ibex_mm200(periodo=periodo)
    if filtro_ibex:
        ult = max(filtro_ibex.keys())
        d   = filtro_ibex[ult]
        alcista = d["mm200"] and d["close"] >= d["mm200"]
        print(f">>> Filtro IBEX OK: {len(filtro_ibex)} barras — hoy {'ALCISTA' if alcista else 'BAJISTA/TRANS'}")
    else:
        print(">>> ADVERTENCIA: Filtro IBEX vacío")

    tickers_operados  = []
    tickers_excluidos = []
    todos_trades      = []
    MIN_VOL           = 9.0

    for ticker in tickers:
        try:
            df = get_df(ticker, periodo=periodo, cache=cache, min_velas=60)
            if df is None or df.empty or len(df) < 60:
                tickers_excluidos.append({"nombre": ticker.replace(".MC",""),
                                          "empresa": get_nombre(ticker), "vol": "sin datos"})
                continue

            precios   = df["Close"].tolist()
            volumenes = df["Volume"].tolist()
            fechas    = list(df.index)
            highs     = df["High"].tolist() if "High" in df.columns else None
            lows      = df["Low"].tolist()  if "Low"  in df.columns else None

            ventana = min(252, len(precios))
            import statistics
            media = sum(precios[-ventana:]) / ventana
            std   = statistics.stdev(precios[-ventana:]) if ventana > 1 else 0
            vol   = (std / media * 100) if media > 0 else 0

            if vol < MIN_VOL:
                tickers_excluidos.append({"nombre": ticker.replace(".MC",""),
                                          "empresa": get_nombre(ticker), "vol": f"{vol:.1f}"})
                continue

            resultado = ejecutar_backtest_f1(
                precios, volumenes, fechas,
                capital_inicial=capital_inicial,
                riesgo_pct_trade=riesgo_pct_trade,
                highs=highs, lows=lows,
                filtro_ibex=filtro_ibex,
                estrategia=estrategia,
            )

            trades_t = resultado.get("trades", [])
            if not trades_t:
                tickers_excluidos.append({"nombre": ticker.replace(".MC",""),
                                          "empresa": get_nombre(ticker),
                                          "vol": f"{vol:.1f} (0 trades)"})
                continue

            todos_trades.extend(trades_t)
            r_acum_ticker = resultado.get("r_acumulado", 0)
            tickers_operados.append({"ticker": ticker, "r_acum": round(r_acum_ticker,2),
                                     "trades": len(trades_t), "vol": round(vol,1)})

        except Exception as e:
            logger.warning(f"Error en {ticker}: {e}")
            tickers_excluidos.append({"nombre": ticker.replace(".MC",""),
                                      "empresa": get_nombre(ticker), "vol": str(e)[:30]})

    if not todos_trades:
        return {"estado": {"color":"danger","texto":"SIN TRADES"},
                "metricas": {"expectancy":0,"winrate":0,"max_dd":0,
                             "total_trades":0,"tickers_activos":0},
                "tickers": {"aprobados":[],"neutros":[],"rechazados":[],
                            "excluidos": tickers_excluidos},
                "recomendacion": {"titulo":"Sin datos","acciones":[]},
                "config": {"target":"3","breakeven":"1","riesgo":"1.0","filtro_vol":">9"},
                "periodo":"5 años","universo":f"IBEX 35 (0 tickers)"}

    Rs      = [t.get("R_alcanzado",0) for t in todos_trades]
    g_R     = [r for r in Rs if r > 0]
    p_R     = [r for r in Rs if r < 0]
    total   = len(todos_trades)
    winrate = len(g_R)/total*100
    pf      = sum(g_R)/abs(sum(p_R)) if p_R else (99 if g_R else 0)
    exp_R   = sum(Rs)/total

    aprobados, neutros, rechazados = [], [], []
    for t in tickers_operados:
        entry = {"nombre": t["ticker"].replace(".MC",""),
                 "empresa": get_nombre(t["ticker"]),
                 "r_acum": t["r_acum"], "trades": t["trades"]}
        if t["r_acum"] >= 1.0:    aprobados.append(entry)
        elif t["r_acum"] >= -1.0: neutros.append(entry)
        else:                      rechazados.append(entry)

    aprobados.sort(key=lambda x: x["r_acum"], reverse=True)
    rechazados.sort(key=lambda x: x["r_acum"])

    if exp_R >= 0.40:   estado = {"color":"success","texto":"EXCELENTE"}
    elif exp_R >= 0.20: estado = {"color":"success","texto":"RENTABLE"}
    elif exp_R > 0:     estado = {"color":"warning","texto":"MARGINAL"}
    else:               estado = {"color":"danger", "texto":"NO RENTABLE"}

    if exp_R >= 0.20 and len(aprobados) >= 5:
        rec = {"titulo":"Sistema listo para operar",
               "acciones":[f"Operar SOLO los {len(aprobados)} tickers aprobados"]}
    elif exp_R >= 0.20:
        rec = {"titulo":"Pocos tickers aprobados",
               "acciones":["Considerar reducir filtro de volatilidad"]}
    else:
        rec = {"titulo":"Sistema requiere optimización",
               "acciones":["NO operar hasta expectancy > 0.20R"]}

    return {
        "estado":   estado,
        "metricas": {"expectancy": round(exp_R,2), "winrate": round(winrate,1),
                     "max_dd": 0, "total_trades": total,
                     "tickers_activos": len(tickers_operados)},
        "tickers":  {"aprobados": aprobados, "neutros": neutros,
                     "rechazados": rechazados, "excluidos": tickers_excluidos},
        "recomendacion": rec,
        "config": {"target":"3","breakeven":"1",
                   "riesgo": f"{riesgo_pct_trade*100:.1f}","filtro_vol":">9"},
        "periodo":  "5 años",
        "universo": f"IBEX 35 ({len(tickers_operados)} tickers)",
        "estrategia": estrategia,
    }
