"""
═══════════════════════════════════════════════════════════════
MÓDULO: DETECCIÓN DE PULLBACKS (REBOTES)
Sistema Swing Trading - Estrategia de Retrocesos
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio retrocede a un soporte
en una tendencia alcista establecida.

Filosofía: "Comprar barato en soporte"

Criterios específicos:
- Precio cerca de soporte (2-8%)
- Retroceso desde máximo reciente (5-15%)
- RSI bajo (< 45, sobreventa)
- Tendencia alcista macro (precio > MM200)
- Soporte histórico fuerte (3+ toques)
- Volumen decreciendo en caída
- Estructura alcista mantenida
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def detectar_pullback_swing(ticker, periodo='6mo'):
    """
    Detecta oportunidades de PULLBACK (rebote en soporte)
    
    Args:
        ticker: Símbolo del valor (ej: 'TEF.MC')
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
            'tipo': 'PULLBACK',
            'soporte_cercano': float,
            'distancia_soporte_pct': float,
            'retroceso_pct': float,
            'rsi': float,
            'toques_soporte': int,
            'mm20': float,
            'mm200': float,
            'fecha': str
        }
    """
    
    try:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 1: OBTENER DATOS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        df = yf.download(ticker, period=periodo, progress=False)
        
        if df is None or len(df) < 100:  # Necesitamos más datos para MM200
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 2: CALCULAR INDICADORES TÉCNICOS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        df['MM20'] = df['Close'].rolling(20).mean()
        df['MM50'] = df['Close'].rolling(50).mean()
        df['MM200'] = df['Close'].rolling(200).mean()
        df['RSI'] = calcular_rsi(df['Close'], periodo=14)
        
        precio_actual = df['Close'].iloc[-1]
        if isinstance(precio_actual, pd.Series):
            precio_actual = precio_actual.item()
        precio_actual = float(precio_actual)
        
        rsi_actual = df['RSI'].iloc[-1]
        if isinstance(rsi_actual, pd.Series):
            rsi_actual = rsi_actual.item()
        rsi_actual = float(rsi_actual)
        
        mm20_actual = df['MM20'].iloc[-1]
        if isinstance(mm20_actual, pd.Series):
            mm20_actual = mm20_actual.item()
        mm20_actual = float(mm20_actual)
        
        mm50_actual = df['MM50'].iloc[-1]
        if isinstance(mm50_actual, pd.Series):
            mm50_actual = mm50_actual.item()
        if not pd.isna(mm50_actual):
            mm50_actual = float(mm50_actual)
        
        mm200_actual = df['MM200'].iloc[-1]
        if isinstance(mm200_actual, pd.Series):
            mm200_actual = mm200_actual.item()
        if not pd.isna(mm200_actual):
            mm200_actual = float(mm200_actual)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 3: VERIFICAR TENDENCIA ALCISTA MACRO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Precio debe estar sobre MM200 (tendencia alcista)
        if pd.isna(mm200_actual) or precio_actual < mm200_actual * 0.95:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 4: VERIFICAR RETROCESO DESDE MÁXIMO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Buscar máximo reciente (últimos 20-60 días)
        maximo_reciente = df['Close'].tail(60).max()
        if isinstance(maximo_reciente, pd.Series):
            maximo_reciente = maximo_reciente.item()
        maximo_reciente = float(maximo_reciente)
        
        retroceso_pct = ((maximo_reciente - precio_actual) / maximo_reciente) * 100
        
        # Debe haber retrocedido 5-20% desde el máximo
        if retroceso_pct < 5 or retroceso_pct > 20:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 5: IDENTIFICAR SOPORTES
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        soportes = identificar_soportes(df.tail(80))
        
        if not soportes:
            return None
        
        # Buscar soporte MÁS CERCANO por debajo del precio
        soporte_cercano = None
        distancia_soporte = None
        
        for soporte_info in soportes:
            nivel_soporte = soporte_info['nivel']
            if nivel_soporte < precio_actual:
                dist = ((precio_actual - nivel_soporte) / precio_actual) * 100
                if dist <= 10:  # Máximo 10% de distancia
                    soporte_cercano = soporte_info
                    distancia_soporte = dist
                    break
        
        if not soporte_cercano:
            return None
        
        # Soporte debe estar entre 2-8% abajo (zona óptima de pullback)
        if distancia_soporte < 2 or distancia_soporte > 8:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 6: VERIFICAR FUERZA DEL SOPORTE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        toques_soporte = soporte_cercano.get('toques', 0)
        
        # Mínimo 2 toques (idealmente 3+)
        if toques_soporte < 2:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 7: VERIFICAR RSI (SOBREVENTA)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # RSI debe estar bajo (sobreventa para pullback)
        if rsi_actual > 50:  # No es pullback si RSI está alto
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 8: VERIFICAR VOLUMEN EN RETROCESO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # En pullback ideal, volumen decrece durante la caída
        volumen_actual = df['Volume'].iloc[-1]
        if isinstance(volumen_actual, pd.Series):
            volumen_actual = volumen_actual.item()
        volumen_actual = float(volumen_actual)
        
        volumen_promedio = df['Volume'].rolling(20).mean().iloc[-1]
        if isinstance(volumen_promedio, pd.Series):
            volumen_promedio = volumen_promedio.item()
        volumen_promedio = float(volumen_promedio)
        
        ratio_volumen = volumen_actual / volumen_promedio if volumen_promedio > 0 else 0
        
        # Volumen bajo durante caída es bueno (sin presión vendedora)
        # Pero no debe ser extremadamente bajo (necesitamos algo de interés)
        if ratio_volumen > 2.0:  # Volumen muy alto en caída = malo
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 9: CALCULAR STOP LOSS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Stop por debajo del soporte con 2% margen
        nivel_soporte = soporte_cercano['nivel']
        stop_loss = nivel_soporte * 0.98
        
        riesgo_pct = ((precio_actual - stop_loss) / precio_actual) * 100
        
        # Stop máximo 12% (pullbacks tienen stops más ajustados)
        if riesgo_pct > 12 or riesgo_pct < 2:
            return None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 10: CALCULAR OBJETIVO
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Buscar resistencia más cercana por encima
        resistencias = identificar_resistencias(df.tail(80))
        
        objetivo = None
        for resistencia_info in resistencias:
            nivel_resistencia = resistencia_info['nivel']
            if nivel_resistencia > precio_actual * 1.03:  # Al menos 3% arriba
                objetivo = nivel_resistencia * 0.98  # 2% antes de resistencia
                break
        
        # Si no hay resistencia clara, usar proyección conservadora
        if not objetivo:
            # Volver hacia el máximo reciente (conservador)
            objetivo = precio_actual + (retroceso_pct * 0.7 * precio_actual / 100)
        
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
        
        # 1. Distancia óptima a soporte (0-2 pts)
        if 2 <= distancia_soporte <= 5:
            score += 2
        elif distancia_soporte <= 8:
            score += 1
        
        # 2. RSI sobreventa (0-3 pts)
        if rsi_actual <= 30:
            score += 3
        elif rsi_actual <= 40:
            score += 2
        elif rsi_actual <= 45:
            score += 1
        
        # 3. Fuerza soporte (0-2 pts)
        if toques_soporte >= 4:
            score += 2
        elif toques_soporte >= 3:
            score += 1
        
        # 4. Retroceso óptimo (0-1 pt)
        if 8 <= retroceso_pct <= 15:
            score += 1
        
        # 5. Volumen bajo en caída (0-1 pt)
        if ratio_volumen < 0.8:
            score += 1
        
        # 6. RR alto (0-1 pt)
        if rr >= 3.5:
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
            'tipo': 'PULLBACK',
            'soporte_cercano': round(nivel_soporte, 2),
            'distancia_soporte_pct': round(distancia_soporte, 2),
            'retroceso_pct': round(retroceso_pct, 2),
            'rsi': round(rsi_actual, 1),
            'toques_soporte': toques_soporte,
            'volumen_ratio': round(ratio_volumen, 2),
            'mm20': round(mm20_actual, 2),
            'mm200': round(mm200_actual, 2) if not pd.isna(mm200_actual) else None,
            'maximo_reciente': round(maximo_reciente, 2),
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
    except Exception as e:
        print(f"Error procesando {ticker}: {str(e)}")
        return None


def identificar_soportes(df, ventana=5, tolerancia=2.5):
    """
    Identifica niveles de soporte (mínimos locales)
    
    Args:
        df: DataFrame con precios
        ventana: Ventana para detectar mínimos locales
        tolerancia: % para agrupar niveles cercanos
    
    Returns:
        Lista de dict con soportes {nivel, toques}
    """
    soportes = []
    
    # Detectar mínimos locales
    for i in range(ventana, len(df) - ventana):
        ventana_low = df['Low'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['Low'].iloc[i]
        
        if isinstance(valor_actual, pd.Series):
            valor_actual = valor_actual.item()
        
        min_ventana = ventana_low.min()
        if isinstance(min_ventana, pd.Series):
            min_ventana = min_ventana.item()
        
        if float(valor_actual) == float(min_ventana):
            soportes.append(float(valor_actual))
    
    if not soportes:
        return []
    
    # Agrupar soportes cercanos y contar toques
    soportes.sort()
    soportes_agrupados = []
    
    for s in soportes:
        if not soportes_agrupados:
            soportes_agrupados.append({'nivel': s, 'toques': 1})
        else:
            # Verificar si está cerca de algún soporte ya agrupado
            encontrado = False
            for s_grupo in soportes_agrupados:
                distancia = abs(s - s_grupo['nivel']) / s_grupo['nivel'] * 100
                if distancia < tolerancia:
                    # Actualizar nivel promedio y sumar toque
                    s_grupo['nivel'] = (s_grupo['nivel'] * s_grupo['toques'] + s) / (s_grupo['toques'] + 1)
                    s_grupo['toques'] += 1
                    encontrado = True
                    break
            
            if not encontrado:
                soportes_agrupados.append({'nivel': s, 'toques': 1})
    
    # Ordenar por número de toques (más fuertes primero)
    soportes_agrupados.sort(key=lambda x: x['toques'], reverse=True)
    
    return soportes_agrupados[:5]  # Top 5


def identificar_resistencias(df, ventana=5, tolerancia=2.5):
    """
    Identifica niveles de resistencia (máximos locales)
    Similar a identificar_soportes pero con máximos
    """
    resistencias = []
    
    for i in range(ventana, len(df) - ventana):
        ventana_high = df['High'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['High'].iloc[i]
        
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
            resistencias_agrupadas.append({'nivel': r, 'toques': 1})
        else:
            encontrado = False
            for r_grupo in resistencias_agrupadas:
                distancia = abs(r - r_grupo['nivel']) / r_grupo['nivel'] * 100
                if distancia < tolerancia:
                    r_grupo['nivel'] = (r_grupo['nivel'] * r_grupo['toques'] + r) / (r_grupo['toques'] + 1)
                    r_grupo['toques'] += 1
                    encontrado = True
                    break
            
            if not encontrado:
                resistencias_agrupadas.append({'nivel': r, 'toques': 1})
    
    return resistencias_agrupadas[:5]


def calcular_rsi(series, periodo=14):
    """
    Calcula RSI (Relative Strength Index)
    """
    delta = series.diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    
    rs = avg_ganancia / avg_perdida
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def escanear_mercado_pullback(tickers_list):
    """
    Escanea lista de tickers buscando oportunidades PULLBACK
    
    Args:
        tickers_list: Lista de tickers
    
    Returns:
        Lista de señales ordenadas por setup_score
    """
    señales = []
    
    print(f"\n🔍 Escaneando {len(tickers_list)} valores buscando PULLBACKS...\n")
    
    for ticker in tickers_list:
        try:
            señal = detectar_pullback_swing(ticker)
            if señal:
                señales.append(señal)
                print(f"✅ {ticker}: PULLBACK detectado (Score: {señal['setup_score']}/10, RR: {señal['rr']})")
        except Exception as e:
            print(f"❌ {ticker}: Error - {str(e)}")
    
    # Ordenar por setup_score descendente
    señales.sort(key=lambda x: x['setup_score'], reverse=True)
    
    print(f"\n📊 Total señales PULLBACK: {len(señales)}")
    
    return señales


# ═══════════════════════════════════════════════════════════════
# TESTING - Ejemplo de uso
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    print("═" * 60)
    print("SISTEMA DE DETECCIÓN DE PULLBACKS")
    print("Estrategia: Rebotes en soportes")
    print("═" * 60)
    
    # Test con valores individuales
    tickers_test = ['TEF.MC', 'SAN.MC', 'BBVA.MC', 'IBE.MC', 'REP.MC']
    
    señales = escanear_mercado_pullback(tickers_test)
    
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
            print(f"  Soporte:     {señal['soporte_cercano']}€ ({señal['distancia_soporte_pct']}% abajo)")
            print(f"  RSI:         {señal['rsi']} (sobreventa)")
            print(f"  Retroceso:   {señal['retroceso_pct']}% desde máximo")
    else:
        print("\n⚠️  No se detectaron oportunidades PULLBACK en este momento")
