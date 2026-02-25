# ==========================================================
# CONFIGURACIÓN - SISTEMA POSICIONAL
# Timeframe: 6 meses - 2 años
# Mercado: IBEX 35 (selectivo)
# Estrategia: Trend Following + Position Trading
# ==========================================================

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 PARÁMETROS DE ANÁLISIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Histórico mínimo requerido
MIN_SEMANAS_HISTORICO = 0  # V3: Sin filtro - IBEX 35
# Medias móviles para tendencia (timeframe semanal)
MM_TENDENCIA_CORTA = 20    # ~5 meses
MM_TENDENCIA_MEDIA = 50    # ~1 año
MM_TENDENCIA_LARGA = 200   # ~4 años

# ATR para stops (semanal)
ATR_PERIODO = 20  # 20 semanas ~5 meses

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 PARÁMETROS DE ENTRADA - TREND FOLLOWING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Consolidación previa
CONSOLIDACION_MIN_SEMANAS = 12  # Mínimo 3 meses consolidando
CONSOLIDACION_MAX_SEMANAS = 26  # Máximo 6 meses consolidando
CONSOLIDACION_MAX_RANGO_PCT = 30.0  # Máximo 30% de rango (más permisivo)

# Breakout de consolidación
BREAKOUT_CONFIRMACION_SEMANAS = 1  # Confirmación en 1 semana
BREAKOUT_VOLUMEN_MIN_RATIO = 1.5   # Volumen 1.5x superior a media

# Tendencia de fondo
REQUIERE_TENDENCIA_ALCISTA = True  # Precio > MM50 > MM200
DISTANCIA_MIN_MM50_PCT = 3.0       # Precio al menos 3% sobre MM50 (bajado de 5%)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🛡️ GESTIÓN DE RIESGO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Rango de riesgo aceptable (% del precio de entrada)
RIESGO_MIN_PCT = 8.0      # Mínimo 8%
RIESGO_MAX_PCT = 15.0     # Máximo 15%

# Multiplicador ATR para stop inicial
STOP_ATR_MULTIPLICADOR = 2.5

# Lookback para stop por estructura
STOP_ESTRUCTURA_LOOKBACK = 26  # Mínimo últimas 26 semanas (6 meses)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 GESTIÓN DE SALIDAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Estados de gestión
ESTADO_INICIAL = "INICIAL"
ESTADO_PROTEGIDO = "PROTEGIDO"
ESTADO_TRAILING = "TRAILING"

# Transiciones entre estados
R_PARA_PROTEGER = 5.0           # A +5R → mover stop a breakeven
R_PARA_TRAILING = 10.0          # A +10R → activar trailing

# Stop en estado protegido
PROTECCION_R_NEGATIVO = -0.5    # Stop a -0.5R (pequeña pérdida aceptable)

# Trailing stop
TRAILING_LOOKBACK = 13          # Mínimo últimas 13 semanas (trimestre)
TRAILING_LOOKBACK_FINAL = 26    # Últimas 26 semanas (semestre) en fase final
TRAILING_R_MINIMO = 15.0        # Solo activar trailing final si > +15R

# Duración mínima en posición
DURACION_MINIMA_SEMANAS = 26    # Mínimo 6 meses (no salir antes)
DURACION_OBJETIVO_SEMANAS = 52  # Objetivo 1 año

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 FILTROS DE CALIDAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Volatilidad mínima (anual)
MIN_VOLATILIDAD_PCT = 18.0   # V3: Más permisivo para posicional

# Volumen mínimo (para liquidez)
MIN_VOLUMEN_MEDIO_DIARIO = 2_000_000  # V3: IBEX garantiza liquidez

# Capitalización mínima
MIN_CAPITALIZACION = 0  # V3: IBEX ya es filtro premium

# Tendencia alcista sostenida
MIN_MESES_TENDENCIA_ALCISTA = 6  # Mínimo 6 meses en tendencia alcista

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎲 BACKTEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Capital y riesgo
CAPITAL_INICIAL = 50_000        # Capital mayor (posiciones grandes)
RIESGO_POR_TRADE_PCT = 2.0      # 2% del capital por operación (vs 1% swing)

# Costes de transacción
COMISION_PCT = 0.05         # 0.05% comisión
SLIPPAGE_PCT = 0.1          # 0.1% slippage estimado

# Periodo de backtest
AÑOS_BACKTEST = 10           # 10 años históricos

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📋 UNIVERSO DE VALORES - SELECTIVO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Solo valores líderes del IBEX 35 con alta capitalización y liquidez
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
    "CIE.MC","VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC",
    "PHM.MC","OHLA.MC","DOM.MC","ENC.MC","GRE.MC","ANE.MC",
    "HOME.MC","CIRSA.MC","FAE.MC","NEA.MC","PSG.MC","LDA.MC",
    "MEL.MC","VIS.MC","ECR.MC","ENO.MC","DIA.MC","IMC.MC","LIB.MC",
    "A3M.MC","ATRY.MC","R4.MC","RLIA.MC","MVC.MC","EBROM.MC","AMP.MC",
    "HBX.MC","CASH.MC","ADX.MC","AMP.MC","IZER.MC","AEDAS.MC"
    
]

# Valores selectos (alta capitalización y liquidez)
# Se filtrarán automáticamente según criterios
UNIVERSO_POSICIONAL = IBEX_35

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 CONFIGURACIÓN WEB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FLASK_DEBUG = True
FLASK_PORT = 5002  # Puerto diferente (swing=5000, medio=5001)

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