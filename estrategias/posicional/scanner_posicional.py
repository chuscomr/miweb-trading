"""
═══════════════════════════════════════════════════════════════
SCANNER POSICIONAL — IBEX 35 + CONTINUO
═══════════════════════════════════════════════════════════════

Uso:
    scanner = ScannerPosicional()

    # Escaneo completo
    resultados = scanner.escanear_todo(cache)

    # Solo IBEX (recomendado para posicional — más liquidez)
    señales = scanner.escanear(IBEX35, cache)
"""

import logging
from core.universos import IBEX35, CONTINUO, TODOS
from core.contexto_mercado import evaluar_contexto_ibex, mercado_operable
from .datos_posicional import obtener_datos_semanales
from .sistema_trading_posicional import evaluar_con_scoring

logger = logging.getLogger(__name__)


class ScannerPosicional:

    def __init__(self):
        pass

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        top_n: int = None,
    ) -> list:
        """
        Escanea posicional usando evaluar_con_scoring.
        Por defecto solo IBEX35 — posicional requiere liquidez garantizada.
        """
        import time
        resultados = []
        for ticker in (tickers or IBEX35):
            try:
                time.sleep(0.5)
                df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)
                if df is None or df.empty or len(df) < 200:
                    continue
                precios   = df["Close"].values
                volumenes = df["Volume"].values if "Volume" in df.columns else None
                res = evaluar_con_scoring(precios, volumenes)
                if res.get("decision") == "COMPRA":
                    resultados.append({
                        "ticker":         ticker,
                        "nombre":         ticker.replace(".MC", ""),
                        "precio":         float(precios[-1]),
                        "entrada":        res.get("entrada", 0),
                        "stop":           res.get("stop", 0),
                        "riesgo_pct":     res.get("riesgo_pct", 0),
                        "score":          res.get("setup_score", 0),
                        "clasificacion":  res.get("clasificacion", ""),
                        "motivo":         " · ".join(res.get("motivos", [])),
                        "fuerza_relativa": res.get("detalles", {}).get("fr_cat", ""),
                        "fr_diferencial":  res.get("detalles", {}).get("fr_diff", 0),
                    })
            except Exception as e:
                logger.warning(f"Scanner posicional error {ticker}: {e}")
        resultados.sort(key=lambda x: x["score"], reverse=True)
        return resultados[:top_n] if top_n else resultados

    def escanear_todo(self, cache=None, top_n: int = 15) -> dict:
        """
        Escaneo completo con contexto de mercado incluido.

        Returns:
            dict con 'señales', 'contexto', 'total', 'cancelado'
        """
        contexto = evaluar_contexto_ibex(cache)

        if not mercado_operable(cache):
            logger.warning("⚠️ ScannerPosicional: mercado bajista — scan cancelado")
            return {
                "señales":   [],
                "contexto":  contexto,
                "total":     0,
                "cancelado": True,
                "motivo":    "Mercado en estado BAJISTA — posicional cancelado",
            }

        señales = self.escanear(cache=cache, top_n=top_n)

        logger.info(
            f"📊 ScannerPosicional: {len(señales)} señales · "
            f"contexto={contexto['estado']}"
        )

        return {
            "señales":   señales,
            "contexto":  contexto,
            "total":     len(señales),
            "cancelado": False,
        }

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        """Evalúa un ticker individual."""
        return {
            "señal":    self.estrategia.evaluar(ticker, cache),
            "contexto": evaluar_contexto_ibex(cache),
        }
