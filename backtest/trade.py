class Trade:
    def __init__(self, entrada, stop, size, fecha_entrada):
        self.entrada = float(entrada)
        self.stop = float(stop)
        self.size = int(size)
        self.fecha_entrada = fecha_entrada

        self.salida = None
        self.fecha_salida = None
        self.motivo_salida = None

        self.riesgo = self.entrada - self.stop
        if self.riesgo <= 0:
            raise ValueError(
                f"Trade inválido: riesgo <= 0 (entrada={entrada}, stop={stop})"
            )

        self.resultado = 0.0
        self.R = 0.0
        self.abierto = True

    def cerrar(self, precio_salida, fecha, motivo="STOP"):
        if not self.abierto:
            return

        self.salida = float(precio_salida)
        self.fecha_salida = fecha
        self.motivo_salida = motivo

        self.resultado = (self.salida - self.entrada) * self.size
        self.R = (self.salida - self.entrada) / self.riesgo

        self.abierto = False
