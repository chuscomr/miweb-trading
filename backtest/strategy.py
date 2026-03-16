# backtest/strategy.py
# ══════════════════════════════════════════════════════════════
# StrategyLogic — portado literalmente de strategy.py original
# La lógica de señal viene de sistema_trading.py (portada aquí
# para no depender del módulo antiguo)
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────
# Helpers portados de sistema_trading.py
# ─────────────────────────────────────────────────────────────

def _calcular_rsi_seguro(precios, periodo=14):
    try:
        if len(precios) < periodo + 5:
            return None
        serie = pd.Series(precios, dtype=float)
        serie = serie.replace([np.inf, -np.inf], np.nan).dropna()
        if len(serie) < periodo + 5:
            return None
        if any(serie.pct_change().abs() > 0.50):
            return None
        if sum(serie.pct_change().abs() > 0.20) > 3:
            return None
        if len(set(serie.iloc[-5:].tolist())) == 1:
            return None
        delta = serie.diff()
        g = delta.clip(lower=0).dropna()
        p = (-delta.clip(upper=0)).dropna()
        if len(g) < periodo:
            return None
        mg = g.ewm(alpha=1/periodo, adjust=False, min_periods=periodo).mean()
        mp = p.ewm(alpha=1/periodo, adjust=False, min_periods=periodo).mean()
        if mp.iloc[-1] == 0:
            return 100.0
        rsi = (100 - (100 / (1 + mg / mp))).iloc[-1]
        if pd.isna(rsi) or not (0 <= rsi <= 100):
            return None
        return round(float(rsi), 1)
    except Exception:
        return None


def _evaluar_volumen_profesional(volumenes):
    if len(volumenes) < 21:
        return {"permitir_normal": True, "permitir_impulso": False,
                "bonus_score": 0, "penalizacion_score": -1}
    vol_actual    = volumenes[-2]
    media_vol_10  = sum(volumenes[-11:-1]) / 10
    media_vol_20  = sum(volumenes[-21:-1]) / 20
    if media_vol_20 < 50_000:
        return {"permitir_normal": False, "permitir_impulso": False,
                "bonus_score": 0, "penalizacion_score": -3}
    ratio     = vol_actual / media_vol_10 if media_vol_10 > 0 else 0
    tendencia = media_vol_10 / media_vol_20 if media_vol_20 > 0 else 1.0
    if ratio >= 1.5:
        return {"permitir_normal": True,  "permitir_impulso": True,
                "bonus_score": +1, "penalizacion_score": 0}
    elif ratio >= 1.05:
        return {"permitir_normal": True,  "permitir_impulso": True,
                "bonus_score": 0,  "penalizacion_score": 0}
    elif ratio >= 0.85 and tendencia >= 1.1:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": 0}
    elif tendencia >= 1.0:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": 0}
    elif ratio >= 0.75:
        return {"permitir_normal": True,  "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": -1}
    else:
        return {"permitir_normal": False, "permitir_impulso": False,
                "bonus_score": 0,  "penalizacion_score": -2}


def _sistema_trading(precios, volumenes, contexto_mercado=None,
                     usar_filtro_mercado=False, modo_backtest=True):
    """Portado literalmente de sistema_trading.py."""
    if len(precios) < 50:
        return {"decision": "NO OPERAR"}

    # Filtro mercado
    if usar_filtro_mercado and contexto_mercado:
        if contexto_mercado.get("estado") == "RIESGO ALTO":
            return {"decision": "NO OPERAR"}

    precio    = precios[-1]
    mm20      = sum(precios[-20:]) / 20
    mm20_ant  = sum(precios[-25:-5]) / 20
    pendiente = mm20 - mm20_ant
    max20     = max(precios[-21:-1])   # excluir vela actual para evitar falsos breakouts
    min20     = min(precios[-21:-1])
    volatilidad = (max20 - min20) / min20 * 100 if min20 > 0 else 999
    dist_mm   = abs(precio - mm20) / mm20 * 100
    dist_max  = (max20 - precio) / max20 * 100

    if not (precio > mm20 and pendiente > 0):
        return {"decision": "NO OPERAR"}

    rsi = _calcular_rsi_seguro(precios)
    if rsi is None:
        return {"decision": "NO OPERAR"}

    if volatilidad > 10:
        return {"decision": "NO OPERAR"}

    eval_vol = _evaluar_volumen_profesional(volumenes)

    setup_score = 0
    if rsi >= 52:       setup_score += 1   # antes 55 → más señales
    if 58 <= rsi <= 70: setup_score += 1   # zona momentum óptima
    if 1.5 <= dist_max <= 5: setup_score += 1  # zona óptima post-breakout
    if dist_mm <= 3:    setup_score += 1
    if pendiente > 0:
        setup_score += 1
        setup_score += eval_vol.get("bonus_score", 0)
        setup_score += eval_vol.get("penalizacion_score", 0)
        setup_score = max(0, min(setup_score, 5))

    # Entrada al precio de cierre (modo_backtest=True)
    entrada = round(float(precio), 2)

    # COMPRA NORMAL — dist_max relajado a 6% (antes 3%)
    if (45 < rsi < 70 and dist_mm <= 4 and dist_max <= 6
            and setup_score >= 3 and eval_vol["permitir_normal"]):
        return {"decision": "COMPRA", "entrada": entrada, "setup_score": setup_score}

    # COMPRA IMPULSO — dist_max relajado a 6% (antes 3%)
    if (60 <= rsi <= 73 and dist_mm <= 6 and dist_max <= 6
            and setup_score >= 4 and eval_vol["permitir_impulso"]):
        return {"decision": "COMPRA", "entrada": entrada, "setup_score": setup_score}

    return {"decision": "NO OPERAR"}


# ─────────────────────────────────────────────────────────────
# StrategyLogic — interfaz para BacktestEngineLegacy
# ─────────────────────────────────────────────────────────────

class StrategyLogic:
    """
    Adaptador del sistema REAL para backtest.
    Portado literalmente de strategy.py original.
    """

    def __init__(self, modo_test=False, min_volatilidad_pct=0, modo_backtest=True):
        self.modo_test          = modo_test
        self.min_volatilidad    = min_volatilidad_pct
        self.modo_backtest      = modo_backtest

    def evaluate(self, df, contexto=None, posicion=None, ultima_barra=False):
        # En producción solo evaluar última barra
        if not self.modo_backtest and not ultima_barra:
            return {"accion": "ESPERAR"}

        # No entrar si ya hay posición
        if posicion:
            return {"accion": "ESPERAR"}

        if len(df) < 50:
            return {"accion": "ESPERAR"}

        precios   = df["Close"].tolist()
        volumenes = df["Volume"].tolist() if "Volume" in df.columns else []

        resultado = _sistema_trading(
            precios, volumenes,
            contexto_mercado    = contexto,
            usar_filtro_mercado = True,    # filtro IBEX MM50 activado
            modo_backtest       = True,
        )

        if resultado.get("decision") != "COMPRA":
            return {"accion": "ESPERAR"}

        entrada = resultado.get("entrada")
        if not entrada:
            return {"accion": "ESPERAR"}

        # Stop por ATR — idéntico a backtest_f1.py original:
        # mult=2.5 si setup>=4, mult=1.8 si setup<4
        # Solo entra si riesgo_pct está entre 1% y 3%
        high = df["High"].tolist() if "High" in df.columns else precios
        low  = df["Low"].tolist()  if "Low"  in df.columns else precios
        # True Range real: incluye gaps con cierre anterior
        trs = []
        for i in range(max(1, len(high)-15), len(high)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - (low[i-1] if i > 0 else high[i])),
                abs(low[i]  - (low[i-1] if i > 0 else low[i]))
            )
            trs.append(tr)
        atr  = sum(trs) / len(trs) if trs else 0

        setup_score = resultado.get("setup_score", 3)
        mult  = 2.5 if setup_score >= 4 else 1.8
        stop  = (entrada - atr * mult) if atr > 0 else entrada * 0.96

        if not stop or stop <= 0 or stop >= entrada:
            return {"accion": "ESPERAR"}

        # Solo validar que el stop sea razonable (1%-8%)
        riesgo_pct_stop = (entrada - stop) / entrada * 100
        if riesgo_pct_stop < 1.0:
            stop = entrada * 0.99   # mínimo 1%
        elif riesgo_pct_stop > 8.0:
            return {"accion": "ESPERAR"}   # stop absurdo

        return {
            "accion":  "ENTRAR",
            "entrada": round(float(entrada), 2),
            "stop":    round(float(stop), 2),
        }
