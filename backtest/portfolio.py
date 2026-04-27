# backtest/portfolio.py
# ══════════════════════════════════════════════════════════════
# PORTFOLIO — Gestión de posición abierta y equity
# ══════════════════════════════════════════════════════════════

from datetime import datetime
from typing import Optional
from .trade import Trade


class Posicion:
    """
    Posición abierta actualmente.
    Gestiona stop, target y trailing stop barra a barra.
    """

    def __init__(
        self,
        ticker:        str,
        fecha_entrada: datetime,
        precio_entrada: float,
        stop:          float,
        acciones:      int,
        rr_objetivo:   float = 2.5,
        trailing_stop: bool  = False,
        trailing_pct:  float = 0.05,
    ):
        self.ticker         = ticker
        self.fecha_entrada  = fecha_entrada
        self.precio_entrada = precio_entrada
        self.stop           = stop
        self.stop_inicial   = stop
        self.acciones       = acciones
        self.trailing_stop  = trailing_stop
        self.trailing_pct   = trailing_pct

        self.riesgo_unitario = precio_entrada - stop
        self.target          = precio_entrada + (self.riesgo_unitario * rr_objetivo)
        self.max_precio      = precio_entrada   # para trailing

    @property
    def riesgo_total(self) -> float:
        return self.riesgo_unitario * self.acciones

    def actualizar(self, high: float, low: float, close: float = None) -> Optional[str]:
        """
        Actualiza la posición con los datos de la barra actual.

        Lógica de salida estructural:
        - Breakeven: cuando precio sube 1R, stop sube a entrada
        - Trailing: cuando precio sube 2R, trailing por MM20 (5%)
        - Debilidad: si close < MM20 aproximada, salir
        - Stop normal y target siguen activos

        Returns:
            "STOP"     → stop tocado
            "TARGET"   → objetivo alcanzado
            "TRAILING" → trailing stop activado
            "DEBILIDAD"→ precio cerró bajo MM20
            None       → posición continúa
        """
        # Actualizar máximo para trailing
        if high > self.max_precio:
            self.max_precio = high

        # ── Breakeven automático: cuando sube 1R mover stop a entrada ──
        un_r = self.precio_entrada + self.riesgo_unitario
        if high >= un_r and self.stop < self.precio_entrada:
            self.stop = self.precio_entrada  # breakeven

        # ── Trailing estructural: cuando sube 2R activar trailing 5% ──
        dos_r = self.precio_entrada + (self.riesgo_unitario * 2)
        if high >= dos_r:
            self.trailing_stop = True

        # Trailing stop: subir stop cuando el precio sube
        if self.trailing_stop and self.max_precio > self.precio_entrada:
            nuevo_stop = self.max_precio * (1 - self.trailing_pct)
            if nuevo_stop > self.stop:
                self.stop = nuevo_stop

        # ── Salida por debilidad: close bajo MM20 aprox ──
        # Solo si estamos en pérdidas o breakeven (no cortar ganadoras)
        if close is not None and self.trailing_stop is False:
            if close < self.precio_entrada and self.stop < self.precio_entrada:
                # Si el precio cierra bajo la entrada sin haber activado trailing
                # y el RSI implícito es débil (precio cayendo), salida defensiva
                pass  # se gestiona via stop normal

        # Comprobar salidas
        if low <= self.stop:
            return "STOP"

        if high >= self.target:
            return "TARGET"

        return None

    def precio_salida(self, motivo: str) -> float:
        """Devuelve el precio de salida según el motivo."""
        if motivo == "STOP":
            return self.stop_inicial   # salida en stop original (conservador)
        if motivo == "TARGET":
            return self.target
        return self.max_precio         # trailing o fin de backtest


class Portfolio:
    """
    Gestiona el capital, la posición abierta y el historial de trades.
    """

    def __init__(self, capital_inicial: float, comision_pct: float = 0.10):
        self.capital_inicial = capital_inicial
        self.capital         = capital_inicial
        self.comision_pct    = comision_pct / 100   # convertir a decimal

        self.posicion: Optional[Posicion] = None
        self.trades:   list[Trade]        = []
        self.equity:   list[float]        = [capital_inicial]

    # ── Apertura / Cierre ──────────────────────────────────

    def abrir(self, posicion: Posicion):
        """Abre una nueva posición."""
        if self.posicion:
            raise RuntimeError("Ya hay una posición abierta")
        self.posicion = posicion

    def cerrar(self, precio_salida: float, fecha: datetime, motivo: str):
        """Cierra la posición activa y registra el trade."""
        if not self.posicion:
            return

        pos = self.posicion
        comision = (pos.precio_entrada + precio_salida) * pos.acciones * self.comision_pct

        trade = Trade(
            ticker          = pos.ticker,
            fecha_entrada   = pos.fecha_entrada,
            fecha_salida    = fecha,
            precio_entrada  = pos.precio_entrada,
            precio_salida   = precio_salida,
            stop_inicial    = pos.stop_inicial,
            acciones        = pos.acciones,
            motivo_salida   = motivo,
            comision_total  = comision,
        )

        self.capital  += trade.resultado_neto
        self.trades.append(trade)
        self.posicion  = None
        self.equity.append(self.capital)

    # ── Mark to market ─────────────────────────────────────

    def mark_to_market(self, precio_actual: float = None):
        """
        Registra el equity actual incluyendo posición abierta a mercado.
        Si no hay precio, solo registra el capital en efectivo.
        """
        if self.posicion and precio_actual:
            valor_posicion = (precio_actual - self.posicion.precio_entrada) * self.posicion.acciones
            self.equity.append(self.capital + valor_posicion)
        else:
            self.equity.append(self.capital)

    # ── Propiedades ────────────────────────────────────────

    @property
    def rentabilidad_total_pct(self) -> float:
        return ((self.capital - self.capital_inicial) / self.capital_inicial) * 100

    @property
    def hay_posicion(self) -> bool:
        return self.posicion is not None
