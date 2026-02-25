# diagnostico_universo.py
import sys
sys.path.append('C:/Users/chusc/Desktop/MiWeb')

from posicional.config_posicional import (
    IBEX_35,
    MIN_VOLATILIDAD_PCT,
    MIN_VOLUMEN_MEDIO_DIARIO,
    MIN_CAPITALIZACION
)
from posicional.datos_posicional import cargar_datos_posicionales, calcular_metricas_universo

print("=" * 70)
print("🔍 DIAGNÓSTICO UNIVERSO POSICIONAL")
print("=" * 70)
print(f"Total valores IBEX 35: {len(IBEX_35)}")
print(f"\n📊 FILTROS ACTUALES:")
print(f"   Volatilidad mínima: {MIN_VOLATILIDAD_PCT}%")
print(f"   Volumen mínimo: {MIN_VOLUMEN_MEDIO_DIARIO:,.0f}€")
print(f"   Capitalización mínima: {MIN_CAPITALIZACION:,.0f}€")
print("=" * 70)

# Analizar cada ticker
incluidos = []
excluidos = []

for ticker in IBEX_35:
    df = cargar_datos_posicionales(ticker)
    if df is None or df.empty:
        excluidos.append((ticker, "Sin datos históricos"))
        continue
    
    metricas = calcular_metricas_universo(df, ticker)
    if metricas is None:
        excluidos.append((ticker, "Error al calcular métricas"))
        continue
    
    motivos = []
    if metricas['volatilidad_anual'] < MIN_VOLATILIDAD_PCT:
        motivos.append(f"Volatilidad {metricas['volatilidad_anual']:.1f}% < {MIN_VOLATILIDAD_PCT}%")
    if metricas['volumen_medio_diario'] < MIN_VOLUMEN_MEDIO_DIARIO:
        motivos.append(f"Volumen {metricas['volumen_medio_diario']/1e6:.1f}M€ < {MIN_VOLUMEN_MEDIO_DIARIO/1e6:.1f}M€")
    if metricas['capitalizacion'] < MIN_CAPITALIZACION:
        motivos.append(f"Cap {metricas['capitalizacion']/1e9:.1f}B€ < {MIN_CAPITALIZACION/1e9:.1f}B€")
    
    if motivos:
        excluidos.append((ticker, " | ".join(motivos)))
    else:
        incluidos.append((ticker, metricas))

print(f"\n✅ INCLUIDOS ({len(incluidos)}):")
for ticker, metricas in sorted(incluidos):
    print(f"   {ticker:10} | Vol:{metricas['volatilidad_anual']:5.1f}% | "
          f"Volumen:{metricas['volumen_medio_diario']/1e6:6.1f}M€ | "
          f"Cap:{metricas['capitalizacion']/1e9:5.1f}B€")

print(f"\n❌ EXCLUIDOS ({len(excluidos)}):")
for ticker, motivo in sorted(excluidos):
    print(f"   {ticker:10} | {motivo}")

print("=" * 70)