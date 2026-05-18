"""
Módulo para registro y gestión del historial de trades.
Tracking real de resultados por sistema/setup/filtros.
"""

import sqlite3
from pathlib import Path


# Ruta base de datos - SIEMPRE en raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "analytics" / "trades.db"

# Crear directorio si no existe
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# DB Path configurado
import logging


logger = logging.getLogger(__name__)


def init_db():
    """Inicializa la base de datos con el schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            ticker TEXT NOT NULL,
            sistema TEXT NOT NULL,
            tipo_setup TEXT,
            
            score_tecnico REAL,
            rating_fundamental REAL,
            semaforo TEXT,
            
            contexto_mercado TEXT,
            fuerza_mercado REAL,
            
            precio_entrada REAL,
            precio_salida REAL,
            stop REAL,
            
            r_inicial REAL,
            r_real REAL,
            
            mae REAL,
            mfe REAL,
            
            duracion_dias INTEGER,
            max_drawdown REAL,
            
            tipo_salida TEXT,
            
            ejecutado BOOLEAN DEFAULT 0,
            motivo_no_ejecucion TEXT,
            
            tags TEXT,
            notas TEXT
        )
    """)

    conn.commit()
    conn.close()


def registrar_trade(
    ticker: str,
    sistema: str,
    tipo_setup: str | None = None,
    score_tecnico: float | None = None,
    rating_fundamental: float | None = None,
    semaforo: str | None = None,
    contexto_mercado: str | None = None,
    fuerza_mercado: float | None = None,
    precio_entrada: float | None = None,
    precio_salida: float | None = None,
    stop: float | None = None,
    r_inicial: float | None = None,
    r_real: float | None = None,
    mae: float | None = None,
    mfe: float | None = None,
    duracion_dias: int | None = None,
    max_drawdown: float | None = None,
    tipo_salida: str | None = None,
    ejecutado: bool = False,
    motivo_no_ejecucion: str | None = None,
    tags: str | None = None,
    notas: str | None = None
) -> int:
    """
    Registra un nuevo trade en la base de datos.
    
    Returns:
        int: ID del trade registrado
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trades (
            ticker, sistema, tipo_setup,
            score_tecnico, rating_fundamental, semaforo,
            contexto_mercado, fuerza_mercado,
            precio_entrada, precio_salida, stop,
            r_inicial, r_real,
            mae, mfe,
            duracion_dias, max_drawdown,
            tipo_salida,
            ejecutado, motivo_no_ejecucion,
            tags, notas
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker, sistema, tipo_setup,
        score_tecnico, rating_fundamental, semaforo,
        contexto_mercado, fuerza_mercado,
        precio_entrada, precio_salida, stop,
        r_inicial, r_real,
        mae, mfe,
        duracion_dias, max_drawdown,
        tipo_salida,
        ejecutado, motivo_no_ejecucion,
        tags, notas
    ))

    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return trade_id


def actualizar_trade(trade_id: int, **kwargs):
    """
    Actualiza campos de un trade existente.
    
    Args:
        trade_id: ID del trade
        **kwargs: Campos a actualizar
    """
    if not kwargs:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    set_clause = ", ".join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [trade_id]

    cursor.execute(f"""
        UPDATE trades 
        SET {set_clause}
        WHERE id = ?
    """, values)

    conn.commit()
    conn.close()


def obtener_trade(trade_id: int) -> dict | None:
    """Obtiene un trade por ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def listar_trades(
    sistema: str | None = None,
    ejecutado: bool | None = None,
    limit: int = 100
) -> list[dict]:
    """
    Lista trades con filtros opcionales.
    
    Args:
        sistema: Filtrar por sistema
        ejecutado: Filtrar por estado ejecución
        limit: Máximo número de resultados
    
    Returns:
        Lista de trades
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM trades WHERE 1=1"
    params = []

    if sistema:
        query += " AND sistema = ?"
        params.append(sistema)

    if ejecutado is not None:
        query += " AND ejecutado = ?"
        params.append(ejecutado)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def eliminar_trade(trade_id: int):
    """Elimina un trade por ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()


# Inicializar DB al importar
init_db()
