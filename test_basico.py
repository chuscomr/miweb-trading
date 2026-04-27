print("="*80)
print("TEST BÁSICO - ESTRATEGIAS BASE")
print("="*80)

# Test 1: Importar
print("\n1. Importando módulos...")
try:
    from estrategias.swing.pullback import PullbackSwing
    from estrategias.swing.breakout import BreakoutSwing
    print("   ✅ Imports OK")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit()

# Test 2: Crear instancias
print("\n2. Creando instancias...")
try:
    pb = PullbackSwing()
    br = BreakoutSwing()
    print("   ✅ Instancias OK")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit()

# Test 3: Evaluar un valor
print("\n3. Evaluando SAN.MC (Pullback)...")
try:
    resultado_pb = pb.evaluar('SAN.MC')
    print(f"   Resultado: {resultado_pb}")
    if resultado_pb:
        print(f"   ¿Válido? {resultado_pb.get('valido', False)}")
        print(f"   Score: {resultado_pb.get('score', 0)}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n4. Evaluando SAN.MC (Breakout)...")
try:
    resultado_br = br.evaluar('SAN.MC')
    print(f"   Resultado: {resultado_br}")
    if resultado_br:
        print(f"   ¿Válido? {resultado_br.get('valido', False)}")
        print(f"   Score: {resultado_br.get('score', 0)}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETADO")
print("="*80)

input("\nPresiona ENTER...")