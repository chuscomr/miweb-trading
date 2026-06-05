"""
Diagnóstico FER.MC - ¿Por qué sigue en 6/10?
"""
import sys
sys.path.insert(0, 'D:\\a\\MiWeb')

# Forzar recarga de módulos
import importlib
if 'estrategias.medio.config_medio' in sys.modules:
    importlib.reload(sys.modules['estrategias.medio.config_medio'])
if 'estrategias.medio.logica_medio' in sys.modules:
    importlib.reload(sys.modules['estrategias.medio.logica_medio'])

from estrategias.medio.config_medio import *
print("=== VERIFICACIÓN CONFIG ===")
print(f"TIMING_SANO_PUNTOS: {TIMING_SANO_PUNTOS}")
print(f"TIMING_DETERIORO_UMBRAL: {TIMING_DETERIORO_UMBRAL}")
print(f"TIMING_DETERIORO_PENALIZACION: {TIMING_DETERIORO_PENALIZACION}")
print(f"SCORE_MIN_ESTRUCTURA: {SCORE_MIN_ESTRUCTURA}")
print()

from estrategias.medio.logica_medio import calcular_score_medio_v2
import yfinance as yf

ticker = "FER.MC"
print(f"=== DIAGNÓSTICO: {ticker} ===\n")

# Obtener datos
stock = yf.Ticker(ticker)
df = stock.history(period="1y", interval="1wk")

precios = df['Close'].tolist()
precio_actual = precios[-1]

# Calcular indicadores
mm20 = sum(precios[-20:]) / 20 if len(precios) >= 20 else 0
mm50 = sum(precios[-50:]) / 50 if len(precios) >= 50 else 0
mm200 = sum(precios[-200:]) / 200 if len(precios) >= 200 else 0

mm20_anterior = sum(precios[-25:-5]) / 20 if len(precios) >= 25 else 0
pendiente_mm20 = (mm20 - mm20_anterior) / mm20_anterior * 100 if mm20_anterior > 0 else 0

mm50_sobre_mm200 = mm50 > mm200

# Pullback
maximo_20 = max(precios[-20:])
retroceso_pct = ((maximo_20 - precio_actual) / maximo_20) * 100

print("DATOS BÁSICOS:")
print(f"Precio: {precio_actual:.2f}€")
print(f"MM20: {mm20:.2f}€")
print(f"MM50: {mm50:.2f}€")
print(f"MM200: {mm200:.2f}€")
print(f"Pendiente MM20: {pendiente_mm20:+.2f}%")
print(f"MM50 > MM200: {mm50_sobre_mm200}")
print(f"Retroceso: {retroceso_pct:.2f}%")
print()

# Calcular score
tendencia = {
    "mm20": mm20,
    "mm50": mm50,
    "mm200": mm200,
    "pendiente_mm20": pendiente_mm20,
    "mm50_sobre_mm200": mm50_sobre_mm200
}

pullback = {
    "retroceso_pct": retroceso_pct,
    "es_pullback": 3.0 <= retroceso_pct <= 12.0
}

resultado = calcular_score_medio_v2(precios, tendencia, pullback, df=df)

print("=== RESULTADO SCORING V2 ===")
print(f"Score Total: {resultado['score']}/10")
print(f"Válido: {resultado['valido']}")
print()

desglose = resultado.get('desglose', {})
print("DESGLOSE:")
print(f"  Estructura: {desglose.get('estructura', 0)}/5")
print(f"  Timing: {desglose.get('timing', 0)}/3")
print(f"  Momentum: {desglose.get('momentum', 0)}/2")
print()

# DEBUG: Mostrar RSI calculado
rsi_calculado = resultado.get('rsi', None)
print(f"RSI Calculado por sistema: {rsi_calculado}")
print(f"RSI Rango válido: {RSI_MIN_PULLBACK}-{RSI_MAX_PULLBACK}")
if rsi_calculado:
    if RSI_MIN_PULLBACK <= rsi_calculado <= RSI_MAX_PULLBACK:
        print("  ✓ RSI EN RANGO → debería sumar +1.0")
    else:
        print(f"  ✗ RSI FUERA DE RANGO → por eso momentum=0")
print()

# Calcular distancia MM20
dist_mm20 = (precio_actual - mm20) / mm20 * 100 if mm20 > 0 else 0
print(f"Distancia MM20: {dist_mm20:+.2f}%")
print()

# Verificar umbrales
print("ANÁLISIS TIMING:")
if TIMING_PERFECTO_MIN <= dist_mm20 <= TIMING_PERFECTO_MAX:
    print(f"  ✓ En rango PERFECTO ({TIMING_PERFECTO_MIN} a {TIMING_PERFECTO_MAX}%)")
    print(f"    Debería sumar: +{TIMING_PERFECTO_PUNTOS}")
elif TIMING_SANO_MIN <= dist_mm20 < TIMING_PERFECTO_MIN:
    print(f"  ✓ En rango SANO ({TIMING_SANO_MIN} a {TIMING_PERFECTO_MIN}%)")
    print(f"    Debería sumar: +{TIMING_SANO_PUNTOS}")
elif dist_mm20 < TIMING_DETERIORO_UMBRAL:
    print(f"  ✗ DETERIORO (< {TIMING_DETERIORO_UMBRAL}%)")
    print(f"    Debería penalizar: {TIMING_DETERIORO_PENALIZACION}")
else:
    print(f"  ? Fuera de rangos definidos")

print()
print("Si el score sigue en 6/10 con estos cambios:")
print("1. __pycache__ no se limpió → Python usa versión antigua")
print("2. Servidor no se reinició → Flask carga módulos al inicio")
print("3. Hay otra penalización fuerte que no identifiqué")
