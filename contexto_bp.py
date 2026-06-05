# ==========================================================
# BLUEPRINT - CONTEXTO DE MERCADO
# Página de entrada a los módulos de análisis
# ==========================================================

from flask import Blueprint, jsonify, render_template, request

from analytics.metrics import (
    analisis_mae_mfe,
    calcular_kpis,
    mejor_peor_setup,
    resultados_por_contexto,
    resultados_por_fundamental,
    resultados_por_setup,
    trades_no_ejecutados,
    winrate_por_score,
)
from analytics.trades_log import actualizar_trade, eliminar_trade, listar_trades, obtener_trade, registrar_trade


contexto_bp = Blueprint('contexto', __name__, url_prefix='/contexto')

@contexto_bp.route('/')
def index():
    """Página principal de Contexto de Mercado con acceso a los 3 módulos"""
    return render_template('contexto_index.html')


# ============================================================
# ANALYTICS - TRACKING DE RESULTADOS
# ============================================================

@contexto_bp.route('/analytics/kpis')
def analytics_kpis():
    """KPIs generales del sistema."""
    sistema = request.args.get('sistema')
    kpis = calcular_kpis(sistema=sistema)
    return jsonify(kpis)


@contexto_bp.route('/analytics/winrate-score')
def analytics_winrate_score():
    """Winrate segmentado por score técnico."""
    datos = winrate_por_score()
    return jsonify(datos)


@contexto_bp.route('/analytics/resultados-fundamental')
def analytics_fundamental():
    """Resultados por rating fundamental."""
    semaforo = request.args.get('semaforo', 'true').lower() == 'true'
    datos = resultados_por_fundamental(semaforo=semaforo)
    return jsonify(datos)


@contexto_bp.route('/analytics/resultados-contexto')
def analytics_contexto():
    """Resultados por contexto de mercado."""
    datos = resultados_por_contexto()
    return jsonify(datos)


@contexto_bp.route('/analytics/resultados-setup')
def analytics_setup():
    """Resultados por tipo de setup."""
    sistema = request.args.get('sistema')
    datos = resultados_por_setup(sistema=sistema)
    return jsonify(datos)


@contexto_bp.route('/analytics/mejor-peor')
def analytics_mejor_peor():
    """Mejor y peor setup por expectancy."""
    mejor, peor = mejor_peor_setup()
    return jsonify({'mejor': mejor, 'peor': peor})


@contexto_bp.route('/analytics/no-ejecutados')
def analytics_no_ejecutados():
    """Trades señalados pero no ejecutados."""
    datos = trades_no_ejecutados()
    return jsonify(datos)


@contexto_bp.route('/analytics/mae-mfe')
def analytics_mae_mfe():
    """Análisis MAE/MFE."""
    datos = analisis_mae_mfe()
    return jsonify(datos)


@contexto_bp.route('/analytics/trades', methods=['GET'])
def analytics_listar_trades():
    """Lista trades con filtros."""
    sistema = request.args.get('sistema')
    ejecutado = request.args.get('ejecutado')
    limit = int(request.args.get('limit', 100))

    if ejecutado is not None:
        ejecutado = ejecutado.lower() == 'true'

    trades = listar_trades(sistema=sistema, ejecutado=ejecutado, limit=limit)
    return jsonify(trades)


@contexto_bp.route('/analytics/trades/<int:trade_id>', methods=['GET'])
def analytics_obtener_trade(trade_id):
    """Obtiene un trade específico."""
    trade = obtener_trade(trade_id)
    if trade:
        return jsonify(trade)
    return jsonify({'error': 'Trade no encontrado'}), 404


@contexto_bp.route('/analytics/trades', methods=['POST'])
def analytics_registrar_trade():
    """Registra un nuevo trade."""
    data = request.json
    trade_id = registrar_trade(**data)
    return jsonify({'id': trade_id, 'mensaje': 'Trade registrado'}), 201


@contexto_bp.route('/analytics/trades/<int:trade_id>', methods=['PUT'])
def analytics_actualizar_trade(trade_id):
    """Actualiza un trade existente."""
    data = request.json
    actualizar_trade(trade_id, **data)
    return jsonify({'mensaje': 'Trade actualizado'})


@contexto_bp.route('/analytics/trades/<int:trade_id>', methods=['DELETE'])
def analytics_eliminar_trade(trade_id):
    """Elimina un trade."""
    eliminar_trade(trade_id)
    return jsonify({'mensaje': 'Trade eliminado'})


# ============================================================
# CALENDARIO DE DIVIDENDOS (v86.1)
# ============================================================

@contexto_bp.route('/dividendos', methods=['GET'])
def obtener_dividendos():
    """
    Obtiene dividendos próximos de todos los tickers (IBEX35 + Continuo).
    
    Returns:
        JSON con lista de dividendos ordenada por fecha
    """
    from core.universos import IBEX35, CONTINUO
    from core.calendario_eventos import get_calendario
    from datetime import datetime
    
    try:
        calendario = get_calendario()
        todos_tickers = list(set(IBEX35 + CONTINUO))  # Eliminar duplicados
        
        dividendos = []
        
        for ticker in todos_tickers:
            eventos = calendario.eventos_proximos(ticker, dias_adelante=30)
            
            if eventos['dividendo'] and eventos['dividendo']['tiene_dividendo']:
                div = eventos['dividendo']
                
                # Obtener nombre de empresa (simplificar ticker)
                nombre = ticker.replace('.MC', '')
                
                dividendos.append({
                    'ticker': ticker,
                    'nombre': nombre,
                    'fecha_ex': div['fecha_ex'].strftime('%d/%m/%Y') if div['fecha_ex'] else None,
                    'dias_hasta': div['dias_hasta'],
                    'importe': div['importe'],
                    'yield_aprox': div['yield_aprox'],
                    'advertir': div['advertir_entrada']
                })
        
        # Ordenar por días hasta dividendo (más cercanos primero)
        dividendos.sort(key=lambda x: x['dias_hasta'] if x['dias_hasta'] is not None else 999)
        
        return jsonify({
            'dividendos': dividendos,
            'total': len(dividendos)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


print("✅ Blueprint contexto_bp cargado")
