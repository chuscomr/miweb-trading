from .position import Position


def calcular_contexto(df):
    """
    Stub de contexto.
    El sistema real calcula el contexto dentro de logica.py
    """
    return {}


def calcular_atr(df, periodos=14):
    """
    ATR mínimo funcional.
    Se puede sustituir más adelante por el ATR real del sistema.
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"].shift(1)

    tr = (high - low).abs()
    atr = tr.rolling(periodos).mean()

    return atr.iloc[-1] if not atr.isna().iloc[-1] else tr.mean()


class BacktestEngine:
    def __init__(self, data, strategy, execution, risk, portfolio):
        self.data = data
        self.strategy = strategy
        self.execution = execution
        self.risk = risk
        self.portfolio = portfolio

    def run(self):
        for i, df in self.data.iter_bars():

            if i % 50 == 0:
                print(f"⏳ Procesando barra {i}")

            fecha = df.index[-1]
            contexto = calcular_contexto(df)

            # 1️⃣ Gestionar posición abierta
            if self.portfolio.position:
                self._manage(df, fecha)

            # 2️⃣ Evaluar entrada (diagnóstico)
            if not self.portfolio.position:
                decision = self.strategy.evaluate(
                    df,
                    contexto,
                    None,
                    ultima_barra=True
                )

                # 🔎 PRINT TEMPORAL DE DIAGNÓSTICO
                if decision["accion"] == "ENTRAR":
                    print("📌 SEÑAL HISTÓRICA EN:", fecha)

                if decision["accion"] == "ENTRAR":
                    self._enter(df, decision, fecha)

        # 3️⃣ Marcar equity
        self.portfolio.mark_to_market()



    def _enter(self, df, d, fecha):
        atr = calcular_atr(df)

        entrada_real = self.execution.ejecutar_entrada(
            d["entrada"], atr
        )
        stop = d["stop"]

        size = self.risk.size(entrada_real, stop)
        if size <= 0:
            return

        self.portfolio.open(
            Position(
                entrada_real,
                stop,
                size,
                fecha
            )
        )

    def _manage(self, df, fecha):
        pos = self.portfolio.position
        row = df.iloc[-1]

        estado = pos.update(row["High"], row["Low"])

        if estado in ("STOP", "TARGET"):
            # 🔧 CORRECCIÓN: Usar precio correcto según el motivo
            if estado == "STOP":
                salida_precio = pos.trade.stop
            else:  # TARGET
                # Target está a +2R del precio de entrada
                salida_precio = pos.trade.entrada + (3 * pos.riesgo)

            salida_real = self.execution.ejecutar_salida(
                salida_precio,
                calcular_atr(df)
            )

            self.portfolio.close(
                salida_real,
                fecha,
                motivo=estado
            )
