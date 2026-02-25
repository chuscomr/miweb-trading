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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ------------------------------------------------------------
# IMPORTAR LÓGICAS COMO SIEMPRE (SIN RELATIVOS)
# ------------------------------------------------------------
from swing_trading.logica_breakout import detectar_breakout_swing
from swing_trading.logica_pullback import detectar_pullback_swing


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

def escanear_ticker(ticker, tipo_scan='ambos'):

    if tipo_scan == 'breakout':
        r = detectar_breakout_swing(ticker)

    elif tipo_scan == 'pullback':
        r = detectar_pullback_swing(ticker)

    else:
        b = detectar_breakout_swing(ticker)
        p = detectar_pullback_swing(ticker)

        r = max([b,p], key=lambda x: x.get("setup_score",0))

    if not isinstance(r, dict):
        return None

    if not r.get("valido", False):
        return None

    return formatear_resultado(r)

# =============================
# ESCANEO MASIVO
# =============================

import copy

def escanear_mercado(tickers, tipo_scan='ambos', max_workers=2):

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

    return {
        "ticker": ticker.replace(".MC",""),
        "ticker_completo": ticker,

        # ⭐ campos frontend
        "precio": float(r.get("precio_actual",0)),
        "score": score,
        "confianza": confianza,
        "variacion_1d": float(r.get("variacion_1d",0)),
        "es_senal": r.get("valido", False),

        # ⭐ campos trading
        "entrada": float(r.get("entrada",0)),
        "stop": float(r.get("stop",0)),
        "objetivo": float(r.get("objetivo",0)),
        "rr": float(r.get("rr",0)),
        "tipo": r.get("tipo","")
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
