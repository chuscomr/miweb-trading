# backtest/engine_legacy.py
# ══════════════════════════════════════════════════════════════
# BacktestEngine ORIGINAL — portado literalmente del sistema antiguo
# Usa portfolio_legacy.Portfolio/Position y mark_to_market por barra
# ══════════════════════════════════════════════════════════════

import pandas as pd


def calcular_contexto(df):
    """
    Contexto de mercado calculado con datos del propio ticker hasta la barra actual.
    En backtest usar_filtro_mercado=False, así que no bloquea entradas.
    El filtro real IBEX>MA200 solo aplica en producción.
    """
    if len(df) < 50:
        return {"estado": "RIESGO MEDIO"}

    close  = df["Close"]
    ma200  = close.rolling(200).mean().iloc[-1]
    ma50   = close.rolling(50).mean().iloc[-1]
    precio = close.iloc[-1]

    if pd.isna(ma200) or pd.isna(ma50):
        estado = "RIESGO MEDIO"
    elif precio > ma200 and ma50 > ma200:
        estado = "RIESGO BAJO"
    elif precio < ma200:
        estado = "RIESGO ALTO"
    else:
        estado = "RIESGO MEDIO"

    return {"estado": estado}


def calcular_atr(df, periodos=14):
    high  = df["High"]
    low   = df["Low"]
    tr    = (high - low).abs()
    atr   = tr.rolling(periodos).mean()
    return atr.iloc[-1] if not atr.isna().iloc[-1] else tr.mean()


class BacktestEngineLegacy:
    """
    Motor de backtest original.
    Requiere Portfolio/Position de portfolio_legacy (no el nuevo Portfolio).
    """

    def __init__(self, data, strategy, execution, risk, portfolio):
        self.data      = data
        self.strategy  = strategy
        self.execution = execution
        self.risk      = risk
        self.portfolio = portfolio

    def run(self):
        last_df   = None
        last_fecha = None

        for i, df in self.data.iter_bars():

            # datos.py hace reset_index → índice es int; fecha en columna 'Date'/'index'
            _idx = df.index[-1]
            if hasattr(_idx, "strftime"):
                fecha = _idx
            else:
                # Buscar columna de fecha
                for _col in ("Date", "date", "index", "Fecha"):
                    if _col in df.columns:
                        fecha = df[_col].iloc[-1]
                        break
                else:
                    fecha = _idx   # fallback int

            contexto = calcular_contexto(df)

            # 1️⃣ Gestionar posición abierta
            if self.portfolio.position:
                self._manage(df, fecha)

            # 2️⃣ Evaluar entrada si no hay posición
            if not self.portfolio.position:
                decision = self.strategy.evaluate(
                    df,
                    contexto,
                    None,
                    ultima_barra=True
                )
                if decision["accion"] == "ENTRAR":
                    self._enter(df, decision, fecha)

            # ✅ mark_to_market en cada barra (igual que original)
            self.portfolio.mark_to_market()
            last_df    = df
            last_fecha = fecha

        # 3️⃣ Cierre final si queda posición abierta
        if self.portfolio.position and last_df is not None:
            precio_f = float(last_df["Close"].iloc[-1])
            self.portfolio.close(precio_f, last_fecha, motivo="FIN_BACKTEST")
            self.portfolio.mark_to_market()

    def _enter(self, df, d, fecha):
        from .portfolio_legacy import Position

        atr          = calcular_atr(df)
        entrada_real = self.execution.ejecutar_entrada(d["entrada"], atr)
        stop         = d["stop"]
        size         = self.risk.size(entrada_real, stop)

        if size <= 0:
            return

        self.portfolio.open(Position(entrada_real, stop, size, fecha))

    def _manage(self, df, fecha):
        from .portfolio_legacy import Position

        pos    = self.portfolio.position
        row    = df.iloc[-1]
        estado = pos.update(row["High"], row["Low"])

        if estado in ("STOP", "TARGET"):
            if estado == "STOP":
                salida_precio = pos.trade.stop
            else:
                salida_precio = pos.trade.entrada + (3 * pos.riesgo)

            salida_real = self.execution.ejecutar_salida(
                salida_precio,
                calcular_atr(df)
            )
            self.portfolio.close(salida_real, fecha, motivo=estado)
