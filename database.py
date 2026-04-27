import sqlite3
import time

DB_NAME = "trading.db"

def crear_base_datos():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_entrada REAL,
            fecha_salida REAL,
            ticker TEXT NOT NULL,
            entrada REAL,
            salida REAL,
            acciones INTEGER,
            riesgo_inicial REAL,
            beneficio REAL,
            R_alcanzado REAL,
            setup_score INTEGER,
            gestion TEXT,
            tipo_entrada TEXT,
            estrategia TEXT,
            notas TEXT,
            creado_en REAL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS equity_curve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha REAL,
            capital REAL,
            drawdown REAL,
            num_trades INTEGER,
            creado_en REAL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS analisis_guardados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            fecha_analisis REAL,
            señal TEXT,
            entrada REAL,
            stop REAL,
            objetivo REAL,
            setup_score INTEGER,
            motivos TEXT,
            grafico_path TEXT,
            ejecutado INTEGER DEFAULT 0,
            creado_en REAL
        )
        """)

        conn.commit()


def guardar_trade(trade):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO trades (
            fecha_entrada, fecha_salida, ticker, entrada, salida,
            acciones, riesgo_inicial, beneficio, R_alcanzado,
            setup_score, gestion, tipo_entrada, estrategia, notas, creado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade["fecha_entrada"],
            trade.get("fecha_salida"),
            trade["ticker"],
            trade["entrada"],
            trade.get("salida"),
            trade["acciones"],
            trade["riesgo_inicial"],
            trade.get("beneficio"),
            trade.get("R_alcanzado"),
            trade["setup_score"],
            trade["gestion"],
            trade["tipo_entrada"],
            trade["estrategia"],
            trade.get("notas"),
            time.time()
        ))
        conn.commit()


def obtener_estadisticas_globales():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        row = c.execute("""
        SELECT 
            COUNT(*),
            SUM(CASE WHEN beneficio > 0 THEN 1 ELSE 0 END),
            SUM(beneficio),
            AVG(R_alcanzado),
            MAX(beneficio),
            MIN(beneficio)
        FROM trades
        """).fetchone()

    total = row[0] or 0
    wins = row[1] or 0

    return {
        "total_trades": total,
        "ganadores": wins,
        "win_rate": round((wins / total * 100), 2) if total else 0,
        "beneficio_total": row[2] or 0,
        "R_promedio": round(row[3] or 0, 2),
        "mejor_trade": row[4] or 0,
        "peor_trade": row[5] or 0
    }
