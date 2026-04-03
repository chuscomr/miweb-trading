# backtest/portfolio_legacy.py
# ══════════════════════════════════════════════════════════════
# Trade, Position, Portfolio del sistema original de swing
# Portado literalmente de: trade.py, position.py, portfolio.py, metrics.py
# ══════════════════════════════════════════════════════════════


class Trade:
    """
    Trade mutable del sistema original.
    - .stop es mutable (se mueve a BE en +1R)
    - .abierto controla si la posición sigue viva
    - .R y .resultado se calculan al cerrar
    """

    def __init__(self, entrada, stop, size, fecha):
        self.entrada       = entrada
        self.stop          = stop          # ← mutable (BE lo modifica)
        self.stop_inicial  = stop          # fijo para calcular riesgo
        self.size          = size
        self.fecha_entrada = fecha

        self.abierto       = True
        self.fecha_salida  = None
        self.precio_salida = None
        self.motivo        = None
        self.resultado     = 0.0
        self.R             = 0.0

    def cerrar(self, precio_salida, fecha, motivo):
        self.precio_salida = precio_salida
        self.fecha_salida  = fecha
        self.motivo        = motivo
        self.abierto       = False

        self.resultado = (precio_salida - self.entrada) * self.size

        riesgo_unitario = self.entrada - self.stop_inicial
        riesgo_total    = riesgo_unitario * self.size
        self.R = self.resultado / riesgo_total if riesgo_total > 0 else 0.0

        # Aliases para compatibilidad con metrics.py del nuevo sistema
        self.resultado_neto = self.resultado
        self.ganadora       = self.resultado > 0
        self.motivo_salida  = motivo
        try:
            self.duracion_dias = max((self.fecha_salida - self.fecha_entrada).days, 1)
        except Exception:
            self.duracion_dias = 1

    def to_dict(self):
        return {
            "fecha_entrada":  str(self.fecha_entrada)[:10] if self.fecha_entrada else "",
            "fecha_salida":   str(self.fecha_salida)[:10]  if self.fecha_salida  else "",
            "precio_entrada": round(self.entrada, 2),
            "precio_salida":  round(self.precio_salida, 2) if self.precio_salida else 0,
            "stop_inicial":   round(self.stop_inicial, 2),
            "acciones":       self.size,
            "resultado_neto": round(self.resultado, 2),
            "R":              round(self.R, 2),
            "motivo_salida":  self.motivo or "",
            "ganadora":       self.resultado > 0,
        }


class Position:
    """
    Posición abierta con break-even en +1R y target en +3R.
    Portado literalmente de position.py original.
    """

    def __init__(self, entrada, stop, size, fecha):
        self.trade        = Trade(entrada, stop, size, fecha)
        self.riesgo       = entrada - stop   # riesgo unitario (por acción)
        self.be_activado  = False

    def update(self, high, low):
        if not self.trade.abierto:
            return "CERRADA"

        # 1️⃣ Break-even en +1R
        if not self.be_activado and high >= self.trade.entrada + self.riesgo:
            self.trade.stop  = self.trade.entrada
            self.be_activado = True

        # 2️⃣ Target en +3R
        if high >= self.trade.entrada + 3 * self.riesgo:
            return "TARGET"

        # 3️⃣ Stop (puede ser BE si ya se activó)
        if low <= self.trade.stop:
            return "STOP"

        return "VIVA"


class Portfolio:
    """
    Portfolio original: .position, .trades, .equity_curve
    Portado literalmente de portfolio.py original.
    """

    def __init__(self, capital_inicial):
        self.capital         = capital_inicial
        self.capital_inicial = capital_inicial
        self.position        = None
        self.trades          = []
        self.equity_curve    = []

    def open(self, position):
        self.position = position

    def close(self, precio_salida, fecha, motivo="STOP"):
        trade = self.position.trade
        trade.cerrar(precio_salida=precio_salida, fecha=fecha, motivo=motivo)
        self.capital     += trade.resultado
        self.trades.append(trade)
        self.position     = None

    def mark_to_market(self):
        """Registra equity en cada barra (igual que el original)."""
        self.equity_curve.append(self.capital)
