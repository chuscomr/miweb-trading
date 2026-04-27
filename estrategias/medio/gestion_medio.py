# ==========================================================
# GESTIÓN DE SALIDAS - SISTEMA MEDIO PLAZO
# Sistema de estados: INICIAL → PROTEGIDO → TRAILING
# ==========================================================

from estrategias.medio.config_medio import (
    ESTADO_INICIAL, ESTADO_PROTEGIDO, ESTADO_TRAILING,
    R_PARA_PROTEGER, R_PARA_TRAILING,
    PROTECCION_R_NEGATIVO, TRAILING_LOOKBACK, TRAILING_LOOKBACK_FINAL
)


class PosicionMedioPlazo:
    """
    Representa una posición abierta en medio plazo.
    Gestiona 3 estados: INICIAL → PROTEGIDO → TRAILING
    """

    def __init__(self, entrada, stop_inicial, fecha_entrada=None):
        self.entrada          = entrada
        self.stop_inicial     = stop_inicial
        self.stop_actual      = stop_inicial
        self.estado           = ESTADO_INICIAL
        self.riesgo_inicial   = entrada - stop_inicial
        self.fecha_entrada    = fecha_entrada
        self.semanas_en_posicion = 0
        self.historial_precios = []

    def actualizar(self, precio_actual, high=None, low=None):
        """
        Actualiza la posición con nueva semana de datos.
        Devuelve dict con: salir, motivo, stop_nuevo, estado_nuevo.
        """
        self.semanas_en_posicion += 1
        self.historial_precios.append(precio_actual)

        if self.riesgo_inicial <= 0:
            return {"salir": True, "motivo": "RIESGO_INVALIDO",
                    "stop_nuevo": self.stop_actual, "estado_nuevo": self.estado}

        R_actual = (precio_actual - self.entrada) / self.riesgo_inicial
        precio_check = low if low is not None else precio_actual

        # ── FASE 1: INICIAL ────────────────────────────────────
        if self.estado == ESTADO_INICIAL:
            if R_actual >= R_PARA_PROTEGER:
                nuevo_stop = self.entrada + (self.riesgo_inicial * PROTECCION_R_NEGATIVO)
                return {"salir": False, "motivo": "PROTECCION_ACTIVADA",
                        "stop_nuevo": nuevo_stop, "estado_nuevo": ESTADO_PROTEGIDO}
            if precio_check <= self.stop_actual:
                return {"salir": True, "motivo": "STOP_INICIAL",
                        "stop_nuevo": self.stop_actual, "estado_nuevo": self.estado}
            return {"salir": False, "motivo": None,
                    "stop_nuevo": self.stop_actual, "estado_nuevo": ESTADO_INICIAL}

        # ── FASE 2: PROTEGIDO ──────────────────────────────────
        if self.estado == ESTADO_PROTEGIDO:
            if R_actual >= R_PARA_TRAILING and len(self.historial_precios) >= TRAILING_LOOKBACK:
                trailing_stop = min(self.historial_precios[-TRAILING_LOOKBACK:])
                nuevo_stop = max(self.stop_actual, trailing_stop)
                return {"salir": False, "motivo": "TRAILING_ACTIVADO",
                        "stop_nuevo": nuevo_stop, "estado_nuevo": ESTADO_TRAILING}
            if precio_check <= self.stop_actual:
                return {"salir": True, "motivo": "STOP_PROTEGIDO",
                        "stop_nuevo": self.stop_actual, "estado_nuevo": self.estado}
            return {"salir": False, "motivo": None,
                    "stop_nuevo": self.stop_actual, "estado_nuevo": ESTADO_PROTEGIDO}

        # ── FASE 3: TRAILING ───────────────────────────────────
        if self.estado == ESTADO_TRAILING:
            lookback    = min(TRAILING_LOOKBACK_FINAL, len(self.historial_precios))
            trailing    = min(self.historial_precios[-lookback:])
            nuevo_stop  = max(self.stop_actual, trailing)
            if precio_check <= nuevo_stop:
                return {"salir": True, "motivo": "TRAILING_STOP",
                        "stop_nuevo": nuevo_stop, "estado_nuevo": self.estado}
            return {"salir": False, "motivo": None,
                    "stop_nuevo": nuevo_stop, "estado_nuevo": ESTADO_TRAILING}

        return {"salir": False, "motivo": None,
                "stop_nuevo": self.stop_actual, "estado_nuevo": self.estado}

    def aplicar_actualizacion(self, resultado):
        self.stop_actual = resultado["stop_nuevo"]
        self.estado      = resultado["estado_nuevo"]

    def calcular_R_actual(self, precio_actual):
        if self.riesgo_inicial <= 0:
            return 0
        return (precio_actual - self.entrada) / self.riesgo_inicial
