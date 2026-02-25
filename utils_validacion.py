from datetime import datetime, timedelta

def validar_datos_ticker(ticker, precios, volumenes, fechas):
    errores = []
    advertencias = []

    if not (len(precios) == len(volumenes) == len(fechas)):
        errores.append("Desalineación de datos")
        return {"valido": False, "errores": errores, "advertencias": advertencias}

    if len(precios) < 50:
        errores.append("Historial insuficiente (<50 sesiones)")

    if fechas:
        ultima_fecha = fechas[-1]
        if datetime.now() - ultima_fecha > timedelta(days=7):
            advertencias.append(f"Datos desactualizados ({ultima_fecha.date()})")

    if any(p <= 0 for p in precios[-20:]):
        errores.append("Precios inválidos")

    if any(v == 0 for v in volumenes[-10:]):
        advertencias.append("Sesiones sin volumen")

    media_vol_20 = sum(volumenes[-20:]) / 20
    if any(v < media_vol_20 * 0.1 for v in volumenes[-5:]):
        advertencias.append("Volumen anormalmente bajo")

    for i in range(-10, -1):
        if precios[i-1] > 0:
            variacion = abs(precios[i] - precios[i-1]) / precios[i-1]
            if variacion > 0.20:
                advertencias.append(f"Gap extremo {variacion*100:.1f}%")

    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "advertencias": advertencias
    }

def construir_df_desde_listas(precios, volumenes, fechas):
    import pandas as pd

    if not precios or not volumenes:
        return None

    if fechas and len(fechas) == len(precios):
        index = pd.DatetimeIndex(fechas)
    else:
        index = range(len(precios))

    df = pd.DataFrame({
        "Open": precios,
        "High": precios,
        "Low": precios,
        "Close": precios,
        "Volume": volumenes
    }, index=index)

    return df
