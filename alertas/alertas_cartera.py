# alertas/alertas_cartera.py
"""
═══════════════════════════════════════════════════════════════
ALERTAS INTELIGENTES DE CARTERA (v89.2)
═══════════════════════════════════════════════════════════════

Detecta situaciones importantes en posiciones abiertas.
Se integra en la pantalla de Alertas existente (/alertas/).

Tipos:
  1. Stop en peligro (<2% distancia) → CRÍTICA
  2. Objetivo cerca (<5% distancia) → ALTA
  3. Trailing disponible (+1R o +3R) → ALTA/MEDIA
  4. Setup degradado (estancada >30d o pérdida -0.5R/-1R) → MEDIA
═══════════════════════════════════════════════════════════════
"""

import logging
from typing import List, Dict


logger = logging.getLogger(__name__)


def detectar_alertas_posiciones(posiciones: List[dict]) -> List[dict]:
    """
    Detecta alertas en posiciones de cartera.
    
    Args:
        posiciones: Lista con métricas calculadas (precio_actual, pnl_R, etc.)
    
    Returns:
        [{
            'tipo': 'STOP_PELIGRO' | 'OBJETIVO_CERCA' | 'TRAILING' | 'DEGRADADO',
            'ticker': 'BBVA.MC',
            'prioridad': 'CRITICA' | 'ALTA' | 'MEDIA',
            'mensaje': str,
            'accion': str
        }, ...]
    """
    alertas = []
    
    for pos in posiciones:
        try:
            # 1. Stop en peligro
            alerta = _stop_peligro(pos)
            if alerta:
                alertas.append(alerta)
            
            # 2. Objetivo cerca
            alerta = _objetivo_cerca(pos)
            if alerta:
                alertas.append(alerta)
            
            # 3. Trailing disponible
            alerta = _trailing_disponible(pos)
            if alerta:
                alertas.append(alerta)
            
            # 4. Setup degradado
            alerta = _setup_degradado(pos)
            if alerta:
                alertas.append(alerta)
        
        except Exception as e:
            logger.warning(f"Error detectando alertas en {pos.get('ticker')}: {e}")
            continue
    
    # Ordenar por prioridad
    prioridades = {'CRITICA': 3, 'ALTA': 2, 'MEDIA': 1}
    alertas.sort(key=lambda a: prioridades.get(a['prioridad'], 0), reverse=True)
    
    return alertas


def _stop_peligro(pos: dict) -> dict:
    """Stop en peligro (<2% distancia)."""
    precio = pos.get('precio_actual')
    stop = pos.get('stop_actual') or pos.get('stop_inicial')
    
    if not precio or not stop:
        return None
    
    try:
        precio = float(precio)
        stop = float(stop)
    except (TypeError, ValueError):
        return None
    
    if precio <= stop:
        return None
    
    distancia_pct = ((precio - stop) / precio) * 100
    
    if distancia_pct <= 2.0:
        return {
            'tipo': 'STOP_PELIGRO',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'CRITICA',
            'mensaje': f"Stop a {distancia_pct:.1f}% ({stop:.2f}€)",
            'accion': 'Decidir: ¿mantener o cerrar?'
        }
    
    return None


def _objetivo_cerca(pos: dict) -> dict:
    """Objetivo cerca (<5% distancia)."""
    precio = pos.get('precio_actual')
    objetivo = pos.get('objetivo')
    
    if not precio or not objetivo:
        return None
    
    try:
        precio = float(precio)
        objetivo = float(objetivo)
    except (TypeError, ValueError):
        return None
    
    if precio >= objetivo:
        return None
    
    distancia_pct = ((objetivo - precio) / precio) * 100
    
    if distancia_pct <= 5.0:
        pnl_r = pos.get('pnl_R', 0)
        return {
            'tipo': 'OBJETIVO_CERCA',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'ALTA',
            'mensaje': f"A {distancia_pct:.1f}% del objetivo ({objetivo:.2f}€)",
            'accion': f"Preparar salida (llevas {pnl_r:.1f}R)" if pnl_r else "Preparar salida"
        }
    
    return None


def _trailing_disponible(pos: dict) -> dict:
    """Trailing disponible (+1R o +3R alcanzado)."""
    pnl_r = pos.get('pnl_R')
    fase = pos.get('fase', 'INICIAL')
    
    if pnl_r is None:
        return None
    
    try:
        pnl_r = float(pnl_r)
    except (TypeError, ValueError):
        return None
    
    if pnl_r < 1.0:
        return None
    
    # Si ya tiene fase correcta, no alertar
    if fase in ('BREAKEVEN', 'PROFIT_LOCK'):
        return None
    
    if pnl_r >= 3.0:
        return {
            'tipo': 'TRAILING',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'ALTA',
            'mensaje': f"Profit Lock disponible (+{pnl_r:.1f}R)",
            'accion': 'Asegurar +2R con trailing'
        }
    elif pnl_r >= 1.0:
        return {
            'tipo': 'TRAILING',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'MEDIA',
            'mensaje': f"Breakeven disponible (+{pnl_r:.1f}R)",
            'accion': 'Proteger capital con trailing'
        }
    
    return None


def _setup_degradado(pos: dict) -> dict:
    """Setup degradándose (pérdida o estancamiento)."""
    pnl_r = pos.get('pnl_R')
    dias = pos.get('duracion', 0)
    
    if pnl_r is None:
        return None
    
    try:
        pnl_r = float(pnl_r)
        dias = int(dias)
    except (TypeError, ValueError):
        return None
    
    # Pérdida moderada
    if -1.0 < pnl_r < -0.5:
        return {
            'tipo': 'DEGRADADO',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'MEDIA',
            'mensaje': f"Pérdida de {pnl_r:.1f}R — setup no funciona",
            'accion': 'Revisar tesis'
        }
    
    # Estancada
    if dias > 30 and -0.5 < pnl_r < 0.5:
        return {
            'tipo': 'DEGRADADO',
            'ticker': pos.get('ticker', ''),
            'prioridad': 'MEDIA',
            'mensaje': f"{dias} días sin movimiento",
            'accion': 'Considerar cerrar — capital inmovilizado'
        }
    
    return None
