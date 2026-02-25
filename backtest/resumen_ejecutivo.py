"""
Módulo de Resumen Ejecutivo
Genera dashboard y guarda histórico de resultados
"""

from datetime import datetime
import json
from pathlib import Path


def generar_resumen_ejecutivo(metricas, tickers_operados, tickers_excluidos, config):
    """
    Genera resumen ejecutivo de una pantalla
    
    Args:
        metricas: dict con métricas del backtest
        tickers_operados: list de dicts con info de tickers operados
        tickers_excluidos: list de dicts con info de tickers excluidos
        config: dict con configuración del sistema
    """
    
    # Clasificar tickers por performance
    aprobados = [t for t in tickers_operados if t['retorno'] >= 2.0]
    neutros = [t for t in tickers_operados if -2.0 <= t['retorno'] < 2.0]
    rechazados = [t for t in tickers_operados if t['retorno'] < -2.0]
    
    # Determinar estado del sistema
    expectancy = metricas['expectancy_R']
    if expectancy >= 0.40:
        estado = "✅ EXCELENTE"
        color_estado = "🟢"
    elif expectancy >= 0.20:
        estado = "✅ RENTABLE"
        color_estado = "🟢"
    elif expectancy > 0:
        estado = "⚠️  MARGINAL"
        color_estado = "🟡"
    else:
        estado = "❌ NO RENTABLE"
        color_estado = "🔴"
    
    # Generar dashboard
    print("\n" + "="*70)
    print("📊 RESUMEN EJECUTIVO - SISTEMA IBEX")
    print("="*70)
    
    # Estado general
    print(f"\n{color_estado} Estado del Sistema: {estado}")
    print(f"💰 Expectancy: {expectancy:+.2f}R")
    print(f"📉 Drawdown Máximo: {metricas['max_drawdown_pct']:.1f}% (tolerancia: 15%)")
    
    # Estadísticas de trading
    print(f"\n📊 Estadísticas:")
    print(f"  • Total trades: {metricas['trades']}")
    print(f"  • Win Rate: {metricas['winrate']:.1f}%")
    print(f"  • Tickers activos: {len(tickers_operados)}/{len(tickers_operados) + len(tickers_excluidos)}")
    
    # Tickers aprobados
    if aprobados:
        print(f"\n✅ TICKERS APROBADOS ({len(aprobados)}) - Operar prioritariamente:")
        aprobados_sorted = sorted(aprobados, key=lambda x: x['retorno'], reverse=True)
        tickers_str = ", ".join([f"{t['ticker'][:-3]}" for t in aprobados_sorted[:10]])
        print(f"  {tickers_str}")
        if len(aprobados) > 10:
            print(f"  ... y {len(aprobados) - 10} más")
    else:
        print(f"\n⚠️  TICKERS APROBADOS (0) - Sin tickers con retorno >2%")
    
    # Tickers neutros
    if neutros:
        print(f"\n⚪ TICKERS NEUTROS ({len(neutros)}) - Operar con cautela:")
        neutros_sorted = sorted(neutros, key=lambda x: x['retorno'], reverse=True)
        tickers_str = ", ".join([f"{t['ticker'][:-3]}" for t in neutros_sorted[:10]])
        print(f"  {tickers_str}")
    
    # Tickers rechazados
    if rechazados:
        print(f"\n❌ TICKERS RECHAZADOS ({len(rechazados)}) - NO operar:")
        rechazados_sorted = sorted(rechazados, key=lambda x: x['retorno'])
        tickers_str = ", ".join([f"{t['ticker'][:-3]}" for t in rechazados_sorted[:10]])
        print(f"  {tickers_str}")
    
    # Tickers excluidos por filtros
    if tickers_excluidos:
        excluidos_vol = [t for t in tickers_excluidos if not t.get('sin_señales')]
        if excluidos_vol:
            print(f"\n🚫 EXCLUIDOS POR VOLATILIDAD ({len(excluidos_vol)}) - Incompatibles:")
            tickers_str = ", ".join([f"{t['ticker'][:-3]}" for t in excluidos_vol[:10]])
            print(f"  {tickers_str}")
    
    # Configuración del sistema
    print(f"\n⚙️  Configuración:")
    print(f"  • Target: +{int(config['target'])}R | Break-even: +{int(config['breakeven'])}R")
    print(f"  • Riesgo por trade: {config['riesgo_pct']*100:.1f}%")
    print(f"  • Filtro volatilidad: >{config['min_volatilidad']:.0f}%")
    
    # Recomendaciones
    print(f"\n💡 ACCIÓN RECOMENDADA:")
    if expectancy >= 0.20:
        if len(aprobados) >= 5:
            print(f"  ✅ Sistema listo para operar")
            print(f"  ➡️  Operar SOLO los {len(aprobados)} tickers aprobados")
            print(f"  ➡️  Mantener configuración actual")
        else:
            print(f"  ⚠️  Pocos tickers aprobados ({len(aprobados)})")
            print(f"  ➡️  Considerar reducir filtro volatilidad a {config['min_volatilidad']-2:.0f}%")
            print(f"  ➡️  O incluir tickers neutros en watchlist")
    else:
        print(f"  ❌ Sistema requiere optimización")
        print(f"  ➡️  Revisar parámetros de entrada (evaluar_valor)")
        print(f"  ➡️  Considerar aumentar target a +4R")
        print(f"  ➡️  NO operar hasta mejorar expectancy >0.20R")
    
    print("\n" + "="*70)
    
    # Retornar resumen para guardado
    return {
        'timestamp': datetime.now().isoformat(),
        'estado': estado,
        'expectancy': expectancy,
        'winrate': metricas['winrate'],
        'max_dd': metricas['max_drawdown_pct'],
        'total_trades': metricas['trades'],
        'tickers_aprobados': [t['ticker'] for t in aprobados],
        'tickers_neutros': [t['ticker'] for t in neutros],
        'tickers_rechazados': [t['ticker'] for t in rechazados],
        'tickers_excluidos': [t['ticker'] for t in tickers_excluidos],
        'config': config
    }


def guardar_historico(resumen, directorio='backtest_historico'):
    """
    Guarda resumen en archivo JSON para tracking histórico
    """
    # Crear directorio si no existe
    Path(directorio).mkdir(exist_ok=True)
    
    # Nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{directorio}/backtest_{timestamp}.json"
    
    # Guardar
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    return filename


def comparar_con_anterior(resumen_actual, directorio='backtest_historico'):
    """
    Compara con el último backtest guardado
    """
    historico_path = Path(directorio)
    
    if not historico_path.exists():
        return None
    
    # Buscar último archivo
    archivos = sorted(historico_path.glob('backtest_*.json'))
    
    if len(archivos) < 2:
        return None
    
    # Cargar penúltimo (el último es el actual que acabamos de guardar)
    with open(archivos[-2], 'r', encoding='utf-8') as f:
        resumen_anterior = json.load(f)
    
    # Comparar
    print("\n" + "="*70)
    print("📈 COMPARACIÓN CON BACKTEST ANTERIOR")
    print("="*70)
    
    print(f"\nFecha anterior: {resumen_anterior['timestamp'][:10]}")
    print(f"Fecha actual: {resumen_actual['timestamp'][:10]}")
    
    # Cambios en expectancy
    exp_anterior = resumen_anterior['expectancy']
    exp_actual = resumen_actual['expectancy']
    cambio_exp = exp_actual - exp_anterior
    
    icono_exp = "📈" if cambio_exp > 0 else "📉" if cambio_exp < 0 else "➡️"
    print(f"\nExpectancy: {exp_anterior:+.2f}R → {exp_actual:+.2f}R {icono_exp} ({cambio_exp:+.2f}R)")
    
    # Cambios en win rate
    wr_anterior = resumen_anterior['winrate']
    wr_actual = resumen_actual['winrate']
    cambio_wr = wr_actual - wr_anterior
    
    icono_wr = "📈" if cambio_wr > 0 else "📉" if cambio_wr < 0 else "➡️"
    print(f"Win Rate: {wr_anterior:.1f}% → {wr_actual:.1f}% {icono_wr} ({cambio_wr:+.1f}%)")
    
    # Cambios en tickers
    tickers_ant = set(resumen_anterior['tickers_aprobados'])
    tickers_act = set(resumen_actual['tickers_aprobados'])
    
    nuevos = tickers_act - tickers_ant
    perdidos = tickers_ant - tickers_act
    
    if nuevos:
        print(f"\n✅ Nuevos tickers aprobados: {', '.join([t[:-3] for t in nuevos])}")
    if perdidos:
        print(f"❌ Tickers que ya no aprueban: {', '.join([t[:-3] for t in perdidos])}")
    
    if not nuevos and not perdidos:
        print(f"\n➡️  Sin cambios en tickers aprobados")
    
    print("="*70)


def resumen_rapido(metricas, tickers_operados):
    """
    Versión ultra-compacta (3 líneas) para checks rápidos
    """
    aprobados = [t['ticker'][:-3] for t in tickers_operados if t['retorno'] >= 2.0]
    
    estado = "✅" if metricas['expectancy_R'] >= 0.20 else "⚠️" if metricas['expectancy_R'] > 0 else "❌"
    
    print(f"\n{estado} E:{metricas['expectancy_R']:+.2f}R | WR:{metricas['winrate']:.0f}% | DD:{metricas['max_drawdown_pct']:.1f}% | Tickers:{len(aprobados)}")
    print(f"✅ {', '.join(aprobados[:8])}{' ...' if len(aprobados) > 8 else ''}")
