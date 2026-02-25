# nucleo/calculos.py
import pandas as pd
import numpy as np
from .patrones_velas import detectar_patrones_velas
from .analisis_tecnico import generar_resumen_tecnico

def calcular_rsi(df, periodo=14):
    """Calcula el RSI (Relative Strength Index)"""
    delta = df['Close'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = ganancia / perdida
    rsi = 100 - (100 / (1 + rs))
    return rsi.round(2)

def calcular_macd(df, rapido=12, lento=26, señal=9):
    """Calcula MACD, línea de señal e histograma"""
    exp_rapida = df['Close'].ewm(span=rapido, adjust=False).mean()
    exp_lenta = df['Close'].ewm(span=lento, adjust=False).mean()
    macd = exp_rapida - exp_lenta
    linea_señal = macd.ewm(span=señal, adjust=False).mean()
    histograma = macd - linea_señal
    
    return {
        'MACD': macd.round(4),
        'SEÑAL': linea_señal.round(4),
        'HISTOGRAMA': histograma.round(4)
    }

def calcular_bandas_bollinger(df, periodo=20, desviaciones=2):
    """Calcula las Bandas de Bollinger"""
    media = df['Close'].rolling(window=periodo).mean()
    desviacion = df['Close'].rolling(window=periodo).std()
    
    banda_superior = media + (desviacion * desviaciones)
    banda_inferior = media - (desviacion * desviaciones)
    ancho_banda = ((banda_superior - banda_inferior) / media) * 100
    
    return {
        'MEDIA': media.round(4),
        'SUPERIOR': banda_superior.round(4),
        'INFERIOR': banda_inferior.round(4),
        'ANCHO': ancho_banda.round(2)
    }

def calcular_medias_moviles(df, periodos=[20, 50, 200]):
    """Calcula múltiples medias móviles"""
    resultados = {}
    for periodo in periodos:
        nombre = f"MM{periodo}"
        resultados[nombre] = df['Close'].rolling(window=periodo).mean().round(4)
    return resultados


# ========================================
# NUEVOS INDICADORES CRÍTICOS - FASE 2
# ========================================

def calcular_cci(df, periodo=20):
    """
    Calcula el Commodity Channel Index (CCI)
    
    CCI detecta ciclos y condiciones extremas. Es menos propenso a falsos
    positivos que RSI en tendencias fuertes.
    
    Señales:
    - CCI > +100: Sobrecompra
    - CCI < -100: Sobreventa
    - CCI entre -100 y +100: Zona normal
    
    Args:
        df: DataFrame con OHLC
        periodo: Ventana de cálculo (default 20)
    
    Returns:
        Series: CCI values
    """
    # Precio típico (TP) = (High + Low + Close) / 3
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    
    # Media móvil simple del TP
    sma_tp = tp.rolling(window=periodo).mean()
    
    # Desviación media
    mad = tp.rolling(window=periodo).apply(lambda x: abs(x - x.mean()).mean())
    
    # CCI = (TP - SMA(TP)) / (0.015 × MAD)
    cci = (tp - sma_tp) / (0.015 * mad)
    
    return cci.round(2)


def calcular_bollinger_percent_b(df):
    """
    Calcula el %B de Bollinger Bands
    
    %B indica dónde está el precio dentro de las bandas:
    - %B > 1.0: Precio por encima de banda superior
    - %B = 0.5: Precio en la media
    - %B < 0.0: Precio por debajo de banda inferior
    
    Args:
        df: DataFrame que ya debe tener BB_SUPERIOR y BB_INFERIOR
    
    Returns:
        Series: %B values
    """
    if 'BB_SUPERIOR' not in df.columns or 'BB_INFERIOR' not in df.columns:
        return pd.Series([np.nan] * len(df), index=df.index)
    
    # %B = (Precio - BB_Inferior) / (BB_Superior - BB_Inferior)
    percent_b = (df['Close'] - df['BB_INFERIOR']) / (df['BB_SUPERIOR'] - df['BB_INFERIOR'])
    
    return percent_b.round(3)


def calcular_williams_r(df, periodo=14):
    """
    Calcula Williams %R
    
    Similar al Estocástico pero más sensible. Mide el nivel del cierre
    respecto al rango high-low del periodo.
    
    Señales:
    - %R > -20: Sobrecompra
    - %R < -80: Sobreventa
    
    Args:
        df: DataFrame con OHLC
        periodo: Ventana de cálculo (default 14)
    
    Returns:
        Series: Williams %R values (negativos, de 0 a -100)
    """
    # Máximo más alto
    highest_high = df['High'].rolling(window=periodo).max()
    
    # Mínimo más bajo
    lowest_low = df['Low'].rolling(window=periodo).min()
    
    # Williams %R = -100 × (Highest High - Close) / (Highest High - Lowest Low)
    williams_r = -100 * ((highest_high - df['Close']) / (highest_high - lowest_low))
    
    return williams_r.round(2)


# ========================================
# NUEVOS INDICADORES CRÍTICOS
# ========================================

def calcular_estocastico(df, periodo=14, suavizado=3):
    """
    Calcula el oscilador estocástico LENTO (Slow Stochastic)
    
    El estocástico lento es más suave y fiable para swing trading,
    generando menos señales falsas que el rápido.
    
    Args:
        df: DataFrame con OHLC
        periodo: Ventana para calcular máximo/mínimo (default 14)
        suavizado: Periodos para suavizar %K y %D (default 3)
    
    Returns:
        dict: {'K': Series, 'D': Series}
    """
    # Mínimo más bajo en el periodo
    low_min = df['Low'].rolling(window=periodo).min()
    
    # Máximo más alto en el periodo
    high_max = df['High'].rolling(window=periodo).max()
    
    # %K RÁPIDO (raw stochastic)
    # Fórmula: 100 * (Close - Low14) / (High14 - Low14)
    k_rapido = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    
    # %K LENTO - Primera suavización (SMA de %K rápido)
    k_lento = k_rapido.rolling(window=suavizado).mean()
    
    # %D LENTO - Segunda suavización (SMA de %K lento)
    d_lento = k_lento.rolling(window=suavizado).mean()
    
    return {
        'K': k_lento.round(2),
        'D': d_lento.round(2)
    }


def calcular_adx(df, periodo=14):
    """
    Calcula el Average Directional Index (ADX)
    
    ⭐ EL INDICADOR MÁS IMPORTANTE PARA TRADING ⭐
    
    ADX mide la FUERZA de la tendencia, no la dirección.
    - ADX > 25: Tendencia fuerte → OPERAR
    - ADX < 20: Lateral débil → NO OPERAR
    - ADX > 50: Tendencia muy fuerte
    
    Args:
        df: DataFrame con OHLCV
        periodo: Ventana de cálculo (default 14)
    
    Returns:
        dict: {'ADX': Series, 'PLUS_DI': Series, 'MINUS_DI': Series}
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # ===========================
    # 1. TRUE RANGE (TR)
    # ===========================
    tr1 = high - low  # Rango actual
    tr2 = abs(high - close.shift())  # High menos cierre anterior
    tr3 = abs(low - close.shift())  # Low menos cierre anterior
    
    # El True Range es el máximo de los 3
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periodo).mean()
    
    # ===========================
    # 2. DIRECTIONAL MOVEMENT
    # ===========================
    up_move = high - high.shift()  # Movimiento alcista
    down_move = low.shift() - low  # Movimiento bajista
    
    # +DM: Solo cuando up_move > down_move Y up_move > 0
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    
    # -DM: Solo cuando down_move > up_move Y down_move > 0
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Suavizar con media móvil
    plus_dm = pd.Series(plus_dm, index=df.index).rolling(window=periodo).mean()
    minus_dm = pd.Series(minus_dm, index=df.index).rolling(window=periodo).mean()
    
    # ===========================
    # 3. DIRECTIONAL INDICATORS
    # ===========================
    plus_di = 100 * (plus_dm / atr)
    minus_di = 100 * (minus_dm / atr)
    
    # ===========================
    # 4. ADX (Average Directional Index)
    # ===========================
    # DX = diferencia absoluta entre +DI y -DI
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # ADX = media móvil de DX
    adx = dx.rolling(window=periodo).mean()
    
    return {
        'ADX': adx.round(2),
        'PLUS_DI': plus_di.round(2),
        'MINUS_DI': minus_di.round(2)
    }


def analizar_volumen(df, periodo=20):
    """
    Analiza el volumen relativo
    
    "Volume precedes price" - El volumen debe confirmar el movimiento
    
    Args:
        df: DataFrame con Volume
        periodo: Ventana para calcular volumen medio
    
    Returns:
        dict: {'ratio': float, 'señal': str, 'volumen_actual': float, 'volumen_medio': float}
    """
    if 'Volume' not in df.columns or df['Volume'].isna().all():
        return None
    
    # Volumen medio de los últimos N días
    volumen_medio = df['Volume'].rolling(window=periodo).mean()
    
    # Volumen actual
    volumen_actual = df['Volume'].iloc[-1]
    volumen_medio_actual = volumen_medio.iloc[-1]
    
    if pd.isna(volumen_medio_actual) or volumen_medio_actual == 0:
        return None
    
    # Ratio: cuántas veces más que el promedio
    ratio = volumen_actual / volumen_medio_actual
    
    # Clasificar
    if ratio > 2.0:
        señal = 'muy_alto'
        descripcion = 'Volumen excepcional (2x+ promedio)'
    elif ratio > 1.5:
        señal = 'alto'
        descripcion = 'Volumen alto (1.5x+ promedio)'
    elif ratio > 1.2:
        señal = 'normal_alto'
        descripcion = 'Volumen ligeramente elevado'
    elif ratio < 0.5:
        señal = 'muy_bajo'
        descripcion = 'Volumen muy bajo (sospechoso)'
    elif ratio < 0.8:
        señal = 'bajo'
        descripcion = 'Volumen bajo'
    else:
        señal = 'normal'
        descripcion = 'Volumen normal'
    
    return {
        'ratio': float(round(ratio, 2)),
        'señal': señal,
        'descripcion': descripcion,
        'volumen_actual': int(volumen_actual),
        'volumen_medio': int(volumen_medio_actual)
    }



def calcular_obv(df):
    """
    Calcula el On Balance Volume (OBV)
    
    OBV es un indicador de volumen acumulativo que relaciona volumen con precio:
    - Si precio sube → Suma el volumen
    - Si precio baja → Resta el volumen
    - Si precio igual → OBV no cambia
    
    Uso principal:
    - Confirmar tendencias (OBV y precio en misma dirección)
    - Detectar divergencias (OBV y precio en direcciones opuestas)
    - Anticipar cambios de tendencia
    
    Args:
        df: DataFrame con Close y Volume
    
    Returns:
        Series: Valores de OBV
    
    Ejemplo:
        Día 1: Precio=100, Vol=1000 → OBV=1000
        Día 2: Precio=102, Vol=1500 → OBV=2500 (subió → suma)
        Día 3: Precio=101, Vol=1200 → OBV=1300 (bajó → resta)
    """
    if 'Volume' not in df.columns or df.empty:
        return pd.Series(index=df.index, dtype=float)
    
    # Calcular cambio de precio
    precio_cambio = df['Close'].diff()
    
    # Inicializar OBV
    obv = pd.Series(index=df.index, dtype=float)
    obv.iloc[0] = df['Volume'].iloc[0]  # Primer valor = volumen del primer día
    
    # Calcular OBV acumulativo
    for i in range(1, len(df)):
        if precio_cambio.iloc[i] > 0:
            # Precio subió → Suma volumen
            obv.iloc[i] = obv.iloc[i-1] + df['Volume'].iloc[i]
        elif precio_cambio.iloc[i] < 0:
            # Precio bajó → Resta volumen
            obv.iloc[i] = obv.iloc[i-1] - df['Volume'].iloc[i]
        else:
            # Precio igual → OBV no cambia
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def detectar_divergencias_obv(df, lookback=20, min_distancia=5):
    """
    Detecta divergencias entre precio y OBV
    
    Divergencia Alcista (bullish):
    - Precio hace mínimos más bajos
    - OBV hace mínimos más altos
    - Señal: Posible cambio alcista
    
    Divergencia Bajista (bearish):
    - Precio hace máximos más altos
    - OBV hace máximos más bajos
    - Señal: Posible cambio bajista
    
    Args:
        df: DataFrame con Close y OBV
        lookback: Ventana de búsqueda de divergencias
        min_distancia: Distancia mínima entre picos/valles
    
    Returns:
        list: Lista de divergencias encontradas
    """
    if 'OBV' not in df.columns or len(df) < lookback:
        return []
    
    divergencias = []
    
    # Buscar en las últimas 'lookback' velas
    ventana = df.tail(lookback).copy()
    
    # Encontrar picos y valles en precio
    precio = ventana['Close']
    obv = ventana['OBV']
    
    # Picos de precio (máximos locales)
    picos_precio_idx = []
    for i in range(min_distancia, len(ventana) - min_distancia):
        if (precio.iloc[i] > precio.iloc[i-1] and 
            precio.iloc[i] > precio.iloc[i+1]):
            picos_precio_idx.append(i)
    
    # Valles de precio (mínimos locales)
    valles_precio_idx = []
    for i in range(min_distancia, len(ventana) - min_distancia):
        if (precio.iloc[i] < precio.iloc[i-1] and 
            precio.iloc[i] < precio.iloc[i+1]):
            valles_precio_idx.append(i)
    
    # ========================================
    # DIVERGENCIA BAJISTA (Bearish)
    # ========================================
    # Buscar 2 picos de precio consecutivos donde:
    # - Precio2 > Precio1 (máximo más alto)
    # - OBV2 < OBV1 (OBV más bajo)
    
    if len(picos_precio_idx) >= 2:
        for i in range(len(picos_precio_idx) - 1):
            idx1 = picos_precio_idx[i]
            idx2 = picos_precio_idx[i + 1]
            
            if idx2 - idx1 >= min_distancia:
                precio1 = precio.iloc[idx1]
                precio2 = precio.iloc[idx2]
                obv1 = obv.iloc[idx1]
                obv2 = obv.iloc[idx2]
                
                # Divergencia bajista
                if precio2 > precio1 and obv2 < obv1:
                    divergencias.append({
                        'tipo': 'bajista',
                        'indicador': 'OBV',
                        'fecha1': ventana.index[idx1],
                        'fecha2': ventana.index[idx2],
                        'precio1': float(precio1),
                        'precio2': float(precio2),
                        'obv1': float(obv1),
                        'obv2': float(obv2),
                        'fuerza': 'media'
                    })
    
    # ========================================
    # DIVERGENCIA ALCISTA (Bullish)
    # ========================================
    # Buscar 2 valles de precio consecutivos donde:
    # - Precio2 < Precio1 (mínimo más bajo)
    # - OBV2 > OBV1 (OBV más alto)
    
    if len(valles_precio_idx) >= 2:
        for i in range(len(valles_precio_idx) - 1):
            idx1 = valles_precio_idx[i]
            idx2 = valles_precio_idx[i + 1]
            
            if idx2 - idx1 >= min_distancia:
                precio1 = precio.iloc[idx1]
                precio2 = precio.iloc[idx2]
                obv1 = obv.iloc[idx1]
                obv2 = obv.iloc[idx2]
                
                # Divergencia alcista
                if precio2 < precio1 and obv2 > obv1:
                    divergencias.append({
                        'tipo': 'alcista',
                        'indicador': 'OBV',
                        'fecha1': ventana.index[idx1],
                        'fecha2': ventana.index[idx2],
                        'precio1': float(precio1),
                        'precio2': float(precio2),
                        'obv1': float(obv1),
                        'obv2': float(obv2),
                        'fuerza': 'media'
                    })
    
    return divergencias


def calcular_soportes_resistencias(df, ventana=10, umbral_agrupacion=0.02, max_niveles=8):
    """
    Calcula soportes y resistencias de forma inteligente
    
    MEJORAS V2:
    - Busca máximos/mínimos en TODA la serie de datos (no solo ventanas pequeñas)
    - Detecta zonas de rechazo históricas (múltiples toques)
    - Filtra soportes DEBAJO del precio actual
    - Filtra resistencias ENCIMA del precio actual
    - Prioriza niveles más recientes y con más toques
    - Limita cantidad de niveles mostrados
    
    Args:
        df: DataFrame con OHLCV
        ventana: Ventana para detectar máximos/mínimos locales (default 10)
        umbral_agrupacion: % para agrupar niveles cercanos (default 0.02 = 2%)
        max_niveles: Máximo de niveles a devolver por tipo (default 8)
    
    Returns:
        tuple: (soportes, resistencias)
    """
    from collections import defaultdict
    import numpy as np
    
    # Obtener precio actual (último cierre)
    precio_actual = float(df['Close'].iloc[-1])
    
    # =====================================================
    # PASO 1: ENCONTRAR MÁXIMOS Y MÍNIMOS LOCALES
    # =====================================================
    # Analizamos TODO el dataset para no perder niveles históricos importantes
    
    maximos = []
    minimos = []
    
    # Asegurarnos que tenemos suficientes datos
    if len(df) < ventana * 2:
        ventana = max(3, len(df) // 4)
    
    # Buscar en TODA la serie temporal
    for i in range(ventana, len(df) - ventana):
        precio_high = df['High'].iloc[i]
        precio_low = df['Low'].iloc[i]
        
        # Máximo local: el high es el más alto en su ventana
        ventana_highs = df['High'].iloc[i-ventana:i+ventana+1]
        if precio_high == ventana_highs.max():
            maximos.append({
                'precio': float(precio_high),
                'fecha': df.index[i],
                'volumen': float(df['Volume'].iloc[i]) if 'Volume' in df else 0,
                'dias_desde_hoy': (df.index[-1] - df.index[i]).days
            })
        
        # Mínimo local: el low es el más bajo en su ventana
        ventana_lows = df['Low'].iloc[i-ventana:i+ventana+1]
        if precio_low == ventana_lows.min():
            minimos.append({
                'precio': float(precio_low),
                'fecha': df.index[i],
                'volumen': float(df['Volume'].iloc[i]) if 'Volume' in df else 0,
                'dias_desde_hoy': (df.index[-1] - df.index[i]).days
            })
    
    # =====================================================
    # PASO 2: AGRUPAR NIVELES CERCANOS
    # =====================================================
    def agrupar_niveles(niveles, umbral):
        if not niveles:
            return []
        
        # Ordenar por precio
        niveles_ordenados = sorted(niveles, key=lambda x: x['precio'])
        grupos = []
        grupo_actual = [niveles_ordenados[0]]
        
        for nivel in niveles_ordenados[1:]:
            # Si está cerca del último del grupo (dentro del umbral), añadir al grupo
            if abs(nivel['precio'] - grupo_actual[-1]['precio']) / grupo_actual[-1]['precio'] < umbral:
                grupo_actual.append(nivel)
            else:
                # Procesar grupo completado
                precio_promedio = sum(n['precio'] for n in grupo_actual) / len(grupo_actual)
                
                # ===================================
                # CALCULAR FUERZA DEL NIVEL
                # ===================================
                # La fuerza se basa en:
                # 1. Número de toques (más toques = más fuerte)
                # 2. Volumen en esos toques (alto volumen = más significativo)
                # 3. Recencia (niveles recientes valen más)
                
                fuerza_base = len(grupo_actual)  # Número de toques
                
                # Bonus por volumen alto
                bonus_volumen = sum(1 for n in grupo_actual if n.get('volumen', 0) > 0) * 0.3
                
                # Factor de recencia (penalizar niveles muy antiguos)
                dias_promedio = sum(n['dias_desde_hoy'] for n in grupo_actual) / len(grupo_actual)
                factor_recencia = max(0.3, 1 - (dias_promedio / 365))  # Máximo 70% penalización
                
                fuerza = (fuerza_base + bonus_volumen) * factor_recencia
                
                grupos.append({
                    'precio': float(round(precio_promedio, 2)),
                    'fuerza': round(fuerza, 1),
                    'toques': len(grupo_actual),
                    'fecha_mas_reciente': max(n['fecha'] for n in grupo_actual),
                    'dias_desde_hoy': min(n['dias_desde_hoy'] for n in grupo_actual)
                })
                grupo_actual = [nivel]
        
        # Procesar último grupo
        if grupo_actual:
            precio_promedio = sum(n['precio'] for n in grupo_actual) / len(grupo_actual)
            fuerza_base = len(grupo_actual)
            bonus_volumen = sum(1 for n in grupo_actual if n.get('volumen', 0) > 0) * 0.3
            dias_promedio = sum(n['dias_desde_hoy'] for n in grupo_actual) / len(grupo_actual)
            factor_recencia = max(0.3, 1 - (dias_promedio / 365))
            fuerza = (fuerza_base + bonus_volumen) * factor_recencia
            
            grupos.append({
                'precio': float(round(precio_promedio, 2)),
                'fuerza': round(fuerza, 1),
                'toques': len(grupo_actual),
                'fecha_mas_reciente': max(n['fecha'] for n in grupo_actual),
                'dias_desde_hoy': min(n['dias_desde_hoy'] for n in grupo_actual)
            })
        
        return grupos
    
    # Agrupar máximos y mínimos
    resistencias_agrupadas = agrupar_niveles(maximos, umbral_agrupacion)
    soportes_agrupados = agrupar_niveles(minimos, umbral_agrupacion)
    
    # ===========================
    # FILTRADO CRÍTICO MEJORADO
    # ===========================
    # SOPORTES: Solo los que están DEBAJO del precio actual
    # Relajamos el criterio de fuerza mínima de 0.8 a 0.5 para capturar más niveles
    soportes = [s for s in soportes_agrupados 
                if s['precio'] < precio_actual * 0.995  # Al menos 0.5% debajo
                and s['fuerza'] >= 0.5]  # Reducido de 0.8
    
    # RESISTENCIAS: Solo las que están ENCIMA del precio actual
    # CLAVE: Relajamos criterios para capturar resistencias como 8.10 en Meliá
    resistencias = [r for r in resistencias_agrupadas 
                    if r['precio'] > precio_actual * 1.005  # Al menos 0.5% encima
                    and r['fuerza'] >= 0.5]  # Reducido de 0.8 para capturar más niveles
    
    # ===========================
    # ORDENAR Y LIMITAR
    # ===========================
    # Soportes: más cercanos primero (descendente por precio)
    soportes.sort(key=lambda x: (-x['fuerza'], -x['precio']))  # Por fuerza primero, luego precio
    soportes = soportes[:max_niveles]
    
    # Resistencias: más cercanos primero (ascendente por precio)
    resistencias.sort(key=lambda x: (-x['fuerza'], x['precio']))  # Por fuerza primero, luego precio
    resistencias = resistencias[:max_niveles]
    
    # ===========================
    # AÑADIR DISTANCIA AL PRECIO ACTUAL
    # ===========================
    for s in soportes:
        distancia_pct = ((precio_actual - s['precio']) / precio_actual) * 100
        s['distancia_pct'] = round(distancia_pct, 1)
    
    for r in resistencias:
        distancia_pct = ((r['precio'] - precio_actual) / precio_actual) * 100
        r['distancia_pct'] = round(distancia_pct, 1)
    
    return soportes, resistencias


def calcular_fibonacci(df, lookback=None):
    """
    Fibonacci original mejorado SIN romper el frontend.
    Nunca devuelve None. Siempre devuelve niveles.
    """

    # Si no hay datos suficientes, devolvemos niveles planos
    if df is None or len(df) < 20:
        return {
            'niveles': [],
            'direccion': 'indefinido',
            'precio_max': 0,
            'precio_min': 0,
            'fecha_max': '',
            'fecha_min': '',
            'swing_pct': 0,
            'precio_actual': 0
        }

    LOOKBACK_SWING = 60
    df_work = df.tail(LOOKBACK_SWING).copy()

    # Limpieza mínima para evitar NaN y ceros
    df_work = df_work[(df_work['High'] > 0) & (df_work['Low'] > 0) & (df_work['Close'] > 0)]
    df_work = df_work.dropna()

    # Si tras limpiar queda poco, usamos el df original sin limpiar
    if len(df_work) < 10:
        df_work = df.tail(LOOKBACK_SWING)

    precio_actual = float(df_work['Close'].iloc[-1])

    idx_max = df_work['High'].idxmax()
    idx_min = df_work['Low'].idxmin()

    precio_max = float(df_work.loc[idx_max, 'High'])
    precio_min = float(df_work.loc[idx_min, 'Low'])

    # Evitar división por cero
    if precio_min <= 0:
        precio_min = precio_actual * 0.95

    rango = precio_max - precio_min
    if rango == 0:
        rango = precio_actual * 0.05  # rango mínimo artificial

    def fmt(idx):
        return idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]

    fecha_max = fmt(idx_max)
    fecha_min = fmt(idx_min)

    pos_max = df_work.index.get_loc(idx_max)
    pos_min = df_work.index.get_loc(idx_min)

    if pos_max > pos_min:
        direccion = 'bajista'
    else:
        direccion = 'alcista'

    swing_pct = ((precio_max - precio_min) / precio_min) * 100

    NIVELES_FIBO = [0.0, 0.382, 0.5, 0.618, 1.0]
    NOMBRES_FIBO = ['0%', '38.2%', '50%', '61.8%', '100%']
    IMPORTANCIA  = ['extremo', 'clave', 'medio', 'clave', 'extremo']

    niveles = []
    for ratio, nombre, importancia in zip(NIVELES_FIBO, NOMBRES_FIBO, IMPORTANCIA):

        if direccion == 'bajista':
            precio_nivel = precio_max - (rango * ratio)
        else:
            precio_nivel = precio_min + (rango * ratio)

        distancia_pct = ((precio_actual - precio_nivel) / precio_nivel) * 100
        cerca = abs(distancia_pct) <= 1.5

        niveles.append({
            'ratio':        ratio,
            'nombre':       nombre,
            'precio':       float(round(precio_nivel, 2)),
            'importancia':  importancia,
            'distancia_pct': round(distancia_pct, 1),
            'cerca':        cerca
        })

    return {
        'niveles':      niveles,
        'direccion':    direccion,
        'precio_max':   float(round(precio_max, 2)),
        'precio_min':   float(round(precio_min, 2)),
        'fecha_max':    fecha_max,
        'fecha_min':    fecha_min,
        'swing_pct':    round(swing_pct, 1),
        'precio_actual': float(round(precio_actual, 2))
    }

def detectar_divergencias(df, ventana=5, lookback=120):
    """
    Detecta divergencias entre precio e indicadores (RSI y MACD).
    
    Tipos detectados:
    - ALCISTA: Precio hace mínimos decrecientes, indicador hace mínimos crecientes
      → Señal de compra potencial (el impulso bajista se agota)
    - BAJISTA: Precio hace máximos crecientes, indicador hace máximos decrecientes
      → Señal de venta potencial (el impulso alcista se agota)
    
    Args:
        df: DataFrame con Close, RSI, MACD ya calculados
        ventana: Ventana para detectar máximos/mínimos locales (default 5)
        lookback: Cuántas velas mirar hacia atrás (default 120)
    
    Returns:
        list de dicts con cada divergencia encontrada
    """
    divergencias = []
    
    if len(df) < ventana * 4:
        return divergencias
    
    # Trabajar con los últimos N datos
    df_work = df.tail(lookback).copy()
    precios = df_work['Close'].values
    fechas  = df_work.index.tolist()
    n       = len(precios)

    def fmt_fecha(f):
        return f.strftime('%Y-%m-%d') if hasattr(f, 'strftime') else str(f)[:10]

    def encontrar_maximos(series, v):
        """Índices de máximos locales en la series (array numpy)"""
        result = []
        for i in range(v, len(series) - v):
            if np.isnan(series[i]):
                continue
            if series[i] >= np.nanmax(series[i-v:i]) and series[i] >= np.nanmax(series[i+1:i+v+1]):
                result.append(i)
        return result

    def encontrar_minimos(series, v):
        """Índices de mínimos locales en la series (array numpy)"""
        result = []
        for i in range(v, len(series) - v):
            if np.isnan(series[i]):
                continue
            if series[i] <= np.nanmin(series[i-v:i]) and series[i] <= np.nanmin(series[i+1:i+v+1]):
                result.append(i)
        return result

    def indicador_cercano(extremos_ind, idx_precio, margen):
        """Busca el extremo del indicador más cercano a idx_precio"""
        candidatos = [p for p in extremos_ind if abs(p - idx_precio) <= margen]
        if not candidatos:
            return None
        return min(candidatos, key=lambda p: abs(p - idx_precio))

    # ─────────────────────────────────────────────
    # Divergencias con RSI
    # ─────────────────────────────────────────────
    if 'RSI' in df_work.columns:
        rsi = df_work['RSI'].values

        max_precio = encontrar_maximos(precios, ventana)
        min_precio = encontrar_minimos(precios, ventana)
        max_rsi    = encontrar_maximos(rsi,     ventana)
        min_rsi    = encontrar_minimos(rsi,     ventana)
        margen     = ventana * 2

        # BAJISTA: precio sube, RSI baja (en máximos)
        for i in range(1, len(max_precio)):
            i1, i2 = max_precio[i-1], max_precio[i]
            # Precio hace higher high (al menos 0.5%)
            if precios[i2] <= precios[i1] * 1.005:
                continue
            r1 = indicador_cercano(max_rsi, i1, margen)
            r2 = indicador_cercano(max_rsi, i2, margen)
            if r1 is None or r2 is None or r1 == r2:
                continue
            # RSI hace lower high (al menos 2 puntos)
            if rsi[r2] < rsi[r1] - 2:
                # Solo divergencias recientes (último 30% del lookback)
                if i2 >= n * 0.7:
                    divergencias.append({
                        'tipo': 'bajista',
                        'indicador': 'RSI',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(rsi[r1]), 1),
                        'ind2': round(float(rsi[r2]), 1),
                        'descripcion': f'Precio ↑ {precios[i1]:.2f}→{precios[i2]:.2f} · RSI ↓ {rsi[r1]:.1f}→{rsi[r2]:.1f}',
                        'señal': 'VENTA'
                    })

        # ALCISTA: precio baja, RSI sube (en mínimos)
        for i in range(1, len(min_precio)):
            i1, i2 = min_precio[i-1], min_precio[i]
            # Precio hace lower low (al menos 0.5%)
            if precios[i2] >= precios[i1] * 0.995:
                continue
            r1 = indicador_cercano(min_rsi, i1, margen)
            r2 = indicador_cercano(min_rsi, i2, margen)
            if r1 is None or r2 is None or r1 == r2:
                continue
            # RSI hace higher low (al menos 2 puntos)
            if rsi[r2] > rsi[r1] + 2:
                if i2 >= n * 0.7:
                    divergencias.append({
                        'tipo': 'alcista',
                        'indicador': 'RSI',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(rsi[r1]), 1),
                        'ind2': round(float(rsi[r2]), 1),
                        'descripcion': f'Precio ↓ {precios[i1]:.2f}→{precios[i2]:.2f} · RSI ↑ {rsi[r1]:.1f}→{rsi[r2]:.1f}',
                        'señal': 'COMPRA'
                    })

    # ─────────────────────────────────────────────
    # Divergencias con MACD
    # ─────────────────────────────────────────────
    if 'MACD' in df_work.columns:
        macd = df_work['MACD'].values

        max_precio = encontrar_maximos(precios, ventana)
        min_precio = encontrar_minimos(precios, ventana)
        max_macd   = encontrar_maximos(macd,    ventana)
        min_macd   = encontrar_minimos(macd,    ventana)
        margen     = ventana * 2

        # BAJISTA MACD
        for i in range(1, len(max_precio)):
            i1, i2 = max_precio[i-1], max_precio[i]
            if precios[i2] <= precios[i1] * 1.005:
                continue
            m1 = indicador_cercano(max_macd, i1, margen)
            m2 = indicador_cercano(max_macd, i2, margen)
            if m1 is None or m2 is None or m1 == m2:
                continue
            rango = abs(np.nanmax(macd) - np.nanmin(macd))
            if rango == 0:
                continue
            if macd[m2] < macd[m1] - rango * 0.05:
                if i2 >= n * 0.7:
                    divergencias.append({
                        'tipo': 'bajista',
                        'indicador': 'MACD',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(macd[m1]), 4),
                        'ind2': round(float(macd[m2]), 4),
                        'descripcion': f'Precio ↑ {precios[i1]:.2f}→{precios[i2]:.2f} · MACD ↓',
                        'señal': 'VENTA'
                    })

        # ALCISTA MACD
        for i in range(1, len(min_precio)):
            i1, i2 = min_precio[i-1], min_precio[i]
            if precios[i2] >= precios[i1] * 0.995:
                continue
            m1 = indicador_cercano(min_macd, i1, margen)
            m2 = indicador_cercano(min_macd, i2, margen)
            if m1 is None or m2 is None or m1 == m2:
                continue
            rango = abs(np.nanmax(macd) - np.nanmin(macd))
            if rango == 0:
                continue
            if macd[m2] > macd[m1] + rango * 0.05:
                if i2 >= n * 0.7:
                    divergencias.append({
                        'tipo': 'alcista',
                        'indicador': 'MACD',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(macd[m1]), 4),
                        'ind2': round(float(macd[m2]), 4),
                        'descripcion': f'Precio ↓ {precios[i1]:.2f}→{precios[i2]:.2f} · MACD ↑',
                        'señal': 'COMPRA'
                    })


    # ─────────────────────────────────────────────
    # Divergencias con OBV
    # ─────────────────────────────────────────────
    if 'OBV' in df_work.columns:
        obv = df_work['OBV'].values
        
        max_obv = encontrar_maximos(obv, ventana)
        min_obv = encontrar_minimos(obv, ventana)
        
        # BAJISTA: precio sube, OBV baja (en máximos)
        for i in range(1, len(max_precio)):
            i1, i2 = max_precio[i-1], max_precio[i]
            # Precio hace higher high
            if precios[i2] <= precios[i1] * 1.005:
                continue
            o1 = indicador_cercano(max_obv, i1, margen)
            o2 = indicador_cercano(max_obv, i2, margen)
            if o1 is None or o2 is None or o1 == o2:
                continue
            # OBV hace lower high
            if obv[o2] < obv[o1]:
                if i2 >= n * 0.7:  # Solo recientes
                    divergencias.append({
                        'tipo': 'bajista',
                        'indicador': 'OBV',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(obv[o1]), 0),
                        'ind2': round(float(obv[o2]), 0),
                        'descripcion': f'Precio ↑ {precios[i1]:.2f}→{precios[i2]:.2f} · OBV ↓',
                        'señal': 'VENTA'
                    })
        
        # ALCISTA: precio baja, OBV sube (en mínimos)
        for i in range(1, len(min_precio)):
            i1, i2 = min_precio[i-1], min_precio[i]
            # Precio hace lower low
            if precios[i2] >= precios[i1] * 0.995:
                continue
            o1 = indicador_cercano(min_obv, i1, margen)
            o2 = indicador_cercano(min_obv, i2, margen)
            if o1 is None or o2 is None or o1 == o2:
                continue
            # OBV hace higher low
            if obv[o2] > obv[o1]:
                if i2 >= n * 0.7:  # Solo recientes
                    divergencias.append({
                        'tipo': 'alcista',
                        'indicador': 'OBV',
                        'fecha1': fmt_fecha(fechas[i1]),
                        'fecha2': fmt_fecha(fechas[i2]),
                        'precio1': round(float(precios[i1]), 2),
                        'precio2': round(float(precios[i2]), 2),
                        'ind1': round(float(obv[o1]), 0),
                        'ind2': round(float(obv[o2]), 0),
                        'descripcion': f'Precio ↓ {precios[i1]:.2f}→{precios[i2]:.2f} · OBV ↑',
                        'señal': 'COMPRA'
                    })

    # Ordenar por más reciente y eliminar duplicados obvios
    divergencias.sort(key=lambda x: x['fecha2'], reverse=True)
    return divergencias[:8]  # Máximo 8 divergencias


def detectar_patrones_chartistas(df, lookback=100, ventana=7):
    """
    Detecta patrones chartistas clásicos: doble techo/suelo y hombro-cabeza-hombro.
    
    Args:
        df: DataFrame con OHLC
        lookback: Velas a analizar (default 100)
        ventana: Tamaño ventana para extremos locales (default 7)
    
    Returns:
        list: Patrones encontrados con metadatos
    """
    try:
        if df is None or len(df) < lookback:
            return []
        
        df_work = df.tail(lookback).copy()
        patrones = []
        
        # Función auxiliar: encontrar máximos locales
        def encontrar_maximos(precios, ventana):
            maximos = []
            for i in range(ventana, len(precios) - ventana):
                if precios[i] == max(precios[i-ventana:i+ventana+1]):
                    maximos.append(i)
            return maximos
        
        # Función auxiliar: encontrar mínimos locales
        def encontrar_minimos(precios, ventana):
            minimos = []
            for i in range(ventana, len(precios) - ventana):
                if precios[i] == min(precios[i-ventana:i+ventana+1]):
                    minimos.append(i)
            return minimos
        
        precios_high = df_work['High'].values
        precios_low  = df_work['Low'].values
        fechas = df_work.index
        
        maximos_idx = encontrar_maximos(precios_high, ventana)
        minimos_idx = encontrar_minimos(precios_low, ventana)
        
        # ========================================
        # DOBLE TECHO (Double Top) - BAJISTA
        # ========================================
        for i in range(len(maximos_idx) - 1):
            idx1 = maximos_idx[i]
            idx2 = maximos_idx[i + 1]
            
            # Debe haber distancia MÍNIMA 15 días entre techos (antes 10)
            # Máximo 60 días (antes 50) para dar más margen
            if idx2 - idx1 < 15 or idx2 - idx1 > 60:
                continue
            
            precio1 = precios_high[idx1]
            precio2 = precios_high[idx2]
            
            # Los dos techos deben estar a menos del 2% de diferencia (antes 2.5%)
            dif_pct = abs(precio2 - precio1) / precio1 * 100
            if dif_pct > 2.0:
                continue
            
            # Valle entre los techos (neckline)
            valle_slice = precios_low[idx1:idx2+1]
            valle_idx = idx1 + valle_slice.argmin()
            valle_precio = valle_slice.min()
            
            # El valle debe ser al menos 5% más bajo que los techos (antes 3%)
            caida_valle = (precio1 - valle_precio) / precio1 * 100
            if caida_valle < 5.0:
                continue
            
            # NUEVO: Verificar si hay ruptura del soporte (neckline)
            precio_actual = df_work['Close'].iloc[-1]
            ruptura_confirmada = precio_actual < valle_precio
            
            # SOLO mostrar patrones que:
            # 1. Estén confirmados (ruptura) O
            # 2. Estén muy cerca del segundo techo Y haya señales de debilidad
            cerca_segundo_techo = abs(precio_actual - precio2) / precio2 * 100 < 3.0
            
            # NUEVO: Verificar volumen decreciente en segundo techo
            volumen_decreciente = False
            if 'Volume' in df_work.columns:
                vol1_avg = df_work['Volume'].iloc[max(0, idx1-5):idx1+1].mean()
                vol2_avg = df_work['Volume'].iloc[max(0, idx2-5):idx2+1].mean()
                if vol1_avg > 0:
                    volumen_decreciente = vol2_avg < vol1_avg * 0.8  # 20% menos volumen
            
            # CRITERIO ESTRICTO: Solo detectar si está confirmado O cerca con volumen débil
            if not (ruptura_confirmada or (cerca_segundo_techo and volumen_decreciente)):
                continue
            
            patrones.append({
                'tipo': 'doble_techo',
                'direccion': 'bajista',
                'fecha1': fechas[idx1].strftime('%Y-%m-%d'),
                'fecha2': fechas[idx2].strftime('%Y-%m-%d'),
                'precio1': float(round(precio1, 2)),
                'precio2': float(round(precio2, 2)),
                'neckline': float(round(valle_precio, 2)),
                'fecha_neckline': fechas[valle_idx].strftime('%Y-%m-%d'),
                'objetivo': float(round(valle_precio - (precio1 - valle_precio), 2)),
                'confirmado': bool(ruptura_confirmada),
                'volumen_decreciente': bool(volumen_decreciente),
                'descripcion': f'Doble techo en {precio1:.2f}€. Neckline: {valle_precio:.2f}€' + 
                              (' (CONFIRMADO)' if ruptura_confirmada else ' (en formación)')
            })
        
        # ========================================
        # DOBLE SUELO (Double Bottom) - ALCISTA
        # ========================================
        for i in range(len(minimos_idx) - 1):
            idx1 = minimos_idx[i]
            idx2 = minimos_idx[i + 1]
            
            if idx2 - idx1 < 10 or idx2 - idx1 > 50:
                continue
            
            precio1 = precios_low[idx1]
            precio2 = precios_low[idx2]
            
            dif_pct = abs(precio2 - precio1) / precio1 * 100
            if dif_pct > 2.5:
                continue
            
            # Pico entre los suelos (neckline)
            pico_slice = precios_high[idx1:idx2+1]
            pico_idx = idx1 + pico_slice.argmax()
            pico_precio = pico_slice.max()
            
            subida_pico = (pico_precio - precio1) / precio1 * 100
            if subida_pico < 3.0:
                continue
            
            precio_actual = df_work['Close'].iloc[-1]
            if abs(precio_actual - precio2) / precio2 * 100 > 5.0:
                continue
            
            patrones.append({
                'tipo': 'doble_suelo',
                'direccion': 'alcista',
                'fecha1': fechas[idx1].strftime('%Y-%m-%d'),
                'fecha2': fechas[idx2].strftime('%Y-%m-%d'),
                'precio1': float(round(precio1, 2)),
                'precio2': float(round(precio2, 2)),
                'neckline': float(round(pico_precio, 2)),
                'fecha_neckline': fechas[pico_idx].strftime('%Y-%m-%d'),
                'objetivo': float(round(pico_precio + (pico_precio - precio1), 2)),
                'confirmado': bool(precio_actual > pico_precio),
                'descripcion': f'Doble suelo en {precio1:.2f}€. Neckline: {pico_precio:.2f}€'
            })
        
        # ========================================
        # HOMBRO-CABEZA-HOMBRO (H&S) - BAJISTA
        # ========================================
        if len(maximos_idx) >= 3:
            for i in range(len(maximos_idx) - 2):
                idx_h1 = maximos_idx[i]      # Hombro izquierdo
                idx_c  = maximos_idx[i + 1]  # Cabeza
                idx_h2 = maximos_idx[i + 2]  # Hombro derecho
                
                if idx_h2 - idx_h1 < 20 or idx_h2 - idx_h1 > 80:
                    continue
                
                h1 = precios_high[idx_h1]
                c  = precios_high[idx_c]
                h2 = precios_high[idx_h2]
                
                # Cabeza debe ser más alta que ambos hombros
                if c <= h1 or c <= h2:
                    continue
                
                # Hombros deben estar a altura similar (±3.5%)
                dif_hombros = abs(h2 - h1) / h1 * 100
                if dif_hombros > 3.5:
                    continue
                
                # Cabeza al menos 5% más alta que hombros
                if (c - max(h1, h2)) / max(h1, h2) * 100 < 5.0:
                    continue
                
                # Neckline = promedio de valles
                valle1_slice = precios_low[idx_h1:idx_c+1]
                valle2_slice = precios_low[idx_c:idx_h2+1]
                valle1 = valle1_slice.min()
                valle2 = valle2_slice.min()
                neckline = (valle1 + valle2) / 2
                
                precio_actual = df_work['Close'].iloc[-1]
                if abs(precio_actual - h2) / h2 * 100 > 8.0:
                    continue
                
                patrones.append({
                    'tipo': 'hch',
                    'direccion': 'bajista',
                    'hombro1': float(round(h1, 2)),
                    'cabeza': float(round(c, 2)),
                    'hombro2': float(round(h2, 2)),
                    'fecha_h1': fechas[idx_h1].strftime('%Y-%m-%d'),
                    'fecha_c': fechas[idx_c].strftime('%Y-%m-%d'),
                    'fecha_h2': fechas[idx_h2].strftime('%Y-%m-%d'),
                    'neckline': float(round(neckline, 2)),
                    'objetivo': float(round(neckline - (c - neckline), 2)),
                    'confirmado': bool(precio_actual < neckline),
                    'descripcion': f'HCH: cabeza {c:.2f}€, hombros {h1:.2f}-{h2:.2f}€'
                })
        
        # ========================================
        # HCH INVERTIDO - ALCISTA
        # ========================================
        if len(minimos_idx) >= 3:
            for i in range(len(minimos_idx) - 2):
                idx_h1 = minimos_idx[i]
                idx_c  = minimos_idx[i + 1]
                idx_h2 = minimos_idx[i + 2]
                
                if idx_h2 - idx_h1 < 20 or idx_h2 - idx_h1 > 80:
                    continue
                
                h1 = precios_low[idx_h1]
                c  = precios_low[idx_c]
                h2 = precios_low[idx_h2]
                
                # Cabeza debe ser más baja que ambos hombros
                if c >= h1 or c >= h2:
                    continue
                
                dif_hombros = abs(h2 - h1) / h1 * 100
                if dif_hombros > 3.5:
                    continue
                
                if (min(h1, h2) - c) / c * 100 < 5.0:
                    continue
                
                # Neckline = promedio de picos
                pico1_slice = precios_high[idx_h1:idx_c+1]
                pico2_slice = precios_high[idx_c:idx_h2+1]
                pico1 = pico1_slice.max()
                pico2 = pico2_slice.max()
                neckline = (pico1 + pico2) / 2
                
                precio_actual = df_work['Close'].iloc[-1]
                if abs(precio_actual - h2) / h2 * 100 > 8.0:
                    continue
                
                patrones.append({
                    'tipo': 'hch_invertido',
                    'direccion': 'alcista',
                    'hombro1': float(round(h1, 2)),
                    'cabeza': float(round(c, 2)),
                    'hombro2': float(round(h2, 2)),
                    'fecha_h1': fechas[idx_h1].strftime('%Y-%m-%d'),
                    'fecha_c': fechas[idx_c].strftime('%Y-%m-%d'),
                    'fecha_h2': fechas[idx_h2].strftime('%Y-%m-%d'),
                    'neckline': float(round(neckline, 2)),
                    'objetivo': float(round(neckline + (neckline - c), 2)),
                    'confirmado': bool(precio_actual > neckline),
                    'descripcion': f'HCH inv: cabeza {c:.2f}€, hombros {h1:.2f}-{h2:.2f}€'
                })
        
        # Devolver máximo 2 patrones más recientes
        return patrones[-2:] if len(patrones) > 2 else patrones
    
    except Exception as e:
        # Si hay cualquier error, devolver lista vacía para no romper la app
        print(f"⚠️ Error en detectar_patrones_chartistas: {e}")
        return []


        def encontrar_maximos(precios, ventana):
            maximos = []
            for i in range(ventana, len(precios) - ventana):
                if precios[i] == max(precios[i-ventana:i+ventana+1]):
                    maximos.append(i)
            return maximos
    
        # Función auxiliar: encontrar mínimos locales
        def encontrar_minimos(precios, ventana):
            minimos = []
            for i in range(ventana, len(precios) - ventana):
                if precios[i] == min(precios[i-ventana:i+ventana+1]):
                    minimos.append(i)
            return minimos
    
        precios_high = df_work['High'].values
        precios_low  = df_work['Low'].values
        fechas = df_work.index
    
        maximos_idx = encontrar_maximos(precios_high, ventana)
        minimos_idx = encontrar_minimos(precios_low, ventana)
    
        # ========================================
        # DOBLE TECHO (Double Top) - BAJISTA
        # ========================================
        for i in range(len(maximos_idx) - 1):
            idx1 = maximos_idx[i]
            idx2 = maximos_idx[i + 1]
        
            # Debe haber distancia MÍNIMA 15 días entre techos (antes 10)
            # Máximo 60 días (antes 50) para dar más margen
            if idx2 - idx1 < 15 or idx2 - idx1 > 60:
                continue
        
            precio1 = precios_high[idx1]
            precio2 = precios_high[idx2]
        
            # Los dos techos deben estar a menos del 2% de diferencia (antes 2.5%)
            dif_pct = abs(precio2 - precio1) / precio1 * 100
            if dif_pct > 2.0:
                continue
        
            # Valle entre los techos (neckline)
            valle_slice = precios_low[idx1:idx2+1]
            valle_idx = idx1 + valle_slice.argmin()
            valle_precio = valle_slice.min()
        
            # El valle debe ser al menos 5% más bajo que los techos (antes 3%)
            caida_valle = (precio1 - valle_precio) / precio1 * 100
            if caida_valle < 5.0:
                continue
        
            # NUEVO: Verificar si hay ruptura del soporte (neckline)
            precio_actual = df_work['Close'].iloc[-1]
            ruptura_confirmada = precio_actual < valle_precio
            
            # SOLO mostrar patrones que:
            # 1. Estén confirmados (ruptura) O
            # 2. Estén muy cerca del segundo techo Y haya señales de debilidad
            cerca_segundo_techo = abs(precio_actual - precio2) / precio2 * 100 < 3.0
            
            # NUEVO: Verificar volumen decreciente en segundo techo
            volumen_decreciente = False
            if 'Volume' in df_work.columns:
                vol1_avg = df_work['Volume'].iloc[max(0, idx1-5):idx1+1].mean()
                vol2_avg = df_work['Volume'].iloc[max(0, idx2-5):idx2+1].mean()
                if vol1_avg > 0:
                    volumen_decreciente = vol2_avg < vol1_avg * 0.8  # 20% menos volumen
            
            # CRITERIO ESTRICTO: Solo detectar si está confirmado O cerca con volumen débil
            if not (ruptura_confirmada or (cerca_segundo_techo and volumen_decreciente)):
                continue
        
            patrones.append({
                'tipo': 'doble_techo',
                'direccion': 'bajista',
                'fecha1': fechas[idx1].strftime('%Y-%m-%d'),
                'fecha2': fechas[idx2].strftime('%Y-%m-%d'),
                'precio1': float(round(precio1, 2)),
                'precio2': float(round(precio2, 2)),
                'neckline': float(round(valle_precio, 2)),
                'fecha_neckline': fechas[valle_idx].strftime('%Y-%m-%d'),
                'objetivo': float(round(valle_precio - (precio1 - valle_precio), 2)),
                'confirmado': bool(ruptura_confirmada),
                'volumen_decreciente': bool(volumen_decreciente),
                'descripcion': f'Doble techo en {precio1:.2f}€. Neckline: {valle_precio:.2f}€' + 
                              (' (CONFIRMADO)' if ruptura_confirmada else ' (en formación)')
            })
    
        # ========================================
        # DOBLE SUELO (Double Bottom) - ALCISTA
        # ========================================
        for i in range(len(minimos_idx) - 1):
            idx1 = minimos_idx[i]
            idx2 = minimos_idx[i + 1]
        
            if idx2 - idx1 < 10 or idx2 - idx1 > 50:
                continue
        
            precio1 = precios_low[idx1]
            precio2 = precios_low[idx2]
        
            dif_pct = abs(precio2 - precio1) / precio1 * 100
            if dif_pct > 2.5:
                continue
        
            # Pico entre los suelos (neckline)
            pico_slice = precios_high[idx1:idx2+1]
            pico_idx = idx1 + pico_slice.argmax()
            pico_precio = pico_slice.max()
        
            subida_pico = (pico_precio - precio1) / precio1 * 100
            if subida_pico < 3.0:
                continue
        
            precio_actual = df_work['Close'].iloc[-1]
            if abs(precio_actual - precio2) / precio2 * 100 > 5.0:
                continue
        
            patrones.append({
                'tipo': 'doble_suelo',
                'direccion': 'alcista',
                'fecha1': fechas[idx1].strftime('%Y-%m-%d'),
                'fecha2': fechas[idx2].strftime('%Y-%m-%d'),
                'precio1': float(round(precio1, 2)),
                'precio2': float(round(precio2, 2)),
                'neckline': float(round(pico_precio, 2)),
                'fecha_neckline': fechas[pico_idx].strftime('%Y-%m-%d'),
                'objetivo': float(round(pico_precio + (pico_precio - precio1), 2)),
                'confirmado': bool(precio_actual > pico_precio),
                'descripcion': f'Doble suelo en {precio1:.2f}€. Neckline: {pico_precio:.2f}€'
            })
    
        # ========================================
        # HOMBRO-CABEZA-HOMBRO (H&S) - BAJISTA
        # ========================================
        if len(maximos_idx) >= 3:
            for i in range(len(maximos_idx) - 2):
                idx_h1 = maximos_idx[i]      # Hombro izquierdo
                idx_c  = maximos_idx[i + 1]  # Cabeza
                idx_h2 = maximos_idx[i + 2]  # Hombro derecho
            
                if idx_h2 - idx_h1 < 20 or idx_h2 - idx_h1 > 80:
                    continue
            
                h1 = precios_high[idx_h1]
                c  = precios_high[idx_c]
                h2 = precios_high[idx_h2]
            
                # Cabeza debe ser más alta que ambos hombros
                if c <= h1 or c <= h2:
                    continue
            
                # Hombros deben estar a altura similar (±3.5%)
                dif_hombros = abs(h2 - h1) / h1 * 100
                if dif_hombros > 3.5:
                    continue
            
                # Cabeza al menos 5% más alta que hombros
                if (c - max(h1, h2)) / max(h1, h2) * 100 < 5.0:
                    continue
            
                # Neckline = promedio de valles
                valle1_slice = precios_low[idx_h1:idx_c+1]
                valle2_slice = precios_low[idx_c:idx_h2+1]
                valle1 = valle1_slice.min()
                valle2 = valle2_slice.min()
                neckline = (valle1 + valle2) / 2
            
                precio_actual = df_work['Close'].iloc[-1]
                if abs(precio_actual - h2) / h2 * 100 > 8.0:
                    continue
            
                patrones.append({
                    'tipo': 'hch',
                    'direccion': 'bajista',
                    'hombro1': float(round(h1, 2)),
                    'cabeza': float(round(c, 2)),
                    'hombro2': float(round(h2, 2)),
                    'fecha_h1': fechas[idx_h1].strftime('%Y-%m-%d'),
                    'fecha_c': fechas[idx_c].strftime('%Y-%m-%d'),
                    'fecha_h2': fechas[idx_h2].strftime('%Y-%m-%d'),
                    'neckline': float(round(neckline, 2)),
                    'objetivo': float(round(neckline - (c - neckline), 2)),
                    'confirmado': bool(precio_actual < neckline),
                    'descripcion': f'HCH: cabeza {c:.2f}€, hombros {h1:.2f}-{h2:.2f}€'
                })
    
        # ========================================
        # HCH INVERTIDO - ALCISTA
        # ========================================
        if len(minimos_idx) >= 3:
            for i in range(len(minimos_idx) - 2):
                idx_h1 = minimos_idx[i]
                idx_c  = minimos_idx[i + 1]
                idx_h2 = minimos_idx[i + 2]
            
                if idx_h2 - idx_h1 < 20 or idx_h2 - idx_h1 > 80:
                    continue
            
                h1 = precios_low[idx_h1]
                c  = precios_low[idx_c]
                h2 = precios_low[idx_h2]
            
                # Cabeza debe ser más baja que ambos hombros
                if c >= h1 or c >= h2:
                    continue
            
                dif_hombros = abs(h2 - h1) / h1 * 100
                if dif_hombros > 3.5:
                    continue
            
                if (min(h1, h2) - c) / c * 100 < 5.0:
                    continue
            
                # Neckline = promedio de picos
                pico1_slice = precios_high[idx_h1:idx_c+1]
                pico2_slice = precios_high[idx_c:idx_h2+1]
                pico1 = pico1_slice.max()
                pico2 = pico2_slice.max()
                neckline = (pico1 + pico2) / 2
            
                precio_actual = df_work['Close'].iloc[-1]
                if abs(precio_actual - h2) / h2 * 100 > 8.0:
                    continue
            
                patrones.append({
                    'tipo': 'hch_invertido',
                    'direccion': 'alcista',
                    'hombro1': float(round(h1, 2)),
                    'cabeza': float(round(c, 2)),
                    'hombro2': float(round(h2, 2)),
                    'fecha_h1': fechas[idx_h1].strftime('%Y-%m-%d'),
                    'fecha_c': fechas[idx_c].strftime('%Y-%m-%d'),
                    'fecha_h2': fechas[idx_h2].strftime('%Y-%m-%d'),
                    'neckline': float(round(neckline, 2)),
                    'objetivo': float(round(neckline + (neckline - c), 2)),
                    'confirmado': bool(precio_actual > neckline),
                    'descripcion': f'HCH inv: cabeza {c:.2f}€, hombros {h1:.2f}-{h2:.2f}€'
                })
    
        # Devolver máximo 2 patrones más recientes
            return patrones[-2:] if len(patrones) > 2 else patrones
    
    except Exception as e:
        # Si hay cualquier error, devolver lista vacía para no romper la app
        print(f"⚠️ Error en detectar_patrones_chartistas: {e}")
        return []


def calcular_pivot_points(df, timeframe='1d'):
    """
    Calcula Pivot Points adaptados al timeframe
    
    TIMEFRAMES SOPORTADOS:
    - '1d' (diario): Pivot del día anterior → Para Swing (1-3 semanas)
    - '1wk' (semanal): Pivot de la semana anterior → Para Medio plazo (4-24 semanas)
    - '1mo' (mensual): Pivot del mes anterior → Para Posicional (6-24 meses)
    
    VENTAJA: shift(1) se adapta automáticamente:
    - En datos diarios: shift(1) = ayer
    - En datos semanales: shift(1) = semana anterior  
    - En datos mensuales: shift(1) = mes anterior
    
    Fórmulas (estándar para todos los timeframes):
    PP = (High + Low + Close) / 3
    R1 = (2 * PP) - Low
    R2 = PP + (High - Low)  
    R3 = High + 2 * (PP - Low)
    S1 = (2 * PP) - High
    S2 = PP - (High - Low)
    S3 = Low - 2 * (High - PP)
    
    Args:
        df: DataFrame con columnas High, Low, Close
        timeframe: '1d', '1wk', '1mo' (default: '1d')
    
    Returns:
        DataFrame con columnas añadidas: PIVOT_PP, PIVOT_R1, PIVOT_R2, PIVOT_R3,
                                          PIVOT_S1, PIVOT_S2, PIVOT_S3
    """
    # Usar período anterior para calcular pivots del período actual
    df['PIVOT_PP'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
    
    # Resistencias
    df['PIVOT_R1'] = (2 * df['PIVOT_PP']) - df['Low'].shift(1)
    df['PIVOT_R2'] = df['PIVOT_PP'] + (df['High'].shift(1) - df['Low'].shift(1))
    df['PIVOT_R3'] = df['High'].shift(1) + 2 * (df['PIVOT_PP'] - df['Low'].shift(1))
    
    # Soportes
    df['PIVOT_S1'] = (2 * df['PIVOT_PP']) - df['High'].shift(1)
    df['PIVOT_S2'] = df['PIVOT_PP'] - (df['High'].shift(1) - df['Low'].shift(1))
    df['PIVOT_S3'] = df['Low'].shift(1) - 2 * (df['High'].shift(1) - df['PIVOT_PP'])
    
    # Redondear a 2 decimales
    for col in ['PIVOT_PP', 'PIVOT_R1', 'PIVOT_R2', 'PIVOT_R3', 'PIVOT_S1', 'PIVOT_S2', 'PIVOT_S3']:
        df[col] = df[col].round(2)
    
    return df


def aplicar_indicadores(df, indicadores_lista, timeframe='1d'):
    """
    Función principal que orquesta todos los cálculos
    
    Args:
        df: DataFrame con datos OHLCV
        indicadores_lista: Lista de indicadores a calcular
        timeframe: Timeframe de los datos ('1d', '1wk', '1mo')
                   Usado para adaptar pivot points al período correcto
    
    IMPORTANTE: SIEMPRE calcula TODOS los indicadores para el análisis técnico,
    pero solo los pasa al gráfico si están en indicadores_lista
    """
    soportes = []
    resistencias = []
    patrones = []
    
    # =========================
    # CALCULAR SIEMPRE TODOS LOS INDICADORES (para análisis técnico)
    # =========================
    
    # MEDIAS MÓVILES - Siempre calcular
    df["MM20"] = df["Close"].rolling(20).mean()
    df["MM50"] = df["Close"].rolling(50).mean()
    df["MM200"] = df["Close"].rolling(200).mean()
    
    # RSI - Siempre calcular
    df["RSI"] = calcular_rsi(df)
    
    # MACD - Siempre calcular
    macd = calcular_macd(df)
    df["MACD"] = macd["MACD"]
    df["MACD_SEÑAL"] = macd["SEÑAL"]
    df["MACD_HIST"] = macd["HISTOGRAMA"]
    
    # BANDAS DE BOLLINGER - Siempre calcular
    bb = calcular_bandas_bollinger(df)
    df["BB_MEDIA"] = bb["MEDIA"]
    df["BB_SUPERIOR"] = bb["SUPERIOR"]
    df["BB_INFERIOR"] = bb["INFERIOR"]
    df["BB_ANCHO"] = bb["ANCHO"]
    
    # ATR - Siempre calcular
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean().round(4)
    
    # ESTOCÁSTICO - Siempre calcular
    stoch = calcular_estocastico(df)
    df["STOCH_K"] = stoch["K"]
    df["STOCH_D"] = stoch["D"]
    
    # ADX - Siempre calcular
    adx_data = calcular_adx(df)
    df["ADX"] = adx_data["ADX"]
    df["PLUS_DI"] = adx_data["PLUS_DI"]
    df["MINUS_DI"] = adx_data["MINUS_DI"]
    
    # ANÁLISIS DE VOLUMEN - Siempre calcular
    volumen_info = analizar_volumen(df)
    if volumen_info:
        df.loc[df.index[-1], 'VOLUMEN_RATIO'] = volumen_info['ratio']
    
    # OBV - Siempre calcular
    df["OBV"] = calcular_obv(df)
    
    # =========================
    # PIVOT POINTS (ADAPTATIVO POR TIMEFRAME)
    # =========================
    if "PIVOT" in indicadores_lista:
        df = calcular_pivot_points(df, timeframe)
    
    # =========================
    # SOPORTES Y RESISTENCIAS
    # =========================
    if "SR" in indicadores_lista:
        soportes, resistencias = calcular_soportes_resistencias(
            df, 
            ventana=10,
            umbral_agrupacion=0.02,
            max_niveles=8
        )
    
    # =========================
    # PATRONES DE VELAS JAPONESAS
    # =========================
    if "PATRONES" in indicadores_lista:
        try:
            patrones = detectar_patrones_velas(df, ultimas_n=50)
        except Exception as e:
            print(f"Error detectando patrones: {e}")
            patrones = []
    
    # =========================
    # RESUMEN TÉCNICO AUTOMÁTICO
    # Usa TODOS los indicadores calculados
    # =========================
    resumen_tecnico = generar_resumen_tecnico(df, indicadores_lista)
    
    # =========================
    # FIBONACCI
    # =========================
    fibonacci = calcular_fibonacci(df)

    # =========================
    # DIVERGENCIAS RSI / MACD
    # =========================
    divergencias = detectar_divergencias(df)
    
    # =========================
    # PATRONES CHARTISTAS
    # =========================
    patrones_chartistas = detectar_patrones_chartistas(df)
    
    return df, soportes, resistencias, patrones, resumen_tecnico, divergencias, fibonacci, patrones_chartistas
