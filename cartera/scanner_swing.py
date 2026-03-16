"""
ESCÁNER SWING TRADING
Versión corregida y simplificada
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Estrategias
from estrategias.swing.logica_breakout import detectar_breakout_swing
from estrategias.swing.logica_pullback import detectar_pullback_swing

# Universos
from core.universos import IBEX35, CONTINUO


# ==========================================================
# ESCANEO INDIVIDUAL
# ==========================================================

def escanear_ticker(ticker, tipo_scan="breakout"):

    if tipo_scan == "pullback":
        r = detectar_pullback_swing(ticker)
    else:
        r = detectar_breakout_swing(ticker)

    if not isinstance(r, dict):
        return None

    # ⭐ usar score en lugar de "valido"
    score = r.get("setup_score", 0)

    if score < 3:
        return None

    return formatear_resultado(r)


# ==========================================================
# ESCANEO MASIVO
# ==========================================================

def escanear_mercado(tickers, tipo_scan="breakout", max_workers=3):

    resultados = []
    vistos = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = {
            executor.submit(escanear_ticker, t, tipo_scan): t
            for t in tickers
        }

        for future in as_completed(futures):

            r = future.result()

            if isinstance(r, dict):

                ticker = r["ticker"]

                if ticker not in vistos:
                    vistos.add(ticker)
                    resultados.append(r)

    resultados.sort(key=lambda x: x["score"], reverse=True)

    return resultados


# ==========================================================
# FORMATEO RESULTADOS
# ==========================================================

def formatear_resultado(r):

    ticker = r.get("ticker", "")

    score = float(r.get("setup_score", 0))

    # confianza tipo TradingView
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
        "ticker": ticker.replace(".MC", ""),
        "ticker_completo": ticker,

        "precio": float(r.get("precio_actual", 0)),
        "precio_actual": float(r.get("precio_actual", 0)),

        "score": score,
        "setup_score": score,
        "confianza": confianza,

        "variacion_1d": float(r.get("variacion_1d", 0)),

        "entrada": float(r.get("entrada", 0)),
        "stop": float(r.get("stop", 0)),
        "objetivo": float(r.get("objetivo", 0)),
        "rr": float(r.get("rr", 0)),

        "tipo": tipo,
        "tipo_señal": tipo,
    }


# ==========================================================
# EXPORTACIÓN JSON
# ==========================================================

def formatear_para_json(resultados):
    return resultados


# ==========================================================
# WRAPPER CLASE (para Flask)
# ==========================================================

class ScannerSwing:

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        return escanear_ticker(ticker, tipo_scan="breakout")

    def escanear_todo(self, tickers=None, cache=None, top_n=20):

        if tickers is None:
            tickers = IBEX35 + CONTINUO

        breakouts = escanear_mercado(tickers, "breakout")
        pullbacks = escanear_mercado(tickers, "pullback")

        señales = breakouts + pullbacks

        señales = sorted(
            señales,
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:top_n]

        return {
            "señales": señales,
            "total": len(señales),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }


# ==========================================================
# TEST DIRECTO
# ==========================================================

if __name__ == "__main__":

    print("\nEscaneando Mercado Continuo...\n")

    res = escanear_mercado(CONTINUO, "breakout")

    print(f"Analizados: {len(CONTINUO)}")

    for r in res[:5]:
        print(r)