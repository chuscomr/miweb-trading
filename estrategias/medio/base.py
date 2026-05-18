# estrategias/base.py
# ══════════════════════════════════════════════════════════════
# CLASE BASE PARA TODAS LAS ESTRATEGIAS
#
# Toda estrategia (breakout, pullback, medio, posicional)
# hereda de EstrategiaBase e implementa:
#   - evaluar(df) → dict de señal estándar
#   - escanear(tickers, cache) → list de señales válidas
#
# Esto garantiza que el backtest engine y el scanner
# puedan tratar cualquier estrategia de forma genérica.
# ══════════════════════════════════════════════════════════════

from abc import ABC, abstractmethod
from typing import Optional
import logging
import pandas as pd

from core.data_provider import get_df
from core.contexto_mercado import evaluar_contexto_ibex, mercado_operable
from core.universos import IBEX35, CONTINUO, TODOS, get_nombre
from core.utilidades import respuesta_invalida

logger = logging.getLogger(__name__)


class EstrategiaBase(ABC):
    """
    Interfaz común para todas las estrategias de trading.

    Subclases deben implementar:
        _evaluar_df(self, df: pd.DataFrame, ticker: str) -> dict

    Opcionalmente pueden sobreescribir:
        periodo_datos   → str  (default "1y")
        min_velas       → int  (default 60)
        nombre          → str  (para logs)
    """

    nombre:       str = "Estrategia"
    periodo_datos: str = "1y"
    min_velas:    int = 60

    # ── Interfaz pública ───────────────────────────────────

    def evaluar(self, ticker: str, cache=None) -> dict:
        """
        Descarga datos y evalúa la señal para un ticker.

        Returns:
            dict estándar con claves: valido, ticker, tipo, entrada,
            stop, objetivo, rr, setup_score, motivos, variacion_1d
        """
        df = get_df(ticker, periodo=self.periodo_datos, cache=cache, min_velas=self.min_velas)

        if df is None:
            return respuesta_invalida(
                ticker=ticker,
                tipo=self.nombre,
                motivo=f"Datos insuficientes (mínimo {self.min_velas} velas)",
            )

        try:
            return self._evaluar_df(df, ticker)
        except Exception as e:
            logger.error(f"❌ {self.nombre} / {ticker}: {e}", exc_info=True)
            return respuesta_invalida(
                ticker=ticker,
                tipo=self.nombre,
                motivo=f"Error en evaluación: {e}",
            )

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        filtrar_mercado: bool = True,
        top_n: int = None,
    ) -> list:
        """
        Escanea una lista de tickers y devuelve las señales válidas
        ordenadas por setup_score descendente.

        Args:
            tickers:         Lista de tickers. Default: IBEX35 + CONTINUO
            cache:           Cache Flask o MemoryCache
            filtrar_mercado: Si True, no escanea en mercado bajista
            top_n:           Limitar resultados (None = todos)

        Returns:
            Lista de dicts de señal, ordenada por setup_score desc.
        """
        if tickers is None:
            tickers = TODOS

        if filtrar_mercado and not mercado_operable(cache):
            logger.warning(f"⚠️ {self.nombre}: mercado bajista, scan cancelado")
            return []

        señales = []
        logger.info(f"🔍 {self.nombre}: escaneando {len(tickers)} valores...")

        for ticker in tickers:
            try:
                resultado = self.evaluar(ticker, cache=cache)
                if resultado.get("valido"):
                    resultado["nombre"] = get_nombre(ticker)
                    señales.append(resultado)
                    logger.info(
                        f"  ✅ {ticker}: score={resultado.get('setup_score', 0)}, "
                        f"RR={resultado.get('rr', 0)}"
                    )
            except Exception as e:
                logger.error(f"  ❌ {ticker}: {e}")

        señales.sort(key=lambda x: x.get("setup_score", 0), reverse=True)

        if top_n is not None:
            señales = señales[:top_n]

        logger.info(f"📊 {self.nombre}: {len(señales)} señales encontradas")
        return señales

    # ── Interfaz a implementar ─────────────────────────────

    @abstractmethod
    def _evaluar_df(self, df: pd.DataFrame, ticker: str) -> dict:
        """
        Evalúa la señal sobre un DataFrame ya descargado y limpio.

        Args:
            df:     DataFrame OHLCV limpio (de core/data_provider.py)
            ticker: Ticker del valor

        Returns:
            dict estándar de señal. Usar respuesta_valida() o
            respuesta_invalida() de core/utilidades.py
        """
        ...

    # ── Helpers disponibles para subclases ─────────────────

    def _variacion_1d(self, df: pd.DataFrame) -> float:
        """Variación porcentual del último día."""
        if len(df) < 2:
            return 0.0
        try:
            close = df["Close"]
            return float(((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100)
        except Exception:
            return 0.0

    def _precio_actual(self, df: pd.DataFrame) -> float:
        """Último precio de cierre."""
        try:
            return float(df["Close"].iloc[-1])
        except Exception:
            return 0.0
