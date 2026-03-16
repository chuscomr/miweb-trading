# backtest/engine.py
# ══════════════════════════════════════════════════════════════
# BACKTEST ENGINE — Motor de simulación barra a barra
#
# Recibe un DataFrame completo y simula las decisiones
# que habría tomado la estrategia en cada sesión histórica.
#
# Flujo por barra:
#   1. Si hay posición abierta → gestionar (stop/target/trailing)
#   2. Si no hay posición      → evaluar entrada
#   3. Al final                → cerrar posición abierta si queda
# ══════════════════════════════════════════════════════════════

import pandas as pd
import logging
from datetime import datetime

from core.indicadores import atr_actual
from .portfolio import Portfolio, Posicion
from .risk import RiskManager
from .metrics import calcular_metricas
from .config_backtest import ConfigBacktest

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Motor de backtest barra a barra.

    Uso:
        engine = BacktestEngine(df, estrategia, config)
        resultado = engine.run()
    """

    def __init__(
        self,
        df:        pd.DataFrame,
        estrategia,                    # instancia de EstrategiaBase
        config:    ConfigBacktest,
        ticker:    str = "TICKER",
    ):
        self.df         = df.copy()
        self.estrategia = estrategia
        self.config     = config
        self.ticker     = ticker

        self.portfolio  = Portfolio(
            capital_inicial = config.capital_inicial,
            comision_pct    = config.comision_pct,
        )
        self.risk       = RiskManager(
            capital    = config.capital_inicial,
            riesgo_pct = config.riesgo_pct,
        )

    # ── API pública ────────────────────────────────────────

    def run(self) -> dict:
        """
        Ejecuta el backtest completo.

        Returns:
            dict con 'metricas', 'trades', 'equity', 'config'
        """
        df      = self.df
        n_barras = len(df)
        min_v    = self.config.min_velas

        logger.info(f"🚀 Backtest {self.ticker} · {n_barras} barras · "
                    f"estrategia={self.config.estrategia}")

        for i in range(min_v, n_barras):
            df_ventana = df.iloc[:i + 1]   # todo el histórico hasta la barra i
            fecha      = df_ventana.index[-1]
            high       = float(df_ventana["High"].iloc[-1])
            low        = float(df_ventana["Low"].iloc[-1])
            close      = float(df_ventana["Close"].iloc[-1])

            if self.config.verbose and i % 50 == 0:
                logger.debug(f"  ⏳ Barra {i}/{n_barras} — {fecha.date()}")

            # 1️⃣ Gestionar posición abierta
            if self.portfolio.hay_posicion:
                self._gestionar_posicion(high, low, close, fecha)

            # 2️⃣ Evaluar entrada (solo si no hay posición)
            if not self.portfolio.hay_posicion:
                self._evaluar_entrada(df_ventana, fecha)

            # Sincronizar capital en RiskManager tras cada trade
            self.risk.actualizar_capital(self.portfolio.capital)

        # 3️⃣ Cerrar posición abierta al final del backtest
        if self.portfolio.hay_posicion:
            precio_cierre = float(df["Close"].iloc[-1])
            self.portfolio.cerrar(precio_cierre, df.index[-1], "FIN_BACKTEST")

        return self._construir_resultado()

    # ── Lógica interna ─────────────────────────────────────

    def _gestionar_posicion(self, high: float, low: float, close: float, fecha):
        """Actualiza la posición con la barra actual y cierra si toca stop/target."""
        pos    = self.portfolio.posicion
        estado = pos.actualizar(high, low, close)

        if estado:
            precio_salida = pos.precio_salida(estado)
            # Aplicar slippage en la salida
            if estado == "STOP":
                precio_salida *= (1 - self.config.slippage_pct / 100)
            else:
                precio_salida *= (1 + self.config.slippage_pct / 100)

            self.portfolio.cerrar(precio_salida, fecha, estado)

            if self.config.verbose:
                logger.debug(f"  📤 Salida {estado} en {precio_salida:.2f}€ — {fecha.date()}")

    def _evaluar_entrada(self, df_ventana: pd.DataFrame, fecha):
        """Evalúa si la estrategia genera señal de entrada en la barra actual."""
        try:
            señal = self.estrategia._evaluar_df(df_ventana, self.ticker)
        except Exception as e:
            logger.debug(f"  ⚠️ Error evaluando {fecha.date()}: {e}")
            return

        if not señal.get("valido"):
            return

        entrada = señal.get("entrada", 0)
        stop    = señal.get("stop", 0)

        if not entrada or not stop or stop >= entrada:
            return

        # Aplicar slippage en la entrada
        entrada_real = entrada * (1 + self.config.slippage_pct / 100)

        acciones = self.risk.size(entrada_real, stop)
        if acciones <= 0:
            return

        # Validar que tenemos capital suficiente
        if acciones * entrada_real > self.portfolio.capital:
            acciones = int(self.portfolio.capital / entrada_real)
        if acciones <= 0:
            return

        posicion = Posicion(
            ticker          = self.ticker,
            fecha_entrada   = fecha,
            precio_entrada  = entrada_real,
            stop            = stop,
            acciones        = acciones,
            rr_objetivo     = self.config.rr_objetivo,
            trailing_stop   = self.config.trailing_stop,
            trailing_pct    = self.config.trailing_pct,
        )

        self.portfolio.abrir(posicion)

        if self.config.verbose:
            logger.debug(f"  📥 Entrada {entrada_real:.2f}€ × {acciones} acc — {fecha.date()}")

    def _construir_resultado(self) -> dict:
        """Ensambla el resultado final del backtest."""
        metricas = calcular_metricas(
            trades          = self.portfolio.trades,
            equity          = self.portfolio.equity,
            capital_inicial = self.config.capital_inicial,
        )

        return {
            "metricas": metricas,
            "trades":   [t.to_dict() for t in self.portfolio.trades],
            "equity":   self.portfolio.equity,
            "config":   {
                "ticker":     self.ticker,
                "estrategia": self.config.estrategia,
                "capital":    self.config.capital_inicial,
                "riesgo_pct": self.config.riesgo_pct,
                "periodo":    self.config.periodo,
            },
        }


# ══════════════════════════════════════════════════════════════
# FUNCIÓN STANDALONE — para posicional_routes.py
# ══════════════════════════════════════════════════════════════

def ejecutar_backtest_sistema_completo(universo=None, verbose=False):
    """
    Ejecuta backtest posicional sobre un universo de tickers.
    Orquesta ejecutar_backtest_posicional() ticker a ticker.

    Args:
        universo: lista de tickers (default: IBEX35 + CONTINUO)
        verbose:  mostrar progreso en consola

    Returns:
        dict con: resultados_por_ticker, resumen, errores, total
    """
    from estrategias.posicional.datos_posicional import obtener_datos_semanales
    from estrategias.posicional.backtest_posicional import ejecutar_backtest_posicional
    from core.universos import IBEX35, CONTINUO
    from datetime import datetime

    if universo is None:
        universo = IBEX35 + CONTINUO

    resultados_por_ticker = {}
    errores = []
    equity_total = 0.0
    trades_total = 0

    if verbose:
        print(f"\n🔙 BACKTEST SISTEMA COMPLETO — {len(universo)} tickers")
        print("=" * 60)

    for ticker in universo:
        try:
            df, _ = obtener_datos_semanales(ticker, periodo_años=10)
            if df is None or df.empty:
                errores.append({"ticker": ticker, "error": "Sin datos"})
                continue

            resultado = ejecutar_backtest_posicional(df, ticker, verbose=verbose)

            if verbose:
                if "error" in resultado:
                    print(f"  ❌ {ticker}: error → {resultado['error']}")
                else:
                    print(f"  ✅ {ticker}: keys={list(resultado.keys())[:5]}")

            if "error" in resultado:
                errores.append({"ticker": ticker, "error": resultado["error"]})
                continue

            resultados_por_ticker[ticker] = resultado
            equity_total  += resultado.get("equity_final", 0)
            trades_total  += resultado.get("total_trades", 0)

            if verbose:
                print(f"  ✅ {ticker}: {resultado.get('expectancy', 0):+.2f}R "
                      f"({resultado.get('total_trades', 0)} trades)")

        except Exception as e:
            import traceback
            print(f"  💥 EXCEPCIÓN {ticker}: {e}")
            traceback.print_exc()
            errores.append({"ticker": ticker, "error": str(e)})

    # Resumen agregado
    resultados_lista = list(resultados_por_ticker.values())
    n = len(resultados_lista)

    resumen = {
        "total_tickers":    n,
        "tickers_con_error":len(errores),
        "trades_totales":   trades_total,
        "equity_media":     round(equity_total / n, 2) if n > 0 else 0,
        "expectancy_media": round(
            sum(r.get("expectancy", 0) for r in resultados_lista) / n, 2
        ) if n > 0 else 0,
        "winrate_media":    round(
            sum(r.get("winrate", 0) for r in resultados_lista) / n, 1
        ) if n > 0 else 0,
        "timestamp":        datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    if verbose:
        print(f"\n📊 RESUMEN SISTEMA:")
        print(f"  Tickers analizados: {n}")
        print(f"  Equity media:       {resumen['equity_media']:+.2f}R")
        print(f"  Expectancy media:   {resumen['expectancy_media']:+.2f}R")
        print(f"  Winrate media:      {resumen['winrate_media']:.1f}%")

    return {
        "resultados_por_ticker": resultados_por_ticker,
        "resumen":               resumen,
        "errores":               errores,
        "total":                 n,
    }



# ─────────────────────────────────────────────────────────────
# WRAPPER PARA LA RUTA API (estructura idéntica al original)
# ─────────────────────────────────────────────────────────────

def ejecutar_backtest_sistema_completo_api(tickers, cache=None):
    """
    Wrapper que ejecuta el backtest posicional y devuelve la estructura
    exacta que espera el modal JS:
      estado: {texto, color}
      metricas: {expectancy, winrate, max_dd, total_trades, tickers_activos}
      tickers: {aprobados, neutros, rechazados, excluidos}
      recomendacion: {titulo, acciones}
      config: {target, breakeven, riesgo, filtro_vol}
    """
    from core.universos import get_nombre

    resultado = ejecutar_backtest_sistema_completo(
        universo=tickers,
        verbose=True,
    )

    resumen    = resultado.get("resumen", {})
    resultados = resultado.get("resultados_por_ticker", {})
    errores    = resultado.get("errores", [])
    n          = resumen.get("total_tickers", 0)
    expectancy = resumen.get("expectancy_media", 0)
    winrate    = resumen.get("winrate_media", 0)

    # ── Estado semáforo ───────────────────────────────────────
    if n == 0:
        estado = {"color": "danger",  "texto": "SIN DATOS"}
    elif expectancy >= 0.40:
        estado = {"color": "success", "texto": "EXCELENTE"}
    elif expectancy >= 0.20:
        estado = {"color": "success", "texto": "RENTABLE"}
    elif expectancy > 0:
        estado = {"color": "warning", "texto": "MARGINAL"}
    else:
        estado = {"color": "danger",  "texto": "NO RENTABLE"}

    # ── Clasificar tickers ────────────────────────────────────
    aprobados, neutros, rechazados = [], [], []
    for ticker, r in resultados.items():
        eq = r.get("equity_final", 0)
        entry = {
            "nombre":  ticker.replace(".MC", ""),
            "empresa": get_nombre(ticker),
            "retorno": round(eq, 1),
            "trades":  r.get("total_trades", 0),
        }
        if eq >= 2.0:
            aprobados.append(entry)
        elif eq >= -2.0:
            neutros.append(entry)
        else:
            rechazados.append(entry)

    aprobados.sort(key=lambda x: x["retorno"], reverse=True)
    rechazados.sort(key=lambda x: x["retorno"])

    # ── Excluidos: tickers con error de datos ─────────────────
    excluidos = []
    for e in errores:
        ticker = e.get("ticker", "")
        motivo = e.get("error", "")
        excluidos.append({
            "nombre":  ticker.replace(".MC", ""),
            "empresa": get_nombre(ticker),
            "vol":     motivo[:30] if motivo else "sin datos",
        })

    # ── Max DD global ─────────────────────────────────────────
    mdd_values = [r.get("max_drawdown", 0) for r in resultados.values()]
    max_dd = round(max(mdd_values, default=0), 1)

    # ── Recomendación ─────────────────────────────────────────
    if expectancy >= 0.20 and len(aprobados) >= 5:
        recomendacion = {
            "titulo": "Sistema listo para operar",
            "acciones": [
                f"Operar SOLO los {len(aprobados)} tickers aprobados",
                "Mantener configuración actual",
            ]
        }
    elif expectancy >= 0.20:
        recomendacion = {
            "titulo": "Pocos tickers aprobados",
            "acciones": [
                "Considerar reducir filtro de volatilidad",
                "O incluir tickers neutros en watchlist",
            ]
        }
    else:
        recomendacion = {
            "titulo": "Sistema requiere optimización",
            "acciones": [
                "Revisar parámetros de entrada",
                "NO operar hasta expectancy > 0.20R",
            ]
        }

    return {
        "estado":   estado,
        "metricas": {
            "expectancy":      round(expectancy, 2),
            "winrate":         round(winrate, 1),
            "max_dd":          max_dd,
            "total_trades":    resumen.get("trades_totales", 0),
            "tickers_activos": n,
        },
        "tickers": {
            "aprobados":  aprobados,
            "neutros":    neutros,
            "rechazados": rechazados,
            "excluidos":  excluidos,
        },
        "recomendacion": recomendacion,
        "config": {
            "target":      "3",
            "breakeven":   "1",
            "riesgo":      "1.0",
            "filtro_vol":  ">9",
        },
        "periodo":  "10 años",
        "universo": f"IBEX 35 ({n} tickers)",
    }
