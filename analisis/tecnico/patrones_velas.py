# nucleo/patrones_velas.py
"""
DETECTOR DE PATRONES DE VELAS JAPONESAS
Implementación profesional de los patrones más relevantes para trading
"""
import pandas as pd
import numpy as np

class DetectorPatronesVelas:
    """Clase para detectar patrones de velas japonesas"""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame con columnas ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.df = df
        self.patrones = []
        
    def detectar_todos(self, ultimas_n=50):
        """
        Detecta todos los patrones en las últimas N velas
        
        Args:
            ultimas_n: Número de velas a analizar (por defecto últimas 50)
            
        Returns:
            list: Lista de patrones detectados
        """
        # Analizar solo las últimas N velas para rendimiento
        inicio = max(0, len(self.df) - ultimas_n)
        
        for i in range(inicio, len(self.df)):
            # Necesitamos al menos 3 velas de contexto
            if i < 3:
                continue
            
            # Detectar patrones de 1 vela
            self._detectar_martillo(i)
            self._detectar_estrella_fugaz(i)
            self._detectar_doji(i)
            self._detectar_spinning_top(i)
            
            # Detectar patrones de 2 velas (necesitan i-1)
            if i >= 1:
                self._detectar_envolvente(i)
                self._detectar_harami(i)
                self._detectar_piercing_line(i)
                self._detectar_dark_cloud(i)
                self._detectar_tweezer(i)
            
            # Detectar patrones de 3 velas (necesitan i-2)
            if i >= 2:
                self._detectar_estrella_manana(i)
                self._detectar_estrella_tarde(i)
                self._detectar_tres_soldados(i)
                self._detectar_tres_cuervos(i)
        
        # Ordenar por fecha (más reciente primero)
        self.patrones.sort(key=lambda x: x['index'], reverse=True)
        
        return self.patrones
    
    # ========================================
    # HELPERS - CÁLCULOS BÁSICOS
    # ========================================
    
    def _cuerpo(self, i):
        """Tamaño del cuerpo de la vela"""
        return abs(self.df['Close'].iloc[i] - self.df['Open'].iloc[i])
    
    def _rango(self, i):
        """Rango total de la vela (High - Low)"""
        return self.df['High'].iloc[i] - self.df['Low'].iloc[i]
    
    def _sombra_superior(self, i):
        """Tamaño de la sombra superior"""
        return self.df['High'].iloc[i] - max(self.df['Open'].iloc[i], self.df['Close'].iloc[i])
    
    def _sombra_inferior(self, i):
        """Tamaño de la sombra inferior"""
        return min(self.df['Open'].iloc[i], self.df['Close'].iloc[i]) - self.df['Low'].iloc[i]
    
    def _es_alcista(self, i):
        """True si la vela es alcista (cierre > apertura)"""
        return self.df['Close'].iloc[i] > self.df['Open'].iloc[i]
    
    def _es_bajista(self, i):
        """True si la vela es bajista (cierre < apertura)"""
        return self.df['Close'].iloc[i] < self.df['Open'].iloc[i]
    
    def _detectar_tendencia(self, i, ventana=10):
        """
        Detecta la tendencia previa usando pendiente de MM
        
        Returns:
            str: 'alcista', 'bajista', 'lateral'
        """
        if i < ventana:
            return 'lateral'
        
        precios = self.df['Close'].iloc[i-ventana:i]
        pendiente = (precios.iloc[-1] - precios.iloc[0]) / precios.iloc[0]
        
        if pendiente > 0.02:  # +2%
            return 'alcista'
        elif pendiente < -0.02:  # -2%
            return 'bajista'
        else:
            return 'lateral'
    
    def _añadir_patron(self, i, nombre, tipo, confianza, descripcion):
        """Añade un patrón a la lista"""
        self.patrones.append({
            'index': i,
            'fecha': self.df.index[i],
            'precio': float(self.df['Close'].iloc[i]),
            'nombre': nombre,
            'tipo': tipo,  # 'alcista', 'bajista', 'neutral'
            'confianza': confianza,
            'descripcion': descripcion
        })
    
    # ========================================
    # PATRONES DE 1 VELA
    # ========================================
    
    def _detectar_martillo(self, i):
        """
        MARTILLO (Hammer) - Alcista
        - Cuerpo pequeño en la parte superior
        - Sombra inferior larga (2x+ el cuerpo)
        - Sombra superior mínima
        - Aparece en tendencia bajista
        """
        cuerpo = self._cuerpo(i)
        rango = self._rango(i)
        sombra_inf = self._sombra_inferior(i)
        sombra_sup = self._sombra_superior(i)
        
        # Condiciones
        if (sombra_inf > cuerpo * 2 and 
            sombra_sup < cuerpo * 0.3 and
            cuerpo > 0 and
            cuerpo < rango * 0.3):
            
            tendencia = self._detectar_tendencia(i)
            confianza = 0.75 if tendencia == 'bajista' else 0.5
            
            self._añadir_patron(
                i, 'Martillo', 'alcista', confianza,
                'Posible rebote alcista. Confirmar con siguiente vela.'
            )
    
    def _detectar_estrella_fugaz(self, i):
        """
        ESTRELLA FUGAZ (Shooting Star) - Bajista
        - Cuerpo pequeño en la parte inferior
        - Sombra superior larga (2x+ el cuerpo)
        - Sombra inferior mínima
        - Aparece en tendencia alcista
        """
        cuerpo = self._cuerpo(i)
        rango = self._rango(i)
        sombra_inf = self._sombra_inferior(i)
        sombra_sup = self._sombra_superior(i)
        
        if (sombra_sup > cuerpo * 2 and 
            sombra_inf < cuerpo * 0.3 and
            cuerpo > 0 and
            cuerpo < rango * 0.3):
            
            tendencia = self._detectar_tendencia(i)
            confianza = 0.75 if tendencia == 'alcista' else 0.5
            
            self._añadir_patron(
                i, 'Estrella Fugaz', 'bajista', confianza,
                'Posible giro bajista. Confirmar con siguiente vela.'
            )
    
    def _detectar_doji(self, i):
        """
        DOJI - Neutral/Indecisión
        - Apertura ≈ Cierre
        - Sombras pueden variar
        - Indica indecisión del mercado
        """
        cuerpo = self._cuerpo(i)
        rango = self._rango(i)
        
        # Cuerpo muy pequeño (< 5% del rango)
        if cuerpo < rango * 0.05 and rango > 0:
            tendencia = self._detectar_tendencia(i)
            
            # Doji en tendencia fuerte = mayor importancia
            confianza = 0.7 if tendencia != 'lateral' else 0.5
            
            self._añadir_patron(
                i, 'Doji', 'neutral', confianza,
                f'Indecisión en tendencia {tendencia}. Posible cambio de dirección.'
            )
    
    def _detectar_spinning_top(self, i):
        """
        SPINNING TOP (Peonza) - Neutral
        - Cuerpo pequeño en el centro
        - Sombras superior e inferior similares y largas
        - Indica indecisión
        """
        cuerpo = self._cuerpo(i)
        rango = self._rango(i)
        sombra_inf = self._sombra_inferior(i)
        sombra_sup = self._sombra_superior(i)
        
        if (cuerpo < rango * 0.3 and
            sombra_inf > cuerpo and
            sombra_sup > cuerpo and
            abs(sombra_inf - sombra_sup) < rango * 0.3):
            
            self._añadir_patron(
                i, 'Spinning Top', 'neutral', 0.6,
                'Indecisión del mercado. Esperar confirmación.'
            )
    
    # ========================================
    # PATRONES DE 2 VELAS
    # ========================================
    
    def _detectar_envolvente(self, i):
        """
        ENVOLVENTE (Engulfing) - Fuerte
        - Vela actual envuelve completamente a la anterior
        - Alcista: Roja -> Verde grande
        - Bajista: Verde -> Roja grande
        """
        # Necesitamos la vela anterior
        if i < 1:
            return
        
        actual_open = self.df['Open'].iloc[i]
        actual_close = self.df['Close'].iloc[i]
        prev_open = self.df['Open'].iloc[i-1]
        prev_close = self.df['Close'].iloc[i-1]
        
        # ENVOLVENTE ALCISTA
        if (self._es_bajista(i-1) and self._es_alcista(i) and
            actual_open < prev_close and
            actual_close > prev_open):
            
            tendencia = self._detectar_tendencia(i)
            confianza = 0.85 if tendencia == 'bajista' else 0.65
            
            self._añadir_patron(
                i, 'Envolvente Alcista', 'alcista', confianza,
                'Patrón muy fuerte de reversión alcista.'
            )
        
        # ENVOLVENTE BAJISTA
        elif (self._es_alcista(i-1) and self._es_bajista(i) and
              actual_open > prev_close and
              actual_close < prev_open):
            
            tendencia = self._detectar_tendencia(i)
            confianza = 0.85 if tendencia == 'alcista' else 0.65
            
            self._añadir_patron(
                i, 'Envolvente Bajista', 'bajista', confianza,
                'Patrón muy fuerte de reversión bajista.'
            )
    
    def _detectar_harami(self, i):
        """
        HARAMI - Patrón de indecisión/reversión
        - Vela actual está contenida dentro de la anterior
        - Vela grande seguida de vela pequeña
        """
        if i < 1:
            return
        
        actual_open = self.df['Open'].iloc[i]
        actual_close = self.df['Close'].iloc[i]
        prev_open = self.df['Open'].iloc[i-1]
        prev_close = self.df['Close'].iloc[i-1]
        
        # Vela actual dentro de la anterior
        if (min(actual_open, actual_close) > min(prev_open, prev_close) and
            max(actual_open, actual_close) < max(prev_open, prev_close)):
            
            # HARAMI ALCISTA (después de vela bajista)
            if self._es_bajista(i-1):
                self._añadir_patron(
                    i, 'Harami Alcista', 'alcista', 0.65,
                    'Posible fin de tendencia bajista.'
                )
            # HARAMI BAJISTA (después de vela alcista)
            elif self._es_alcista(i-1):
                self._añadir_patron(
                    i, 'Harami Bajista', 'bajista', 0.65,
                    'Posible fin de tendencia alcista.'
                )
    
    def _detectar_piercing_line(self, i):
        """
        PIERCING LINE - Alcista
        - Vela bajista seguida de vela alcista
        - Vela alcista cierra por encima del 50% de la bajista
        """
        if i < 1:
            return
        
        if self._es_bajista(i-1) and self._es_alcista(i):
            prev_medio = (self.df['Open'].iloc[i-1] + self.df['Close'].iloc[i-1]) / 2
            
            if (self.df['Open'].iloc[i] < self.df['Close'].iloc[i-1] and
                self.df['Close'].iloc[i] > prev_medio):
                
                self._añadir_patron(
                    i, 'Piercing Line', 'alcista', 0.75,
                    'Fuerte señal de reversión alcista.'
                )
    
    def _detectar_dark_cloud(self, i):
        """
        DARK CLOUD COVER - Bajista
        - Vela alcista seguida de vela bajista
        - Vela bajista cierra por debajo del 50% de la alcista
        """
        if i < 1:
            return
        
        if self._es_alcista(i-1) and self._es_bajista(i):
            prev_medio = (self.df['Open'].iloc[i-1] + self.df['Close'].iloc[i-1]) / 2
            
            if (self.df['Open'].iloc[i] > self.df['Close'].iloc[i-1] and
                self.df['Close'].iloc[i] < prev_medio):
                
                self._añadir_patron(
                    i, 'Dark Cloud Cover', 'bajista', 0.75,
                    'Fuerte señal de reversión bajista.'
                )
    
    def _detectar_tweezer(self, i):
        """
        TWEEZER (Pinzas) - Reversión
        - Dos velas con máximos o mínimos similares
        """
        if i < 1:
            return
        
        high_actual = self.df['High'].iloc[i]
        high_prev = self.df['High'].iloc[i-1]
        low_actual = self.df['Low'].iloc[i]
        low_prev = self.df['Low'].iloc[i-1]
        
        rango_promedio = (self._rango(i) + self._rango(i-1)) / 2
        
        # Tweezer Top (máximos similares) - Bajista
        if abs(high_actual - high_prev) < rango_promedio * 0.05:
            if self._es_alcista(i-1) and self._es_bajista(i):
                self._añadir_patron(
                    i, 'Tweezer Top', 'bajista', 0.7,
                    'Doble máximo. Posible reversión bajista.'
                )
        
        # Tweezer Bottom (mínimos similares) - Alcista
        if abs(low_actual - low_prev) < rango_promedio * 0.05:
            if self._es_bajista(i-1) and self._es_alcista(i):
                self._añadir_patron(
                    i, 'Tweezer Bottom', 'alcista', 0.7,
                    'Doble mínimo. Posible reversión alcista.'
                )
    
    # ========================================
    # PATRONES DE 3 VELAS
    # ========================================
    
    def _detectar_estrella_manana(self, i):
        """
        ESTRELLA DE LA MAÑANA (Morning Star) - Muy alcista
        - 3 velas: Bajista grande + Pequeña (gap down) + Alcista grande
        """
        if i < 2:
            return
        
        # Vela 1: Bajista grande
        if not self._es_bajista(i-2) or self._cuerpo(i-2) < self._rango(i-2) * 0.5:
            return
        
        # Vela 2: Pequeña (doji o spinning)
        if self._cuerpo(i-1) > self._rango(i-1) * 0.3:
            return
        
        # Vela 3: Alcista grande
        if not self._es_alcista(i) or self._cuerpo(i) < self._rango(i) * 0.5:
            return
        
        # Gap down en vela 2
        if self.df['High'].iloc[i-1] < self.df['Low'].iloc[i-2]:
            self._añadir_patron(
                i, 'Estrella de la Mañana', 'alcista', 0.9,
                'Patrón muy fuerte de reversión alcista.'
            )
    
    def _detectar_estrella_tarde(self, i):
        """
        ESTRELLA DE LA TARDE (Evening Star) - Muy bajista
        - 3 velas: Alcista grande + Pequeña (gap up) + Bajista grande
        """
        if i < 2:
            return
        
        # Vela 1: Alcista grande
        if not self._es_alcista(i-2) or self._cuerpo(i-2) < self._rango(i-2) * 0.5:
            return
        
        # Vela 2: Pequeña
        if self._cuerpo(i-1) > self._rango(i-1) * 0.3:
            return
        
        # Vela 3: Bajista grande
        if not self._es_bajista(i) or self._cuerpo(i) < self._rango(i) * 0.5:
            return
        
        # Gap up en vela 2
        if self.df['Low'].iloc[i-1] > self.df['High'].iloc[i-2]:
            self._añadir_patron(
                i, 'Estrella de la Tarde', 'bajista', 0.9,
                'Patrón muy fuerte de reversión bajista.'
            )
    
    def _detectar_tres_soldados(self, i):
        """
        TRES SOLDADOS BLANCOS - Muy alcista
        - 3 velas alcistas consecutivas
        - Cada cierre superior al anterior
        - Cuerpos similares
        """
        if i < 2:
            return
        
        if (self._es_alcista(i) and self._es_alcista(i-1) and self._es_alcista(i-2) and
            self.df['Close'].iloc[i] > self.df['Close'].iloc[i-1] and
            self.df['Close'].iloc[i-1] > self.df['Close'].iloc[i-2]):
            
            self._añadir_patron(
                i, 'Tres Soldados Blancos', 'alcista', 0.85,
                'Fuerte continuación alcista. Alta probabilidad.'
            )
    
    def _detectar_tres_cuervos(self, i):
        """
        TRES CUERVOS NEGROS - Muy bajista
        - 3 velas bajistas consecutivas
        - Cada cierre inferior al anterior
        - Cuerpos similares
        """
        if i < 2:
            return
        
        if (self._es_bajista(i) and self._es_bajista(i-1) and self._es_bajista(i-2) and
            self.df['Close'].iloc[i] < self.df['Close'].iloc[i-1] and
            self.df['Close'].iloc[i-1] < self.df['Close'].iloc[i-2]):
            
            self._añadir_patron(
                i, 'Tres Cuervos Negros', 'bajista', 0.85,
                'Fuerte continuación bajista. Alta probabilidad.'
            )


def detectar_patrones_velas(df, ultimas_n=50):
    """
    Función principal para detectar patrones de velas
    
    Args:
        df: DataFrame con OHLCV
        ultimas_n: Número de velas a analizar
        
    Returns:
        list: Lista de patrones detectados
    """
    detector = DetectorPatronesVelas(df)
    patrones = detector.detectar_todos(ultimas_n=ultimas_n)
    
    # Filtrar patrones más relevantes (confianza >= 0.6)
    patrones_relevantes = [p for p in patrones if p['confianza'] >= 0.6]
    
    # Limitar a los 10 más recientes
    return patrones_relevantes[:10]
