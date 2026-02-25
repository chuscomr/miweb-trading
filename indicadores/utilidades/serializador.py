# indicadores/utilidades/serializador.py
"""
SERIALIZADOR DE DATOS PARA JSON
Convierte DataFrames y estructuras de Python a formato JSON válido
"""
import pandas as pd
import numpy as np
from datetime import datetime

def preparar_para_json(df):
    """
    Convierte DataFrame a formato JSON válido
    
    Args:
        df: DataFrame con datos OHLCV e indicadores
        
    Returns:
        list: Lista de diccionarios con los datos serializados
    """
    if df.empty:
        return []
    
    registros = []
    for idx, fila in df.iterrows():
        registro = {}
        for columna, valor in fila.items():
            # Manejar valores None/NaN
            if pd.isna(valor) or valor is None:
                registro[columna] = None
            # Manejar fechas
            elif isinstance(valor, (datetime, pd.Timestamp)):
                registro[columna] = valor.strftime('%Y-%m-%dT%H:%M:%S')
            # Manejar números numpy
            elif isinstance(valor, (np.integer, np.floating)):
                # Convertir a float nativo de Python
                registro[columna] = float(round(valor, 4))
            # Manejar infinitos
            elif isinstance(valor, float) and (np.isinf(valor) or np.isnan(valor)):
                registro[columna] = None
            else:
                registro[columna] = valor
        registros.append(registro)
    
    return registros


def formatear_niveles_sr(niveles):
    """
    Formatea niveles de soporte/resistencia para JSON
    
    Args:
        niveles: Lista de diccionarios con información de niveles
        
    Returns:
        list: Lista de niveles formateados para JSON
    """
    if not niveles:
        return []
    
    formateados = []
    for nivel in niveles:
        nivel_json = {
            'precio': round(float(nivel['precio']), 4),
            'fuerza': float(nivel.get('fuerza', 1)),
            'toques': int(nivel.get('toques', 1))
        }
        
        # Distancia porcentual al precio actual (muy útil para trading)
        if 'distancia_pct' in nivel:
            nivel_json['distancia_pct'] = float(nivel['distancia_pct'])
        
        # Solo añadir fecha si existe y es válida
        if 'fecha' in nivel and nivel['fecha'] is not None:
            if isinstance(nivel['fecha'], (datetime, pd.Timestamp)):
                nivel_json['fecha'] = nivel['fecha'].strftime('%Y-%m-%d')
            else:
                nivel_json['fecha'] = str(nivel['fecha'])
        
        # Campo alternativo por si existe
        if 'fecha_mas_reciente' in nivel and nivel['fecha_mas_reciente'] is not None:
            if isinstance(nivel['fecha_mas_reciente'], (datetime, pd.Timestamp)):
                nivel_json['fecha'] = nivel['fecha_mas_reciente'].strftime('%Y-%m-%d')
        
        # Días desde hoy (útil para saber si es nivel reciente)
        if 'dias_desde_hoy' in nivel:
            nivel_json['dias_desde_hoy'] = int(nivel['dias_desde_hoy'])
        
        formateados.append(nivel_json)
    
    return formateados


def serializar_patron_vela(patron):
    """
    Serializa un patrón de vela japonesa
    
    Args:
        patron: Diccionario con información del patrón
        
    Returns:
        dict: Patrón serializado
    """
    return {
        'nombre': str(patron.get('nombre', 'Desconocido')),
        'tipo': str(patron.get('tipo', 'neutral')),  # alcista, bajista, neutral
        'confianza': float(patron.get('confianza', 0.5)),
        'fecha': patron['fecha'].strftime('%Y-%m-%d') if 'fecha' in patron else None,
        'descripcion': str(patron.get('descripcion', ''))
    }


def serializar_patrones(patrones):
    """
    Serializa patrones de velas japonesas para JSON
    
    Args:
        patrones: Lista de diccionarios con patrones detectados
        
    Returns:
        list: Lista de patrones formateados
    """
    if not patrones:
        return []
    
    formateados = []
    for patron in patrones:
        patron_json = {
            'nombre': str(patron.get('nombre', 'Desconocido')),
            'tipo': str(patron.get('tipo', 'neutral')),  # alcista, bajista, neutral
            'confianza': round(float(patron.get('confianza', 0.5)), 2),
            'descripcion': str(patron.get('descripcion', '')),
            'precio': round(float(patron.get('precio', 0)), 2)
        }
        
        # Añadir fecha si existe
        if 'fecha' in patron and patron['fecha'] is not None:
            if isinstance(patron['fecha'], (datetime, pd.Timestamp)):
                patron_json['fecha'] = patron['fecha'].strftime('%Y-%m-%d')
            else:
                patron_json['fecha'] = str(patron['fecha'])
        
        # Añadir índice si existe (útil para ubicar en el gráfico)
        if 'indice' in patron:
            patron_json['indice'] = int(patron['indice'])
        
        formateados.append(patron_json)
    
    return formateados


def validar_datos_json(datos):
    """
    Valida que los datos sean serializables a JSON
    
    Args:
        datos: Estructura de datos a validar
        
    Returns:
        bool: True si es válido, False si no
    """
    try:
        import json
        json.dumps(datos)
        return True
    except (TypeError, ValueError) as e:
        print(f"Error de validación JSON: {e}")
        return False


def formatear_patrones(patrones):
    """
    Formatea patrones de velas japonesas para JSON
    
    Args:
        patrones: Lista de diccionarios con información de patrones
        
    Returns:
        list: Lista de patrones formateados para JSON
    """
    if not patrones:
        return []
    
    formateados = []
    for patron in patrones:
        patron_json = {
            'nombre': str(patron.get('nombre', 'Desconocido')),
            'tipo': str(patron.get('tipo', 'neutral')),  # alcista, bajista, neutral
            'confianza': float(patron.get('confianza', 0.5)),
            'descripcion': str(patron.get('descripcion', '')),
            'precio': float(patron.get('precio', 0))
        }
        
        # Fecha
        if 'fecha' in patron and patron['fecha'] is not None:
            if isinstance(patron['fecha'], (datetime, pd.Timestamp)):
                patron_json['fecha'] = patron['fecha'].strftime('%Y-%m-%d')
            else:
                patron_json['fecha'] = str(patron['fecha'])
        
        # Index (para referencias)
        if 'index' in patron:
            patron_json['index'] = int(patron['index'])
        
        formateados.append(patron_json)
    
    return formateados
