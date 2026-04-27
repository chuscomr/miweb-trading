#!/usr/bin/env python3
"""
VALIDACIÓN RÁPIDA - SISTEMA BASE vs MEJORADO

Compara resultados REALES del mercado actual:
- Evalúa contexto actual del IBEX
- Escanea con sistema BASE (sin filtro)
- Escanea con sistema MEJORADO (con filtro)
- Muestra diferencias

VERSIÓN: v82.7
FECHA: 2026-04-25
"""

import sys
import os
from datetime import datetime

# Agregar path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

print("\n" + "="*80)
print("🔍 VALIDACIÓN RÁPIDA: SISTEMA BASE vs MEJORADO")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80 + "\n")

try:
    from core.contexto_mercado import evaluar_contexto_ibex
    from estrategias.swing.scanner_swing import escanear_mercado
    from estrategias.swing.perfiles_contexto import obtener_perfil_trading
    from core.universos import IBEX35
    from flask import Flask
    import config
    
    # Crear app Flask temporal para cache
    app = Flask(__name__)
    app.config['CACHE_TYPE'] = config.CACHE_TYPE
    app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_DEFAULT_TIMEOUT
    app.config['SECRET_KEY'] = 'validacion-temporal-key'
    
    with app.app_context():
        from database import init_app
        init_app(app)
        
        cache = app.config.get("CACHE_INSTANCE")
        
        print("📊 PASO 1: EVALUAR CONTEXTO ACTUAL DEL MERCADO")
        print("─"*80)
        
        try:
            contexto = evaluar_contexto_ibex(cache=cache)
            tendencia = contexto.get("tendencia", "DESCONOCIDO")
            detalles = contexto.get("detalles", {})
            
            print(f"✅ Contexto detectado: {tendencia}")
            print(f"\nDetalles:")
            for key, value in detalles.items():
                print(f"  • {key}: {value}")
            
        except Exception as e:
            print(f"⚠️ Error evaluando contexto: {e}")
            tendencia = "LATERAL"  # Default
            print(f"Usando contexto por defecto: {tendencia}")
        
        print("\n" + "="*80)
        print("📊 PASO 2: ESCANEAR CON SISTEMA BASE (sin filtro)")
        print("="*80)
        print("Configuración: Score mínimo fijo 5.5, sin ponderación\n")
        
        # Escanear SIN filtro adaptativo
        resultados_base = escanear_mercado(
            tickers=IBEX35,
            tipo_scan="ambos",
            max_workers=4,
            cache=cache,
            usar_perfil_adaptativo=False  # ← SIN FILTRO
        )
        
        print(f"\n✅ Scan BASE completado: {len(resultados_base)} señales encontradas")
        
        if resultados_base:
            print("\n📋 Top 10 señales BASE:")
            print(f"{'Ticker':<10} {'Tipo':<10} {'Score':<8} {'Calidad':<12}")
            print("─"*50)
            for i, r in enumerate(resultados_base[:10], 1):
                ticker = r.get('ticker', '?')
                tipo = r.get('tipo_estrategia', '?')
                score = r.get('score', 0)
                calidad = r.get('calidad', '?')
                print(f"{ticker:<10} {tipo:<10} {score:<8.1f} {calidad:<12}")
        else:
            print("❌ No se encontraron señales con sistema BASE")
        
        print("\n" + "="*80)
        print("🎯 PASO 3: ESCANEAR CON SISTEMA MEJORADO (con filtro)")
        print("="*80)
        print(f"Configuración: Contexto {tendencia}, filtro adaptativo activado\n")
        
        # Mostrar perfil que se aplicará
        perfil = obtener_perfil_trading(tendencia)
        print(f"Perfil activo: {perfil['contexto']}")
        print(f"  • Score base mínimo: {perfil['score_base_minimo']}")
        print(f"  • Peso Breakout: {perfil['peso_breakout']:.1f}x")
        print(f"  • Peso Pullback: {perfil['peso_pullback']:.1f}x")
        print(f"  • Bonus Breakout: +{perfil['bonus_breakout']}")
        print(f"  • Bonus Pullback: +{perfil['bonus_pullback']}")
        print()
        
        # Escanear CON filtro adaptativo
        resultados_mejorado = escanear_mercado(
            tickers=IBEX35,
            tipo_scan="ambos",
            max_workers=4,
            cache=cache,
            usar_perfil_adaptativo=True  # ← CON FILTRO
        )
        
        print(f"\n✅ Scan MEJORADO completado: {len(resultados_mejorado)} señales encontradas")
        
        if resultados_mejorado:
            print("\n📋 Top 10 señales MEJORADAS:")
            print(f"{'Ticker':<10} {'Tipo':<10} {'Score Orig':<12} {'Score Pond':<12} {'Score Rank':<12} {'Calidad':<12}")
            print("─"*80)
            for i, r in enumerate(resultados_mejorado[:10], 1):
                ticker = r.get('ticker', '?')
                tipo = r.get('tipo_estrategia', '?')
                score_orig = r.get('score_original', r.get('score', 0))
                score_pond = r.get('score_ponderado', 0)
                score_rank = r.get('score_ranking', 0)
                calidad = r.get('calidad', '?')
                print(f"{ticker:<10} {tipo:<10} {score_orig:<12.1f} {score_pond:<12.1f} {score_rank:<12.1f} {calidad:<12}")
        else:
            print("❌ No se encontraron señales con sistema MEJORADO")
        
        print("\n" + "="*80)
        print("📊 PASO 4: COMPARACIÓN DE RESULTADOS")
        print("="*80 + "\n")
        
        print(f"RESUMEN:")
        print(f"  • Contexto del mercado:     {tendencia}")
        print(f"  • Señales BASE:             {len(resultados_base)}")
        print(f"  • Señales MEJORADO:         {len(resultados_mejorado)}")
        print(f"  • Diferencia:               {len(resultados_mejorado) - len(resultados_base)} ({((len(resultados_mejorado)/max(len(resultados_base), 1) - 1)*100):.0f}%)")
        
        # Comparar calidad
        if resultados_base:
            base_excelentes = sum(1 for r in resultados_base if r.get('calidad') == 'excelente')
            base_buenos = sum(1 for r in resultados_base if r.get('calidad') == 'bueno')
            base_mediocres = sum(1 for r in resultados_base if r.get('calidad') == 'mediocre')
            
            print(f"\n📊 Distribución calidad BASE:")
            print(f"  ⭐ Excelentes: {base_excelentes} ({base_excelentes/max(len(resultados_base), 1)*100:.0f}%)")
            print(f"  🔵 Buenos:     {base_buenos} ({base_buenos/max(len(resultados_base), 1)*100:.0f}%)")
            print(f"  🟢 Mediocres:  {base_mediocres} ({base_mediocres/max(len(resultados_base), 1)*100:.0f}%)")
        
        if resultados_mejorado:
            mej_excelentes = sum(1 for r in resultados_mejorado if r.get('calidad') == 'excelente')
            mej_buenos = sum(1 for r in resultados_mejorado if r.get('calidad') == 'bueno')
            mej_mediocres = sum(1 for r in resultados_mejorado if r.get('calidad') == 'mediocre')
            
            print(f"\n📊 Distribución calidad MEJORADO:")
            print(f"  ⭐ Excelentes: {mej_excelentes} ({mej_excelentes/max(len(resultados_mejorado), 1)*100:.0f}%)")
            print(f"  🔵 Buenos:     {mej_buenos} ({mej_buenos/max(len(resultados_mejorado), 1)*100:.0f}%)")
            print(f"  🟢 Mediocres:  {mej_mediocres} ({mej_mediocres/max(len(resultados_mejorado), 1)*100:.0f}%)")
        
        print("\n" + "="*80)
        print("🎯 CONCLUSIONES")
        print("="*80)
        
        if len(resultados_mejorado) < len(resultados_base):
            print(f"\n✅ El filtro está funcionando:")
            print(f"   • Rechazó {len(resultados_base) - len(resultados_mejorado)} señales de baja calidad")
            print(f"   • Redujo ruido en {abs((len(resultados_mejorado)/max(len(resultados_base), 1) - 1)*100):.0f}%")
        elif len(resultados_mejorado) > len(resultados_base):
            print(f"\n⚠️ El filtro está agregando señales:")
            print(f"   • Esto puede indicar un problema en la configuración")
        else:
            print(f"\n⚠️ Mismo número de señales:")
            print(f"   • El filtro puede no estar teniendo efecto")
        
        if resultados_mejorado and resultados_base:
            # Comparar scores promedio
            avg_base = sum(r.get('score', 0) for r in resultados_base) / len(resultados_base)
            avg_mej = sum(r.get('score_original', r.get('score', 0)) for r in resultados_mejorado) / len(resultados_mejorado)
            
            print(f"\n📊 Score promedio:")
            print(f"   • BASE:     {avg_base:.2f}")
            print(f"   • MEJORADO: {avg_mej:.2f}")
            print(f"   • Mejora:   {avg_mej - avg_base:+.2f} ({((avg_mej/avg_base - 1)*100):+.1f}%)")
        
        print("\n" + "="*80)
        print("✅ Validación completada")
        print("="*80 + "\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\n⚠️ Asegúrate de:")
    print("  1. Estar en el directorio correcto (D:\\a\\MiWeb)")
    print("  2. Tener todas las dependencias instaladas")
    print("  3. Tener conexión a internet para descargar datos")
    print("="*80 + "\n")
