# analisis_tecnico.py - Sistema jerárquico de 4 niveles
import pandas as pd
import numpy as np


def generar_resumen_tecnico(df, indicadores_lista=None):
    """
    Sistema jerárquico de análisis técnico para swing trading.
    
    Estructura de 4 niveles:
    1. ESTRUCTURA (filtros eliminatorios): ADX, MM200
    2. TENDENCIA (contexto direccional): Alineación MMs, MACD
    3. MOMENTUM (fuerza): RSI, MACD histograma
    4. TIMING (refinamiento): Estocástico, S/R, Fibonacci, patrones
    
    Args:
        df: DataFrame con indicadores ya calculados
        indicadores_lista: Lista de indicadores activos (opcional)
    
    Returns:
        dict: Resumen técnico con señal jerárquica
    """
    if df is None or df.empty:
        return {
            'señal_global': 'neutral',
            'puntuacion': 0,
            'nivel_confianza': 'bajo',
            'razon': 'Sin datos suficientes',
            'desglose_compra': [],
            'desglose_venta': [],
            'desglose_neutral': [],
            'gauge_volumen': 0,
            'gauge_momentum': 0,
            'ratio_volumen': 1.0,
            'puntos_compra': 0,
            'puntos_venta': 0,
            'puntos_neutral': 0,
            # Compatibilidad
            'recomendacion': 'NEUTRAL',
            'puntuacion_global': 0,
            'color': 'neutral',
            'indicadores': {
                'puntuacion': 0,
                'compras': 0,
                'ventas': 0,
                'neutrales': 0,
                'detalles': []
            },
            'medias_moviles': {
                'puntuacion': 0,
                'compras': 0,
                'ventas': 0,
                'neutrales': 0,
                'detalles': []
            }
        }
    
    ultimo = df.iloc[-1]
    precio = ultimo['Close']
    
    # Variables de control jerárquico
    estructura_valida = True
    razon_bloqueo = None
    sesgo_tendencial = 0  # -2 (muy bajista) a +2 (muy alcista)
    score_momentum = 0
    score_timing = 0
    
    señales = []
    
    # ========================================
    # NIVEL 1: ESTRUCTURA (Filtros eliminatorios)
    # ========================================
    
    # Filtro 1: ADX - Fuerza de tendencia
    if 'ADX' in df.columns and pd.notna(ultimo['ADX']):
        adx = ultimo['ADX']
        
        if adx < 15:
            # Sin tendencia clara - mercado lateral
            estructura_valida = False
            razon_bloqueo = f'Sin tendencia (ADX={adx:.1f} < 15)'
            señales.append({
                'indicador': 'ADX',
                'señal': 'neutral',
                'peso': 0,
                'razon': 'Mercado lateral - no operar'
            })
        elif adx < 25:
            # Tendencia débil
            señales.append({
                'indicador': 'ADX',
                'señal': 'neutral',
                'peso': 0.3,
                'razon': f'Tendencia débil (ADX={adx:.1f})'
            })
        elif adx > 40:
            # Tendencia muy fuerte - reforzar señales
            señales.append({
                'indicador': 'ADX',
                'señal': 'neutral',
                'peso': 0.5,
                'razon': f'Tendencia muy fuerte (ADX={adx:.1f})'
            })
    
    # Filtro 2: MM200 - Contexto de largo plazo
    bajo_mm200 = False
    sobre_mm200 = False
    
    if 'MM200' in df.columns and pd.notna(ultimo['MM200']):
        mm200 = ultimo['MM200']
        distancia_mm200_pct = ((precio - mm200) / mm200) * 100
        
        if precio < mm200:
            bajo_mm200 = True
            sesgo_tendencial -= 1  # Sesgo bajista
            señales.append({
                'indicador': 'MM200',
                'señal': 'venta',
                'peso': 0.7,
                'razon': f'Precio bajo MM200 ({distancia_mm200_pct:.1f}%)'
            })
        else:
            sobre_mm200 = True
            sesgo_tendencial += 1  # Sesgo alcista
            señales.append({
                'indicador': 'MM200',
                'señal': 'compra',
                'peso': 0.7,
                'razon': f'Precio sobre MM200 (+{distancia_mm200_pct:.1f}%)'
            })
    
    # Si estructura no es válida, devolver señal neutral

    # ========================================
    # CALCULAR GAUGES (antes de validar estructura)
    # ========================================
    gauge_volumen = 0
    ratio_volumen = 1.0
    
    if 'Volume' in df.columns:
        volumen_actual = ultimo['Volume']
        volumen_promedio = df['Volume'].tail(10).mean()
        
        if volumen_promedio > 0:
            ratio_volumen = volumen_actual / volumen_promedio
            
            # ===================================
            # FUNCIÓN CONTINUA: ratio → gauge
            # ===================================
            # ratio = 2.0  → +100 (volumen doble)
            # ratio = 1.5  → +50  (volumen 50% superior)
            # ratio = 1.0  → 0    (volumen normal)
            # ratio = 0.5  → -100 (volumen mitad)
            
            if ratio_volumen >= 2.0:
                gauge_volumen = 100  # Límite superior
            elif ratio_volumen <= 0.5:
                gauge_volumen = -100  # Límite inferior
            elif ratio_volumen > 1.0:
                # Interpolación lineal: 1.0→0, 2.0→100
                gauge_volumen = (ratio_volumen - 1.0) * 100
            else:  # 0.5 < ratio < 1.0
                # Interpolación lineal: 0.5→-100, 1.0→0
                gauge_volumen = (ratio_volumen - 1.0) * 200
            
            # Añadir señales solo en extremos (para no saturar desglose)
            if ratio_volumen >= 1.5:
                score_timing += 0.5
                señales.append({
                    'indicador': 'Volumen',
                    'señal': 'neutral',
                    'peso': 0.5,
                    'razon': f'Volumen alto ({ratio_volumen:.2f}x promedio) - convicción'
                })
            elif ratio_volumen <= 0.6:
                score_timing -= 0.3
                señales.append({
                    'indicador': 'Volumen',
                    'señal': 'neutral',
                    'peso': -0.3,
                    'razon': f'Volumen bajo ({ratio_volumen:.2f}x promedio) - sin convicción'
                })
            else:
                # Volumen normal
                señales.append({
                    'indicador': 'Volumen',
                    'señal': 'neutral',
                    'peso': 0.3,
                    'razon': f'Volumen normal ({ratio_volumen:.2f}x promedio)'
                })
    
    
    # ========================================
    # GAUGE MOMENTUM (Combinación de indicadores)
    # ========================================
    
    gauge_momentum = 0
    
    # Componente 1: RSI (40% del peso)
    rsi_component = 0
    if 'RSI' in df.columns and pd.notna(ultimo['RSI']):
        rsi = ultimo['RSI']
        # Normalizar RSI de [0-100] a [-100, +100]
        # RSI=50 → 0, RSI=100 → +100, RSI=0 → -100
        rsi_component = (rsi - 50) * 2
    
    # Componente 2: MACD Histograma (30% del peso)
    macd_component = 0
    if 'MACD_HIST' in df.columns and pd.notna(ultimo['MACD_HIST']):
        histograma = ultimo['MACD_HIST']
        # Normalizar histograma (valores típicos entre -1 y +1)
        # Limitamos a rango -100, +100
        if histograma > 0:
            macd_component = min(histograma * 100, 100)
        else:
            macd_component = max(histograma * 100, -100)
    
    # Componente 3: Tendencia MMs (30% del peso)
    mm_component = 0
    # sesgo_tendencial está en rango aproximado -4 a +4
    # Normalizamos a -100, +100
    mm_component = (sesgo_tendencial / 4) * 100
    mm_component = max(-100, min(100, mm_component))
    
    # Combinación ponderada
    gauge_momentum = (
        rsi_component * 0.40 +
        macd_component * 0.30 +
        mm_component * 0.30
    )
    
    # Limitar a rango -100, +100
    gauge_momentum = max(-100, min(100, gauge_momentum))
    
    # ========================================
    # SÍNTESIS JERÁRQUICA
    # ========================================
    if not estructura_valida:
        return {
            'señal_global': 'neutral',
            'puntuacion': 0,
            'nivel_confianza': 'bajo',
            'razon': razon_bloqueo,
            'operar': False,
            'desglose_compra': [],
            'desglose_venta': [],
            'desglose_neutral': señales,
            'gauge_volumen': round(gauge_volumen, 1),
            'gauge_momentum': round(gauge_momentum, 1),
            'ratio_volumen': round(ratio_volumen, 2),
            'puntos_compra': 0,
            'puntos_venta': 0,
            'puntos_neutral': 0,
            # Compatibilidad
            'recomendacion': 'NEUTRAL',
            'puntuacion_global': 0,
            'color': 'neutral',
            'indicadores': {
                'puntuacion': 0,
                'compras': 0,
                'ventas': 0,
                'neutrales': len(señales),
                'detalles': señales
            },
            'medias_moviles': {
                'puntuacion': 0,
                'compras': 0,
                'ventas': 0,
                'neutrales': len(señales),
                'detalles': señales
            }
        }
    
    # ========================================
    # NIVEL 2: TENDENCIA (Contexto direccional)
    # ========================================
    
    # Alineación de medias móviles
    if all(k in df.columns for k in ['MM20', 'MM50', 'MM200']):
        mm20 = ultimo.get('MM20')
        mm50 = ultimo.get('MM50')
        mm200 = ultimo.get('MM200')
        
        if pd.notna(mm20) and pd.notna(mm50) and pd.notna(mm200):
            # Alineación alcista perfecta
            if mm20 > mm50 > mm200 and precio > mm20:
                sesgo_tendencial += 1.5
                score_momentum += 1
                señales.append({
                    'indicador': 'MMs Alineadas',
                    'señal': 'compra',
                    'peso': 1.2,
                    'razon': 'Tendencia alcista fuerte (20>50>200)'
                })
            # Alineación bajista perfecta
            elif mm20 < mm50 < mm200 and precio < mm20:
                sesgo_tendencial -= 1.5
                score_momentum -= 1
                señales.append({
                    'indicador': 'MMs Alineadas',
                    'señal': 'venta',
                    'peso': 1.2,
                    'razon': 'Tendencia bajista fuerte (20<50<200)'
                })
            # Alineación parcial alcista
            elif mm20 > mm50 and precio > mm20:
                sesgo_tendencial += 0.7
                señales.append({
                    'indicador': 'MMs',
                    'señal': 'compra',
                    'peso': 0.6,
                    'razon': 'Tendencia alcista moderada'
                })
            # Alineación parcial bajista
            elif mm20 < mm50 and precio < mm20:
                sesgo_tendencial -= 0.7
                señales.append({
                    'indicador': 'MMs',
                    'señal': 'venta',
                    'peso': 0.6,
                    'razon': 'Tendencia bajista moderada'
                })
    
    # MACD - Tendencia de fondo
    if all(k in df.columns for k in ['MACD', 'MACD_SEÑAL']):
        macd = ultimo.get('MACD')
        señal_macd = ultimo.get('MACD_SEÑAL')
        
        if pd.notna(macd) and pd.notna(señal_macd):
            # MACD por encima/debajo de 0 (sesgo de fondo)
            if macd > 0:
                sesgo_tendencial += 0.5
            elif macd < 0:
                sesgo_tendencial -= 0.5
            
            señal_generada = False
            
            # Cruces MACD (cambio de tendencia) - PRIORIDAD ALTA
            if len(df) >= 2:
                macd_anterior = df.iloc[-2].get('MACD')
                señal_anterior = df.iloc[-2].get('MACD_SEÑAL')
                
                if pd.notna(macd_anterior) and pd.notna(señal_anterior):
                    # Cruce alcista
                    if macd > señal_macd and macd_anterior <= señal_anterior:
                        score_momentum += 2
                        señales.append({
                            'indicador': 'MACD',
                            'señal': 'compra',
                            'peso': 1.3,
                            'razon': 'Cruce alcista MACD'
                        })
                        señal_generada = True
                    # Cruce bajista
                    elif macd < señal_macd and macd_anterior >= señal_anterior:
                        score_momentum -= 2
                        señales.append({
                            'indicador': 'MACD',
                            'señal': 'venta',
                            'peso': 1.3,
                            'razon': 'Cruce bajista MACD'
                        })
                        señal_generada = True
            
            # Si NO hubo cruce, generar señal por posición
            if not señal_generada:
                if macd > señal_macd and macd > 0:
                    señales.append({
                        'indicador': 'MACD',
                        'señal': 'compra',
                        'peso': 0.5,
                        'razon': f'Posición alcista (MACD={macd:.3f})'
                    })
                elif macd < señal_macd and macd < 0:
                    señales.append({
                        'indicador': 'MACD',
                        'señal': 'venta',
                        'peso': 0.5,
                        'razon': f'Posición bajista (MACD={macd:.3f})'
                    })
                else:
                    señales.append({
                        'indicador': 'MACD',
                        'señal': 'neutral',
                        'peso': 0.3,
                        'razon': f'Transición (MACD={macd:.3f})'
                    })
    
    # ========================================
    # NIVEL 3: MOMENTUM (Fuerza del movimiento)
    # ========================================
    
    # RSI - Sobrecompra/sobreventa
    if 'RSI' in df.columns and pd.notna(ultimo['RSI']):
        rsi = ultimo['RSI']
        
        if rsi < 30:
            # Sobreventa
            score_momentum += 2
            señales.append({
                'indicador': 'RSI',
                'señal': 'compra',
                'peso': 1.0,
                'razon': f'Sobreventa (RSI={rsi:.1f})'
            })
        elif rsi > 70:
            # Sobrecompra
            score_momentum -= 2
            señales.append({
                'indicador': 'RSI',
                'señal': 'venta',
                'peso': 1.0,
                'razon': f'Sobrecompra (RSI={rsi:.1f})'
            })
        elif 45 <= rsi <= 55:
            # Zona neutral
            señales.append({
                'indicador': 'RSI',
                'señal': 'neutral',
                'peso': 0.3,
                'razon': f'Zona neutral (RSI={rsi:.1f})'
            })
        else:
            # Zona normal
            señales.append({
                'indicador': 'RSI',
                'señal': 'neutral',
                'peso': 0.2,
                'razon': f'Zona normal (RSI={rsi:.1f})'
            })
    
    # MACD Histograma - Aceleración/desaceleración
    if 'MACD_HIST' in df.columns and pd.notna(ultimo['MACD_HIST']):
        histograma = ultimo['MACD_HIST']
        
        if len(df) >= 2:
            hist_anterior = df.iloc[-2].get('MACD_HIST')
            
            if pd.notna(hist_anterior):
                # Histograma creciente
                if histograma > hist_anterior and histograma > 0:
                    score_momentum += 0.5
                    señales.append({
                        'indicador': 'MACD Hist',
                        'señal': 'compra',
                        'peso': 0.5,
                        'razon': 'Momentum alcista creciente'
                    })
                # Histograma decreciente
                elif histograma < hist_anterior and histograma < 0:
                    score_momentum -= 0.5
                    señales.append({
                        'indicador': 'MACD Hist',
                        'señal': 'venta',
                        'peso': 0.5,
                        'razon': 'Momentum bajista creciente'
                    })
    
    # ========================================
    # NIVEL 4: TIMING (Refinamiento de entrada)
    # ========================================
    
    # Estocástico - Timing de entrada
    if all(k in df.columns for k in ['STOCH_K', 'STOCH_D']):
        k = ultimo.get('STOCH_K')
        d = ultimo.get('STOCH_D')
        
        if pd.notna(k) and pd.notna(d):
            señal_generada = False
            
            # Intentar detectar cruces (PRIORIDAD ALTA)
            if len(df) >= 2:
                k_anterior = df.iloc[-2].get('STOCH_K')
                d_anterior = df.iloc[-2].get('STOCH_D')
                
                if pd.notna(k_anterior) and pd.notna(d_anterior):
                    # Cruce alcista en sobreventa
                    if k < 20 and k > d and k_anterior <= d_anterior:
                        score_timing += 1
                        señales.append({
                            'indicador': 'Estocástico',
                            'señal': 'compra',
                            'peso': 0.7,
                            'razon': 'Cruce alcista en sobreventa'
                        })
                        señal_generada = True
                    # Cruce bajista en sobrecompra
                    elif k > 80 and k < d and k_anterior >= d_anterior:
                        score_timing -= 1
                        señales.append({
                            'indicador': 'Estocástico',
                            'señal': 'venta',
                            'peso': 0.7,
                            'razon': 'Cruce bajista en sobrecompra'
                        })
                        señal_generada = True
            
            # Si NO hubo cruce, generar señal por zona
            if not señal_generada:
                if k < 20:
                    señales.append({
                        'indicador': 'Estocástico',
                        'señal': 'compra',
                        'peso': 0.3,
                        'razon': f'Sobreventa (K={k:.1f})'
                    })
                elif k > 80:
                    señales.append({
                        'indicador': 'Estocástico',
                        'señal': 'venta',
                        'peso': 0.3,
                        'razon': f'Sobrecompra (K={k:.1f})'
                    })
                else:
                    señales.append({
                        'indicador': 'Estocástico',
                        'señal': 'neutral',
                        'peso': 0.2,
                        'razon': f'Zona media (K={k:.1f})'
                    })
    
    # DI+ y DI- (Dirección de fuerza)
    if all(k in df.columns for k in ['PLUS_DI', 'MINUS_DI']):
        di_plus = ultimo.get('PLUS_DI')
        di_minus = ultimo.get('MINUS_DI')
        
        if pd.notna(di_plus) and pd.notna(di_minus):
            diferencia = di_plus - di_minus
            
            if diferencia > 10:
                señales.append({
                    'indicador': 'DI±',
                    'señal': 'compra',
                    'peso': 0.6,
                    'razon': f'DI+ dominante (+{di_plus:.1f}, -{di_minus:.1f})'
                })
            elif diferencia < -10:
                señales.append({
                    'indicador': 'DI±',
                    'señal': 'venta',
                    'peso': 0.6,
                    'razon': f'DI- dominante (+{di_plus:.1f}, -{di_minus:.1f})'
                })
            else:
                señales.append({
                    'indicador': 'DI±',
                    'señal': 'neutral',
                    'peso': 0.3,
                    'razon': f'Equilibrado (+{di_plus:.1f}, -{di_minus:.1f})'
                })
    
    # ========================================
    # Volumen - Validación de convicción
    # ========================================
    
    # Puntuación total combinando los 4 niveles
    puntuacion_total = sesgo_tendencial + score_momentum + score_timing
    
    # APLICAR FILTROS ESTRUCTURALES (penalizaciones/bloqueos)
    
    # Si precio bajo MM200, penalizar compras fuertes
    if bajo_mm200 and puntuacion_total > 0:
        if puntuacion_total > 2:
            puntuacion_total = puntuacion_total * 0.6  # Penalización 40%
            señales.append({
                'indicador': 'Filtro Estructural',
                'señal': 'neutral',
                'peso': -0.4,
                'razon': 'Compra penalizada (precio bajo MM200)'
            })
    
    # Si precio sobre MM200, penalizar ventas fuertes
    if sobre_mm200 and puntuacion_total < 0:
        if puntuacion_total < -2:
            puntuacion_total = puntuacion_total * 0.6  # Penalización 40%
            señales.append({
                'indicador': 'Filtro Estructural',
                'señal': 'neutral',
                'peso': -0.4,
                'razon': 'Venta penalizada (precio sobre MM200)'
            })
    
    # TODO: Añadir penalizaciones por cercanía a S/R
    # TODO: Añadir refuerzos por Fibonacci
    # TODO: Añadir overrides por divergencias confirmadas
    # TODO: Añadir refuerzos por patrones chartistas confirmados
    
    # ========================================
    # CLASIFICACIÓN PROFESIONAL (Umbrales Asimétricos)
    # ========================================
    # Sistema de 3 niveles: Categoría + Contexto + Warnings
    
    # PASO 1: Categoría base con umbrales asimétricos
    # (Compras más estrictas porque tendencias alcistas duran más,
    #  Ventas más sensibles porque caídas son rápidas)
    
    if puntuacion_total >= 2.5:
        señal_global = 'compra'
        fuerza = 'FUERTE'
        base_confianza = 'alto'
    elif puntuacion_total >= 1.2:
        señal_global = 'compra'
        fuerza = 'MODERADA'
        base_confianza = 'medio'
    elif puntuacion_total <= -2.0:
        señal_global = 'venta'
        fuerza = 'FUERTE'
        base_confianza = 'alto'
    elif puntuacion_total <= -1.0:
        señal_global = 'venta'
        fuerza = 'MODERADA'
        base_confianza = 'medio'
    else:
        # Zona -1.0 a +1.2 = NEUTRAL (asimétrica)
        señal_global = 'neutral'
        fuerza = 'NEUTRAL'
        base_confianza = 'bajo'
    
    # PASO 2: Determinar contexto de MM200
    contexto_mm200 = "en tendencia alcista" if not bajo_mm200 else "en tendencia bajista"
    contexto_favorable = not bajo_mm200 if señal_global == 'compra' else bajo_mm200
    
    # PASO 3: Ajustar confianza según contexto
    # Si la señal va CON la tendencia de fondo → Más confianza
    # Si la señal va CONTRA la tendencia de fondo → Menos confianza
    if base_confianza == 'alto':
        if contexto_favorable:
            nivel_confianza = 'muy_alto'
        else:
            nivel_confianza = 'alto'  # Mantiene pero sin subir
    elif base_confianza == 'medio':
        if contexto_favorable:
            nivel_confianza = 'alto'  # Sube
        else:
            nivel_confianza = 'medio_bajo'  # Baja
    else:
        nivel_confianza = 'bajo'
    
    # PASO 4: Calcular proximidad al siguiente nivel
    proximidad = None
    if señal_global == 'compra' and fuerza == 'MODERADA':
        faltan = 2.5 - puntuacion_total
        proximidad = f"Faltan {faltan:.1f} pts para COMPRA FUERTE"
    elif señal_global == 'venta' and fuerza == 'MODERADA':
        faltan = abs(puntuacion_total - (-2.0))
        proximidad = f"Faltan {faltan:.1f} pts para VENTA FUERTE"
    elif señal_global == 'neutral':
        if puntuacion_total > 0:
            faltan = 1.2 - puntuacion_total
            proximidad = f"Faltan {faltan:.1f} pts para COMPRA"
        elif puntuacion_total < 0:
            faltan = abs(puntuacion_total - (-1.0))
            proximidad = f"Faltan {faltan:.1f} pts para VENTA"
    
    # Separar señales por tipo
    desglose_compra = [s for s in señales if s['señal'] == 'compra']
    desglose_venta = [s for s in señales if s['señal'] == 'venta']
    desglose_neutral = [s for s in señales if s['señal'] == 'neutral']
    
    # PASO 5: Generar warnings
    warnings = []
    
    # Warning 1: Pocas señales para la categoría
    num_señales_direccionales = len(desglose_compra) + len(desglose_venta)
    if señal_global in ['compra', 'venta'] and num_señales_direccionales <= 2:
        warnings.append(f"Solo {num_señales_direccionales} señal(es) direccional(es)")
    
    # Warning 2: Señales contradictorias
    if señal_global == 'compra' and len(desglose_venta) >= 2:
        warnings.append(f"{len(desglose_venta)} señales de venta activas")
    elif señal_global == 'venta' and len(desglose_compra) >= 2:
        warnings.append(f"{len(desglose_compra)} señales de compra activas")
    
    # Warning 3: Contrarian (contra tendencia de fondo)
    if señal_global == 'compra' and bajo_mm200:
        warnings.append("Señal contrarian (precio bajo MM200)")
    elif señal_global == 'venta' and not bajo_mm200:
        warnings.append("Probable corrección (tendencia alcista)")
    
    # Warning 4: Momentum débil en señal fuerte
    if fuerza == 'FUERTE' and abs(score_momentum) < 1.0:
        warnings.append("Momentum débil para señal fuerte")
    
    # Calcular puntuaciones por categoría
    puntos_compra = sum(s['peso'] for s in desglose_compra)
    puntos_venta = abs(sum(s['peso'] for s in desglose_venta))
    puntos_neutral = sum(s['peso'] for s in desglose_neutral)
    
    # ========================================
    # ADAPTADOR DE COMPATIBILIDAD (frontend antiguo)
    # ========================================
    
    # Contar señales por tipo
    num_compras = len(desglose_compra)
    num_ventas = len(desglose_venta)
    num_neutrales = len(desglose_neutral)
    
    # Puntuación normalizada para frontend antiguo (-1 a +1)
    puntuacion_normalizada = puntuacion_total / 5.0  # De [-5, +5] a [-1, +1]
    puntuacion_normalizada = max(-1, min(1, puntuacion_normalizada))
    
    # Recomendación simplificada (solo 5 categorías)
    if fuerza == 'FUERTE' and señal_global == 'compra':
        recomendacion = 'COMPRA FUERTE'
        color = 'compra-fuerte'
    elif fuerza == 'MODERADA' and señal_global == 'compra':
        recomendacion = 'COMPRA'
        color = 'compra'
    elif fuerza == 'FUERTE' and señal_global == 'venta':
        recomendacion = 'VENTA FUERTE'
        color = 'venta-fuerte'
    elif fuerza == 'MODERADA' and señal_global == 'venta':
        recomendacion = 'VENTA'
        color = 'venta'
    else:
        recomendacion = 'NEUTRAL'
        color = 'neutral'
    
    return {
        # ===== FORMATO NUEVO (jerárquico) =====
        'señal_global': señal_global,
        'fuerza': fuerza,
        'puntuacion': round(puntuacion_total, 2),
        'nivel_confianza': nivel_confianza,
        'contexto_mm200': contexto_mm200,
        'contexto_favorable': contexto_favorable,
        'proximidad': proximidad,
        'warnings': warnings,
        'operar': True,
        'desglose': {
            'tendencia': sesgo_tendencial,
            'momentum': score_momentum,
            'timing': score_timing
        },
        'puntos_compra': round(puntos_compra, 1),
        'puntos_venta': round(puntos_venta, 1),
        'puntos_neutral': round(puntos_neutral, 1),
        'desglose_compra': desglose_compra,
        'desglose_venta': desglose_venta,
        'desglose_neutral': desglose_neutral,
        'gauge_volumen': round(gauge_volumen, 1),
        'gauge_momentum': round(gauge_momentum, 1),
        'ratio_volumen': round(ratio_volumen, 2),
        
        # ===== FORMATO ANTIGUO (compatibilidad) =====
        'recomendacion': recomendacion,
        'puntuacion_global': round(puntuacion_normalizada, 2),
        'color': color,
        'indicadores': {
            'puntuacion': round(puntuacion_normalizada, 2),
            'compras': sum(1 for s in desglose_compra if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±']),
            'ventas': sum(1 for s in desglose_venta if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±']),
            'neutrales': sum(1 for s in desglose_neutral if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±', 'ADX']),
            'desglose_compra': [s for s in desglose_compra if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±']],
            'desglose_venta': [s for s in desglose_venta if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±']],
            'desglose_neutral': [s for s in desglose_neutral if s['indicador'] in ['RSI', 'MACD', 'Estocástico', 'DI±', 'ADX']]
        },
        'medias_moviles': {
            'puntuacion': round(puntuacion_normalizada, 2),
            'compras': sum(1 for s in desglose_compra if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']),
            'ventas': sum(1 for s in desglose_venta if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']),
            'neutrales': sum(1 for s in desglose_neutral if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']),
            'desglose_compra': [s for s in desglose_compra if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']],
            'desglose_venta': [s for s in desglose_venta if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']],
            'desglose_neutral': [s for s in desglose_neutral if s['indicador'] in ['MM200', 'MMs Alineadas', 'MMs', 'Volumen']]
        }
    }
