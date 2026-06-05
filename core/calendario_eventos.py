"""
Calendario de Eventos - Sistema Trading v86.1
============================================

Gestiona eventos corporativos que afectan al trading:
- Dividendos (Fase 1 - ACTUAL)
- Resultados empresariales (Fase 2 - futura)
- Eventos macro (Fase 3 - futura)

Filosofía:
- Dividendos: ADVERTIR, no bloquear (el trader decide)
- Earnings: BLOQUEAR entrada si <2 días, AJUSTAR stops si 1 día antes
- Macro: INFORMAR (contexto adicional)
"""

import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# DIVIDENDOS CONOCIDOS - IBEX35 Y MERCADO CONTINUO
# ══════════════════════════════════════════════════════════════
# FUENTES OFICIALES (por orden de prioridad):
# 1. Invesgrama: https://invesgrama.com/dividendos-previstos-ibex-2026/
#    → Calendario anual consolidado, más completo y claro
# 2. BME: https://www.bolsasymercados.es/.../dividendos.html
#    → Fuente oficial pero menos práctica para consulta
#
# Última actualización: 20 Mayo 2026 (desde Invesgrama)
# 
# ⚠️ IMPORTANTE: Si recibes notificación de cambios en dividendos,
#    actualizar este diccionario consultando las fuentes arriba.
#
# FORMATO:
# "TICKER.MC": [
#     {"fecha_ex": "YYYY-MM-DD", "importe": X.XXXX},  # Pago 1
#     {"fecha_ex": "YYYY-MM-DD", "importe": X.XXXX},  # Pago 2 (si aplica)
# ]

DIVIDENDOS_CONOCIDOS = {
    # ══════════════════════════════════════════════════════════
    # IBEX 35 - DIVIDENDOS 2026 (Fuente: Invesgrama)
    # ══════════════════════════════════════════════════════════
    
    "ACS.MC": [  # ACS
        {"fecha_ex": "2026-05-06", "importe": 0.54},
        {"fecha_ex": "2026-11-04", "importe": 0.54},
    ],
    
    "ACX.MC": [  # Acerinox
        {"fecha_ex": "2026-06-10", "importe": 0.50},
    ],
    
    "ANA.MC": [  # Acciona
        {"fecha_ex": "2026-06-24", "importe": 4.50},
    ],
    
    "ANE.MC": [  # Acciona Energía
        {"fecha_ex": "2026-03-25", "importe": 0.53},
        {"fecha_ex": "2026-10-07", "importe": 0.54},
    ],
    
    "AENA.MC": [  # Aena
        {"fecha_ex": "2026-03-04", "importe": 2.521},
        {"fecha_ex": "2026-09-08", "importe": 2.521},
    ],
    
    "AMS.MC": [  # Amadeus
        {"fecha_ex": "2026-05-08", "importe": 0.60},
        {"fecha_ex": "2026-11-06", "importe": 0.60},
    ],
    
    "MTS.MC": [  # ArcelorMittal
        {"fecha_ex": "2026-06-09", "importe": 0.45},
        {"fecha_ex": "2026-09-08", "importe": 0.45},
        {"fecha_ex": "2026-12-08", "importe": 0.45},
    ],
    
    "BBVA.MC": [  # BBVA
        {"fecha_ex": "2026-04-09", "importe": 0.29},
        {"fecha_ex": "2026-10-08", "importe": 0.29},
    ],
    
    "CABK.MC": [  # CaixaBank
        {"fecha_ex": "2026-04-16", "importe": 0.2322},
        {"fecha_ex": "2026-11-05", "importe": 0.2322},
    ],
    
    "CLNX.MC": [  # Cellnex
        {"fecha_ex": "2026-06-03", "importe": 0.15},
        {"fecha_ex": "2026-12-09", "importe": 0.15},
    ],
    
    "CIE.MC": [  # CIE Automotive
        {"fecha_ex": "2026-06-24", "importe": 0.60},
    ],
    
    "COL.MC": [  # Inmobiliaria Colonial
        {"fecha_ex": "2026-01-19", "importe": 0.065},
        {"fecha_ex": "2026-07-13", "importe": 0.065},
    ],
    
    "ELE.MC": [  # Endesa
        {"fecha_ex": "2026-01-02", "importe": 0.70},
        {"fecha_ex": "2026-07-01", "importe": 0.70},
    ],
    
    "ENG.MC": [  # Enagás
        {"fecha_ex": "2026-01-14", "importe": 0.845},
        {"fecha_ex": "2026-07-14", "importe": 0.845},
    ],
    
    "FER.MC": [  # Ferrovial
        {"fecha_ex": "2026-04-15", "importe": 0.3492},
    ],
    
    "FCC.MC": [  # FCC (Fomento de Construcciones)
        {"fecha_ex": "2026-05-27", "importe": 0.55},
    ],
    
    "GRF.MC": [  # Grifols
        {"fecha_ex": "2026-05-05", "importe": 0.25},
        {"fecha_ex": "2026-11-04", "importe": 0.25},
    ],
    
    "IAG.MC": [  # IAG (International Airlines Group)
        {"fecha_ex": "2026-09-10", "importe": 0.03},
    ],
    
    "IBE.MC": [  # Iberdrola
        {"fecha_ex": "2026-02-02", "importe": 0.252},
        {"fecha_ex": "2026-08-03", "importe": 0.252},
    ],
    
    "ITX.MC": [  # Inditex
        {"fecha_ex": "2026-05-04", "importe": 0.77},
        {"fecha_ex": "2026-11-02", "importe": 0.77},
    ],
    
    "IDR.MC": [  # Indra Sistemas
        {"fecha_ex": "2026-07-01", "importe": 0.30},
    ],
    
    "MAP.MC": [  # Mapfre
        {"fecha_ex": "2026-06-03", "importe": 0.0825},
        {"fecha_ex": "2026-12-02", "importe": 0.0825},
    ],
    
    "MEL.MC": [  # Meliá Hotels
        {"fecha_ex": "2026-04-14", "importe": 0.25},
    ],
    
    "MRL.MC": [  # Merlin Properties
        {"fecha_ex": "2026-01-21", "importe": 0.181},
        {"fecha_ex": "2026-04-15", "importe": 0.181},
        {"fecha_ex": "2026-07-15", "importe": 0.181},
        {"fecha_ex": "2026-10-14", "importe": 0.181},
    ],
    
    "NTGY.MC": [  # Naturgy
        {"fecha_ex": "2026-01-09", "importe": 0.60},
        {"fecha_ex": "2026-07-09", "importe": 0.60},
    ],
    
    "PHM.MC": [  # PharmaMar
        {"fecha_ex": "2026-12-15", "importe": 0.15},
    ],
    
    "RED.MC": [  # Red Eléctrica
        {"fecha_ex": "2026-01-07", "importe": 0.50},
        {"fecha_ex": "2026-07-07", "importe": 0.50},
    ],
    
    "REP.MC": [  # Repsol
        {"fecha_ex": "2026-01-14", "importe": 0.4375},
        {"fecha_ex": "2026-07-14", "importe": 0.4375},
    ],
    
    "SAB.MC": [  # Banco Sabadell
        {"fecha_ex": "2026-05-27", "importe": 0.50},
    ],
    
    "SAN.MC": [  # Banco Santander
        {"fecha_ex": "2026-02-02", "importe": 0.0662},
        {"fecha_ex": "2026-05-04", "importe": 0.0662},
        {"fecha_ex": "2026-08-03", "importe": 0.0662},
        {"fecha_ex": "2026-11-02", "importe": 0.0662},
    ],
    
    "SLR.MC": [  # Solaria Energía
        {"fecha_ex": "2026-06-30", "importe": 0.413},
    ],
    
    "TEF.MC": [  # Telefónica
        {"fecha_ex": "2026-06-10", "importe": 0.15},
        {"fecha_ex": "2026-12-09", "importe": 0.15},
    ],
    
    "UNI.MC": [  # Unicaja Banco
        {"fecha_ex": "2026-04-15", "importe": 0.0699},
    ],
    
    # ══════════════════════════════════════════════════════════
    # MERCADO CONTINUO - Selectos (agregar según necesidad)
    # ══════════════════════════════════════════════════════════
    
    "A3M.MC": [  # Atresmedia
        {"fecha_ex": "2026-06-17", "importe": 0.21},
    ],
    
    "ALM.MC": [  # Almirall
        {"fecha_ex": "2026-05-13", "importe": 0.19},
    ],
    
    "CBAV.MC": [  # Clínica Baviera
        {"fecha_ex": "2026-06-12", "importe": 1.57},
    ],
}


class CalendarioEventos:
    """Gestor de eventos corporativos y macro."""
    
    def __init__(self):
        self.cache_dividendos = {}  # {ticker: {data, expires_at}}
        self.cache_ttl = 3600  # 1 hora
        
    def obtener_dividendo_proximo(self, ticker, dias_ventana=30):
        """
        Obtiene el próximo dividendo programado.
        
        Estrategia (cascada):
        1. DIVIDENDOS_CONOCIDOS (manual — más fiable)
        2. yfinance (fallback)
        
        Args:
            ticker: Ticker (ej: "TEF.MC")
            dias_ventana: Días hacia adelante a revisar
            
        Returns:
            dict con tiene_dividendo, fecha_ex, importe, dias_hasta, yield_aprox
        """
        now = datetime.now()
        
        # Check cache
        if ticker in self.cache_dividendos:
            cached = self.cache_dividendos[ticker]
            if cached['expires_at'] > now:
                return cached['data']
        
        resultado = {
            'tiene_dividendo': False,
            'fecha_ex': None,
            'importe': None,
            'dias_hasta': None,
            'yield_aprox': None,
            'advertir_entrada': False,
            'razon_advertencia': None,
        }
        
        # ──────────────────────────────────────────────────────────
        # PRIORIDAD 1: DIVIDENDOS_CONOCIDOS
        # ──────────────────────────────────────────────────────────
        if ticker in DIVIDENDOS_CONOCIDOS:
            for div_manual in DIVIDENDOS_CONOCIDOS[ticker]:
                try:
                    fecha_ex = datetime.strptime(div_manual['fecha_ex'], '%Y-%m-%d')
                    dias_hasta = (fecha_ex - now).days
                    
                    if 0 <= dias_hasta <= dias_ventana:
                        importe = div_manual.get('importe')
                        
                        # Intentar calcular yield (necesita precio actual)
                        yield_aprox = None
                        try:
                            info = yf.Ticker(ticker).info or {}
                            precio = info.get('currentPrice') or info.get('regularMarketPrice')
                            if importe and precio:
                                yield_aprox = (importe / precio) * 100
                        except:
                            pass
                        
                        resultado.update({
                            'tiene_dividendo': True,
                            'fecha_ex': fecha_ex,
                            'importe': float(importe) if importe else None,
                            'dias_hasta': dias_hasta,
                            'yield_aprox': yield_aprox,
                            'advertir_entrada': dias_hasta <= 3,
                        })
                        
                        if resultado['advertir_entrada']:
                            msg = f"⚠️ Dividendo"
                            if importe:
                                msg += f" {importe:.2f}€"
                            msg += f" en {dias_hasta} día{'s' if dias_hasta != 1 else ''}"
                            if yield_aprox:
                                msg += f" — gap esperado ~{yield_aprox:.1f}%"
                            resultado['razon_advertencia'] = msg
                        
                        # Cachear
                        self.cache_dividendos[ticker] = {
                            'data': resultado,
                            'expires_at': now + timedelta(seconds=self.cache_ttl)
                        }
                        return resultado
                except Exception as e:
                    logger.debug(f"Error procesando dividendo manual {ticker}: {e}")
                    continue
        
        # ──────────────────────────────────────────────────────────
        # PRIORIDAD 2: yfinance (fallback — deshabilitado por ahora)
        # ──────────────────────────────────────────────────────────
        # yfinance no funciona bien para mercado español
        # Si se necesita, descomentar y arreglar el error de tipos datetime
        
        # Cachear resultado vacío
        self.cache_dividendos[ticker] = {
            'data': resultado,
            'expires_at': now + timedelta(seconds=self.cache_ttl)
        }
        
        return resultado
    
    def eventos_proximos(self, ticker, dias_adelante=3):
        """
        Obtiene todos los eventos próximos del ticker.
        
        Args:
            ticker: Ticker a consultar
            dias_adelante: Ventana de días hacia adelante
            
        Returns:
            dict con:
                - tiene_eventos: bool
                - advertir_entrada: bool (si algún evento crítico)
                - razon_advertencia: str o None
                - dividendo: dict (resultado de obtener_dividendo_proximo)
                - earnings: dict (Fase 2 - futura)
                - macro: list (Fase 3 - futura)
        """
        dividendo = self.obtener_dividendo_proximo(ticker, dias_ventana=dias_adelante)
        
        resultado = {
            'tiene_eventos': dividendo['tiene_dividendo'],
            'advertir_entrada': dividendo['advertir_entrada'],
            'razon_advertencia': dividendo['razon_advertencia'],
            'dividendo': dividendo,
            'earnings': None,  # Fase 2
            'macro': []  # Fase 3
        }
        
        return resultado
    
    def ajustar_stop_dividendo(self, precio_entrada, dividendo_importe, yield_aprox):
        """
        Calcula ajuste de stop sugerido por dividendo.
        
        El gap típico de apertura es ~80% del yield (no 100% porque
        parte se anticipa días antes).
        
        Args:
            precio_entrada: Precio de entrada
            dividendo_importe: Importe del dividendo
            yield_aprox: Yield % aproximado
            
        Returns:
            dict con:
                - stop_original: float
                - stop_ajustado: float
                - ajuste_pips: float
                - razon: str
        """
        if not dividendo_importe or not yield_aprox:
            return None
        
        # Gap esperado es ~80% del yield
        gap_esperado = yield_aprox * 0.8
        ajuste_porcentaje = gap_esperado / 100
        
        ajuste_absoluto = precio_entrada * ajuste_porcentaje
        
        return {
            'gap_esperado_pct': gap_esperado,
            'ajuste_absoluto': ajuste_absoluto,
            'sugerencia': f"Bajar stop {ajuste_absoluto:.2f}€ ({gap_esperado:.1f}%) para compensar gap de dividendo"
        }


# Instancia global (singleton)
_calendario_instance = None

def get_calendario():
    """Obtiene la instancia singleton del calendario."""
    global _calendario_instance
    if _calendario_instance is None:
        _calendario_instance = CalendarioEventos()
    return _calendario_instance
