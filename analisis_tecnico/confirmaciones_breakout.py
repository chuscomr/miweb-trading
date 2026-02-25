"""
═══════════════════════════════════════════════════════════════
MÓDULO: CONFIRMACIONES PROFESIONALES PARA BREAKOUTS
Sistema de validación 0-100 puntos para rupturas
═══════════════════════════════════════════════════════════════

Valida señales de BREAKOUT con 10 factores específicos para rupturas.

Diferencias clave vs PULLBACK:
- Volumen en RUPTURA (no en rebote)
- RSI alto 60-75 = BUENO (momentum fuerte)
- NO necesita soporte cercano
- Necesita consolidación previa
- Resistencia clara rota

Puntuación:
- 75-100: EXCELENTE (compra prioritaria)
- 60-74:  BUENO (compra)
- 45-59:  ACEPTABLE (compra condicional)
- 30-44:  DUDOSO (esperar)
- 0-29:   MALO (no operar)
"""

import pandas as pd
import numpy as np


def calcular_confirmaciones_breakout(df, señal_swing):
    """
    Valida señales de BREAKOUT con sistema profesional 0-100
    
    10 Factores específicos para rupturas:
    1. Volumen en ruptura (0-30 pts) - MUY CRÍTICO
    2. Fuerza resistencia rota (0-15 pts)
    3. RSI momentum 60-75 (0-10 pts)
    4. ATR creciendo (0-10 pts)
    5. Precio vs máximo histórico (0-15 pts)
    6. MACD acelerando (0-10 pts)
    7. Consolidación previa (0-10 pts)
    8. MM20 pendiente fuerte (0-10 pts)
    9. Velas alcistas consecutivas (0-10 pts)
    10. Sin resistencia próxima (0-10 pts)
    
    Args:
        df: DataFrame con datos OHLCV y indicadores
        señal_swing: dict con datos de logica_breakout
    
    Returns:
        dict {
            'puntuacion': int (0-100),
            'nivel': str,
            'recomendacion': str,
            'color': str,
            'desglose': dict con detalle de cada factor
        }
    """
    
    puntuacion_total = 0
    desglose = {}
    
    # Extraer datos de la señal
    ticker = señal_swing.get('ticker', 'N/A')
    precio_actual = señal_swing.get('precio_actual', 0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 1: VOLUMEN EN RUPTURA (0-30 pts) - MUY CRÍTICO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    volumen_ruptura = señal_swing.get('volumen_ruptura', 1.0)
    
    if volumen_ruptura >= 2.5:
        puntos_volumen = 30
        detalle_vol = f"🔥 MUY ALTA ({volumen_ruptura:.1f}x promedio)"
        color_vol = "positivo"
    elif volumen_ruptura >= 2.0:
        puntos_volumen = 25
        detalle_vol = f"✅ ALTA ({volumen_ruptura:.1f}x promedio)"
        color_vol = "positivo"
    elif volumen_ruptura >= 1.5:
        puntos_volumen = 20
        detalle_vol = f"✅ Buena ({volumen_ruptura:.1f}x promedio)"
        color_vol = "positivo"
    elif volumen_ruptura >= 1.2:
        puntos_volumen = 10
        detalle_vol = f"Normal ({volumen_ruptura:.1f}x promedio)"
        color_vol = "neutro"
    else:
        puntos_volumen = 0
        detalle_vol = f"❌ BAJA ({volumen_ruptura:.1f}x promedio)"
        color_vol = "negativo"
    
    desglose['volumen_ruptura'] = {
        'nombre': 'Volumen Ruptura',
        'puntos': puntos_volumen,
        'detalle': detalle_vol,
        'color': color_vol
    }
    puntuacion_total += puntos_volumen
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 2: FUERZA RESISTENCIA ROTA (0-15 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    resistencia_rota = señal_swing.get('resistencia_rota', 0)
    
    if resistencia_rota > 0:
        # Verificar cuánto ha superado la resistencia
        distancia_pct = ((precio_actual - resistencia_rota) / resistencia_rota) * 100
        
        if distancia_pct >= 2.0:
            puntos_resistencia = 15
            detalle_res = f"✅ Rota con claridad ({resistencia_rota:.2f}€, +{distancia_pct:.1f}%)"
            color_res = "positivo"
        elif distancia_pct >= 0.5:
            puntos_resistencia = 12
            detalle_res = f"✅ Rota ({resistencia_rota:.2f}€, +{distancia_pct:.1f}%)"
            color_res = "positivo"
        elif distancia_pct >= -0.5:
            puntos_resistencia = 8
            detalle_res = f"En resistencia ({resistencia_rota:.2f}€)"
            color_res = "neutro"
        else:
            puntos_resistencia = 3
            detalle_res = f"⚠️ Aún bajo resistencia ({resistencia_rota:.2f}€)"
            color_res = "neutro"
    else:
        puntos_resistencia = 0
        detalle_res = "Sin resistencia identificada"
        color_res = "neutro"
    
    desglose['resistencia'] = {
        'nombre': 'Fuerza Resistencia',
        'puntos': puntos_resistencia,
        'detalle': detalle_res,
        'color': color_res
    }
    puntuacion_total += puntos_resistencia
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 3: RSI MOMENTUM (0-10 pts) - Alto = BUENO en breakout
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    rsi = señal_swing.get('rsi', 50)
    
    if 62 <= rsi <= 72:
        puntos_rsi = 10
        detalle_rsi = f"✅ ÓPTIMO ({rsi:.1f}) - Momentum fuerte controlado"
        color_rsi = "positivo"
    elif 55 <= rsi < 62 or 72 < rsi <= 75:
        puntos_rsi = 7
        detalle_rsi = f"Bueno ({rsi:.1f}) - Momentum positivo"
        color_rsi = "positivo"
    elif 50 <= rsi < 55 or 75 < rsi <= 78:
        puntos_rsi = 3
        detalle_rsi = f"Aceptable ({rsi:.1f})"
        color_rsi = "neutro"
    elif rsi > 78:
        puntos_rsi = -5
        detalle_rsi = f"⚠️ Sobrecompra extrema ({rsi:.1f})"
        color_rsi = "negativo"
    else:
        puntos_rsi = 0
        detalle_rsi = f"Bajo ({rsi:.1f}) - Poco momentum"
        color_rsi = "neutro"
    
    desglose['rsi'] = {
        'nombre': 'RSI Momentum',
        'puntos': puntos_rsi,
        'detalle': detalle_rsi,
        'color': color_rsi
    }
    puntuacion_total += puntos_rsi
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 4: ATR CRECIENDO (0-10 pts) - Expansión volatilidad
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if 'ATR' in df.columns and len(df) >= 20:
        atr_actual = df['ATR'].iloc[-1]
        if isinstance(atr_actual, pd.Series):
            atr_actual = atr_actual.item()
        
        atr_promedio = df['ATR'].rolling(20).mean().iloc[-1]
        if isinstance(atr_promedio, pd.Series):
            atr_promedio = atr_promedio.item()
        
        ratio_atr = atr_actual / atr_promedio if atr_promedio > 0 else 1.0
        
        if ratio_atr >= 1.25:
            puntos_atr = 10
            detalle_atr = f"✅ Expansión fuerte ({ratio_atr:.2f}x)"
            color_atr = "positivo"
        elif ratio_atr >= 1.15:
            puntos_atr = 7
            detalle_atr = f"✅ Expansión moderada ({ratio_atr:.2f}x)"
            color_atr = "positivo"
        elif ratio_atr >= 1.05:
            puntos_atr = 3
            detalle_atr = f"Ligera expansión ({ratio_atr:.2f}x)"
            color_atr = "neutro"
        else:
            puntos_atr = 0
            detalle_atr = f"Sin expansión ({ratio_atr:.2f}x)"
            color_atr = "neutro"
    else:
        puntos_atr = 0
        detalle_atr = "No disponible"
        color_atr = "neutro"
    
    desglose['atr'] = {
        'nombre': 'ATR (Volatilidad)',
        'puntos': puntos_atr,
        'detalle': detalle_atr,
        'color': color_atr
    }
    puntuacion_total += puntos_atr
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 5: PRECIO VS MÁXIMO (0-15 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    distancia_maximo = señal_swing.get('distancia_maximo_pct', 0)
    
    if abs(distancia_maximo) <= 0.5:
        puntos_maximo = 15
        detalle_max = f"✅ En máximo absoluto ({distancia_maximo:+.1f}%)"
        color_max = "positivo"
    elif abs(distancia_maximo) <= 1.5:
        puntos_maximo = 12
        detalle_max = f"✅ Muy cerca máximo ({distancia_maximo:+.1f}%)"
        color_max = "positivo"
    elif abs(distancia_maximo) <= 3.0:
        puntos_maximo = 8
        detalle_max = f"Cerca máximo ({distancia_maximo:+.1f}%)"
        color_max = "neutro"
    else:
        puntos_maximo = 0
        detalle_max = f"Lejos máximo ({distancia_maximo:+.1f}%)"
        color_max = "negativo"
    
    desglose['distancia_maximo'] = {
        'nombre': 'Distancia Máximo',
        'puntos': puntos_maximo,
        'detalle': detalle_max,
        'color': color_max
    }
    puntuacion_total += puntos_maximo
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 6: MACD ACELERANDO (0-10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if 'MACD' in df.columns and 'MACD_signal' in df.columns and len(df) >= 3:
        macd = df['MACD'].iloc[-1]
        macd_signal = df['MACD_signal'].iloc[-1]
        
        if isinstance(macd, pd.Series):
            macd = macd.item()
        if isinstance(macd_signal, pd.Series):
            macd_signal = macd_signal.item()
        
        histograma = macd - macd_signal
        histograma_anterior = df['MACD'].iloc[-2] - df['MACD_signal'].iloc[-2]
        
        if isinstance(histograma_anterior, pd.Series):
            histograma_anterior = histograma_anterior.item()
        
        if histograma > 0 and histograma > histograma_anterior:
            puntos_macd = 10
            detalle_macd = f"✅ ALCISTA acelerando ({histograma:.3f})"
            color_macd = "positivo"
        elif histograma > 0:
            puntos_macd = 7
            detalle_macd = f"✅ ALCISTA ({histograma:.3f})"
            color_macd = "positivo"
        elif histograma > histograma_anterior:
            puntos_macd = 3
            detalle_macd = f"Mejorando ({histograma:.3f})"
            color_macd = "neutro"
        else:
            puntos_macd = 0
            detalle_macd = f"Bajista ({histograma:.3f})"
            color_macd = "negativo"
    else:
        # Calcular MACD si no existe
        try:
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            histograma = macd.iloc[-1] - macd_signal.iloc[-1]
            
            if isinstance(histograma, pd.Series):
                histograma = histograma.item()
            
            if histograma > 0:
                puntos_macd = 7
                detalle_macd = f"✅ Momentum alcista ({histograma:.3f})"
                color_macd = "positivo"
            else:
                puntos_macd = 0
                detalle_macd = f"Momentum bajista ({histograma:.3f})"
                color_macd = "negativo"
        except:
            puntos_macd = 0
            detalle_macd = "No disponible"
            color_macd = "neutro"
    
    desglose['macd'] = {
        'nombre': 'MACD',
        'puntos': puntos_macd,
        'detalle': detalle_macd,
        'color': color_macd
    }
    puntuacion_total += puntos_macd
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 7: CONSOLIDACIÓN PREVIA (0-10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    consolidacion_dias = señal_swing.get('consolidacion_dias', 0)
    
    if consolidacion_dias >= 20:
        puntos_consol = 10
        detalle_consol = f"✅ FUERTE ({consolidacion_dias} días)"
        color_consol = "positivo"
    elif consolidacion_dias >= 15:
        puntos_consol = 8
        detalle_consol = f"✅ Buena ({consolidacion_dias} días)"
        color_consol = "positivo"
    elif consolidacion_dias >= 10:
        puntos_consol = 5
        detalle_consol = f"Moderada ({consolidacion_dias} días)"
        color_consol = "neutro"
    else:
        puntos_consol = 0
        detalle_consol = f"Débil ({consolidacion_dias} días)"
        color_consol = "negativo"
    
    desglose['consolidacion'] = {
        'nombre': 'Consolidación Previa',
        'puntos': puntos_consol,
        'detalle': detalle_consol,
        'color': color_consol
    }
    puntuacion_total += puntos_consol
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 8: MM20 PENDIENTE FUERTE (0-10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    pendiente_mm20 = señal_swing.get('pendiente_mm20', 0)
    
    if pendiente_mm20 >= 2.0:
        puntos_mm20 = 10
        detalle_mm20 = f"✅ MUY ALCISTA (+{pendiente_mm20:.1f}%)"
        color_mm20 = "positivo"
    elif pendiente_mm20 >= 1.0:
        puntos_mm20 = 7
        detalle_mm20 = f"✅ Alcista (+{pendiente_mm20:.1f}%)"
        color_mm20 = "positivo"
    elif pendiente_mm20 >= 0.3:
        puntos_mm20 = 3
        detalle_mm20 = f"Ligera alza (+{pendiente_mm20:.1f}%)"
        color_mm20 = "neutro"
    elif pendiente_mm20 >= -0.5:
        puntos_mm20 = 0
        detalle_mm20 = f"Plana ({pendiente_mm20:+.1f}%)"
        color_mm20 = "neutro"
    else:
        puntos_mm20 = -5
        detalle_mm20 = f"❌ Bajista ({pendiente_mm20:+.1f}%)"
        color_mm20 = "negativo"
    
    desglose['mm20_pendiente'] = {
        'nombre': 'Pendiente MM20',
        'puntos': puntos_mm20,
        'detalle': detalle_mm20,
        'color': color_mm20
    }
    puntuacion_total += puntos_mm20
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 9: VELAS ALCISTAS CONSECUTIVAS (0-10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if len(df) >= 5:
        velas_verdes = 0
        for i in range(1, min(6, len(df) + 1)):
            close = df['Close'].iloc[-i]
            open_price = df['Open'].iloc[-i]
            
            if isinstance(close, pd.Series):
                close = close.item()
            if isinstance(open_price, pd.Series):
                open_price = open_price.item()
            
            if close > open_price:
                velas_verdes += 1
            else:
                break
        
        if velas_verdes >= 4:
            puntos_velas = 10
            detalle_velas = f"✅ {velas_verdes} velas alcistas seguidas"
            color_velas = "positivo"
        elif velas_verdes >= 3:
            puntos_velas = 7
            detalle_velas = f"✅ {velas_verdes} velas alcistas"
            color_velas = "positivo"
        elif velas_verdes >= 2:
            puntos_velas = 3
            detalle_velas = f"{velas_verdes} velas alcistas"
            color_velas = "neutro"
        else:
            puntos_velas = 0
            detalle_velas = f"Pocas velas alcistas ({velas_verdes})"
            color_velas = "neutro"
    else:
        puntos_velas = 0
        detalle_velas = "No disponible"
        color_velas = "neutro"
    
    desglose['velas_alcistas'] = {
        'nombre': 'Velas Alcistas',
        'puntos': puntos_velas,
        'detalle': detalle_velas,
        'color': color_velas
    }
    puntuacion_total += puntos_velas
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FACTOR 10: SIN RESISTENCIA PRÓXIMA (0-10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Buscar resistencias por encima del precio actual
    resistencias_encima = []
    if len(df) >= 30:
        for i in range(5, len(df) - 5):
            ventana = df['High'].iloc[i-5:i+6]
            valor = df['High'].iloc[i]
            
            if isinstance(valor, pd.Series):
                valor = valor.item()
            
            max_ventana = ventana.max()
            if isinstance(max_ventana, pd.Series):
                max_ventana = max_ventana.item()
            
            if float(valor) == float(max_ventana) and valor > precio_actual * 1.03:
                resistencias_encima.append(valor)
    
    if not resistencias_encima:
        puntos_res_proxima = 10
        detalle_res_proxima = "✅ Sin resistencias próximas"
        color_res_proxima = "positivo"
    else:
        resistencia_cercana = min(resistencias_encima)
        distancia = ((resistencia_cercana - precio_actual) / precio_actual) * 100
        
        if distancia >= 10:
            puntos_res_proxima = 7
            detalle_res_proxima = f"Resistencia lejana (+{distancia:.1f}%)"
            color_res_proxima = "positivo"
        elif distancia >= 5:
            puntos_res_proxima = 3
            detalle_res_proxima = f"Resistencia a +{distancia:.1f}%"
            color_res_proxima = "neutro"
        else:
            puntos_res_proxima = 0
            detalle_res_proxima = f"⚠️ Resistencia cerca (+{distancia:.1f}%)"
            color_res_proxima = "negativo"
    
    desglose['resistencia_proxima'] = {
        'nombre': 'Resistencias Superiores',
        'puntos': puntos_res_proxima,
        'detalle': detalle_res_proxima,
        'color': color_res_proxima
    }
    puntuacion_total += puntos_res_proxima
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # NORMALIZAR PUNTUACIÓN A 0-100
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Máximo teórico: 130 puntos (puede ser negativo por penalizaciones)
    puntuacion_normalizada = max(0, min(100, int((puntuacion_total / 130) * 100)))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DETERMINAR NIVEL Y RECOMENDACIÓN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if puntuacion_normalizada >= 75:
        nivel = "EXCELENTE"
        recomendacion = "🟢 COMPRA PRIORITARIA"
        color = "success"
    elif puntuacion_normalizada >= 60:
        nivel = "BUENO"
        recomendacion = "🟢 COMPRA"
        color = "success"
    elif puntuacion_normalizada >= 45:
        nivel = "ACEPTABLE"
        recomendacion = "🟡 COMPRA CONDICIONAL"
        color = "warning"
    elif puntuacion_normalizada >= 30:
        nivel = "DUDOSO"
        recomendacion = "🟠 ESPERAR MEJOR MOMENTO"
        color = "warning"
    else:
        nivel = "MALO"
        recomendacion = "🔴 NO OPERAR"
        color = "danger"
    
    return {
        'puntuacion': puntuacion_normalizada,
        'puntuacion_bruta': puntuacion_total,
        'nivel': nivel,
        'recomendacion': recomendacion,
        'color': color,
        'desglose': desglose,
        'tipo_estrategia': 'BREAKOUT'
    }


# ═══════════════════════════════════════════════════════════════
# TESTING - Ejemplo de uso
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import yfinance as yf
    from swing_trading.logica_breakout import detectar_breakout_swing
    
    print("═" * 60)
    print("SISTEMA DE CONFIRMACIÓN BREAKOUT")
    print("Análisis Técnico 0-100 para rupturas")
    print("═" * 60)
    
    # Test con ACS
    ticker = 'ACS.MC'
    print(f"\n🔍 Analizando {ticker}...")
    
    # Obtener señal Swing
    señal = detectar_breakout_swing(ticker)
    
    if señal:
        print(f"\n✅ Señal BREAKOUT detectada:")
        print(f"   Entrada: {señal['entrada']}€")
        print(f"   Stop: {señal['stop']}€")
        print(f"   RR: {señal['rr']}")
        print(f"   Setup Score: {señal['setup_score']}/10")
        
        # Obtener datos para análisis
        df = yf.download(ticker, period='6mo', progress=False)
        
        # Calcular indicadores necesarios
        df['MM20'] = df['Close'].rolling(20).mean()
        df['RSI'] = calcular_rsi_simple(df['Close'])
        df['ATR'] = calcular_atr_simple(df)
        
        # Analizar
        confirmaciones = calcular_confirmaciones_breakout(df, señal)
        
        print(f"\n📊 ANÁLISIS TÉCNICO PROFESIONAL:")
        print(f"   Puntuación: {confirmaciones['puntuacion']}/100")
        print(f"   Nivel: {confirmaciones['nivel']}")
        print(f"   Recomendación: {confirmaciones['recomendacion']}")
        
        print(f"\n📋 DESGLOSE DE FACTORES:")
        for key, factor in confirmaciones['desglose'].items():
            signo = "+" if factor['puntos'] > 0 else ""
            print(f"   {factor['nombre']:25} {signo}{factor['puntos']:3} pts - {factor['detalle']}")
    
    else:
        print(f"\n❌ No hay señal BREAKOUT en {ticker}")


def calcular_rsi_simple(series, periodo=14):
    """Cálculo simple de RSI para testing"""
    delta = series.diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    rs = avg_ganancia / avg_perdida
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calcular_atr_simple(df, periodo=14):
    """Cálculo simple de ATR para testing"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periodo).mean()
    return atr
