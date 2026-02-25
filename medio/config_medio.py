# ==========================================================
# CONFIGURACIÓN - SISTEMA MEDIO PLAZO
# Timeframe: Semanal (4-24 semanas)
# Mercado: IBEX 35 + Mercado Continuo
# Estrategia: Pullback en tendencia alcista
# ==========================================================

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 PARÁMETROS DE ANÁLISIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Histórico mínimo requerido
MIN_SEMANAS_HISTORICO = 52  # 1 año de datos semanales

# Medias móviles para tendencia
MM_TENDENCIA_CORTA = 10   # ~2.5 meses
MM_TENDENCIA_MEDIA = 20   # ~5 meses
MM_TENDENCIA_LARGA = 40   # ~10 meses

# ATR para stops
ATR_PERIODO = 14  # 14 semanas ~3.5 meses

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 PARÁMETROS DE ENTRADA - PULLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Retroceso desde máximo reciente
PULLBACK_MIN_PCT = 3.0    # Mínimo 3% de retroceso
PULLBACK_MAX_PCT = 12.0   # Máximo 12% de retroceso

# Lookback para máximo reciente
LOOKBACK_MAXIMO = 10      # Buscar máximo en últimas 10 semanas

# Confirmación de giro
REQUIERE_GIRO_SEMANAL = True  # Precio > cierre semana anterior

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ GESTIÓN DE RIESGO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Rango de riesgo aceptable (% del precio de entrada)
RIESGO_MIN_PCT = 1.5      # Mínimo 1.5%
RIESGO_MAX_PCT = 4.0      # Máximo 4%

# Multiplicador ATR para stop inicial
STOP_ATR_MULTIPLICADOR = 2.0

# Lookback para stop por estructura
STOP_ESTRUCTURA_LOOKBACK = 5  # Mínimo últimas 5 semanas

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 GESTIÓN DE SALIDAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Estados de gestión
ESTADO_INICIAL = "INICIAL"
ESTADO_PROTEGIDO = "PROTEGIDO"
ESTADO_TRAILING = "TRAILING"

# Transiciones entre estados
R_PARA_PROTEGER = 2.0           # A +2R → mover stop a breakeven
R_PARA_TRAILING = 4.0           # A +4R → activar trailing

# Stop en estado protegido
PROTECCION_R_NEGATIVO = -0.25   # Stop a -0.25R (pequeña pérdida)

# Trailing stop
TRAILING_LOOKBACK = 5           # Mínimo últimas 5 semanas
TRAILING_LOOKBACK_FINAL = 3     # Últimas 3 semanas en fase final

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 FILTROS DE CALIDAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Volatilidad mínima (para evitar valores muertos)
MIN_VOLATILIDAD_PCT = 8.0   # Mínimo 8% de volatilidad anual

# Volumen mínimo (opcional, se puede deshabilitar poniendo 0)
MIN_VOLUMEN_SEMANAL = 0     # 0 = deshabilitado

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧠 PARÁMETROS ADAPTATIVOS POR VOLATILIDAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calcular_parametros_adaptativos(volatilidad_actual):
    """
    Ajusta parámetros del sistema según el régimen de volatilidad.
    Devuelve SIEMPRE un dict válido.
    """
    if volatilidad_actual is None:
        volatilidad_actual = MIN_VOLATILIDAD_PCT

    if volatilidad_actual < 10:
        # 🟢 Mercado tranquilo
        return {
            "stop_atr_mult": 1.5,
            "pullback_min": 2.5,
            "riesgo_max": 3.0
        }

    elif volatilidad_actual > 20:
        # 🔴 Mercado volátil
        return {
            "stop_atr_mult": 2.5,
            "pullback_min": 4.0,
            "riesgo_max": 5.0
        }

    else:
        # 🟡 Régimen normal
        return {
            "stop_atr_mult": STOP_ATR_MULTIPLICADOR,
            "pullback_min": PULLBACK_MIN_PCT,
            "riesgo_max": RIESGO_MAX_PCT
        }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎲 BACKTEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Capital y riesgo
CAPITAL_INICIAL = 10_000
RIESGO_POR_TRADE_PCT = 1.0  # 1% del capital por operación

# Costes de transacción
COMISION_PCT = 0.05         # 0.05% comisión
SLIPPAGE_PCT = 0.1          # 0.1% slippage estimado

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 UNIVERSO DE VALORES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IBEX_35 = [
    "ACS.MC", "AENA.MC", "AMS.MC", "ANA.MC", "BBVA.MC",
    "CABK.MC", "ELE.MC", "FER.MC", "GRF.MC", "IBE.MC",
    "IAG.MC", "IDR.MC", "ITX.MC", "MAP.MC", "MRL.MC",
    "NTGY.MC", "RED.MC", "REP.MC", "ROVI.MC", "SAB.MC",
    "SAN.MC", "SCYR.MC", "SLR.MC", "TEF.MC", "UNI.MC",
    "CLNX.MC", "LOG.MC", "ACX.MC", "BKT.MC", "COL.MC",
    "ANE.MC", "ENG.MC", "FCC.MC", "PUIG.MC", "MTS.MC"
]

MERCADO_CONTINUO = [
    "CIE.MC", "VID.MC", "TUB.MC", "TRE.MC", "CAF.MC",
    "GEST.MC", "APAM.MC", "PHM.MC", "OHLA.MC", "DOM.MC",
    "ENC.MC", "GRE.MC", "HOME.MC", "FAE.MC", "NEA.MC",
    "PSG.MC", "LDA.MC", "MEL.MC", "VIS.MC", "ECR.MC",
    "ENO.MC", "DIA.MC", "IMC.MC", "LIB.MC", "A3M.MC",
    "ATRY.MC", "R4.MC", "RLIA.MC", "MVC.MC", "EBROM.MC",
    "AMP.MC", "HBX.MC", "CASH.MC", "ADX.MC", "IZER.MC",
    "AEDAS.MC","MRL.MC"
]
# Diccionario de nombres de empresas
TICKER_EMPRESA = {
    "ACS.MC":"ACS","AENA.MC":"AENA","AMS.MC":"Amadeus","ANA.MC":"Acciona",
    "BBVA.MC":"BBVA","CABK.MC":"CaixaBank","ELE.MC":"Endesa","FER.MC":"Ferrovial",
    "GRF.MC":"Grifols","IBE.MC":"Iberdrola","IAG.MC":"IAG","IDR.MC":"Indra",
    "ITX.MC":"Inditex","MAP.MC":"Mapfre","MRL.MC":"Merlin",
    "NTGY.MC":"Naturgy","RED.MC":"Redeia","REP.MC":"Repsol","ROVI.MC":"Rovi",
    "SAB.MC":"Sabadell","SAN.MC":"Santander","SCYR.MC":"Sacyr","SLR.MC":"Solaria",
    "TEF.MC":"Telefónica","UNI.MC":"Unicaja","CLNX.MC":"Cellnex","LOG.MC":"Logista",
    "ACX.MC":"Acerinox","BKT.MC":"Bankinter","COL.MC":"Colonial","ANE.MC":"Acciona Energía",
    "ENG.MC":"Enagás","FCC.MC":"FCC","PUIG.MC":"PUIG","MTS.MC":"ARCELOR",
     
    "CIE.MC":"CIE Automotive","VID.MC":"Vidrala",
    "TUB.MC":"Tubacex","TRE.MC":"Técnicas Reunidas","CAF.MC":"CAF",
    "GEST.MC":"Gestamp","APAM.MC":"Applus","PHM.MC":"PharmaMar",
    "OHLA.MC":"OHLA","DOM.MC":"Global Dominion",
    "ENC.MC":"ENCE","GRE.MC":"Grenergy","ADX.MC":"Audax Renovables",
    "HOME.MC":"Neinor Homes","NHH.MC":"NH Hotel Group","AMP.MC":"AMPER",
    "MEL.MC":"Meliá","VIS.MC":"Viscofan","ENO.MC":"Elecnor",
    "ECR.MC":"Ercros","A3M.MC":"Atresmedia","ATRY.MC":"Atrys Health",
    "R4.MC":"Renta 4","HBX.MC":"HBX Group","LIB.MC":"Libertas",
    "CASH.MC":"Cash Converters","NEA.MC":"Naturhouse",
    "PSG.MC":"Prosegur","AMP.MC":"Amper","MVC.MC":"Metrovacesa",
    "CIRSA.MC":"CIRSA","DIA.MC":"DIA","LDA.MC":"Linea Directa",
    "IMC.MC":"Inmocentro","FAE.MC":"Faes Farma","RLIA.MC":"Realia Business",
    "EBROM.MC":"Ebro Motor","IZER.MC":"Izertis","AEDAS.MC":"AEDAS Inmb."
}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 CONFIGURACIÓN WEB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FLASK_DEBUG = True
FLASK_PORT = 5001  # Puerto diferente al swing (5000)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📝 NOTAS DE DISEÑO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
FILOSOFÍA DEL SISTEMA MEDIO PLAZO:

1. TIMEFRAME SEMANAL
   - Reduce ruido del mercado
   - Permite stops más amplios
   - Menos operaciones, más selectivas

2. ESTRATEGIA PULLBACK
   - Comprar retrocesos en tendencia alcista
   - Precio > MM20 semanal (tendencia)
   - Retroceso 3-12% desde máximo
   - Confirmación: giro alcista semanal

3. GESTIÓN CONSERVADORA
   - Stop inicial: estructura + ATR
   - +2R → Proteger en breakeven
   - +4R → Trailing stop agresivo
   
4. DIFERENCIAS CON SWING
   - Swing: 1-3 semanas, datos diarios
   - Medio: 4-24 semanas, datos semanales
   - Swing: Breakouts, momentum
   - Medio: Pullbacks, mean reversion
"""
