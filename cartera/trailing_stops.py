# cartera/trailing_stops.py
"""
═══════════════════════════════════════════════════════════════
TRAILING STOPS AUTOMÁTICO (v88.2)
═══════════════════════════════════════════════════════════════

Ajusta stops automáticamente según el P&L:
  1. Breakeven (+1R): Stop sube a precio entrada
  2. Profit Lock (+3R): Stop sube a +2R (asegura 2R mínimo)
  3. Trailing Estructura: Stop sigue mínimos crecientes

Uso:
    from cartera.trailing_stops import TrailingStopManager
    
    tsm = TrailingStopManager()
    nuevo_stop, fase = tsm.calcular_nuevo_stop(
        precio_entrada=10.0,
        stop_inicial=9.0,
        stop_actual=9.0,
        precio_actual=11.5,
        fase_actual='INICIAL'
    )
═══════════════════════════════════════════════════════════════
"""

from typing import Tuple, Optional


class TrailingStopManager:
    """Gestiona el ajuste automático de stops según P&L."""
    
    # ─── Configuración ─────────────────────────────────────
    
    BREAKEVEN_R = 1.0       # A partir de +1R → stop a entrada
    PROFIT_LOCK_R = 3.0     # A partir de +3R → stop a +2R
    PROFIT_LOCK_STOP_R = 2.0  # Stop asegurado a +2R
    
    FASES = {
        'INICIAL': 'Stop inicial (sin ajuste)',
        'BREAKEVEN': 'Breakeven (+1R alcanzado)',
        'PROFIT_LOCK': 'Profit Lock (+3R alcanzado, stop en +2R)',
        'TRAILING': 'Trailing por estructura',
    }
    
    def calcular_nuevo_stop(
        self,
        precio_entrada: float,
        stop_inicial: float,
        stop_actual: float,
        precio_actual: float,
        fase_actual: str = 'INICIAL'
    ) -> Tuple[float, str]:
        """
        Calcula el nuevo stop y fase según las reglas de trailing.
        
        Args:
            precio_entrada: Precio de entrada de la posición
            stop_inicial: Stop loss inicial
            stop_actual: Stop actual (puede haber sido movido manualmente)
            precio_actual: Precio de cotización actual
            fase_actual: Fase actual ('INICIAL', 'BREAKEVEN', 'PROFIT_LOCK', 'TRAILING')
        
        Returns:
            (nuevo_stop, nueva_fase)
            - nuevo_stop: Valor del stop ajustado
            - nueva_fase: Nueva fase de la posición
        
        Reglas:
        - El stop NUNCA baja (solo sube)
        - INICIAL → BREAKEVEN cuando P&L >= +1R
        - BREAKEVEN → PROFIT_LOCK cuando P&L >= +3R
        - Si stop manual está más alto que el calculado, se respeta
        """
        if not stop_inicial or stop_inicial <= 0:
            return stop_actual, fase_actual
        
        # Calcular R (distancia entrada - stop inicial)
        R = precio_entrada - stop_inicial
        if R <= 0:
            return stop_actual, fase_actual
        
        # Calcular P&L en unidades R
        pnl_r = (precio_actual - precio_entrada) / R
        
        # ─── 1. Regla PROFIT LOCK (+3R) ───
        if pnl_r >= self.PROFIT_LOCK_R:
            stop_profit_lock = precio_entrada + (R * self.PROFIT_LOCK_STOP_R)
            
            # Solo aplicar si mejora el stop actual
            if stop_profit_lock > stop_actual:
                return round(stop_profit_lock, 4), 'PROFIT_LOCK'
            else:
                # Stop actual ya está más alto (manual o trailing previo)
                return stop_actual, fase_actual if fase_actual != 'INICIAL' else 'PROFIT_LOCK'
        
        # ─── 2. Regla BREAKEVEN (+1R) ───
        if pnl_r >= self.BREAKEVEN_R and fase_actual == 'INICIAL':
            # Stop sube a entrada (protege capital)
            if precio_entrada > stop_actual:
                return round(precio_entrada, 4), 'BREAKEVEN'
            else:
                # Stop actual ya está en o sobre entrada
                return stop_actual, 'BREAKEVEN'
        
        # ─── 3. Sin cambios ───
        return stop_actual, fase_actual
    
    def sugerir_trailing_estructura(
        self,
        precio_entrada: float,
        stop_actual: float,
        precio_actual: float,
        minimo_reciente: float,
        lookback_periodos: int = 5
    ) -> Optional[float]:
        """
        Sugiere un stop basado en estructura (mínimos recientes).
        
        Esta función NO modifica automáticamente el stop, solo sugiere.
        El usuario debe confirmar el ajuste manualmente.
        
        Args:
            precio_entrada: Precio de entrada
            stop_actual: Stop actual
            precio_actual: Precio actual
            minimo_reciente: Mínimo de los últimos N periodos
            lookback_periodos: Número de periodos para el mínimo (default 5)
        
        Returns:
            float: Stop sugerido, o None si no hay mejora
        """
        # El stop por estructura debe estar:
        # 1. Por debajo del precio actual (obvio)
        # 2. Por encima del stop actual (mejora)
        # 3. Por debajo del mínimo reciente (con margen de seguridad)
        
        margen_seguridad = 0.02  # 2% de margen bajo el mínimo
        stop_sugerido = minimo_reciente * (1 - margen_seguridad)
        
        # Validar que mejora el stop actual
        if stop_sugerido > stop_actual and stop_sugerido < precio_actual:
            return round(stop_sugerido, 4)
        
        return None
    
    def validar_ajuste_manual(
        self,
        precio_entrada: float,
        stop_actual: float,
        stop_nuevo_manual: float,
        precio_actual: float
    ) -> Tuple[bool, str]:
        """
        Valida que un ajuste manual de stop sea válido.
        
        Reglas:
        - El stop nuevo debe ser >= stop actual (no bajar nunca)
        - El stop nuevo debe ser < precio actual (sino salta inmediatamente)
        
        Returns:
            (es_valido, razon)
        """
        if stop_nuevo_manual < stop_actual:
            return False, f"⛔ El stop no puede bajar (actual: {stop_actual:.2f}€)"
        
        if stop_nuevo_manual >= precio_actual:
            return False, f"⛔ El stop debe estar por debajo del precio actual ({precio_actual:.2f}€)"
        
        return True, "✅ Ajuste válido"
    
    def obtener_descripcion_fase(self, fase: str) -> str:
        """Devuelve descripción legible de una fase."""
        return self.FASES.get(fase, fase)


# Singleton
_tsm_instance = None

def get_trailing_stop_manager():
    """Devuelve instancia singleton del TrailingStopManager."""
    global _tsm_instance
    if _tsm_instance is None:
        _tsm_instance = TrailingStopManager()
    return _tsm_instance
