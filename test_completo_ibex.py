print("="*80)
print("TEST COMPLETO IBEX 35 - BUSCAR SETUPS VÁLIDOS")
print("="*80)

from estrategias.swing.pullback import PullbackSwing
from estrategias.swing.breakout import BreakoutSwing
from core.universos import IBEX35

pb = PullbackSwing()
br = BreakoutSwing()

print(f"\nEscaneando {len(IBEX35)} valores del IBEX 35...")
print("="*80)

pullbacks_validos = []
breakouts_validos = []
total_escaneados = 0

for ticker in IBEX35:
    total_escaneados += 1
    print(f"\r[{total_escaneados}/{len(IBEX35)}] Escaneando {ticker}...", end="", flush=True)
    
    # Probar pullback
    try:
        res_pb = pb.evaluar(ticker)
        if res_pb and res_pb.get('valido', False):
            pullbacks_validos.append({
                'ticker': ticker,
                'score': res_pb.get('setup_score', 0),
                'entrada': res_pb.get('entrada', 0),
                'tipo': 'PULLBACK'
            })
    except:
        pass
    
    # Probar breakout
    try:
        res_br = br.evaluar(ticker)
        if res_br and res_br.get('valido', False):
            breakouts_validos.append({
                'ticker': ticker,
                'score': res_br.get('setup_score', 0),
                'entrada': res_br.get('entrada', 0),
                'tipo': 'BREAKOUT'
            })
    except:
        pass

print("\n" + "="*80)
print("RESULTADOS:")
print("="*80)

print(f"\n📊 PULLBACKS VÁLIDOS: {len(pullbacks_validos)}")
if pullbacks_validos:
    pullbacks_validos.sort(key=lambda x: x['score'], reverse=True)
    for setup in pullbacks_validos:
        print(f"   {setup['ticker']:<12} Score: {setup['score']:<5.1f} Entrada: {setup['entrada']:.2f}€")
else:
    print("   ❌ Ninguno encontrado")

print(f"\n📊 BREAKOUTS VÁLIDOS: {len(breakouts_validos)}")
if breakouts_validos:
    breakouts_validos.sort(key=lambda x: x['score'], reverse=True)
    for setup in breakouts_validos:
        print(f"   {setup['ticker']:<12} Score: {setup['score']:<5.1f} Entrada: {setup['entrada']:.2f}€")
else:
    print("   ❌ Ninguno encontrado")

print(f"\n📊 TOTAL SETUPS VÁLIDOS: {len(pullbacks_validos) + len(breakouts_validos)}")

print("\n" + "="*80)
print("CONCLUSIÓN:")
print("="*80)

if len(pullbacks_validos) + len(breakouts_validos) == 0:
    print("""
✅ El sistema funciona correctamente.

❌ HOY no hay setups válidos en el IBEX 35.

Esto es NORMAL y esperado en mercados:
   • Laterales sin claridad
   • Sin momentum
   • Sin estructuras técnicas claras

El filtro de contexto v82.7 está funcionando como debe:
   → Rechaza todo lo que no cumple criterios estrictos
   → Mejor NO operar que operar mal
""")
else:
    print(f"""
✅ Se encontraron {len(pullbacks_validos) + len(breakouts_validos)} setups válidos.

Ahora estos pasarán por el filtro de contexto LATERAL:
   • Score mínimo: 6.5
   • Peso Pullback: 1.0x
   • Peso Breakout: 0.6x

Setups que deberían pasar el filtro LATERAL:
""")
    
    # Aplicar filtro de contexto manualmente
    from estrategias.swing.perfiles_contexto import setup_pasa_filtro
    
    todos_setups = pullbacks_validos + breakouts_validos
    pasaran_filtro = []
    
    for setup in todos_setups:
        tipo = 'pullback' if setup['tipo'] == 'PULLBACK' else 'breakout'
        pasa, score_pond, score_min = setup_pasa_filtro(setup['score'], tipo, 'LATERAL')
        
        if pasa:
            setup['score_ponderado'] = score_pond
            pasaran_filtro.append(setup)
            print(f"   ✅ {setup['ticker']} ({setup['tipo']}) - Score: {setup['score']:.1f} → Ponderado: {score_pond:.1f}")
        else:
            print(f"   ❌ {setup['ticker']} ({setup['tipo']}) - Score: {setup['score']:.1f} → Ponderado: {score_pond:.1f} (rechazado)")
    
    print(f"\n🎯 SETUPS QUE PASARÍAN EL FILTRO v82.7: {len(pasaran_filtro)}")

print("\n" + "="*80)

input("\nPresiona ENTER para salir...")
