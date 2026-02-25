"""
Script de prueba para verificar que las funciones de breakout y pullback funcionan
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swing_trading.logica_breakout import detectar_breakout_swing
from swing_trading.logica_pullback import detectar_pullback_swing

print("=" * 60)
print("TEST 1: Probando detectar_breakout_swing con SAN.MC")
print("=" * 60)

resultado_breakout = detectar_breakout_swing('SAN.MC', periodo='6mo')
print(f"\nResultado breakout:")
print(f"  Tipo: {type(resultado_breakout)}")
print(f"  Valido: {resultado_breakout.get('valido') if resultado_breakout else None}")
if resultado_breakout:
    print(f"  Keys: {list(resultado_breakout.keys())}")
    if resultado_breakout.get('valido'):
        print(f"  Setup score: {resultado_breakout.get('setup_score')}")
        print(f"  RR: {resultado_breakout.get('rr')}")
    else:
        print(f"  Motivos: {resultado_breakout.get('motivos', [])}")

print("\n" + "=" * 60)
print("TEST 2: Probando detectar_pullback_swing con SAN.MC")
print("=" * 60)

resultado_pullback = detectar_pullback_swing('SAN.MC', periodo='1y')
print(f"\nResultado pullback:")
print(f"  Tipo: {type(resultado_pullback)}")
print(f"  Valido: {resultado_pullback.get('valido') if resultado_pullback else None}")
if resultado_pullback:
    print(f"  Keys: {list(resultado_pullback.keys())}")
    if resultado_pullback.get('valido'):
        print(f"  Setup score: {resultado_pullback.get('setup_score')}")
        print(f"  RR: {resultado_pullback.get('rr')}")
    else:
        print(f"  Motivos: {resultado_pullback.get('motivos', [])}")

print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)
print(f"Breakout valido: {resultado_breakout.get('valido') if resultado_breakout else False}")
print(f"Pullback valido: {resultado_pullback.get('valido') if resultado_pullback else False}")
