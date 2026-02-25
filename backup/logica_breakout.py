"""
═══════════════════════════════════════════════════════════════
MÓDULO: DETECCIÓN DE BREAKOUTS (RUPTURAS)
Sistema Swing Trading - Estrategia de Impulsos
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio rompe resistencias
y entra en nueva fase de tendencia alcista.

Filosofía: "Comprar caro para vender más caro"

Criterios específicos:
- Precio en máximos (< 2% del máximo 20 sesiones)
- Resistencia clara identificada (2+ toques)
- Consolidación previa (10+ días)
- Volumen en ruptura (1.3x+ promedio)
- RSI momentum fuerte (55-75)
- Estructura alcista (precio > MM20 > MM50)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def detectar_breakout_swing(ticker, periodo='6mo'):
    """
    Detecta oportunidades de BREAKOUT (ruptura de resistencia)
    
    Args:
        ticker: Símbolo del valor (ej: 'ACS.MC')
        periodo: Periodo histórico ('3mo', '6mo', '1y')
    
    Returns:
        dict con datos operación o None si no hay señal
        {
            'ticker': str,
            'precio_actual': float,
            'entrada': float,
            'stop': float,
            'objetivo': float,
            'riesgo_pct': float,
            'beneficio_pct': float,
            'rr': float,
            'setup_score': int (0-10),
            'tipo': 'BREAKOUT',
            'resistencia_rota': float,
            'consolidacion_dias': int,
            'volumen_ruptura': float,
            'rsi': float,
            'atr': float,
            'mm20': float,
            'mm50': float,
            'distancia_maximo_pct': float,
            'fecha': str
        }
    """
    
    try:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 1: OBTENER DATOS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        df = yf.download(ticker, period=periodo, progress=False)
        
        if df is None or len(df) < 60:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 2: CALCULAR INDICADORES TÉCNICOS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        df['MM20'] = df['Close'].rolling(20).mean()
        df['MM50'] = df['Close'].rolling(50).mean()
        df['ATR'] = calcular_atr(df, periodo=14)
        df['RSI'] = calcular_rsi(df['Close'], periodo=14)
        
        # Extraer valores correctamente (evitar FutureWarning)
        precio_actual = df['Close'].iloc[-1]
        if isinstance(precio_actual, pd.Series):
            precio_actual = precio_actual.item()
        precio_actual = float(precio_actual)
        
        volumen_actual = df['Volume'].iloc[-1]
        if isinstance(volumen_actual, pd.Series):
            volumen_actual = volumen_actual.item()
        volumen_actual = float(volumen_actual)
        
        rsi_actual = df['RSI'].iloc[-1]
        if isinstance(rsi_actual, pd.Series):
            rsi_actual = rsi_actual.item()
        rsi_actual = float(rsi_actual)
        
        atr_actual = df['ATR'].iloc[-1]
        if isinstance(atr_actual, pd.Series):
            atr_actual = atr_actual.item()
        atr_actual = float(atr_actual)
        
        mm20_actual = df['MM20'].iloc[-1]
        if isinstance(mm20_actual, pd.Series):
            mm20_actual = mm20_actual.item()
        mm20_actual = float(mm20_actual)
        
        mm50_actual = df['MM50'].iloc[-1]
        if isinstance(mm50_actual, pd.Series):
            mm50_actual = mm50_actual.item()
        if not pd.isna(mm50_actual):
            mm50_actual = float(mm50_actual)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 3: VERIFICAR PRECIO EN MÁXIMOS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Verificar precio en máximos
        maximo_20 = df['Close'].tail(20).max()
        if isinstance(maximo_20, pd.Series):
            maximo_20 = maximo_20.item()
        maximo_20 = float(maximo_20)
        distancia_maximo_pct = ((precio_actual - maximo_20) / maximo_20) * 100
        
        # Debe estar dentro del 2% del máximo
        if distancia_maximo_pct < -2.0:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 4: IDENTIFICAR RESISTENCIA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        resistencias = identificar_resistencias(df.tail(60))
        
        if not resistencias or len(resistencias) == 0:
            return None
        
        resistencia_principal = resistencias[0]
        
        # El precio debe estar cerca o haber roto la resistencia
        distancia_resistencia_pct = ((precio_actual - resistencia_principal) / resistencia_principal) * 100
        
        if distancia_resistencia_pct < -3.0 or distancia_resistencia_pct > 5.0:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 5: VERIFICAR CONSOLIDACIÓN PREVIA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        consolidacion_dias = detectar_consolidacion(df.tail(40))
        
        if consolidacion_dias < 10:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 6: VERIFICAR VOLUMEN EN RUPTURA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Verificar volumen en ruptura
        volumen_promedio = df['Volume'].rolling(20).mean().iloc[-1]
        if isinstance(volumen_promedio, pd.Series):
            volumen_promedio = volumen_promedio.item()
        volumen_promedio = float(volumen_promedio)
        
        ratio_volumen = volumen_actual / volumen_promedio if volumen_promedio > 0 else 0
        
        # Volumen últimas 3 velas
        volumen_3_velas = df['Volume'].tail(3).mean()
        if isinstance(volumen_3_velas, pd.Series):
            volumen_3_velas = volumen_3_velas.item()
        volumen_3_velas = float(volumen_3_velas)
        
        ratio_volumen_3 = volumen_3_velas / volumen_promedio if volumen_promedio > 0 else 0
        
        # Necesitamos volumen moderado mínimo (1.2x)
        if ratio_volumen_3 < 1.2:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 7: VERIFICAR RSI (MOMENTUM)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # RSI debe estar en rango de momentum (50-78)
        # No demasiado bajo (no es pullback) ni excesivamente alto
        if rsi_actual < 50 or rsi_actual > 78:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 8: VERIFICAR ESTRUCTURA ALCISTA
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Precio > MM20 > MM50 (estructura alcista)
        if precio_actual < mm20_actual * 0.98:  # 2% tolerancia
            return None
        
        # Verificar MM50 solo si tiene valor válido
        if not pd.isna(mm50_actual):
            if mm20_actual < mm50_actual * 0.98:
                return None
        
        # MM20 debe tener pendiente positiva
        mm20_hace_5 = df['MM20'].iloc[-6]
        if isinstance(mm20_hace_5, pd.Series):
            mm20_hace_5 = mm20_hace_5.item()
        mm20_hace_5 = float(mm20_hace_5)
        pendiente_mm20 = ((mm20_actual - mm20_hace_5) / mm20_hace_5) * 100
        
        if pendiente_mm20 < -0.5:  # Pendiente negativa
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 9: CALCULAR STOP LOSS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Stop en mínimo de consolidación con margen 2%
        minimo_consolidacion = df['Low'].tail(consolidacion_dias).min()
        if isinstance(minimo_consolidacion, pd.Series):
            minimo_consolidacion = minimo_consolidacion.item()
        minimo_consolidacion = float(minimo_consolidacion)
        
        stop_loss = minimo_consolidacion * 0.98
        
        riesgo_pct = ((precio_actual - stop_loss) / precio_actual) * 100
        
        # Stop máximo 18% (breakouts pueden ser más amplios)
        if riesgo_pct > 18 or riesgo_pct < 2:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 10: CALCULAR OBJETIVO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Proyección 1: Altura de consolidación
        altura_max = df['High'].tail(consolidacion_dias).max()
        if isinstance(altura_max, pd.Series):
            altura_max = altura_max.item()
        altura_max = float(altura_max)
        
        altura_consolidacion = altura_max - minimo_consolidacion
        objetivo_proyeccion = precio_actual + (altura_consolidacion * 1.0)
        
        # Proyección 2: Siguiente resistencia (si existe)
        objetivo_resistencia = None
        if len(resistencias) > 1:
            for r in resistencias[1:]:
                if r > precio_actual * 1.05:  # Al menos 5% arriba
                    objetivo_resistencia = r * 0.98  # 2% antes
                    break
        
        # Usar el más conservador
        if objetivo_resistencia and objetivo_resistencia < objetivo_proyeccion:
            objetivo = objetivo_resistencia
        else:
            objetivo = objetivo_proyeccion
        
        # Objetivo mínimo: RR 2.5
        objetivo_minimo = precio_actual + (riesgo_pct * 2.5 * precio_actual / 100)
        if objetivo < objetivo_minimo:
            objetivo = objetivo_minimo
        
        beneficio_pct = ((objetivo - precio_actual) / precio_actual) * 100
        rr = beneficio_pct / riesgo_pct if riesgo_pct > 0 else 0
        
        # RR mínimo 2.5
        if rr < 2.5:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 11: CALCULAR SETUP SCORE (0-10)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        score = 0
        
        # 1. Distancia a máximo (0-2 pts)
        if abs(distancia_maximo_pct) < 0.5:
            score += 2
        elif abs(distancia_maximo_pct) < 1.5:
            score += 1
        
        # 2. Volumen ruptura (0-3 pts)
        if ratio_volumen >= 2.5:
            score += 3
        elif ratio_volumen >= 2.0:
            score += 2
        elif ratio_volumen >= 1.5:
            score += 1
        
        # 3. RSI momentum (0-2 pts)
        if 60 <= rsi_actual <= 72:
            score += 2
        elif 55 <= rsi_actual < 60 or 72 < rsi_actual <= 75:
            score += 1
        
        # 4. Consolidación (0-1 pt)
        if consolidacion_dias >= 15:
            score += 1
        
        # 5. ATR expansión (0-1 pt)
        atr_promedio = df['ATR'].rolling(20).mean().iloc[-1]
        if isinstance(atr_promedio, pd.Series):
            atr_promedio = atr_promedio.item()
        atr_promedio = float(atr_promedio)
        
        if atr_actual > atr_promedio * 1.15:
            score += 1
        
        # 6. RR alto (0-1 pt)
        if rr >= 4.0:
            score += 1
        
        # 7. Pendiente MM20 (0-1 pt)
        if pendiente_mm20 > 1.0:
            score += 1
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 12: CONSTRUIR Y RETORNAR RESULTADO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        return {
            'ticker': ticker,
            'precio_actual': round(precio_actual, 2),
            'entrada': round(precio_actual, 2),
            'stop': round(stop_loss, 2),
            'objetivo': round(objetivo, 2),
            'riesgo_pct': round(riesgo_pct, 2),
            'beneficio_pct': round(beneficio_pct, 2),
            'rr': round(rr, 2),
            'setup_score': score,
            'tipo': 'BREAKOUT',
            'resistencia_rota': round(resistencia_principal, 2),
            'consolidacion_dias': consolidacion_dias,
            'volumen_ruptura': round(ratio_volumen, 2),
            'rsi': round(rsi_actual, 1),
            'atr': round(atr_actual, 2),
            'mm20': round(mm20_actual, 2),
            'mm50': round(mm50_actual, 2) if pd.notna(mm50_actual) else None,
            'distancia_maximo_pct': round(distancia_maximo_pct, 2),
            'pendiente_mm20': round(pendiente_mm20, 2),
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
    except Exception as e:
        print(f"Error procesando {ticker}: {str(e)}")
        return None


def identificar_resistencias(df, ventana=5, tolerancia=2.5):
    """
    Identifica niveles de resistencia (máximos locales)
    
    Args:
        df: DataFrame con precios
        ventana: Ventana para detectar máximos locales
        tolerancia: % para agrupar niveles cercanos
    
    Returns:
        Lista de niveles de resistencia ordenados (mayor a menor)
    """
    resistencias = []
    
    # Detectar máximos locales
    for i in range(ventana, len(df) - ventana):
        ventana_high = df['High'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['High'].iloc[i]
        
        # Convertir a float si es Series
        if isinstance(valor_actual, pd.Series):
            valor_actual = valor_actual.item()
        
        max_ventana = ventana_high.max()
        if isinstance(max_ventana, pd.Series):
            max_ventana = max_ventana.item()
        
        if float(valor_actual) == float(max_ventana):
            resistencias.append(float(valor_actual))
    
    if not resistencias:
        return []
    
    # Agrupar resistencias cercanas
    resistencias.sort(reverse=True)
    resistencias_agrupadas = []
    
    for r in resistencias:
        if not resistencias_agrupadas:
            resistencias_agrupadas.append(r)
        else:
            # Verificar si está cerca de alguna resistencia ya agrupada
            es_nuevo = True
            for r_existente in resistencias_agrupadas:
                distancia = abs(r - r_existente) / r_existente * 100
                if distancia < tolerancia:
                    es_nuevo = False
                    break
            
            if es_nuevo:
                resistencias_agrupadas.append(r)
    
    return resistencias_agrupadas[:5]  # Top 5


def detectar_consolidacion(df):
    """
    Detecta período de consolidación (rango lateral)
    
    Args:
        df: DataFrame con precios
    
    Returns:
        Número de días consolidando (0 si no hay consolidación)
    """
    if len(df) < 10:
        return 0
    
    # Buscar ventana donde precio está en rango estrecho
    for ventana in range(min(30, len(df)), 9, -1):
        datos_ventana = df.tail(ventana)
        
        maximo = datos_ventana['High'].max()
        minimo = datos_ventana['Low'].min()
        
        # Convertir a float si son Series
        if isinstance(maximo, pd.Series):
            maximo = maximo.item()
        if isinstance(minimo, pd.Series):
            minimo = minimo.item()
        
        maximo = float(maximo)
        minimo = float(minimo)
        
        if minimo == 0:
            continue
        
        rango_pct = ((maximo - minimo) / minimo) * 100
        
        # Consolidación si rango < 10%
        if rango_pct <= 10:
            return ventana
    
    return 0


def calcular_atr(df, periodo=14):
    """
    Calcula Average True Range (ATR)
    
    Args:
        df: DataFrame con OHLC
        periodo: Periodo para el cálculo
    
    Returns:
        Series con valores ATR
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periodo).mean()
    
    return atr


def calcular_rsi(series, periodo=14):
    """
    Calcula RSI (Relative Strength Index)
    
    Args:
        series: Series de precios
        periodo: Periodo para el cálculo
    
    Returns:
        Series con valores RSI
    """
    delta = series.diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    
    rs = avg_ganancia / avg_perdida
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def escanear_mercado_breakout(tickers_list):
    """
    Escanea lista de tickers buscando oportunidades BREAKOUT
    
    Args:
        tickers_list: Lista de tickers (ej: ['TEF.MC', 'SAN.MC'])
    
    Returns:
        Lista de señales ordenadas por setup_score
    """
    señales = []
    
    print(f"\n🔍 Escaneando {len(tickers_list)} valores buscando BREAKOUTS...\n")
    
    for ticker in tickers_list:
        try:
            señal = detectar_breakout_swing(ticker)
            if señal:
                señales.append(señal)
                print(f"✅ {ticker}: BREAKOUT detectado (Score: {señal['setup_score']}/10, RR: {señal['rr']})")
        except Exception as e:
            print(f"❌ {ticker}: Error - {str(e)}")
    
    # Ordenar por setup_score descendente
    señales.sort(key=lambda x: x['setup_score'], reverse=True)
    
    print(f"\n📊 Total señales BREAKOUT: {len(señales)}")
    
    return señales


# ═══════════════════════════════════════════════════════════════
# TESTING - Ejemplo de uso
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    print("═" * 60)
    print("SISTEMA DE DETECCIÓN DE BREAKOUTS")
    print("Estrategia: Rupturas de resistencia")
    print("═" * 60)
    
    # Test con valores individuales
    tickers_test = ['ACS.MC', 'REP.MC', 'BBVA.MC', 'TEF.MC', 'SAN.MC']
    
    señales = escanear_mercado_breakout(tickers_test)
    
    if señales:
        print("\n" + "=" * 60)
        print("SEÑALES DETECTADAS:")
        print("=" * 60)
        
        for señal in señales:
            print(f"\n{señal['ticker']}:")
            print(f"  Entrada:     {señal['entrada']}€")
            print(f"  Stop:        {señal['stop']}€ (-{señal['riesgo_pct']}%)")
            print(f"  Objetivo:    {señal['objetivo']}€ (+{señal['beneficio_pct']}%)")
            print(f"  RR:          {señal['rr']}")
            print(f"  Setup Score: {señal['setup_score']}/10")
            print(f"  Resistencia: {señal['resistencia_rota']}€")
            print(f"  Volumen:     {señal['volumen_ruptura']}x")
            print(f"  RSI:         {señal['rsi']}")
    else:
        print("\n⚠️  No se detectaron oportunidades BREAKOUT en este momento")
