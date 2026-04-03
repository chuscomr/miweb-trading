"""
═══════════════════════════════════════════════════════════════
SCANNER MEDIO PLAZO — IBEX 35 + CONTINUO
═══════════════════════════════════════════════════════════════

Uso:
    scanner = ScannerMedio()

    # Escaneo completo
    resultados = scanner.escanear_todo(cache)

    # Solo IBEX
    señales = scanner.escanear(IBEX35, cache)
"""

import logging
from core.universos import IBEX35, CONTINUO, TODOS
from core.contexto_mercado import evaluar_contexto_ibex, mercado_operable
from .logica_medio import MedioPlazo

logger = logging.getLogger(__name__)


class ScannerMedio:

    def __init__(self):
        self.estrategia = MedioPlazo()

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        top_n: int = None,
    ) -> list:
        """Escanea medio plazo sobre la lista de tickers."""
        return self.estrategia.escanear(
            tickers=tickers or TODOS,
            cache=cache,
            filtrar_mercado=True,
            top_n=top_n,
        )

    def escanear_todo(self, cache=None, top_n: int = 20) -> dict:
        """
        Escaneo completo con contexto de mercado incluido.

        Returns:
            dict con 'señales', 'contexto', 'total', 'cancelado'
        """
        contexto = evaluar_contexto_ibex(cache)

        if not mercado_operable(cache):
            logger.warning("⚠️ ScannerMedio: mercado bajista — scan cancelado")
            return {
                "señales":   [],
                "contexto":  contexto,
                "total":     0,
                "cancelado": True,
                "motivo":    "Mercado en estado BAJISTA",
            }

        señales = self.escanear(cache=cache, top_n=top_n)

        logger.info(f"📊 ScannerMedio: {len(señales)} señales · contexto={contexto['estado']}")

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
