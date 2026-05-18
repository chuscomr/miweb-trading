"""
Módulo de métricas y análisis de trades.
KPIs clave + cruces potentes para detectar edge real.
"""

import sqlite3
from collections import defaultdict
from pathlib import Path


DB_PATH = Path(__file__).parent / "trades.db"


def get_connection():
    """Crea conexión a BD."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# KPIs BÁSICOS
# ============================================================================

def calcular_kpis(
    sistema: str | None = None,
    ejecutado: bool = True
) -> dict:
    """
    Calcula KPIs básicos del sistema.
    
    Returns:
        {
            'total_trades': int,
            'ganadores': int,
            'perdedores': int,
            'winrate': float,
            'expectancy': float,
            'profit_factor': float,
            'r_promedio_ganador': float,
            'r_promedio_perdedor': float,
            'r_mejor': float,
            'r_peor': float,
            'max_drawdown': float,
            'r_total': float,
            'curva_equity': list  # [(fecha, r_acum), ...]
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            r_real,
            max_drawdown,
            timestamp
        FROM trades 
        WHERE ejecutado = ? AND r_real IS NOT NULL
    """
    params = [ejecutado]

    if sistema:
        query += " AND sistema = ?"
        params.append(sistema)

    query += " ORDER BY timestamp ASC"

    cursor.execute(query, params)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return {
            'total_trades': 0,
            'ganadores': 0,
            'perdedores': 0,
            'winrate': 0.0,
            'expectancy': 0.0,
            'profit_factor': 0.0,
            'r_promedio_ganador': 0.0,
            'r_promedio_perdedor': 0.0,
            'r_mejor': 0.0,
            'r_peor': 0.0,
            'max_drawdown': 0.0,
            'r_total': 0.0,
            'curva_equity': []
        }

    # Separar ganadores y perdedores
    ganadores = [t['r_real'] for t in trades if t['r_real'] > 0]
    perdedores = [abs(t['r_real']) for t in trades if t['r_real'] < 0]

    total = len(trades)
    n_ganadores = len(ganadores)
    n_perdedores = len(perdedores)

    # Winrate
    winrate = (n_ganadores / total * 100) if total > 0 else 0

    # R promedio
    r_avg_ganador = (sum(ganadores) / n_ganadores) if n_ganadores > 0 else 0
    r_avg_perdedor = (sum(perdedores) / n_perdedores) if n_perdedores > 0 else 0

    # Mejor y peor
    r_mejor = max(ganadores) if ganadores else 0
    r_peor = -max(perdedores) if perdedores else 0

    # Expectancy
    sum_r = sum([t['r_real'] for t in trades])
    expectancy = sum_r / total if total > 0 else 0

    # Profit Factor
    total_ganado = sum(ganadores)
    total_perdido = sum(perdedores)
    profit_factor = (total_ganado / total_perdido) if total_perdido > 0 else 0

    # Max Drawdown
    drawdowns = [t['max_drawdown'] for t in trades if t['max_drawdown'] is not None]
    max_dd = max(drawdowns) if drawdowns else 0

    # Curva Equity
    curva = []
    r_acum = 0
    for t in trades:
        r_acum += t['r_real']
        curva.append({
            'fecha': t['timestamp'][:10] if t['timestamp'] else '',
            'r_acum': round(r_acum, 2)
        })

    return {
        'total_trades': total,
        'ganadores': n_ganadores,
        'perdedores': n_perdedores,
        'winrate': round(winrate, 2),
        'expectancy': round(expectancy, 2),
        'profit_factor': round(profit_factor, 2),
        'r_promedio_ganador': round(r_avg_ganador, 2),
        'r_promedio_perdedor': round(r_avg_perdedor, 2),
        'r_mejor': round(r_mejor, 2),
        'r_peor': round(r_peor, 2),
        'max_drawdown': round(max_dd, 2),
        'r_total': round(sum_r, 2),
        'curva_equity': curva
    }


# ============================================================================
# CRUCES POTENTES
# ============================================================================

def winrate_por_score(
    min_score: float | None = None,
    max_score: float | None = None,
    bins: int = 5
) -> list[dict]:
    """
    Winrate segmentado por rangos de score técnico.
    
    Returns:
        [{'rango': '0-20', 'trades': 10, 'winrate': 45.5, ...}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT score_tecnico, r_real
        FROM trades
        WHERE ejecutado = 1 
        AND score_tecnico IS NOT NULL 
        AND r_real IS NOT NULL
    """

    cursor.execute(query)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return []

    # Determinar rangos
    scores = [t['score_tecnico'] for t in trades]
    min_s = min_score if min_score else min(scores)
    max_s = max_score if max_score else max(scores)
    step = (max_s - min_s) / bins

    # Agrupar por rangos
    rangos = defaultdict(list)
    for t in trades:
        score = t['score_tecnico']
        bin_idx = min(int((score - min_s) / step), bins - 1)
        rango_min = min_s + bin_idx * step
        rango_max = rango_min + step
        key = f"{rango_min:.0f}-{rango_max:.0f}"
        rangos[key].append(t['r_real'])

    # Calcular winrate por rango
    resultado = []
    for rango, rs in sorted(rangos.items()):
        ganadores = len([r for r in rs if r > 0])
        total = len(rs)
        wr = (ganadores / total * 100) if total > 0 else 0

        resultado.append({
            'rango': rango,
            'trades': total,
            'winrate': round(wr, 2),
            'r_promedio': round(sum(rs) / total, 2) if total > 0 else 0
        })

    return resultado


def resultados_por_fundamental(semaforo: bool = True) -> list[dict]:
    """
    Resultados segmentados por rating fundamental o semáforo.
    
    Args:
        semaforo: Si True agrupa por semáforo, si False por rating
    
    Returns:
        [{'categoria': 'VERDE', 'trades': 15, 'expectancy': 1.2, ...}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    campo = 'semaforo' if semaforo else 'rating_fundamental'

    query = f"""
        SELECT {campo}, r_real
        FROM trades
        WHERE ejecutado = 1 
        AND {campo} IS NOT NULL 
        AND r_real IS NOT NULL
    """

    cursor.execute(query)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return []

    # Agrupar
    grupos = defaultdict(list)
    for t in trades:
        key = t[campo]
        grupos[key].append(t['r_real'])

    # Calcular métricas por grupo
    resultado = []
    for categoria, rs in sorted(grupos.items()):
        ganadores = len([r for r in rs if r > 0])
        total = len(rs)
        wr = (ganadores / total * 100) if total > 0 else 0
        exp = sum(rs) / total if total > 0 else 0

        resultado.append({
            'categoria': str(categoria),
            'trades': total,
            'winrate': round(wr, 2),
            'expectancy': round(exp, 2),
            'r_total': round(sum(rs), 2)
        })

    return resultado


def resultados_por_contexto() -> list[dict]:
    """
    Resultados segmentados por contexto de mercado.
    
    Returns:
        [{'contexto': 'ALCISTA', 'trades': 25, ...}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT contexto_mercado, r_real, fuerza_mercado
        FROM trades
        WHERE ejecutado = 1 
        AND contexto_mercado IS NOT NULL 
        AND r_real IS NOT NULL
    """

    cursor.execute(query)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return []

    # Agrupar por contexto
    grupos = defaultdict(list)
    fuerzas = defaultdict(list)

    for t in trades:
        ctx = t['contexto_mercado']
        grupos[ctx].append(t['r_real'])
        if t['fuerza_mercado']:
            fuerzas[ctx].append(t['fuerza_mercado'])

    # Calcular métricas
    resultado = []
    for contexto, rs in sorted(grupos.items()):
        ganadores = len([r for r in rs if r > 0])
        total = len(rs)
        wr = (ganadores / total * 100) if total > 0 else 0
        exp = sum(rs) / total if total > 0 else 0
        fuerza_avg = sum(fuerzas[contexto]) / len(fuerzas[contexto]) if fuerzas[contexto] else None

        resultado.append({
            'contexto': contexto,
            'trades': total,
            'winrate': round(wr, 2),
            'expectancy': round(exp, 2),
            'fuerza_promedio': round(fuerza_avg, 2) if fuerza_avg else None
        })

    return resultado


def resultados_por_setup(sistema: str | None = None) -> list[dict]:
    """
    Resultados segmentados por tipo de setup.
    
    Returns:
        [{'setup': 'breakout', 'trades': 30, ...}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT tipo_setup, r_real, sistema
        FROM trades
        WHERE ejecutado = 1 
        AND tipo_setup IS NOT NULL 
        AND r_real IS NOT NULL
    """
    params = []

    if sistema:
        query += " AND sistema = ?"
        params.append(sistema)

    cursor.execute(query, params)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return []

    # Agrupar
    grupos = defaultdict(list)
    for t in trades:
        key = f"{t['sistema']}_{t['tipo_setup']}" if not sistema else t['tipo_setup']
        grupos[key].append(t['r_real'])

    # Calcular métricas
    resultado = []
    for setup, rs in sorted(grupos.items()):
        ganadores = len([r for r in rs if r > 0])
        total = len(rs)
        wr = (ganadores / total * 100) if total > 0 else 0
        exp = sum(rs) / total if total > 0 else 0

        resultado.append({
            'setup': setup,
            'trades': total,
            'winrate': round(wr, 2),
            'expectancy': round(exp, 2),
            'r_total': round(sum(rs), 2)
        })

    return resultado


# ============================================================================
# ANÁLISIS AVANZADO
# ============================================================================

def mejor_peor_setup() -> tuple[dict | None, dict | None]:
    """
    Identifica el mejor y peor setup por expectancy.
    
    Returns:
        (mejor_setup, peor_setup)
    """
    setups = resultados_por_setup()
    if not setups:
        return None, None

    mejor = max(setups, key=lambda x: x['expectancy'])
    peor = min(setups, key=lambda x: x['expectancy'])

    return mejor, peor


def trades_no_ejecutados() -> list[dict]:
    """
    Retorna trades señalados pero no ejecutados con motivo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ticker, sistema, tipo_setup, score_tecnico, 
               semaforo, motivo_no_ejecucion, timestamp
        FROM trades
        WHERE ejecutado = 0
        ORDER BY timestamp DESC
    """)

    trades = cursor.fetchall()
    conn.close()

    return [dict(t) for t in trades]


def analisis_mae_mfe() -> dict:
    """
    Análisis de MAE (Maximum Adverse Excursion) y MFE (Maximum Favorable Excursion).
    
    Returns:
        {
            'mae_promedio': float,
            'mfe_promedio': float,
            'ratio_mfe_mae': float
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT mae, mfe
        FROM trades
        WHERE ejecutado = 1 
        AND mae IS NOT NULL 
        AND mfe IS NOT NULL
    """)

    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return {'mae_promedio': 0, 'mfe_promedio': 0, 'ratio_mfe_mae': 0}

    mae_avg = sum([abs(t['mae']) for t in trades]) / len(trades)
    mfe_avg = sum([t['mfe'] for t in trades]) / len(trades)
    ratio = mfe_avg / mae_avg if mae_avg > 0 else 0

    return {
        'mae_promedio': round(mae_avg, 2),
        'mfe_promedio': round(mfe_avg, 2),
        'ratio_mfe_mae': round(ratio, 2)
    }


def cruce_setup_contexto(sistema: str | None = None, min_trades: int = 5) -> list[dict]:
    """
    CRUCE POTENTE: Setup × Contexto.
    Donde está el edge REAL.
    
    Args:
        min_trades: Mínimo de trades para mostrar (filtro calidad)
    
    Returns:
        [{'setup': str, 'contexto': str, 'trades': int, 'winrate': float, 'expectancy': float}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT tipo_setup, contexto_mercado, r_real
        FROM trades
        WHERE ejecutado = 1 
        AND tipo_setup IS NOT NULL 
        AND contexto_mercado IS NOT NULL
        AND r_real IS NOT NULL
    """
    params = []

    if sistema:
        query += " AND sistema = ?"
        params.append(sistema)

    cursor.execute(query, params)
    trades = cursor.fetchall()
    conn.close()

    if not trades:
        return []

    # Agrupar por setup + contexto
    grupos = defaultdict(list)
    for t in trades:
        key = f"{t['tipo_setup']}_{t['contexto_mercado']}"
        grupos[key].append(t['r_real'])

    # Calcular métricas por grupo
    resultado = []
    for key, rs in grupos.items():
        total = len(rs)

        # FILTRO DE CALIDAD
        if total < min_trades:
            continue

        setup, ctx = key.split('_', 1)
        ganadores = len([r for r in rs if r > 0])
        wr = (ganadores / total * 100) if total > 0 else 0
        exp = sum(rs) / total if total > 0 else 0

        resultado.append({
            'setup': setup,
            'contexto': ctx,
            'trades': total,
            'winrate': round(wr, 2),
            'expectancy': round(exp, 2),
            'r_total': round(sum(rs), 2)
        })

    # Ordenar por expectancy descendente
    resultado.sort(key=lambda x: x['expectancy'], reverse=True)

    return resultado
