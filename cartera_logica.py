"""
cartera_logica.py
Lógica de cálculos y actualización de precios para el panel de cartera
"""

import yfinance as yf
from datetime import datetime


def obtener_precio_actual(ticker):
    """
    Obtiene el precio actual de un ticker desde yfinance
    """
    try:
        stock = yf.Ticker(ticker)
        precio = stock.fast_info.get('last_price')
        
        if precio is None or precio <= 0:
            # Intentar con history como fallback
            hist = stock.history(period='1d')
            if not hist.empty:
                precio = hist['Close'].iloc[-1]
        
        return round(float(precio), 2) if precio else None
        
    except Exception as e:
        print(f"❌ Error obteniendo precio de {ticker}: {e}")
        return None


def calcular_metricas_posicion(posicion, precio_actual=None):
    """
    Calcula todas las métricas de una posición
    
    Args:
        posicion (dict): Datos de la posición desde la BD
        precio_actual (float): Precio actual (si no se proporciona, se descarga)
    
    Returns:
        dict: Métricas calculadas
    """
    ticker = posicion['ticker']
    precio_entrada = posicion['precio_entrada']
    stop_loss = posicion['stop_loss']
    objetivo = posicion['objetivo']
    acciones = posicion['acciones']
    
    # Obtener precio actual si no se proporcionó
    if precio_actual is None:
        precio_actual = obtener_precio_actual(ticker)
    
    if precio_actual is None:
        return None
    
    # Cálculos básicos
    riesgo_por_accion = precio_entrada - stop_loss
    beneficio_objetivo = objetivo - precio_entrada
    
    # P&L actual
    pnl_por_accion = precio_actual - precio_entrada
    pnl_euros = pnl_por_accion * acciones
    pnl_porcentaje = (pnl_por_accion / precio_entrada) * 100
    
    # R alcanzado
    r_alcanzado = pnl_por_accion / riesgo_por_accion if riesgo_por_accion > 0 else 0
    
    # Distancias
    distancia_stop_porcentaje = ((precio_actual - stop_loss) / precio_actual) * 100
    distancia_objetivo_porcentaje = ((objetivo - precio_actual) / precio_actual) * 100
    
    # Progreso hacia objetivo (0-100%)
    if precio_actual >= objetivo:
        progreso = 100
    elif precio_actual <= precio_entrada:
        progreso = 0
    else:
        progreso = ((precio_actual - precio_entrada) / (objetivo - precio_entrada)) * 100
    
    # Capital invertido
    capital_invertido = precio_entrada * acciones
    
    # Determinar estado y alertas
    estado = determinar_estado(r_alcanzado, precio_actual, stop_loss, objetivo, precio_entrada, riesgo_por_accion)
    
    # Dirección del precio
    if pnl_euros > 0:
        direccion = "up"
        color_pnl = "green"
    elif pnl_euros < 0:
        direccion = "down"
        color_pnl = "red"
    else:
        direccion = "neutral"
        color_pnl = "gray"
    
    return {
        "ticker": ticker,
        "nombre": posicion.get('nombre', ticker),
        "precio_actual": precio_actual,
        "precio_entrada": precio_entrada,
        "stop_loss": stop_loss,
        "objetivo": objetivo,
        "acciones": acciones,
        
        "pnl_euros": pnl_euros,
        "pnl_porcentaje": pnl_porcentaje,
        "pnl_por_accion": pnl_por_accion,
        "r_alcanzado": r_alcanzado,
        
        "riesgo_por_accion": riesgo_por_accion,
        "capital_invertido": capital_invertido,
        
        "distancia_stop_pct": distancia_stop_porcentaje,
        "distancia_objetivo_pct": distancia_objetivo_porcentaje,
        "progreso": max(0, min(100, progreso)),
        
        "estado": estado,
        "direccion": direccion,
        "color_pnl": color_pnl,
        
        "setup_score": posicion.get('setup_score'),
        "contexto_ibex": posicion.get('contexto_ibex'),
        "fecha_entrada": posicion.get('fecha_entrada'),
        "id": posicion.get('id')
    }


def determinar_estado(r_alcanzado, precio_actual, stop_loss, objetivo, precio_entrada, riesgo_por_accion):
    """
    Determina el estado de la posición y genera alertas
    """
    # Calcular cercanía al stop (en % de la distancia total)
    distancia_total = precio_actual - stop_loss
    distancia_stop_relativa = distancia_total / precio_actual * 100
    
    if r_alcanzado >= 3.0:
        # Trailing stop del 5% desde precio actual
        nuevo_stop = precio_actual * 0.95
        return {
            "emoji": "🟢",
            "texto": "Excelente - Trailing activo",
            "clase": "success",
            "alerta": f"💡 ACCIÓN: Trailing stop 5% = {nuevo_stop:.2f}€"
        }
    elif r_alcanzado >= 2.0:
        # Asegurar +1R: nuevo stop = entrada + 1R
        nuevo_stop = precio_entrada + riesgo_por_accion
        return {
            "emoji": "🟡",
            "texto": "Alcanzó +2R",
            "clase": "warning",
            "alerta": f"⚠️ ACCIÓN: Asegurar +1R (mover stop a {nuevo_stop:.2f}€)"
        }
    elif r_alcanzado >= 1.0:
        # Breakeven: mover stop a precio de entrada
        return {
            "emoji": "🟡",
            "texto": "Alcanzó +1R",
            "clase": "warning",
            "alerta": f"⚠️ ACCIÓN: Mover stop a breakeven ({precio_entrada:.2f}€)"
        }
    elif r_alcanzado >= 0.5:
        return {
            "emoji": "🟢",
            "texto": "En posición - Vigilar +1R",
            "clase": "info",
            "alerta": None
        }
    elif r_alcanzado >= 0:
        return {
            "emoji": "⚪",
            "texto": "En posición",
            "clase": "neutral",
            "alerta": None
        }
    elif r_alcanzado >= -0.5:
        return {
            "emoji": "🟠",
            "texto": "Ligera pérdida",
            "clase": "warning-light",
            "alerta": None
        }
    elif distancia_stop_relativa < 2:  # Muy cerca del stop
        return {
            "emoji": "🔴",
            "texto": "ALERTA - Muy cerca del stop",
            "clase": "danger",
            "alerta": "🔴 VIGILAR: Posición cerca del stop loss"
        }
    else:
        return {
            "emoji": "🔴",
            "texto": "En pérdida",
            "clase": "danger-light",
            "alerta": None
        }


def calcular_resumen_cartera(posiciones_con_metricas):
    """
    Calcula el resumen global de la cartera
    """
    if not posiciones_con_metricas:
        return {
            "num_posiciones": 0,
            "capital_invertido": 0,
            "pnl_total": 0,
            "pnl_porcentaje": 0,
            "riesgo_total_pct": 0,
            "mejor_posicion": None,
            "peor_posicion": None
        }
    
    num_posiciones = len(posiciones_con_metricas)
    capital_invertido = sum(p['capital_invertido'] for p in posiciones_con_metricas)
    pnl_total = sum(p['pnl_euros'] for p in posiciones_con_metricas)
    pnl_porcentaje = (pnl_total / capital_invertido * 100) if capital_invertido > 0 else 0
    
    # Riesgo total (suma de todos los riesgos)
    riesgo_total = sum(p['riesgo_por_accion'] * p['acciones'] for p in posiciones_con_metricas)
    riesgo_total_pct = (riesgo_total / capital_invertido * 100) if capital_invertido > 0 else 0
    
    # Mejor y peor posición
    mejor = max(posiciones_con_metricas, key=lambda p: p['pnl_porcentaje'])
    peor = min(posiciones_con_metricas, key=lambda p: p['pnl_porcentaje'])
    
    return {
        "num_posiciones": num_posiciones,
        "capital_invertido": capital_invertido,
        "pnl_total": pnl_total,
        "pnl_porcentaje": pnl_porcentaje,
        "riesgo_total_pct": riesgo_total_pct,
        "mejor_posicion": f"{mejor['ticker']} ({mejor['pnl_porcentaje']:+.1f}%)",
        "peor_posicion": f"{peor['ticker']} ({peor['pnl_porcentaje']:+.1f}%)"
    }


def validar_nueva_posicion(ticker, precio_entrada, stop_loss, objetivo, acciones):
    """
    Valida que los datos de una nueva posición sean correctos
    """
    errores = []
    
    if not ticker or len(ticker.strip()) == 0:
        errores.append("El ticker es obligatorio")
    
    if precio_entrada <= 0:
        errores.append("El precio de entrada debe ser mayor que 0")
    
    if stop_loss <= 0:
        errores.append("El stop loss debe ser mayor que 0")
    
    if stop_loss >= precio_entrada:
        errores.append("El stop loss debe ser menor que el precio de entrada")
    
    if objetivo <= precio_entrada:
        errores.append("El objetivo debe ser mayor que el precio de entrada")
    
    if acciones <= 0:
        errores.append("El número de acciones debe ser mayor que 0")
    
    # Validar R/R mínimo
    riesgo = precio_entrada - stop_loss
    beneficio = objetivo - precio_entrada
    rr = beneficio / riesgo if riesgo > 0 else 0
    
    if rr < 1.5:
        errores.append(f"R/R muy bajo ({rr:.2f}). Debería ser al menos 2.0")
    
    return errores


def validar_edicion_posicion(ticker, precio_entrada, stop_loss, objetivo, acciones):
    """
    Valida que los datos de una posición editada sean correctos.
    Permite stop >= entrada (para breakeven o asegurar ganancias)
    """
    errores = []
    
    if not ticker or len(ticker.strip()) == 0:
        errores.append("El ticker es obligatorio")
    
    if precio_entrada <= 0:
        errores.append("El precio de entrada debe ser mayor que 0")
    
    if stop_loss <= 0:
        errores.append("El stop loss debe ser mayor que 0")
    
    # ✅ PERMITIR stop >= entrada (breakeven o asegurar ganancias)
    # Solo validar que el objetivo sea mayor que la entrada
    if objetivo <= precio_entrada:
        errores.append("El objetivo debe ser mayor que el precio de entrada")
    
    if acciones <= 0:
        errores.append("El número de acciones debe ser mayor que 0")
    
    # Si stop < entrada, validar R/R como antes
    if stop_loss < precio_entrada:
        riesgo = precio_entrada - stop_loss
        beneficio = objetivo - precio_entrada
        rr = beneficio / riesgo if riesgo > 0 else 0
        
        if rr < 1.5:
            errores.append(f"R/R muy bajo ({rr:.2f}). Debería ser al menos 2.0")
    
    return errores


def calcular_niveles_gestion_r(precio_entrada, stop_original, objetivo):
    """
    Calcula los niveles de gestión por R (+1R, +2R, +3R, etc.)
    basándose en el stop ORIGINAL, no en el stop actual
    """
    riesgo = precio_entrada - stop_original
    
    if riesgo <= 0:
        return None
    
    return {
        "stop_original": stop_original,
        "riesgo_r": riesgo,
        "nivel_1r": round(precio_entrada + (riesgo * 1), 2),  # +1R = Breakeven
        "nivel_2r": round(precio_entrada + (riesgo * 2), 2),  # +2R = Asegurar +1R
        "nivel_3r": round(precio_entrada + (riesgo * 3), 2),  # +3R = Trailing
        "nivel_4r": round(precio_entrada + (riesgo * 4), 2),  # +4R
        "nivel_5r": round(precio_entrada + (riesgo * 5), 2),  # +5R
    }
