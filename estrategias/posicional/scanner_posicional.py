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
from .logica_posicional import Posicional

logger = logging.getLogger(__name__)


class ScannerPosicional:

    def __init__(self):
        self.estrategia = Posicional()

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        top_n: int = None,
    ) -> list:
        """
        Escanea posicional. Por defecto solo IBEX35 — posicional
        requiere liquidez garantizada para entradas y salidas limpias.
        """
        return self.estrategia.escanear(
            tickers=tickers or IBEX35,   # default IBEX35, no TODOS
            cache=cache,
            filtrar_mercado=True,
            top_n=top_n,
        )

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
