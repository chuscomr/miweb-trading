class Portfolio:
    def __init__(self, capital_inicial):
        self.capital = capital_inicial
        self.capital_inicial = capital_inicial

        self.position = None
        self.trades = []
        self.equity_curve = []

    def open(self, position):
        self.position = position

    def close(self, precio_salida, fecha, motivo="STOP"):
        trade = self.position.trade

        trade.cerrar(
            precio_salida=precio_salida,
            fecha=fecha,
            motivo=motivo
        )

        self.capital += trade.resultado
        self.trades.append(trade)
        self.position = None

    def mark_to_market(self):
        self.equity_curve.append(self.capital)
