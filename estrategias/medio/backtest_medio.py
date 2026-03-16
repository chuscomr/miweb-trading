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
    """Evalúa si hay señal de compra en la barra actual."""
    precios = df_hasta_ahora["Close"].tolist()

    # 1. Tendencia alcista
    tendencia = detectar_tendencia_semanal(precios)
    if tendencia.get("tendencia") != "ALCISTA":
        return {"decision": "NO_OPERAR"}

    # 2. Volatilidad mínima
    vol = calcular_volatilidad(precios)
    if vol is not None and vol < VOL_MIN_PCT:
        return {"decision": "NO_OPERAR"}

    # 3. Pullback válido
    pullback = detectar_pullback(precios)
    if not pullback.get("es_pullback"):
        return {"decision": "NO_OPERAR"}

    # 4. Giro semanal (precio > cierre semana anterior)
    if REQUIERE_GIRO_SEMANAL:
        giro = detectar_giro_semanal(precios)
        if not giro.get("hay_giro"):
            return {"decision": "NO_OPERAR"}

    # 5. Stop y riesgo con parámetros adaptativos
    params        = calcular_parametros_adaptativos(vol)
    stop_atr_mult = params["stop_atr_mult"]
    riesgo_max    = params["riesgo_max"]

    entrada = precios[-1]
    stop    = calcular_stop_inicial(entrada, precios, df=df_hasta_ahora, stop_atr_mult=stop_atr_mult)
    if stop is None or stop >= entrada:
        return {"decision": "NO_OPERAR"}

    v = validar_riesgo(entrada, stop)
    riesgo_pct = v.get("riesgo_pct", 0)
    if riesgo_pct < 1.5 or riesgo_pct > riesgo_max:
        return {"decision": "NO_OPERAR"}

    return {"decision": "COMPRA", "entrada": entrada, "stop": stop}


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
    Gestión: INICIAL → PROTEGIDO → TRAILING STOP (sin target fijo).
    """
    if df_semanal is None or df_semanal.empty or len(df_semanal) < MIN_SEMANAS_HISTORICO:
        return {"trades": [], "equity": [0.0], "metricas": _calcular_metricas([], [])}

    trades       = []
    equity_curve = [0.0]
    posicion     = None

    for i in range(MIN_SEMANAS_HISTORICO, len(df_semanal)):
        df_v   = df_semanal.iloc[:i + 1]
        precio = float(df_v["Close"].iloc[-1])
        high   = float(df_v["High"].iloc[-1])
        low    = float(df_v["Low"].iloc[-1])
        fecha  = df_v.index[-1]

        # Gestión posición abierta
        if posicion is not None:
            resultado = posicion.actualizar(precio, high=high, low=low)
            posicion.aplicar_actualizacion(resultado)

            if resultado["salir"]:
                R_final = posicion.calcular_R_actual(precio)
                trades.append({
                    "fecha_entrada": posicion.fecha_entrada,
                    "fecha_salida":  fecha,
                    "entrada":       posicion.entrada,
                    "stop_inicial":  posicion.stop_inicial,
                    "salida":        precio,
                    "R":             round(R_final, 2),
                    "motivo":        resultado["motivo"],
                    "semanas":       posicion.semanas_en_posicion,
                })
                equity_curve.append(equity_curve[-1] + R_final)
                if verbose:
                    print(f"  SALIDA {fecha.date()}: {R_final:+.2f}R ({resultado['motivo']})")
                posicion = None

        # Buscar nueva entrada
        if posicion is None:
            señal = _evaluar_entrada(df_v)
            if señal.get("decision") == "COMPRA":
                posicion = PosicionMedioPlazo(señal["entrada"], señal["stop"], fecha)
                if verbose:
                    print(f"  ENTRADA {fecha.date()}: {señal['entrada']:.2f}€  Stop: {señal['stop']:.2f}€")

    # Cerrar posición abierta al final
    if posicion is not None:
        precio_f = float(df_semanal["Close"].iloc[-1])
        R_final  = posicion.calcular_R_actual(precio_f)
        trades.append({
            "fecha_entrada": posicion.fecha_entrada,
            "fecha_salida":  df_semanal.index[-1],
            "entrada":       posicion.entrada,
            "stop_inicial":  posicion.stop_inicial,
            "salida":        precio_f,
            "R":             round(R_final, 2),
            "motivo":        "FIN_BACKTEST",
            "semanas":       posicion.semanas_en_posicion,
        })
        equity_curve.append(equity_curve[-1] + R_final)

    return {"trades": trades, "equity": equity_curve, "metricas": _calcular_metricas(trades, equity_curve)}
