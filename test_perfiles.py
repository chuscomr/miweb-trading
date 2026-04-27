#!/usr/bin/env python3
"""
TEST SIMPLE - SISTEMA DE PERFILES
Muestra cómo funciona el sistema de ponderación
"""

print("\n" + "="*80)
print("PRUEBA DE PERFILES DE TRADING")
print("="*80 + "\n")

try:
    from estrategias.swing.perfiles_contexto import (
        mostrar_perfil,
        mostrar_ejemplos_ponderacion
    )
    
    # Mostrar los 3 perfiles
    for contexto in ["ALCISTA", "LATERAL", "BAJISTA"]:
        mostrar_perfil(contexto)
    
    # Mostrar ejemplos de ponderación
    mostrar_ejemplos_ponderacion()
    
    print("\n✅ Test completado exitosamente")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona ENTER para salir...")
