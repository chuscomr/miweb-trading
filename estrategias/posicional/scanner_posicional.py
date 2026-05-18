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

from core.contexto_mercado import evaluar_contexto_ibex
from core.universos import IBEX35

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
            f"🎯 ScannerPosicional: contexto={contexto['estado']} "
            f"→ multiplicador={multiplicador}x"
        )

        señales = self.escanear(cache=cache, top_n=None)  # Obtener todas primero

        # Aplicar multiplicador de contexto al score
        for señal in señales:
            score_original = señal.get("score", 0)
            score_ajustado = round(score_original * multiplicador, 2)
            señal["score_original"] = score_original
            señal["score"] = score_ajustado
            señal["multiplicador_aplicado"] = multiplicador

        # Re-ordenar por score ajustado
        señales.sort(key=lambda x: x["score"], reverse=True)

        # Aplicar top_n si se especificó
        if top_n:
            señales = señales[:top_n]

        logger.info(
            f"📊 ScannerPosicional: {len(señales)} señales · "
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
