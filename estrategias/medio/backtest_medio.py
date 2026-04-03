# estrategias/medio/backtest_medio.py
# Motor de backtest semanal con gestión completa INICIAL → PROTEGIDO → TRAILING

import numpy as np
from estrategias.medio.config_medio import (
    MIN_SEMANAS_HISTORICO, calcular_parametros_adaptativos,
    VOL_MIN_PCT, REQUIERE_GIRO_SEMANAL,
)
from estrategias.medio.gestion_medio import PosicionMedioPlazo
from estrategias.medio.logica_medio import (
    detectar_tendencia_semanal,
    detectar_pullback,
    detectar_giro_semanal,
    calcular_stop_inicial,
    calcular_volatilidad,
    validar_riesgo,
)


# ──────────────────────────────────────────────────────────
# EVALUADOR DE ENTRADA
# ──────────────────────────────────────────────────────────

def _evaluar_entrada(df_hasta_ahora):
    """
    Evalúa si hay señal de compra en la barra actual (semanal).

    Condiciones:
    1. Tendencia macro: MM20↑ + MM50 > MM200
    2. Pullback 5-8% desde máximo 10 semanas
    3. Volatilidad mínima 8%
    4. Stop válido: max(estructura×0.98, entrada - ATR×2)
    5. Riesgo 1.5-8% (semanal)
    6. Trigger: high semana actual × 1.001 (entrada semana siguiente)
    """
    precios = df_hasta_ahora["Close"].tolist()
    highs   = df_hasta_ahora["High"].tolist()
    n       = len(precios)

    if n < 210:  # warmup mínimo para MM200 semanal
        return {"decision": "NO_OPERAR"}

    # 1. Tendencia macro: MM20↑ + MM50 > MM200
    from estrategias.medio.logica_medio import detectar_tendencia_semanal
    tendencia = detectar_tendencia_semanal(precios)
    if tendencia.get("tendencia") != "ALCISTA":
        return {"decision": "NO_OPERAR"}
    if not tendencia.get("mm50_sobre_mm200", False):
        return {"decision": "NO_OPERAR"}

    # 2. Volatilidad mínima
    vol = calcular_volatilidad(precios)
    if vol is not None and vol < VOL_MIN_PCT:
        return {"decision": "NO_OPERAR"}

    # 3. Pullback 5-8% desde máximo 10 semanas
    pullback = detectar_pullback(precios)
    if not pullback.get("es_pullback"):
        return {"decision": "NO_OPERAR"}

    # 4. Stop: max(mínimo estructura×0.98, entrada - ATR×2)
    trigger = round(highs[-1] * 1.001, 4)  # Buy Stop semana siguiente
    stop    = calcular_stop_inicial(trigger, precios, df=df_hasta_ahora)
    if stop is None or stop >= trigger:
        return {"decision": "NO_OPERAR"}

    # 5. Riesgo 1.5-8% (semanal — rangos más amplios que diario)
    riesgo_pct = (trigger - stop) / trigger * 100
    if not (1.5 <= riesgo_pct <= 8.0):
        return {"decision": "NO_OPERAR"}

    return {
        "decision": "COMPRA",
        "entrada":  trigger,   # entra al trigger la semana siguiente
        "stop":     stop,
    }


# ──────────────────────────────────────────────────────────
# MÉTRICAS
# ──────────────────────────────────────────────────────────

def _calcular_metricas(trades, equity_curve):
    if not trades:
        return {k: 0 for k in [
            "total_trades", "expectancy_R", "winrate", "mejor_trade", "peor_trade",
            "avg_winner", "avg_loser", "profit_factor", "max_drawdown_R", "equity_final_R"
        ]}
    Rs      = [t["R"] for t in trades]
    winners = [r for r in Rs if r > 0]
    losers  = [r for r in Rs if r <= 0]
    pf      = sum(winners) / abs(sum(losers)) if losers else 0
    eq      = np.array(equity_curve)
    dd      = float(min(eq - np.maximum.accumulate(eq))) if len(eq) > 1 else 0
    return {
        "total_trades":   len(trades),
        "expectancy_R":   round(sum(Rs) / len(Rs), 2),
        "winrate":        round(len(winners) / len(Rs) * 100, 1),
        "mejor_trade":    round(max(Rs), 2),
        "peor_trade":     round(min(Rs), 2),
        "avg_winner":     round(sum(winners) / len(winners), 2) if winners else 0,
        "avg_loser":      round(sum(losers)  / len(losers),  2) if losers  else 0,
        "profit_factor":  round(pf, 2),
        "max_drawdown_R": round(dd, 2),
        "equity_final_R": round(equity_curve[-1], 2) if equity_curve else 0,
    }


# ──────────────────────────────────────────────────────────
# MOTOR PRINCIPAL
# ──────────────────────────────────────────────────────────

def ejecutar_backtest_medio_plazo(df_semanal, ticker=None, verbose=False):
    """
    Motor de backtest semanal para medio plazo.
    Trigger: high semana N × 1.001 → entra semana N+1 si high >= trigger.
    Gestión: INICIAL → PROTEGIDO (+2R) → TRAILING (+4R).
    """
    if df_semanal is None or df_semanal.empty or len(df_semanal) < MIN_SEMANAS_HISTORICO:
        return {"trades": [], "equity": [0.0], "metricas": _calcular_metricas([], [])}

    trades         = []
    equity_curve   = [0.0]
    posicion       = None
    pending_trigger = None  # {trigger, stop, fecha_señal}

    for i in range(MIN_SEMANAS_HISTORICO, len(df_semanal)):
        df_v   = df_semanal.iloc[:i + 1]
        precio = float(df_v["Close"].iloc[-1])
        high   = float(df_v["High"].iloc[-1])
        low    = float(df_v["Low"].iloc[-1])
        fecha  = df_v.index[-1]

        # ── Gestión posición abierta ──────────────────────────────────────────
        if posicion is not None:
            resultado = posicion.actualizar(precio, high=high, low=low)
            posicion.aplicar_actualizacion(resultado)

            if resultado["salir"]:
                # Precio de salida = stop vigente cuando salta por stop
                # (no el cierre, que puede estar muy por debajo)
                motivo = resultado["motivo"]
                if motivo in ("STOP_INICIAL", "STOP_PROTEGIDO", "TRAILING_STOP"):
                    precio_salida = resultado["stop_nuevo"]  # stop vigente = precio real de salida
                else:
                    precio_salida = precio  # FIN_BACKTEST u otros: usar cierre

                R_final = posicion.calcular_R_actual(precio_salida)
                trades.append({
                    "fecha_entrada": posicion.fecha_entrada,
                    "fecha_salida":  fecha,
                    "entrada":       posicion.entrada,
                    "stop_inicial":  posicion.stop_inicial,
                    "salida":        round(precio_salida, 4),
                    "R":             round(R_final, 2),
                    "motivo":        motivo,
                    "fase":          posicion.estado,
                    "semanas":       posicion.semanas_en_posicion,
                })
                equity_curve.append(equity_curve[-1] + R_final)
                if verbose:
                    print(f"  SALIDA {fecha.date()}: {R_final:+.2f}R ({motivo}) @ {precio_salida:.2f}€")
                posicion = None
            continue  # no buscar nueva entrada mientras hay posición

        # ── Comprobar trigger pendiente ───────────────────────────────────────
        if pending_trigger is not None:
            trig = pending_trigger["trigger"]
            stop = pending_trigger["stop"]
            if high >= trig:
                # Trigger activado — entra al precio del trigger
                posicion = PosicionMedioPlazo(trig, stop, fecha)
                if verbose:
                    print(f"  ENTRADA {fecha.date()}: trigger={trig:.2f}€  Stop={stop:.2f}€")
            pending_trigger = None
            continue  # trigger consumido (activado o expirado)

        # ── Buscar nueva señal ────────────────────────────────────────────────
        señal = _evaluar_entrada(df_v)
        if señal.get("decision") == "COMPRA":
            pending_trigger = {
                "trigger":     señal["entrada"],
                "stop":        señal["stop"],
                "fecha_señal": fecha,
            }
            if verbose:
                print(f"  SEÑAL {fecha.date()}: trigger={señal['entrada']:.2f}€ — espera confirmación")

    # ── Cerrar posición abierta al final ──────────────────────────────────────
    if posicion is not None:
        precio_f  = float(df_semanal["Close"].iloc[-1])
        R_final   = posicion.calcular_R_actual(precio_f)
        trades.append({
            "fecha_entrada": posicion.fecha_entrada,
            "fecha_salida":  df_semanal.index[-1],
            "entrada":       posicion.entrada,
            "stop_inicial":  posicion.stop_inicial,
            "salida":        round(precio_f, 4),
            "R":             round(R_final, 2),
            "motivo":        "FIN_BACKTEST",
            "fase":          posicion.estado,
            "semanas":       posicion.semanas_en_posicion,
        })
        equity_curve.append(equity_curve[-1] + R_final)

    return {"trades": trades, "equity": equity_curve, "metricas": _calcular_metricas(trades, equity_curve)}
