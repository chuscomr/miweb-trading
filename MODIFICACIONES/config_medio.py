# ==========================================================
# CONFIGURACIÓN — SISTEMA MEDIO PLAZO
# Timeframe: 4-24 semanas (semanal)
# ==========================================================

# Medias móviles
MM_TENDENCIA_CORTA  = 10
MM_TENDENCIA_MEDIA  = 20
MM_TENDENCIA_LARGA  = 40
MM_TIMING_CORTA     = 5    # MM5 semanal — timing de entrada (~MM20 diaria)
MM_TIMING_MEDIA     = 8    # MM8 semanal — timing alternativo
MM_FILTRO_TENDENCIA = 50   # MM50 debe estar por encima de MM200
MM_FILTRO_LARGO     = 200  # MM200 como referencia macro

# ATR
ATR_PERIODO = 14

# RSI — se calcula sobre datos SEMANALES (no diarios)
RSI_PERIODO = 14           # RSI(14) estándar
RSI_MIN_PULLBACK = 40      # Zona pullback sano: 40-55
RSI_MAX_PULLBACK = 55
# IMPORTANTE: El RSI se calcula sobre cierres SEMANALES, no diarios
# Esto es coherente con el timeframe del sistema (4-24 semanas)

# ══════════════════════════════════════════════════════════════════
# SCORING PROFESIONAL V2 — Sistema de componentes separados
# ══════════════════════════════════════════════════════════════════
# Arquitectura: ESTRUCTURA + TIMING + MOMENTUM
# Ventaja: Distingue pullback sano de deterioro estructural

# ESTRUCTURA (0-5 puntos) — Calidad de la tendencia macro
ESTRUCTURA_MM50_MM200        = 2.0   # Tendencia macro obligatoria
ESTRUCTURA_MM20_ASCENDENTE   = 1.0   # Tendencia corto plazo
ESTRUCTURA_MM20_BAJISTA      = -1.0  # Penalización si gira a la baja
ESTRUCTURA_MM50_ASCENDENTE   = 0.5   # Tendencia medio plazo
ESTRUCTURA_LEJOS_MM50        = -0.5  # Precio muy extendido (>5%)
ESTRUCTURA_BAJO_MM50         = -1.0  # Precio bajo soporte principal (<-2%)
ESTRUCTURA_MAXIMOS_CRECIENTES = 0.5  # Máximos ascendentes

# TIMING (0-3 puntos) — Momento óptimo de entrada
# Contextual: estar bajo MM20 puede ser POSITIVO si estructura intacta
# RECALIBRADO v85.18: Penalizaciones suavizadas, evitar triple castigo
TIMING_PERFECTO_MIN = -1.5   # Rango inferior timing ideal (% vs MM20)
TIMING_PERFECTO_MAX = 1.5    # Rango superior timing ideal
TIMING_PERFECTO_PUNTOS = 1.5 # Bonus por timing perfecto

TIMING_SANO_MIN = -3.0       # Pullback aún válido
TIMING_SANO_PUNTOS = 1.2     # AUMENTADO de 0.5 → 1.2 (menos penalización)

TIMING_DETERIORO_UMBRAL = -5.0  # RELAJADO de -3.0 → -5.0 (más tolerante)
TIMING_DETERIORO_PENALIZACION = -0.3  # SUAVIZADO de -0.75 → -0.3

TIMING_EXTENDIDO_UMBRAL = 4.0   # RELAJADO de 3.0 → 4.0
TIMING_EXTENDIDO_PENALIZACION = -0.15  # SUAVIZADO de -0.25 → -0.15

TIMING_MM20_ROTA_PENALIZACION = -0.5  # SUAVIZADO de -1.0 → -0.5

# Pullback
TIMING_PULLBACK_OPTIMO_MIN = 5.0
TIMING_PULLBACK_OPTIMO_MAX = 10.0  # AMPLIADO de 8.0 → 10.0 (más realista)
TIMING_PULLBACK_OPTIMO_PUNTOS = 1.0

TIMING_PULLBACK_VALIDO_MIN = 3.0
TIMING_PULLBACK_VALIDO_PUNTOS = 0.5

TIMING_PULLBACK_PROFUNDO = 15.0  # AMPLIADO de 12.0 → 15.0 (más tolerante)
TIMING_PULLBACK_PROFUNDO_PENALIZACION = -0.5

# Soporte
TIMING_CERCA_SOPORTE_UMBRAL = 2.0  # Dentro de 2% del mínimo 10w
TIMING_CERCA_SOPORTE_PUNTOS = 0.5

# MOMENTUM (0-2 puntos) — Fuerza compradora actual
MOMENTUM_RSI_PUNTOS = 1.0          # RSI en zona pullback
MOMENTUM_RSI_SOBREVENTA = 35       # Umbral sobreventa
MOMENTUM_RSI_SOBREVENTA_PENALIZACION = -0.3  # SUAVIZADO de -0.5

MOMENTUM_VOLUMEN_RATIO = 0.85      # Vol actual < 85% media
MOMENTUM_VOLUMEN_PUNTOS = 0.5
MOMENTUM_VOLUMEN_VENDEDOR_RATIO = 1.8  # RELAJADO de 1.5 → 1.8 (más tolerante)
MOMENTUM_VOLUMEN_VENDEDOR_PENALIZACION = -0.3  # SUAVIZADO de -0.5

MOMENTUM_VELA_REVERSION_RATIO = 0.3  # Body < 30% rango (doji/martillo)
MOMENTUM_VELA_REVERSION_PUNTOS = 0.5

# VALIDACIÓN FINAL
SCORE_MIN_ESTRUCTURA = 2.0   # REDUCIDO de 2.5 → 2.0 (más permisivo)
SCORE_MIN_TIMING = -0.5      # RELAJADO de 0.0 → -0.5 (permite timing levemente negativo)

# Pullback — validado con backtest comparativo v2 (con fix tendencia)
# Variante A (3-8%) ganadora: WR 41.5%, exp +1.16R, MaxDD 3.6%
PULLBACK_MIN_PCT    = 3.0   # mínimo 3% — zona baja válida
PULLBACK_MAX_PCT    = 8.0   # máximo 8% — evita correcciones profundas
LOOKBACK_MAXIMO     = 10    # máximo reciente 10 semanas

# Volatilidad
VOL_MIN_PCT = 8.0
REQUIERE_GIRO_SEMANAL = True  # trigger: high semana × 1.001

# Stop
STOP_ATR_MULTIPLICADOR   = 2.0
STOP_ESTRUCTURA_LOOKBACK = 5   # mínimo últimas 5 semanas
# Stop = max(estructura×0.98, trigger - ATR×2) → más cercano y realista

# Riesgo — adaptado a timeframe semanal (velas más amplias)
RIESGO_MIN_PCT = 1.5
RIESGO_MAX_PCT = 8.0

# ──────────────────────────────────────────────────────────
# SISTEMA DE TIERS — Universo de operación
# ──────────────────────────────────────────────────────────
# Tier 1 — IBEX35: máxima prioridad, calidad alta, riesgo completo
# Tier 2 — Continuo: secundario, más selectivo, riesgo reducido
#
# Reglas operativas:
#   · Si hay señal IBEX → prioridad absoluta
#   · Si no hay IBEX → mirar Continuo
#   · IBEX → riesgo completo (1R)
#   · Continuo → riesgo reducido (0.5R)
#   · Si hay señal IBEX activa → no abrir Continuo hasta que cierre

TIER_1_UNIVERSO = "IBEX35"
TIER_2_UNIVERSO = "CONTINUO"

TIER_1_RIESGO_PCT = 1.0    # riesgo completo
TIER_2_RIESGO_PCT = 0.5    # riesgo reducido

# Backtest
CAPITAL_INICIAL       = 50_000
RIESGO_POR_TRADE_PCT  = 1.0
MIN_SEMANAS_HISTORICO = 210   # mínimo para calcular MM200 semanal (200 + warmup)

# Trailing
R_PARA_PROTEGER       = 2.0
R_PARA_TRAILING       = 4.0
PROTECCION_R_NEGATIVO = -0.25   # Stop a -0.25R al llegar a +2R
TRAILING_LOOKBACK     = 5       # Mínimo últimas 5 semanas para trailing inicial
TRAILING_LOOKBACK_FINAL = 3     # Últimas 3 semanas en fase final

# Estados de la posición
ESTADO_INICIAL   = "INICIAL"
ESTADO_PROTEGIDO = "PROTEGIDO"
ESTADO_TRAILING  = "TRAILING"

# Universo (importado de core si está disponible)
try:
    from core.universos import IBEX35, CONTINUO
    TICKER_EMPRESA = {
        "ACS.MC": "ACS", "AENA.MC": "AENA", "AMS.MC": "Amadeus", "ANA.MC": "Acciona",
        "BBVA.MC": "BBVA", "CABK.MC": "CaixaBank", "ELE.MC": "Endesa", "FER.MC": "Ferrovial",
        "GRF.MC": "Grifols", "IBE.MC": "Iberdrola", "IAG.MC": "IAG", "IDR.MC": "Indra",
        "ITX.MC": "Inditex", "MAP.MC": "Mapfre", "MRL.MC": "Merlin",
        "NTGY.MC": "Naturgy", "RED.MC": "Redeia", "REP.MC": "Repsol", "ROVI.MC": "Rovi",
        "SAB.MC": "Sabadell", "SAN.MC": "Santander", "SCYR.MC": "Sacyr", "SLR.MC": "Solaria",
        "TEF.MC": "Telefónica", "UNI.MC": "Unicaja", "CLNX.MC": "Cellnex", "LOG.MC": "Logista",
        "ACX.MC": "Acerinox", "BKT.MC": "Bankinter", "COL.MC": "Colonial",
        "ANE.MC": "Acciona Energía", "ENG.MC": "Enagás", "FCC.MC": "FCC",
        "PUIG.MC": "PUIG", "MTS.MC": "ArcelorMittal",
        "CIE.MC": "CIE Automotive", "VID.MC": "Vidrala",
        "TUB.MC": "Tubacex", "TRE.MC": "Técnicas Reunidas", "CAF.MC": "CAF",
        "GEST.MC": "Gestamp", "APAM.MC": "Applus", "PHM.MC": "PharmaMar",
        "OHLA.MC": "OHLA", "DOM.MC": "Global Dominion",
        "ENC.MC": "ENCE", "GRE.MC": "Grenergy", "ADX.MC": "Audax Renovables",
        "HOME.MC": "Neinor Homes", "AMP.MC": "Amper", "MEL.MC": "Meliá",
        "VIS.MC": "Viscofan", "ENO.MC": "Elecnor", "ECR.MC": "Ercros",
        "A3M.MC": "Atresmedia", "ATRY.MC": "Atrys Health", "R4.MC": "Renta 4",
        "HBX.MC": "HBX Group", "LIB.MC": "Libertas", "CASH.MC": "Cash Converters",
        "NEA.MC": "Naturhouse", "PSG.MC": "Prosegur", "MVC.MC": "Metrovacesa",
        "CIRSA.MC": "CIRSA", "DIA.MC": "DIA", "LDA.MC": "Línea Directa",
        "IMC.MC": "Inmocentro", "FAE.MC": "Faes Farma", "RLIA.MC": "Realia Business",
        "EBROM.MC": "Ebro Foods", "IZER.MC": "Izertis", "AEDAS.MC": "AEDAS Homes",
    }
except ImportError:
    IBEX35 = []
    CONTINUO = []
    TICKER_EMPRESA = {}


def calcular_parametros_adaptativos(volatilidad_actual):
    """Ajusta parámetros según régimen de volatilidad."""
    if volatilidad_actual is None:
        volatilidad_actual = VOL_MIN_PCT
    if volatilidad_actual < 10:
        return {"stop_atr_mult": 1.5, "pullback_min": 2.5, "riesgo_max": 3.0}
    elif volatilidad_actual > 20:
        return {"stop_atr_mult": 2.5, "pullback_min": 4.0, "riesgo_max": 5.0}
    else:
        return {"stop_atr_mult": STOP_ATR_MULTIPLICADOR, "pullback_min": PULLBACK_MIN_PCT, "riesgo_max": RIESGO_MAX_PCT}
