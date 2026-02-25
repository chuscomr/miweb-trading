class ExecutionModel:
    """
    Modelo de ejecución realista:
    - Comisiones
    - Slippage dependiente de volatilidad (ATR)
    - Sin hindsight
    """

    def __init__(
        self,
        comision_pct=0.0015,      # 0.15% por operación
        slippage_atr_pct=0.05,    # 5% del ATR
        slippage_min_pct=0.001   # 0.1% mínimo
    ):
        self.comision_pct = comision_pct
        self.slippage_atr_pct = slippage_atr_pct
        self.slippage_min_pct = slippage_min_pct

    # ─────────────────────────────
    # ENTRADA
    # ─────────────────────────────
    def ejecutar_entrada(self, precio_teorico, atr):
        """
        Simula una entrada realista.
        """
        slippage = max(
            precio_teorico * self.slippage_min_pct,
            atr * self.slippage_atr_pct
        )

        precio_real = precio_teorico + slippage
        comision = precio_real * self.comision_pct

        return precio_real + comision

    # ─────────────────────────────
    # SALIDA
    # ─────────────────────────────
    def ejecutar_salida(self, precio_teorico, atr):
        """
        Simula una salida realista.
        """
        slippage = max(
            precio_teorico * self.slippage_min_pct,
            atr * self.slippage_atr_pct
        )

        precio_real = precio_teorico - slippage
        comision = precio_real * self.comision_pct

        return precio_real - comision
