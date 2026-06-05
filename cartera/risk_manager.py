# cartera/risk_manager.py
"""
═══════════════════════════════════════════════════════════════
RISK MANAGER — CONTROL DE LÍMITES DE CARTERA (v88.1)
═══════════════════════════════════════════════════════════════

Controla límites agregados de riesgo:
  1. Máximo de posiciones simultáneas (8-10)
  2. Risk budget global (≤ 6-8% del capital)
  3. Exposición por sector (≤ 30% por sector)

Uso:
    rm = RiskManager(capital=30000)
    validacion = rm.validar_nueva_posicion(
        ticker='BBVA.MC',
        riesgo_eur=600,
        posiciones_abiertas=[...]
    )
    if not validacion['aprobada']:
        print(validacion['razon'])
═══════════════════════════════════════════════════════════════
"""

from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LÍMITES
# ═══════════════════════════════════════════════════════════

# Límite de posiciones simultáneas
LIMITE_POSICIONES_MAX = 10
LIMITE_POSICIONES_RECOMENDADO = 8

# Risk budget (% del capital total)
RISK_BUDGET_MAX = 8.0       # Máximo absoluto
RISK_BUDGET_ALERTA = 6.5    # Umbral de alerta

# Exposición sectorial (% del capital)
LIMITE_SECTOR_PCT = 30.0


# ═══════════════════════════════════════════════════════════
# MAPEO TICKER → SECTOR
# ═══════════════════════════════════════════════════════════

SECTORES = {
    # BANCA
    'SAN.MC': 'BANCA', 'BBVA.MC': 'BANCA', 'CABK.MC': 'BANCA',
    'SAB.MC': 'BANCA', 'UNI.MC': 'BANCA', 'BKT.MC': 'BANCA',
    
    # ENERGÍA & UTILITIES
    'IBE.MC': 'ENERGIA', 'REP.MC': 'ENERGIA', 'ENG.MC': 'ENERGIA',
    'RED.MC': 'ENERGIA', 'NTGY.MC': 'ENERGIA', 'ELE.MC': 'ENERGIA',
    'ANE.MC': 'ENERGIA', 'SLR.MC': 'ENERGIA',
    
    # CONSTRUCCIÓN & INFRAESTRUCTURA
    'ACS.MC': 'CONSTRUCCION', 'FER.MC': 'CONSTRUCCION', 
    'FCC.MC': 'CONSTRUCCION', 'AENA.MC': 'CONSTRUCCION',
    'SCYR.MC': 'CONSTRUCCION', 'ANA.MC': 'CONSTRUCCION',
    
    # TELECOM & TECNOLOGÍA
    'TEF.MC': 'TELECOM', 'AMS.MC': 'TECNOLOGIA', 
    'IDR.MC': 'TECNOLOGIA', 'CLNX.MC': 'TECNOLOGIA',
    
    # CONSUMO & RETAIL
    'ITX.MC': 'CONSUMO', 'MEL.MC': 'CONSUMO',
    'A3M.MC': 'CONSUMO', 'CIE.MC': 'CONSUMO',
    
    # INMOBILIARIO
    'MRL.MC': 'INMOBILIARIO', 'COL.MC': 'INMOBILIARIO',
    
    # SEGUROS
    'MAP.MC': 'SEGUROS',
    
    # FARMA & SALUD
    'GRF.MC': 'SALUD', 'PHM.MC': 'SALUD', 
    'ROVI.MC': 'SALUD', 'CBAV.MC': 'SALUD', 'ALM.MC': 'SALUD',
    
    # INDUSTRIA & MATERIALES
    'MTS.MC': 'INDUSTRIA', 'ACX.MC': 'INDUSTRIA',
    
    # AEROLÍNEAS & TRANSPORTE
    'IAG.MC': 'TRANSPORTE', 'LOG.MC': 'TRANSPORTE',
}


def obtener_sector(ticker: str) -> str:
    """
    Devuelve el sector de un ticker.
    
    Args:
        ticker: Código del valor (ej: 'BBVA.MC', 'BBVA', 'bbva')
    
    Returns:
        Sector (ej: 'BANCA') o 'OTROS' si no está mapeado
    """
    tk = ticker.strip().upper()
    if not tk.endswith('.MC'):
        tk = tk + '.MC'
    return SECTORES.get(tk, 'OTROS')


# ═══════════════════════════════════════════════════════════
# RISK MANAGER
# ═══════════════════════════════════════════════════════════

class RiskManager:
    """Controla límites agregados de riesgo de cartera."""
    
    def __init__(self, capital: float = 30000):
        self.capital = capital
    
    # ── Validación de Nueva Posición ────────────────────────
    
    def validar_nueva_posicion(
        self,
        ticker: str,
        riesgo_eur: float,
        tamano_eur: float,
        posiciones_abiertas: List[dict]
    ) -> Dict:
        """
        Valida si se puede abrir una nueva posición.
        
        Args:
            ticker: Ticker de la nueva posición (ej: 'BBVA.MC')
            riesgo_eur: Riesgo en euros (stop_loss * acciones)
            tamano_eur: Tamaño posición (precio_entrada * acciones)
            posiciones_abiertas: Lista de posiciones actuales
        
        Returns:
            {
                'aprobada': bool,
                'razon': str,
                'alertas': [str],
                'metricas': {
                    'posiciones_actuales': int,
                    'risk_budget_actual_pct': float,
                    'risk_budget_nuevo_pct': float,
                    'exposicion_sector_actual_pct': float,
                    'exposicion_sector_nueva_pct': float,
                }
            }
        """
        alertas = []
        
        # ─── 1. Límite de posiciones (TICKERS ÚNICOS) ───
        tickers_actuales = set(p.get('ticker', '').strip().upper() for p in posiciones_abiertas)
        tickers_actuales.discard('')  # Eliminar vacíos
        
        ticker_nuevo_normalizado = ticker.strip().upper()
        if not ticker_nuevo_normalizado.endswith('.MC'):
            ticker_nuevo_normalizado += '.MC'
        
        # Si el ticker ya existe, no incrementa el contador
        es_ticker_nuevo = ticker_nuevo_normalizado not in tickers_actuales
        num_posiciones_unicas = len(tickers_actuales)
        num_posiciones_tras_nueva = num_posiciones_unicas + (1 if es_ticker_nuevo else 0)
        
        if num_posiciones_tras_nueva > LIMITE_POSICIONES_MAX:
            return {
                'aprobada': False,
                'razon': f'⛔ Máximo de empresas diferentes alcanzado ({num_posiciones_unicas}/{LIMITE_POSICIONES_MAX})',
                'alertas': [],
                'metricas': self._calcular_metricas(ticker, riesgo_eur, tamano_eur, posiciones_abiertas),
            }
        
        if num_posiciones_tras_nueva >= LIMITE_POSICIONES_RECOMENDADO and es_ticker_nuevo:
            alertas.append(
                f'⚠️ Cerca del límite recomendado ({num_posiciones_tras_nueva}/{LIMITE_POSICIONES_RECOMENDADO} empresas)'
            )
        
        if not es_ticker_nuevo:
            alertas.append(
                f'ℹ️ Añadiendo más posición a {ticker_nuevo_normalizado.replace(".MC", "")} existente'
            )
        
        # ─── 2. Risk Budget ───
        riesgo_actual = sum(
            p.get('riesgo_inicial', 0) or 0
            for p in posiciones_abiertas
        )
        riesgo_nuevo = riesgo_actual + riesgo_eur
        
        risk_budget_actual_pct = round(riesgo_actual / self.capital * 100, 2)
        risk_budget_nuevo_pct = round(riesgo_nuevo / self.capital * 100, 2)
        
        if risk_budget_nuevo_pct > RISK_BUDGET_MAX:
            return {
                'aprobada': False,
                'razon': f'⛔ Risk budget excedido: {risk_budget_nuevo_pct:.1f}% > {RISK_BUDGET_MAX}%',
                'alertas': alertas,
                'metricas': self._calcular_metricas(ticker, riesgo_eur, tamano_eur, posiciones_abiertas),
            }
        
        if risk_budget_nuevo_pct > RISK_BUDGET_ALERTA:
            alertas.append(
                f'⚠️ Risk budget alto: {risk_budget_nuevo_pct:.1f}% (límite {RISK_BUDGET_MAX}%)'
            )
        
        # ─── 3. Exposición Sectorial ───
        sector_nuevo = obtener_sector(ticker)
        
        exposicion_sectores = self._calcular_exposicion_sectores(posiciones_abiertas)
        exposicion_actual_sector = exposicion_sectores.get(sector_nuevo, 0)
        exposicion_nueva_sector = exposicion_actual_sector + tamano_eur
        
        exposicion_sector_actual_pct = round(exposicion_actual_sector / self.capital * 100, 1)
        exposicion_sector_nueva_pct = round(exposicion_nueva_sector / self.capital * 100, 1)
        
        if exposicion_sector_nueva_pct > LIMITE_SECTOR_PCT:
            return {
                'aprobada': False,
                'razon': f'⛔ Límite sectorial excedido ({sector_nuevo}): {exposicion_sector_nueva_pct:.1f}% > {LIMITE_SECTOR_PCT}%',
                'alertas': alertas,
                'metricas': self._calcular_metricas(ticker, riesgo_eur, tamano_eur, posiciones_abiertas),
            }
        
        # ─── TODO OK ───
        return {
            'aprobada': True,
            'razon': '✅ Posición aprobada',
            'alertas': alertas,
            'metricas': self._calcular_metricas(ticker, riesgo_eur, tamano_eur, posiciones_abiertas),
        }
    
    # ── Métricas de Riesgo ──────────────────────────────────
    
    def _calcular_metricas(
        self,
        ticker: str,
        riesgo_eur: float,
        tamano_eur: float,
        posiciones: List[dict]
    ) -> Dict:
        """Calcula métricas actuales y proyectadas."""
        riesgo_actual = sum(p.get('riesgo_inicial', 0) or 0 for p in posiciones)
        riesgo_nuevo = riesgo_actual + riesgo_eur
        
        sector_nuevo = obtener_sector(ticker)
        exposicion_sectores = self._calcular_exposicion_sectores(posiciones)
        exposicion_actual_sector = exposicion_sectores.get(sector_nuevo, 0)
        exposicion_nueva_sector = exposicion_actual_sector + tamano_eur
        
        return {
            'posiciones_actuales': len(posiciones),
            'risk_budget_actual_pct': round(riesgo_actual / self.capital * 100, 2),
            'risk_budget_nuevo_pct': round(riesgo_nuevo / self.capital * 100, 2),
            'exposicion_sector_actual_pct': round(exposicion_actual_sector / self.capital * 100, 1),
            'exposicion_sector_nueva_pct': round(exposicion_nueva_sector / self.capital * 100, 1),
            'sector': sector_nuevo,
        }
    
    def _calcular_exposicion_sectores(self, posiciones: List[dict]) -> Dict[str, float]:
        """
        Calcula exposición por sector (suma de valores de mercado).
        
        Returns:
            {'BANCA': 7500.0, 'ENERGIA': 4200.0, ...}
        """
        exposicion = {}
        
        for pos in posiciones:
            ticker = pos.get('ticker', '')
            sector = obtener_sector(ticker)
            
            # Tamaño posición = precio_entrada * acciones
            precio = float(pos.get('precio_entrada', 0))
            acciones = int(pos.get('acciones', 0))
            valor = precio * acciones
            
            exposicion[sector] = exposicion.get(sector, 0) + valor
        
        return exposicion
    
    # ── Dashboard de Exposición ─────────────────────────────
    
    def obtener_exposicion_detallada(self, posiciones: List[dict]) -> Dict:
        """
        Devuelve snapshot completo de riesgo y exposición.
        
        Returns:
            {
                'num_posiciones': 7,  # Tickers únicos, no entradas totales
                'num_entradas': 9,    # Total de entradas (puede haber múltiples por ticker)
                'limite_posiciones': 10,
                'risk_budget_pct': 6.5,
                'risk_budget_max': 8.0,
                'exposicion_sectores': {
                    'BANCA': {'eur': 7500, 'pct': 25.0, 'tickers': ['SAN', 'BBVA']},
                    'ENERGIA': {'eur': 4200, 'pct': 14.0, 'tickers': ['IBE', 'REP']},
                    ...
                }
            }
        """
        riesgo_total = sum(p.get('riesgo_inicial', 0) or 0 for p in posiciones)
        
        # Contar tickers únicos
        tickers_unicos = set(p.get('ticker', '').strip().upper() for p in posiciones if p.get('ticker'))
        
        # Exposición por sector con detalle
        sectores_detalle = {}
        for pos in posiciones:
            ticker = pos.get('ticker', '')
            sector = obtener_sector(ticker)
            precio = float(pos.get('precio_entrada', 0))
            acciones = int(pos.get('acciones', 0))
            valor = precio * acciones
            
            if sector not in sectores_detalle:
                sectores_detalle[sector] = {
                    'eur': 0,
                    'pct': 0,
                    'tickers': set()  # Usar set para evitar duplicados
                }
            
            sectores_detalle[sector]['eur'] += valor
            sectores_detalle[sector]['tickers'].add(ticker.replace('.MC', ''))
        
        # Convertir sets a listas y calcular porcentajes
        for sector in sectores_detalle:
            sectores_detalle[sector]['pct'] = round(
                sectores_detalle[sector]['eur'] / self.capital * 100, 1
            )
            sectores_detalle[sector]['tickers'] = sorted(list(sectores_detalle[sector]['tickers']))
        
        # Ordenar por exposición
        sectores_detalle = dict(sorted(
            sectores_detalle.items(),
            key=lambda x: x[1]['eur'],
            reverse=True
        ))
        
        return {
            'num_posiciones': len(tickers_unicos),  # Empresas únicas
            'num_entradas': len(posiciones),         # Total de entradas
            'limite_posiciones': LIMITE_POSICIONES_MAX,
            'risk_budget_pct': round(riesgo_total / self.capital * 100, 2),
            'risk_budget_max': RISK_BUDGET_MAX,
            'exposicion_sectores': sectores_detalle,
        }
