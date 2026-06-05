"""
Integración automática Analytics con gestión de cartera.
Registra trades automáticamente al abrir/cerrar posiciones.
"""

import logging
from datetime import datetime

from analytics.trades_log import actualizar_trade, registrar_trade


logger = logging.getLogger(__name__)


def registrar_apertura(
    ticker: str,
    sistema: str,
    tipo_setup: str,
    precio_entrada: float,
    stop: float,
    objetivo: float | None = None,
    score_tecnico: float | None = None,
    rating_fundamental: float | None = None,
    semaforo: str | None = None,
    contexto_mercado: str | None = None,
    fuerza_mercado: float | None = None,
    ejecutado: bool = True,
    motivo_no_ejecucion: str | None = None,
    tags: str | None = None,
    notas: str | None = None
) -> int:
    """
    Registra apertura de posición en analytics.
    
    Returns:
        trade_id para posterior actualización
    """
    # Calcular R inicial
    r_inicial = None
    if stop and precio_entrada > stop:
        distancia_stop = precio_entrada - stop
        distancia_objetivo = (objetivo - precio_entrada) if objetivo else distancia_stop * 2
        r_inicial = round(distancia_objetivo / distancia_stop, 2)

    try:
        trade_id = registrar_trade(
            ticker=ticker,
            sistema=sistema,
            tipo_setup=tipo_setup,
            score_tecnico=score_tecnico,
            rating_fundamental=rating_fundamental,
            semaforo=semaforo,
            contexto_mercado=contexto_mercado,
            fuerza_mercado=fuerza_mercado,
            precio_entrada=precio_entrada,
            stop=stop,
            r_inicial=r_inicial,
            ejecutado=ejecutado,
            motivo_no_ejecucion=motivo_no_ejecucion,
            tags=tags,
            notas=notas
        )
        logger.info(f"📊 Analytics: Trade {ticker} registrado (id={trade_id})")
        return trade_id
    except Exception as e:
        logger.error(f"❌ Error registrando trade {ticker}: {e}")
        return -1


def registrar_cierre(
    trade_id: int,
    precio_salida: float,
    precio_entrada: float,
    stop: float,
    tipo_salida: str = "manual",
    mae: float | None = None,
    mfe: float | None = None,
    duracion_dias: int | None = None
):
    """
    Actualiza trade con datos de cierre.
    
    Args:
        trade_id: ID del trade en analytics
        precio_salida: Precio de cierre
        precio_entrada: Precio de entrada (para calcular R)
        stop: Stop inicial
        tipo_salida: 'objetivo', 'stop', 'trailing', 'manual', 'tiempo'
        mae: Maximum Adverse Excursion (negativo)
        mfe: Maximum Favorable Excursion (positivo)
    """
    if trade_id <= 0:
        return

    # Calcular R real
    r_unit = precio_entrada - stop if precio_entrada > stop else 1
    r_real = round((precio_salida - precio_entrada) / r_unit, 2) if r_unit > 0 else 0

    # Calcular max drawdown (en R)
    max_drawdown = None
    if mae is not None and r_unit > 0:
        max_drawdown = round(mae / r_unit, 2)

    try:
        actualizar_trade(
            trade_id,
            precio_salida=precio_salida,
            r_real=r_real,
            tipo_salida=tipo_salida,
            mae=mae,
            mfe=mfe,
            duracion_dias=duracion_dias,
            max_drawdown=max_drawdown
        )
        logger.info(f"📊 Analytics: Trade {trade_id} cerrado (R={r_real})")
    except Exception as e:
        logger.error(f"❌ Error cerrando trade {trade_id}: {e}")


def registrar_señal_no_ejecutada(
    ticker: str,
    sistema: str,
    tipo_setup: str,
    score_tecnico: float,
    motivo: str,
    semaforo: str | None = None,
    contexto_mercado: str | None = None
) -> int:
    """
    Registra señal detectada pero no ejecutada.
    Útil para análisis de qué filtros funcionan.
    """
    try:
        trade_id = registrar_trade(
            ticker=ticker,
            sistema=sistema,
            tipo_setup=tipo_setup,
            score_tecnico=score_tecnico,
            semaforo=semaforo,
            contexto_mercado=contexto_mercado,
            ejecutado=False,
            motivo_no_ejecucion=motivo,
            tags="no_ejecutado"
        )
        logger.info(f"📊 Analytics: Señal {ticker} NO ejecutada - {motivo}")
        return trade_id
    except Exception as e:
        logger.error(f"❌ Error registrando señal no ejecutada {ticker}: {e}")
        return -1


def importar_posiciones_existentes(db_cartera):
    """
    Importa posiciones históricas de cartera_db a analytics.
    Ejecutar UNA VEZ para migrar datos existentes.
    """
    from cartera_db import CarteraDB

    cartera_db = CarteraDB()

    # Importar cerradas
    cerradas = cartera_db.listar_posiciones_cerradas(limite=1000)
    logger.info(f"📦 Importando {len(cerradas)} posiciones cerradas...")

    for pos in cerradas:
        try:
            # Registrar apertura
            trade_id = registrar_apertura(
                ticker=pos['ticker'],
                sistema=pos.get('sistema', 'posicional'),  # asumir posicional si no especificado
                tipo_setup=pos.get('tipo_setup', 'manual'),
                precio_entrada=pos['precio_entrada'],
                stop=pos.get('stop_inicial', pos.get('stop_actual')),
                objetivo=pos.get('objetivo'),
                ejecutado=True,
                notas=pos.get('notas')
            )

            # Registrar cierre
            if trade_id > 0 and pos.get('precio_cierre'):
                duracion = None
                if pos.get('fecha_entrada') and pos.get('fecha_cierre'):
                    try:
                        fe = datetime.strptime(pos['fecha_entrada'][:10], '%Y-%m-%d')
                        fc = datetime.strptime(pos['fecha_cierre'][:10], '%Y-%m-%d')
                        duracion = (fc - fe).days
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"Error calculando duración trade {trade_id}: {e}")

                registrar_cierre(
                    trade_id=trade_id,
                    precio_salida=pos['precio_cierre'],
                    precio_entrada=pos['precio_entrada'],
                    stop=pos.get('stop_inicial', pos.get('stop_actual')),
                    tipo_salida=pos.get('motivo_cierre', 'manual'),
                    duracion_dias=duracion
                )
        except Exception as e:
            logger.error(f"Error importando {pos['ticker']}: {e}")

    logger.info("✅ Importación completada")
