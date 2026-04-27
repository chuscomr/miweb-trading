# backtest/trade.py
# ══════════════════════════════════════════════════════════════
# TRADE — Registro de una operación completa
# ══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Trade:
    """
    Registro inmutable de una operación cerrada.
    Se crea al cerrar una posición en Portfolio.
    """

    ticker:          str
    fecha_entrada:   datetime
    fecha_salida:    datetime
    precio_entrada:  float
    precio_salida:   float
    stop_inicial:    float
    acciones:        int
    motivo_salida:   str              # "STOP" | "TARGET" | "TRAILING" | "FIN_BACKTEST"

    # ── Calculados al cerrar ───────────────────────────────
    resultado_bruto: float = field(init=False)   # € ganados/perdidos sin comisiones
    resultado_neto:  float = field(init=False)   # € después de comisiones
    R:               float = field(init=False)   # resultado en múltiplos de R
    riesgo_inicial:  float = field(init=False)   # € en riesgo al abrir
    duracion_dias:   int   = field(init=False)   # días en posición
    ganadora:        bool  = field(init=False)

    # Comisión aplicada (se pasa desde Portfolio)
    comision_total:  float = 0.0

    def __post_init__(self):
        self.riesgo_inicial  = (self.precio_entrada - self.stop_inicial) * self.acciones
        self.resultado_bruto = (self.precio_salida - self.precio_entrada) * self.acciones
        self.resultado_neto  = self.resultado_bruto - self.comision_total
        self.R               = (self.resultado_neto / self.riesgo_inicial
                                if self.riesgo_inicial > 0 else 0.0)
        self.ganadora        = self.resultado_neto > 0
        self.duracion_dias   = max((self.fecha_salida - self.fecha_entrada).days, 1)

    def to_dict(self) -> dict:
        return {
            "ticker":          self.ticker,
            "fecha_entrada":   self.fecha_entrada.strftime("%Y-%m-%d"),
            "fecha_salida":    self.fecha_salida.strftime("%Y-%m-%d"),
            "precio_entrada":  round(self.precio_entrada, 2),
            "precio_salida":   round(self.precio_salida, 2),
            "stop_inicial":    round(self.stop_inicial, 2),
            "acciones":        self.acciones,
            "resultado_neto":  round(self.resultado_neto, 2),
            "R":               round(self.R, 2),
            "motivo_salida":   self.motivo_salida,
            "duracion_dias":   self.duracion_dias,
            "ganadora":        self.ganadora,
        }
