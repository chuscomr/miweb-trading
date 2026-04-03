# ==========================================================
# CONFIGURACIÓN — SISTEMA MEDIO PLAZO
# Timeframe: 4-24 semanas (semanal)
# ==========================================================

# Medias móviles
MM_TENDENCIA_CORTA  = 10
MM_TENDENCIA_MEDIA  = 20
MM_TENDENCIA_LARGA  = 40
MM_FILTRO_TENDENCIA = 50   # MM50 debe estar por encima de MM200
MM_FILTRO_LARGO     = 200  # MM200 como referencia macro

# ATR
ATR_PERIODO = 14

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
