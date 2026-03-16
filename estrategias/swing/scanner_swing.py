"""
ESCÁNER SWING TRADING (versión clásica para carpeta swing_trading)
Compatible con tu sistema original sin modificar nada más.
"""

import sys
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------------------------------------------------
# AÑADIR RUTA RAÍZ DEL PROYECTO (MiWeb)
# ------------------------------------------------------------
# Imports de nueva arquitectura
from estrategias.swing.logica_breakout import detectar_breakout_swing
from estrategias.swing.logica_pullback import detectar_pullback_swing


# =============================
# LISTAS DE TICKERS
# =============================

IBEX35_TICKERS = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","ANE.MC",
    "ENG.MC","FCC.MC","PUIG.MC","MTS.MC"
]

CONTINUO_LIQUIDO = [
    "CIE.MC","VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC",
    "PHM.MC","OHLA.MC","DOM.MC","ENC.MC","GRE.MC",
    "HOME.MC","CIRSA.MC","FAE.MC","NEA.MC","PSG.MC","LDA.MC",
    "MEL.MC","VIS.MC","ECR.MC","ENO.MC","DIA.MC","IMC.MC","LIB.MC",
    "A3M.MC","ATRY.MC","R4.MC","RLIA.MC","MVC.MC","EBROM.MC","AMP.MC",
    "HBX.MC","CASH.MC","ADX.MC","IZER.MC","AEDAS.MC"
]


# =============================
# ESCANEO INDIVIDUAL
# =============================

def escanear_ticker(ticker, tipo_scan='breakout'):
    """
    Escanea un ticker buscando señal del tipo especificado.
    tipo_scan: 'breakout' | 'pullback'  (nunca ambos)
    """
    if tipo_scan == 'pullback':
        r = detectar_pullback_swing(ticker)
    else:
        r = detectar_breakout_swing(ticker)

    if not isinstance(r, dict):
        return None

    if not r.get("valido", False):
        return None

    return formatear_resultado(r)

# =============================
# ESCANEO MASIVO
# =============================

import copy

def escanear_mercado(tickers, tipo_scan='breakout', max_workers=2):

    resultados = []
    vistos = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(escanear_ticker, t, tipo_scan): t for t in tickers}

        for future in as_completed(futures):
            r = future.result()

            # ⭐ SOLO señales válidas
            if isinstance(r, dict) and r.get("es_senal", False):

                # ⭐ evitar duplicados reales
                if r["ticker"] not in vistos:
                    vistos.add(r["ticker"])
                    resultados.append(r)

    resultados.sort(key=lambda x: (x["tipo"], x["score"]), reverse=True)

    return resultados

# =============================
# FORMATEO RESULTADOS
# =============================
def to_float_safe(x):
    if hasattr(x, "item"):
        return float(x.item())
    return float(x)

def formatear_resultado(r):

    ticker = r.get("ticker","")

    # ⭐ score real
    score = float(r.get("setup_score", 0))

    # ⭐ confianza estilo TradingView
    if score >= 8:
        confianza = "muy_alto"
    elif score >= 6:
        confianza = "alto"
    elif score >= 4:
        confianza = "medio"
    else:
        confianza = "medio_bajo"

    tipo = r.get("tipo", "BREAKOUT")
    return {
        "ticker": ticker.replace(".MC",""),
        "ticker_completo": ticker,

        # campos frontend
        "precio": float(r.get("precio_actual", 0)),
        "precio_actual": float(r.get("precio_actual", 0)),
        "score": score,
        "setup_score": score,
        "confianza": confianza,
        "variacion_1d": float(r.get("variacion_1d", 0)),
        "es_senal": True,

        # campos trading
        "entrada": float(r.get("entrada", 0)),
        "stop": float(r.get("stop", 0)),
        "objetivo": float(r.get("objetivo", 0)),
        "rr": float(r.get("rr", 0)),
        "tipo": tipo,
        "tipo_señal": tipo,  # alias para el HTML
    }

# =============================
# EXPORTACIÓN A JSON (para Flask)
# =============================

def formatear_para_json(resultados):
    return resultados


# =============================
# EJECUCIÓN DIRECTA
# =============================

if __name__ == "__main__":
    res = escanear_mercado(CONTINUO_LIQUIDO, tipo_scan="ambos")
    print("\nTOP 5:")
    for r in res[:5]:
        print(r)


# ══════════════════════════════════════════════════════════════
# CLASE WRAPPER — para compatibilidad con swing_routes.py
# ══════════════════════════════════════════════════════════════

class ScannerSwing:
    """Wrapper OOP sobre las funciones del scanner."""

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        return escanear_ticker(ticker, tipo_scan='breakout')

    def escanear_todo(self, tickers=None, cache=None, top_n: int = 20) -> dict:
        from core.universos import IBEX35, CONTINUO
        from datetime import datetime
        if tickers is None:
            tickers = IBEX35 + CONTINUO
        breakouts = escanear_mercado(tickers, tipo_scan='breakout', max_workers=2)
        pullbacks = escanear_mercado(tickers, tipo_scan='pullback', max_workers=2)
        señales = breakouts + pullbacks
        señales = sorted(señales, key=lambda x: x.get("score", 0), reverse=True)[:top_n]
        return {
            "señales":   señales,
            "total":     len(señales),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
