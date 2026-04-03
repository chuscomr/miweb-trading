"""
ESCÁNER SWING TRADING
Usa las clases BreakoutSwing y PullbackSwing de la nueva arquitectura.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from estrategias.swing.breakout import BreakoutSwing
from estrategias.swing.pullback import PullbackSwing

_breakout_inst = BreakoutSwing()
_pullback_inst  = PullbackSwing()


# ══════════════════════════════════════════════════════════════
# ESCANEO INDIVIDUAL
# ══════════════════════════════════════════════════════════════

def escanear_ticker(ticker: str, tipo_scan: str = "breakout", cache=None):
    """
    Evalúa un ticker con la estrategia indicada.
    tipo_scan: 'breakout' | 'pullback'
    Devuelve dict formateado o None si no hay señal válida.
    """
    if tipo_scan == "pullback":
        r = _pullback_inst.evaluar(ticker, cache)
    else:
        r = _breakout_inst.evaluar(ticker, cache)

    if not isinstance(r, dict) or not r.get("valido", False):
        return None

    return _formatear(r)


# ══════════════════════════════════════════════════════════════
# ESCANEO MASIVO
# ══════════════════════════════════════════════════════════════

def escanear_mercado(tickers: list, tipo_scan: str = "breakout",
                     max_workers: int = 2, cache=None) -> list:
    """
    Escanea una lista de tickers en paralelo.
    tipo_scan: 'breakout' | 'pullback' | 'ambos'
    Devuelve lista de señales válidas ordenadas por score desc.
    """
    if tipo_scan == "ambos":
        breakouts = escanear_mercado(tickers, "breakout", max_workers, cache)
        pullbacks = escanear_mercado(tickers, "pullback", max_workers, cache)
        vistos = set()
        combinados = []
        for r in sorted(breakouts + pullbacks,
                        key=lambda x: x.get("score", 0), reverse=True):
            if r["ticker_completo"] not in vistos:
                vistos.add(r["ticker_completo"])
                combinados.append(r)
        return combinados

    resultados = []
    vistos = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(escanear_ticker, t, tipo_scan, cache): t
            for t in tickers
        }
        for future in as_completed(futures):
            r = future.result()
            if isinstance(r, dict) and r.get("es_senal") and r["ticker_completo"] not in vistos:
                vistos.add(r["ticker_completo"])
                resultados.append(r)

    resultados.sort(key=lambda x: x.get("score", 0), reverse=True)
    return resultados


# ══════════════════════════════════════════════════════════════
# FORMATEO
# ══════════════════════════════════════════════════════════════

def _to_float(x):
    if hasattr(x, "item"):
        return float(x.item())
    return float(x) if x is not None else 0.0


def _nivel_calidad(score: float) -> dict:
    """
    Clasifica el setup en 3 niveles de calidad.
    🟢 Compra            (5.5 - 6.4): estructura + RSI
    🔵 Compra Confirmada (6.5 - 7.9): + soporte cercano
    ⭐ Alta Probabilidad (8.0+):       + patrón de vela
    """
    if score >= 8.0:
        return {"nivel": "alta_probabilidad", "label": "Alta Probabilidad", "emoji": "⭐"}
    elif score >= 6.5:
        return {"nivel": "confirmada",        "label": "Compra Confirmada", "emoji": "🔵"}
    else:
        return {"nivel": "compra",            "label": "Compra",            "emoji": "🟢"}


def _formatear(r: dict) -> dict:
    from core.universos import get_nombre
    ticker = r.get("ticker", "")
    score  = _to_float(r.get("setup_score", 0))
    nivel  = _nivel_calidad(score)

    # Mantener confianza legacy para compatibilidad
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
        "ticker":          ticker.replace(".MC", ""),
        "ticker_completo": ticker,
        "nombre":          get_nombre(ticker),
        "precio":          _to_float(r.get("precio_actual")),
        "precio_actual":   _to_float(r.get("precio_actual")),
        "score":           score,
        "setup_score":     score,
        "setup_max":       10,
        "confianza":       confianza,
        "nivel":           nivel["nivel"],
        "nivel_label":     nivel["label"],
        "nivel_emoji":     nivel["emoji"],
        "variacion_1d":    _to_float(r.get("variacion_1d")),
        "es_senal":        True,
        "entrada":         _to_float(r.get("entrada")),
        "stop":            _to_float(r.get("stop")),
        "objetivo":        _to_float(r.get("objetivo")),
        "rr":              _to_float(r.get("rr")),
        "tipo":            tipo,
        "tipo_señal":      tipo,
    }


# ══════════════════════════════════════════════════════════════
# CLASE WRAPPER — para swing_routes.py
# ══════════════════════════════════════════════════════════════

class ScannerSwing:
    """Wrapper OOP sobre las funciones del scanner."""

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        b = _breakout_inst.evaluar(ticker, cache)
        p = _pullback_inst.evaluar(ticker, cache)
        from core.contexto_mercado import evaluar_contexto_ibex
        return {
            "breakout": b,
            "pullback": p,
            "contexto": evaluar_contexto_ibex(cache),
        }

    def escanear_todo(self, tickers=None, cache=None, top_n: int = 20) -> dict:
        from core.universos import IBEX35, CONTINUO
        if tickers is None:
            tickers = IBEX35 + CONTINUO
        señales = escanear_mercado(tickers, tipo_scan="ambos",
                                   max_workers=2, cache=cache)
        señales = señales[:top_n]
        return {
            "señales":   señales,
            "total":     len(señales),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
