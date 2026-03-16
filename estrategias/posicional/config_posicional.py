# ==========================================================
# CONFIGURACIÓN - SISTEMA POSICIONAL
# Timeframe: 6 meses - 2 años
# Mercado: IBEX 35 (selectivo)
# Estrategia: Trend Following + Position Trading
# ==========================================================

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 PARÁMETROS DE ANÁLISIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MIN_SEMANAS_HISTORICO = 200
MM_TENDENCIA_CORTA  = 20    # ~5 meses
MM_TENDENCIA_MEDIA  = 50    # ~1 año
MM_TENDENCIA_LARGA  = 200   # ~4 años
ATR_PERIODO         = 20    # 20 semanas ~5 meses

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 PARÁMETROS DE ENTRADA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Consolidación previa
CONSOLIDACION_MIN_SEMANAS   = 12    # Mínimo 3 meses consolidando
CONSOLIDACION_MAX_SEMANAS   = 26    # Máximo 6 meses (antes 36)
CONSOLIDACION_MAX_RANGO_PCT = 22.0  # Máximo 22% de rango (antes 30%)

# Breakout
BREAKOUT_CONFIRMACION_SEMANAS = 1
BREAKOUT_VOLUMEN_MIN_RATIO    = 1.5  # Volumen 1.5x sobre media

# Tendencia de fondo
REQUIERE_TENDENCIA_ALCISTA = True
DISTANCIA_MIN_MM50_PCT     = 2.0    # Mínimo 2% sobre MM50 (antes 3%)
DISTANCIA_MAX_MM50_PCT     = 15.0   # NUEVO: máximo 15% (evitar entrar corrido)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ GESTIÓN DE RIESGO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RIESGO_MIN_PCT          = 6.0   # Mínimo 6% (stops menores = entrada mal calibrada)
RIESGO_MAX_PCT          = 15.0  # Máximo 15%
STOP_ATR_MULTIPLICADOR  = 2.5
STOP_ESTRUCTURA_LOOKBACK = 26   # Mínimo últimas 26 semanas

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 GESTIÓN DE SALIDAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESTADO_INICIAL   = "INICIAL"
ESTADO_PROTEGIDO = "PROTEGIDO"
ESTADO_TRAILING  = "TRAILING"

R_PARA_PROTEGER      = 4.0   # A +4R → mover stop a breakeven (antes 5R)
R_PARA_TRAILING      = 8.0   # A +8R → activar trailing (antes 10R)
PROTECCION_R_NEGATIVO = -0.5

TRAILING_LOOKBACK       = 13
TRAILING_LOOKBACK_FINAL = 26
TRAILING_R_MINIMO       = 12.0  # Trailing final desde +12R (antes 15R)

DURACION_MINIMA_SEMANAS  = 26
DURACION_OBJETIVO_SEMANAS = 52

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 FILTROS DE CALIDAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MIN_VOLATILIDAD_PCT       = 20.0       # Mínimo 20% anual (antes 18%)
MAX_VOLATILIDAD_PCT       = 60.0       # NUEVO: máximo 60% (filtra SLR, GRF erráticos)
MIN_VOLUMEN_MEDIO_DIARIO  = 2_000_000
MIN_CAPITALIZACION        = 0
MIN_MESES_TENDENCIA_ALCISTA = 6

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎲 BACKTEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAPITAL_INICIAL        = 50_000
RIESGO_POR_TRADE_PCT   = 2.0
COMISION_PCT           = 0.08   # Más realista para posiciones grandes (antes 0.05%)
SLIPPAGE_PCT           = 0.15   # Entrada en apertura semanal (antes 0.1%)
AÑOS_BACKTEST          = 20

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 UNIVERSO DE VALORES - SELECTIVO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Solo valores líderes del IBEX 35 con alta capitalización y liquidez
IBEX_35 = [
    "ACX.MC", "AENA.MC", "AMS.MC", "ANA.MC", "ANE.MC",
    "BKT.MC", "BBVA.MC", "CABK.MC", "CLNX.MC", "COL.MC",
    "ELE.MC", "ENG.MC", "FCC.MC", "FER.MC", "GRF.MC",
    "IAG.MC", "IBE.MC", "IDR.MC", "ITX.MC", "LOG.MC",
    "MAP.MC", "MRL.MC", "MTS.MC", "NTGY.MC", "PUIG.MC",
    "RED.MC", "REP.MC", "ROVI.MC", "SAB.MC", "SAN.MC",
    "SCYR.MC", "SLR.MC", "TEF.MC", "UNI.MC", "ACS.MC"
]

IBEX_GRUPO_1 = [  # A → F
    "ACX.MC", "AENA.MC", "AMS.MC", "ANA.MC", "ANE.MC",
    "ACS.MC", "BKT.MC", "BBVA.MC", "CABK.MC", "CLNX.MC",
    "COL.MC", "ELE.MC"
]

IBEX_GRUPO_2 = [  # E → M
    "ENG.MC", "FCC.MC", "FER.MC", "GRF.MC", "IAG.MC",
    "IBE.MC", "IDR.MC", "ITX.MC", "LOG.MC", "MAP.MC",
    "MRL.MC", "MTS.MC"
]

IBEX_GRUPO_3 = [  # N → U
    "NTGY.MC", "PUIG.MC", "RED.MC", "REP.MC", "ROVI.MC",
    "SAB.MC", "SAN.MC", "SCYR.MC", "SLR.MC", "TEF.MC",
    "UNI.MC"
]

CONTINUO_GRUPO_1 = [  # A → CIE
    "A3M.MC", "AEDAS.MC", "AMP.MC", "ANE.MC", "APAM.MC",
    "ATRY.MC", "CAF.MC", "CASH.MC", "CIE.MC", "CIRSA.MC",
    "DIA.MC", "DOM.MC", "ECR.MC"
]

CONTINUO_GRUPO_2 = [  # EBR → MEL
    "EBROM.MC", "ENC.MC", "ENO.MC", "FAE.MC", "GEST.MC",
    "GRE.MC", "HBX.MC", "HOME.MC", "IMC.MC", "IZER.MC",
    "LDA.MC", "LIB.MC", "MEL.MC"
]

CONTINUO_GRUPO_3 = [  # MVC → Z
    "MVC.MC", "NEA.MC", "OHLA.MC", "PHM.MC", "PSG.MC",
    "R4.MC", "RLIA.MC", "TRE.MC", "TUB.MC", "VID.MC", "VIS.MC"
]

MERCADO_CONTINUO = CONTINUO_GRUPO_1 + CONTINUO_GRUPO_2 + CONTINUO_GRUPO_3

# Valores selectos (alta capitalización y liquidez)
# Se filtrarán automáticamente según criterios
UNIVERSO_POSICIONAL = IBEX_35

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 CONFIGURACIÓN WEB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FLASK_DEBUG = True
FLASK_PORT = 5001  # Puerto único para todo MiWeb

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📝 FILOSOFÍA DEL SISTEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
FILOSOFÍA DEL SISTEMA POSICIONAL:

1. OBJETIVO
   - Capturar tendencias de 6 meses - 2 años
   - Complementar swing (no solapar)
   - Buy & hold de posiciones ganadoras

2. ESTRATEGIA
   - NO pullbacks (eso es swing extended)
   - SÍ breakouts de consolidaciones largas
   - Trend following puro
   
3. TIMEFRAME
   - Análisis: Datos semanales
   - Evaluación: Cada semana (no cada día)
   - Gestión: Mensual (revisar una vez al mes)
   - Duración: 6-24 meses por posición

4. SELECCIÓN
   - Solo valores líderes (cap > 5B€)
   - Alta liquidez (vol > 1M€/día)
   - Tendencia alcista sostenida
   - 10-15 valores máximo

5. ENTRADA
   - Consolidación 3-6 meses
   - Breakout confirmado
   - Volumen creciente
   - Tendencia de fondo alcista

6. GESTIÓN
   - Stop MUY amplio (8-15%)
   - No tocar hasta +5R
   - Trailing solo después +10R
   - Dejar correr winners

7. EXPECTATIVAS
   - 0.5-1 trade/valor/año (vs 5.6 en swing extended)
   - Expectancy objetivo: +3R (vs 0.32R swing extended)
   - Win rate: 25-30% (vs 35% swing extended)
   - Menos trades, mucho más grandes

8. DIFERENCIAS CON SWING EXTENDED
   
   Swing Extended:
   - Duración: 4-12 semanas
   - Estrategia: Pullbacks
   - Stop: 1.5-4%
   - Objetivo: 2-4R
   - Gestión: Activa (semanal)
   
   Posicional:
   - Duración: 6 meses - 2 años
   - Estrategia: Trend Following
   - Stop: 8-15%
   - Objetivo: 10-30R
   - Gestión: Pasiva (mensual)

9. PSICOLOGÍA
   - Paciencia extrema
   - Aguantar volatilidad
   - No mirar cada día
   - Confiar en la tendencia
   
10. CAPITAL
    - Asignar capital diferente
    - No competir con swing
    - Posiciones más grandes (2% vs 1%)
    - Menos diversificación (5-8 valores max)
"""