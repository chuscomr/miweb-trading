class RiskManager:
    def __init__(self, capital, riesgo_pct):
        self.capital = capital
        self.riesgo_pct = riesgo_pct

    def size(self, entrada, stop):
        riesgo_por_accion = entrada - stop
        if riesgo_por_accion <= 0:
            return 0

        riesgo_total = self.capital * self.riesgo_pct
        size = int(riesgo_total / riesgo_por_accion)

        # 🔑 CLAVE: permitir tamaño mínimo
        return max(size, 1)
