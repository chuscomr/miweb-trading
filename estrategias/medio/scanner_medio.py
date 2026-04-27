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
from core.contexto_mercado import evaluar_contexto_ibex
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
        
        MEJORA v82(2): Filtro flexible de mercado
        - ALCISTA: score sin cambios (1.0x)
        - TRANSICION: score × 0.85 (-15%)
        - BAJISTA: score × 0.7 (-30%, permite giros de mercado)
        
        Resultado: Captura mejores trades incluso en mercados bajistas
        mientras protege contra ruido.

        Returns:
            dict con 'señales', 'contexto', 'total', 'multiplicador'
        """
        from core.contexto_mercado import multiplicador_score_mercado
        
        contexto = evaluar_contexto_ibex(cache)
        multiplicador = multiplicador_score_mercado(cache)

        # CAMBIO: En vez de rechazar, reducimos score según contexto
        logger.info(
            f"🎯 ScannerMedio: contexto={contexto['estado']} "
            f"→ multiplicador={multiplicador}x"
        )

        señales = self.escanear(cache=cache, top_n=None)  # Obtener todas primero

        # Aplicar multiplicador de contexto al score
        for señal in señales:
            score_original = señal.get("setup_score", 0)
            score_ajustado = round(score_original * multiplicador, 2)
            señal["setup_score_original"] = score_original
            señal["setup_score"] = score_ajustado
            señal["multiplicador_aplicado"] = multiplicador

        # Re-ordenar por score ajustado
        señales.sort(key=lambda x: x.get("setup_score", 0), reverse=True)

        # Aplicar top_n si se especificó
        if top_n:
            señales = señales[:top_n]

        logger.info(
            f"📊 ScannerMedio: {len(señales)} señales · "
            f"contexto={contexto['estado']} · "
            f"multiplicador={multiplicador}"
        )

        return {
            "señales":       señales,
            "contexto":      contexto,
            "total":         len(señales),
            "cancelado":     False,
            "multiplicador": multiplicador,
        }

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        """Evalúa un ticker individual."""
        return {
            "señal":    self.estrategia.evaluar(ticker, cache),
            "contexto": evaluar_contexto_ibex(cache),
        }
