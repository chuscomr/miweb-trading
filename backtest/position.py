from .trade import Trade

class Position:
    def __init__(self, entrada, stop, size, fecha):
        self.trade = Trade(entrada, stop, size, fecha)
        self.riesgo = entrada - stop
        self.be_activado = False

    def update(self, high, low):
        if not self.trade.abierto:
            return "CERRADA"

        # 1️⃣ Break-even en +1R
        if not self.be_activado and high >= self.trade.entrada + self.riesgo:
            self.trade.stop = self.trade.entrada
            self.be_activado = True

        # 2️⃣ Salida total en +2R
        if high >= self.trade.entrada + 3 * self.riesgo:
            return "TARGET"

        # 3️⃣ Stop
        if low <= self.trade.stop:
            return "STOP"

        return "VIVA"
