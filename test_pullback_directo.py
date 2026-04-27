#!/usr/bin/env python3
"""
TEST DIRECTO - Probar estrategia pullback en un valor
"""

print("="*80)
print("TEST DIRECTO DE PULLBACK")
print("="*80)

try:
    from estrategias.swing.pullback import PullbackSwing
    
    pb = PullbackSwing()
    
    print("\nProbando SAN.MC...")
    resultado = pb.evaluar('SAN.MC')
    
    print(f"\nResultado: {resultado}")
    
    if resultado and isinstance(resultado, dict):
        print(f"\n¿Es válido? {resultado.get('valido', False)}")
        print(f"Score: {resultado.get('score', 0)}")
        print(f"Razón: {resultado.get('razon', 'N/A')}")
    
    print("\n" + "="*80)
    print("Probando BBVA.MC...")
    resultado2 = pb.evaluar('BBVA.MC')
    print(f"Resultado: {resultado2}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona ENTER para salir...")
