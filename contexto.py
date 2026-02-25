def contexto_ibex(precio, mm200, mm200_prev):

    pendiente_mm200 = mm200 - mm200_prev

    if precio > mm200 and pendiente_mm200 > 0:
        return "RIESGO_ON"

    if precio < mm200 and pendiente_mm200 < 0:
        return "RIESGO_OFF"

    return "NEUTRAL"
