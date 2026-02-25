# nucleo/analisis_tecnico.py
"""
ANÁLISIS TÉCNICO AUTOMÁTICO MEJORADO
Incluye: RSI, MACD, Momentum, Estocástico, ADX (filtro de tendencia), Volumen
Similar a TradingView / Investing.com
"""
import pandas as pd
import numpy as np


def analizar_indicadores_tecnicos(df):
    """
    Analiza indicadores técnicos y genera señales
    MEJORADO con Estocástico, ADX y Volumen
    
    Returns:
        dict: {
            'señal': 'compra', 'venta', 'neutral',
            'puntuacion': float (-1.0 a 1.0),
            'detalles': {...}
        }
    """
    if df.empty or len(df) < 20:
        return None
    
    ultimo = df.iloc[-1]
    señales = []
    
    # =============================
    # FILTRO CRÍTICO 1: ADX
    # =============================
    peso_multiplicador = 1.0
    estado_tendencia = 'desconocido'
    
    if 'ADX' in df.columns and pd.notna(ultimo['ADX']):
        adx = ultimo['ADX']
        
        if adx < 20:
            # LATERAL - Reducir peso de TODAS las señales
            peso_multiplicador = 0.6
            estado_tendencia = 'lateral_debil'
        elif adx < 25:
            peso_multiplicador = 0.8
            estado_tendencia = 'tendencia_debil'
        elif adx < 40:
            peso_multiplicador = 1.0
            estado_tendencia = 'tendencia_normal'
        elif adx < 50:
            # TENDENCIA FUERTE - Aumentar peso
            peso_multiplicador = 1.3
            estado_tendencia = 'tendencia_fuerte'
        else:
            # TENDENCIA MUY FUERTE
            peso_multiplicador = 1.5
            estado_tendencia = 'tendencia_muy_fuerte'
    
    # =============================
    # FILTRO CRÍTICO 2: VOLUMEN
    # =============================
    if 'VOLUMEN_RATIO' in df.columns and pd.notna(ultimo['VOLUMEN_RATIO']):
        vol_ratio = ultimo['VOLUMEN_RATIO']
        
        if vol_ratio < 0.5:
            # Volumen muy bajo - Señales poco fiables
            peso_multiplicador *= 0.7
        elif vol_ratio > 1.5:
            # Volumen alto - Señales más fiables
            peso_multiplicador *= 1.2
    
    # =============================
    # 1. RSI (Relative Strength Index)
    # =============================
    if 'RSI' in df.columns and pd.notna(ultimo['RSI']):
        rsi = ultimo['RSI']
        
        if rsi < 30:
            # Sobreventa (umbral clásico)
            señales.append({'indicador': 'RSI', 'señal': 'compra', 'peso': 1.0 * peso_multiplicador})
        elif rsi > 70:
            # Sobrecompra (umbral clásico)
            señales.append({'indicador': 'RSI', 'señal': 'venta', 'peso': 1.0 * peso_multiplicador})
        elif 45 <= rsi <= 55:
            # Zona neutral equilibrada
            señales.append({'indicador': 'RSI', 'señal': 'neutral', 'peso': 0.5})
        else:
            # Zona normal (30-70, excepto 45-55)
            señales.append({'indicador': 'RSI', 'señal': 'neutral', 'peso': 0.3})
    
    # =============================
    # 2. MACD
    # =============================
    if 'MACD' in df.columns and 'MACD_SEÑAL' in df.columns:
        if pd.notna(ultimo['MACD']) and pd.notna(ultimo['MACD_SEÑAL']):
            macd = ultimo['MACD']
            señal_macd = ultimo['MACD_SEÑAL']
            
            # Detectar cruces
            if len(df) > 1:
                macd_prev = df.iloc[-2]['MACD']
                señal_prev = df.iloc[-2]['MACD_SEÑAL']
                
                # Cruce alcista (MACD cruza por encima de señal)
                if macd > señal_macd and macd_prev <= señal_prev:
                    señales.append({'indicador': 'MACD', 'señal': 'compra', 'peso': 1.3 * peso_multiplicador})
                # Cruce bajista (MACD cruza por debajo de señal)
                elif macd < señal_macd and macd_prev >= señal_prev:
                    señales.append({'indicador': 'MACD', 'señal': 'venta', 'peso': 1.3 * peso_multiplicador})
                # MACD por encima de señal (sin cruce)
                elif macd > señal_macd:
                    señales.append({'indicador': 'MACD', 'señal': 'compra', 'peso': 0.6 * peso_multiplicador})
                # MACD por debajo de señal (sin cruce)
                elif macd < señal_macd:
                    señales.append({'indicador': 'MACD', 'señal': 'venta', 'peso': 0.6 * peso_multiplicador})
                else:
                    señales.append({'indicador': 'MACD', 'señal': 'neutral', 'peso': 0.3})
    
    # =============================
    # 3. ESTOCÁSTICO ⭐ NUEVO
    # =============================
    if 'STOCH_K' in df.columns and 'STOCH_D' in df.columns:
        if pd.notna(ultimo['STOCH_K']) and pd.notna(ultimo['STOCH_D']) and len(df) > 1:
            k = ultimo['STOCH_K']
            d = ultimo['STOCH_D']
            k_prev = df.iloc[-2]['STOCH_K']
            d_prev = df.iloc[-2]['STOCH_D']
            
            # CRUCE ALCISTA en zona de sobreventa (<20)
            if k < 20 and k > d and k_prev <= d_prev:
                señales.append({'indicador': 'Estocástico', 'señal': 'compra', 'peso': 1.5 * peso_multiplicador})
            # CRUCE BAJISTA en zona de sobrecompra (>80)
            elif k > 80 and k < d and k_prev >= d_prev:
                señales.append({'indicador': 'Estocástico', 'señal': 'venta', 'peso': 1.5 * peso_multiplicador})
            # Sobreventa sin cruce
            elif k < 20:
                señales.append({'indicador': 'Estocástico', 'señal': 'compra', 'peso': 0.8 * peso_multiplicador})
            # Sobrecompra sin cruce
            elif k > 80:
                señales.append({'indicador': 'Estocástico', 'señal': 'venta', 'peso': 0.8 * peso_multiplicador})
            # Zona neutral
            else:
                señales.append({'indicador': 'Estocástico', 'señal': 'neutral', 'peso': 0.4})
    
    # =============================
    # 4. MOMENTUM
    # =============================
    if len(df) >= 10:
        precio_actual = ultimo['Close']
        precio_10_dias = df.iloc[-10]['Close']
        momentum = ((precio_actual - precio_10_dias) / precio_10_dias) * 100
        
        if momentum > 5:
            señales.append({'indicador': 'Momentum', 'señal': 'compra', 'peso': 0.9 * peso_multiplicador})
        elif momentum > 2:
            señales.append({'indicador': 'Momentum', 'señal': 'compra', 'peso': 0.5 * peso_multiplicador})
        elif momentum < -5:
            señales.append({'indicador': 'Momentum', 'señal': 'venta', 'peso': 0.9 * peso_multiplicador})
        elif momentum < -2:
            señales.append({'indicador': 'Momentum', 'señal': 'venta', 'peso': 0.5 * peso_multiplicador})
        else:
            señales.append({'indicador': 'Momentum', 'señal': 'neutral', 'peso': 0.4})
    
    # =============================
    # 5. DIRECCIÓN DE TENDENCIA (DI+ y DI-)
    # =============================
    if 'PLUS_DI' in df.columns and 'MINUS_DI' in df.columns:
        if pd.notna(ultimo['PLUS_DI']) and pd.notna(ultimo['MINUS_DI']):
            plus_di = ultimo['PLUS_DI']
            minus_di = ultimo['MINUS_DI']
            
            # DI+ muy por encima de DI-
            if plus_di > minus_di + 10:
                señales.append({'indicador': 'DI±', 'señal': 'compra', 'peso': 0.8 * peso_multiplicador})
            # DI- muy por encima de DI+
            elif minus_di > plus_di + 10:
                señales.append({'indicador': 'DI±', 'señal': 'venta', 'peso': 0.8 * peso_multiplicador})
            else:
                señales.append({'indicador': 'DI±', 'señal': 'neutral', 'peso': 0.3})
    
    # Calcular puntuación total
    if not señales:
        return None
    
    compras = sum(s['peso'] for s in señales if s['señal'] == 'compra')
    ventas = sum(s['peso'] for s in señales if s['señal'] == 'venta')
    neutrales = sum(s['peso'] for s in señales if s['señal'] == 'neutral')
    total = compras + ventas + neutrales
    
    # Normalizar a -1.0 (venta fuerte) a 1.0 (compra fuerte)
    if total == 0:
        puntuacion = 0
    else:
        puntuacion = (compras - ventas) / total
    
    # =============================
    # DESGLOSE DETALLADO POR SEÑAL
    # =============================
    desglose_compra = [s for s in señales if s['señal'] == 'compra']
    desglose_venta = [s for s in señales if s['señal'] == 'venta']
    desglose_neutral = [s for s in señales if s['señal'] == 'neutral']
    
    return {
        'señales': señales,
        'compras': round(compras),
        'ventas': round(ventas),
        'neutrales': round(neutrales),
        'puntuacion': round(puntuacion, 2),
        'estado_tendencia': estado_tendencia,
        'peso_multiplicador': round(peso_multiplicador, 2),
        'desglose_compra': desglose_compra,  # NUEVO
        'desglose_venta': desglose_venta,    # NUEVO
        'desglose_neutral': desglose_neutral # NUEVO
    }


def analizar_medias_moviles(df):
    """
    Analiza medias móviles y genera señales
    MEJORADO: Más estricto y realista
    
    Returns:
        dict: Similar a analizar_indicadores_tecnicos
    """
    if df.empty or len(df) < 20:
        return None
    
    ultimo = df.iloc[-1]
    precio_actual = ultimo['Close']
    señales = []
    
    # =============================
    # VERIFICAR QUE EXISTEN MEDIAS CALCULADAS
    # =============================
    medias_disponibles = []
    for periodo in [20, 50, 200]:
        col_name = f'MM{periodo}'
        # VERIFICAR que existe Y tiene valor válido en la última fila
        if col_name in df.columns and pd.notna(ultimo[col_name]) and ultimo[col_name] > 0:
            medias_disponibles.append(periodo)
    
    # Si NO hay ninguna media calculada, retornar None
    if not medias_disponibles:
        return None
    
    # =============================
    # ANALIZAR SOLO LAS MEDIAS DISPONIBLES (MÁS ESTRICTO)
    # =============================
    for periodo in medias_disponibles:
        col_name = f'MM{periodo}'
        mm = ultimo[col_name]
        
        # Calcular % de distancia
        distancia_pct = ((precio_actual - mm) / mm) * 100
        
        # =============================
        # LÓGICA MÁS ESTRICTA
        # =============================
        
        # Precio MUY por encima (sobreextendido)
        if distancia_pct > 10:
            # Sobreextendido = riesgo, no compra fuerte
            peso = 0.3
            señales.append({'indicador': f'MM{periodo}', 'señal': 'neutral', 'peso': peso})
        # Precio bastante por encima
        elif distancia_pct > 5:
            peso = 0.8 if periodo == 200 else 0.7
            señales.append({'indicador': f'MM{periodo}', 'señal': 'compra', 'peso': peso})
        # Precio moderadamente por encima (zona ideal)
        elif distancia_pct > 1:
            peso = 1.0 if periodo == 200 else 0.9
            señales.append({'indicador': f'MM{periodo}', 'señal': 'compra', 'peso': peso})
        # Muy cerca por encima (débil)
        elif distancia_pct > 0.2:
            peso = 0.5 if periodo == 200 else 0.4
            señales.append({'indicador': f'MM{periodo}', 'señal': 'compra', 'peso': peso})
        
        # Precio MUY por debajo (sobrevendido)
        elif distancia_pct < -10:
            # Muy sobrevendido = oportunidad de compra contraria
            peso = 0.5
            señales.append({'indicador': f'MM{periodo}', 'señal': 'compra', 'peso': peso})
        # Precio bastante por debajo
        elif distancia_pct < -5:
            peso = 1.0 if periodo == 200 else 0.9
            señales.append({'indicador': f'MM{periodo}', 'señal': 'venta', 'peso': peso})
        # Precio moderadamente por debajo
        elif distancia_pct < -1:
            peso = 1.0 if periodo == 200 else 0.9
            señales.append({'indicador': f'MM{periodo}', 'señal': 'venta', 'peso': peso})
        # Muy cerca por debajo (débil)
        elif distancia_pct < -0.2:
            peso = 0.5 if periodo == 200 else 0.4
            señales.append({'indicador': f'MM{periodo}', 'señal': 'venta', 'peso': peso})
        
        # Precio exactamente en la MM (±0.2%)
        else:
            señales.append({'indicador': f'MM{periodo}', 'señal': 'neutral', 'peso': 0.5})
    
    # =============================
    # BONUS: Analizar orden de medias (REDUCIDO EL PESO)
    # =============================
    if len(medias_disponibles) == 3:
        mm20 = ultimo.get('MM20')
        mm50 = ultimo.get('MM50')
        mm200 = ultimo.get('MM200')
        
        if all(pd.notna([mm20, mm50, mm200])):
            # Calcular separación entre medias
            sep_20_50 = ((mm20 - mm50) / mm50) * 100
            sep_50_200 = ((mm50 - mm200) / mm200) * 100
            
            # Alineación alcista perfecta (20 > 50 > 200) CON BUENA SEPARACIÓN
            if mm20 > mm50 > mm200 and sep_20_50 > 0.5 and sep_50_200 > 0.5:
                # Peso reducido de 1.5 a 1.0
                señales.append({'indicador': 'Alineación MM', 'señal': 'compra', 'peso': 1.0})
            # Alineación bajista perfecta (20 < 50 < 200) CON BUENA SEPARACIÓN
            elif mm20 < mm50 < mm200 and sep_20_50 < -0.5 and sep_50_200 < -0.5:
                señales.append({'indicador': 'Alineación MM', 'señal': 'venta', 'peso': 1.0})
            # Medias muy juntas (indecisión)
            elif abs(sep_20_50) < 0.5 or abs(sep_50_200) < 0.5:
                señales.append({'indicador': 'Alineación MM', 'señal': 'neutral', 'peso': 0.8})
    
    # Si después de todo no hay señales, retornar None
    if not señales:
        return None
    
    compras = sum(s['peso'] for s in señales if s['señal'] == 'compra')
    ventas = sum(s['peso'] for s in señales if s['señal'] == 'venta')
    neutrales = sum(s['peso'] for s in señales if s['señal'] == 'neutral')
    total = compras + ventas + neutrales
    
    puntuacion = (compras - ventas) / total if total > 0 else 0
    
    # =============================
    # DESGLOSE DETALLADO POR SEÑAL
    # =============================
    desglose_compra = [s for s in señales if s['señal'] == 'compra']
    desglose_venta = [s for s in señales if s['señal'] == 'venta']
    desglose_neutral = [s for s in señales if s['señal'] == 'neutral']
    
    return {
        'señales': señales,
        'compras': round(compras),
        'ventas': round(ventas),
        'neutrales': round(neutrales),
        'puntuacion': round(puntuacion, 2),
        'desglose_compra': desglose_compra,  # NUEVO
        'desglose_venta': desglose_venta,    # NUEVO
        'desglose_neutral': desglose_neutral # NUEVO
    }


def generar_resumen_tecnico(df, indicadores_lista=None):
    """
    Genera resumen técnico completo combinando indicadores y medias móviles
    MEJORADO con ADX como filtro crítico
    
    Args:
        df: DataFrame con datos OHLCV y indicadores calculados
        indicadores_lista: Lista de indicadores que el usuario activó
    
    Returns:
        dict: {
            'recomendacion': 'COMPRA FUERTE', 'COMPRA', 'NEUTRAL', 'VENTA', 'VENTA FUERTE',
            'puntuacion_global': float (-1.0 a 1.0),
            'indicadores': {...},
            'medias_moviles': {...},
            'info_adicional': {...}
        }
    """
    if indicadores_lista is None:
        indicadores_lista = []
    
    indicadores = analizar_indicadores_tecnicos(df)
    
    # =============================
    # ANALIZAR MEDIAS MÓVILES
    # Siempre analizar si existen columnas MM en el DataFrame
    # (la función ya valida internamente si existen)
    # =============================
    medias = analizar_medias_moviles(df)
    
    if not indicadores and not medias:
        return None
    
    # =============================
    # Combinar puntuaciones
    # =============================
    puntuacion_ind = indicadores['puntuacion'] if indicadores else 0
    puntuacion_mm = medias['puntuacion'] if medias else 0
    
    # Si el usuario NO marcó medias móviles, usar solo indicadores (100%)
    # Si marcó medias, ponderar 60% indicadores + 40% medias
    if medias is None:
        puntuacion_global = puntuacion_ind  # 100% indicadores
    else:
        puntuacion_global = (puntuacion_ind * 0.6) + (puntuacion_mm * 0.4)  # 60-40
    
    # =============================
    # AJUSTE POR ADX (CRÍTICO)
    # =============================
    estado_tendencia = indicadores.get('estado_tendencia', 'desconocido') if indicadores else 'desconocido'
    
    # Si ADX indica lateral débil, moderar la recomendación
    if estado_tendencia == 'lateral_debil':
        # Acercar hacia neutral
        puntuacion_global *= 0.6
    
    # Determinar recomendación
    if puntuacion_global >= 0.5:
        recomendacion = 'COMPRA FUERTE'
        color = 'compra-fuerte'
    elif puntuacion_global >= 0.2:
        recomendacion = 'COMPRA'
        color = 'compra'
    elif puntuacion_global <= -0.5:
        recomendacion = 'VENTA FUERTE'
        color = 'venta-fuerte'
    elif puntuacion_global <= -0.2:
        recomendacion = 'VENTA'
        color = 'venta'
    else:
        recomendacion = 'NEUTRAL'
        color = 'neutral'
    
    # =============================
    # INFORMACIÓN ADICIONAL
    # =============================
    info_adicional = {
        'estado_tendencia': estado_tendencia,
        'confianza': 'alta' if abs(puntuacion_global) > 0.5 else 'media' if abs(puntuacion_global) > 0.2 else 'baja'
    }
    
    # Añadir info de ADX si existe
    if 'ADX' in df.columns and pd.notna(df['ADX'].iloc[-1]):
        adx_valor = float(df['ADX'].iloc[-1])
        info_adicional['adx'] = round(adx_valor, 1)
        
        if adx_valor < 20:
            info_adicional['advertencia'] = 'Lateral débil - Evitar operar'
        elif adx_valor > 50:
            info_adicional['nota'] = 'Tendencia muy fuerte'
    
    # Añadir info de volumen si existe
    if 'VOLUMEN_RATIO' in df.columns and pd.notna(df['VOLUMEN_RATIO'].iloc[-1]):
        vol_ratio = float(df['VOLUMEN_RATIO'].iloc[-1])
        info_adicional['volumen_ratio'] = round(vol_ratio, 2)
        
        if vol_ratio < 0.5:
            info_adicional['advertencia_volumen'] = 'Volumen bajo - Señales poco fiables'
        elif vol_ratio > 1.5:
            info_adicional['nota_volumen'] = 'Volumen elevado - Movimiento confirmado'
    
    return {
        'recomendacion': recomendacion,
        'color': color,
        'puntuacion_global': round(puntuacion_global, 2),
        'indicadores': indicadores,
        'medias_moviles': medias,
        'info_adicional': info_adicional  # NUEVO
    }
