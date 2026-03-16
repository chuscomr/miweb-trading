# backtest/risk.py
# ══════════════════════════════════════════════════════════════
# RISK — Portado literalmente del sistema original
# Lógica simple: riesgo_total / riesgo_por_accion
# ══════════════════════════════════════════════════════════════


class RiskManager:
    """
    Sizing original del sistema antiguo.
    riesgo_pct: decimal (0.01 = 1%) — igual que backtest_api.py original.
    """

    def __init__(self, capital: float, riesgo_pct: float = 0.01):
        self.capital    = capital
        self.riesgo_pct = riesgo_pct

    def size(self, entrada: float, stop: float) -> int:
        riesgo_por_accion = entrada - stop
        if riesgo_por_accion <= 0:
            return 0
        riesgo_total = self.capital * self.riesgo_pct
        return max(int(riesgo_total / riesgo_por_accion), 1)

    def actualizar_capital(self, capital: float):
        self.capital = capital
