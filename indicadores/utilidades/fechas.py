# indicadores/utilidades/fechas.py
from datetime import datetime, timedelta
import pandas as pd

def formatear_fechas_para_json(fechas):
    """Convierte fechas a string ISO para JSON"""
    if isinstance(fechas, pd.DatetimeIndex):
        return [f.strftime('%Y-%m-%dT%H:%M:%S') for f in fechas]
    elif isinstance(fechas, list):
        return [f.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(f, (datetime, pd.Timestamp)) else f for f in fechas]
    else:
        return fechas

def obtener_rango_fechas(periodo):
    """Obtiene fecha inicio y fin según período"""
    fin = datetime.now()
    
    if periodo == "1y":
        inicio = fin - timedelta(days=365)
    elif periodo == "6m":
        inicio = fin - timedelta(days=180)
    elif periodo == "3m":
        inicio = fin - timedelta(days=90)
    elif periodo == "1m":
        inicio = fin - timedelta(days=30)
    else:
        inicio = fin - timedelta(days=365)
    
    return inicio, fin