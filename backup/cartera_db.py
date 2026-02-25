"""
cartera_db.py
Gestión de base de datos SQLite para el seguimiento de cartera
"""

import sqlite3
from datetime import datetime
import os

DATABASE_PATH = "cartera.db"


def init_db():
    """
    Inicializa la base de datos creando las tablas necesarias
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Tabla de posiciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posiciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            nombre TEXT,
            fecha_entrada TEXT NOT NULL,
            precio_entrada REAL NOT NULL,
            stop_loss REAL NOT NULL,
            objetivo REAL NOT NULL,
            acciones INTEGER NOT NULL,
            setup_score INTEGER,
            contexto_ibex TEXT,
            notas TEXT,
            estado TEXT DEFAULT 'ABIERTA',
            fecha_cierre TEXT,
            precio_cierre REAL,
            resultado_r REAL,
            resultado_euros REAL,
            motivo_cierre TEXT,
            creado_en TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")


def agregar_posicion(ticker, nombre, fecha_entrada, precio_entrada, stop_loss, 
                     objetivo, acciones, setup_score=None, contexto_ibex=None, notas=None):
    """
    Agrega una nueva posición a la cartera
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Guardar stop_original = stop_loss inicial (nunca se modificará)
    cursor.execute("""
        INSERT INTO posiciones (
            ticker, nombre, fecha_entrada, precio_entrada, stop_loss, stop_original,
            objetivo, acciones, setup_score, contexto_ibex, notas, 
            estado, creado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ABIERTA', ?)
    """, (ticker, nombre, fecha_entrada, precio_entrada, stop_loss, stop_loss,
          objetivo, acciones, setup_score, contexto_ibex, notas, 
          datetime.now().isoformat()))
    
    conn.commit()
    posicion_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ Posición añadida: {ticker} (ID: {posicion_id}, Stop original: {stop_loss}€)")
    return posicion_id


def obtener_posiciones_abiertas():
    """
    Obtiene todas las posiciones abiertas
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM posiciones 
        WHERE estado = 'ABIERTA'
        ORDER BY fecha_entrada DESC
    """)
    
    posiciones = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return posiciones


def obtener_posicion_por_id(posicion_id):
    """
    Obtiene una posición específica por su ID
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM posiciones WHERE id = ?", (posicion_id,))
    posicion = cursor.fetchone()
    
    conn.close()
    
    return dict(posicion) if posicion else None


def cerrar_posicion(posicion_id, fecha_cierre, precio_cierre, motivo_cierre=None):
    """
    Cierra una posición abierta
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Obtener datos de la posición
    cursor.execute("SELECT precio_entrada, stop_loss, acciones FROM posiciones WHERE id = ?", 
                   (posicion_id,))
    datos = cursor.fetchone()
    
    if not datos:
        conn.close()
        return False
    
    precio_entrada, stop_loss, acciones = datos
    
    # Calcular resultado
    riesgo_por_accion = precio_entrada - stop_loss
    resultado_por_accion = precio_cierre - precio_entrada
    resultado_r = resultado_por_accion / riesgo_por_accion if riesgo_por_accion > 0 else 0
    resultado_euros = resultado_por_accion * acciones
    
    # Actualizar posición
    cursor.execute("""
        UPDATE posiciones 
        SET estado = 'CERRADA',
            fecha_cierre = ?,
            precio_cierre = ?,
            resultado_r = ?,
            resultado_euros = ?,
            motivo_cierre = ?
        WHERE id = ?
    """, (fecha_cierre, precio_cierre, resultado_r, resultado_euros, motivo_cierre, posicion_id))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Posición {posicion_id} cerrada: {resultado_r:.2f}R ({resultado_euros:+.2f}€)")
    return True


def obtener_historial(limite=50):
    """
    Obtiene el historial de posiciones cerradas
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM posiciones 
        WHERE estado = 'CERRADA'
        ORDER BY fecha_cierre DESC
        LIMIT ?
    """, (limite,))
    
    historial = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return historial


def obtener_estadisticas():
    """
    Calcula estadísticas globales de la cartera
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Posiciones cerradas
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN resultado_euros > 0 THEN 1 ELSE 0 END) as ganadoras,
            AVG(resultado_r) as r_promedio,
            SUM(resultado_euros) as total_euros,
            MAX(resultado_euros) as mejor_trade,
            MIN(resultado_euros) as peor_trade
        FROM posiciones 
        WHERE estado = 'CERRADA'
    """)
    
    stats = cursor.fetchone()
    
    conn.close()
    
    if stats and stats[0] > 0:
        total, ganadoras, r_promedio, total_euros, mejor_trade, peor_trade = stats
        win_rate = (ganadoras / total * 100) if total > 0 else 0
        
        return {
            "total_operaciones": total,
            "ganadoras": ganadoras,
            "perdedoras": total - ganadoras,
            "win_rate": win_rate,
            "r_promedio": r_promedio or 0,
            "total_euros": total_euros or 0,
            "mejor_trade": mejor_trade or 0,
            "peor_trade": peor_trade or 0
        }
    else:
        return {
            "total_operaciones": 0,
            "ganadoras": 0,
            "perdedoras": 0,
            "win_rate": 0,
            "r_promedio": 0,
            "total_euros": 0,
            "mejor_trade": 0,
            "peor_trade": 0
        }


def eliminar_posicion(posicion_id):
    """
    Elimina permanentemente una posición (usar con cuidado)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM posiciones WHERE id = ?", (posicion_id,))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected > 0:
        print(f"✅ Posición {posicion_id} eliminada")
        return True
    else:
        print(f"❌ Posición {posicion_id} no encontrada")
        return False


def actualizar_posicion(posicion_id, ticker=None, nombre=None, precio_entrada=None, 
                       stop_loss=None, objetivo=None, acciones=None, 
                       setup_score=None, contexto_ibex=None, notas=None):
    """
    Actualiza una posición existente
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Construir query dinámicamente solo con los campos proporcionados
    campos = []
    valores = []
    
    if ticker is not None:
        campos.append("ticker = ?")
        valores.append(ticker)
    if nombre is not None:
        campos.append("nombre = ?")
        valores.append(nombre)
    if precio_entrada is not None:
        campos.append("precio_entrada = ?")
        valores.append(precio_entrada)
    if stop_loss is not None:
        campos.append("stop_loss = ?")
        valores.append(stop_loss)
    if objetivo is not None:
        campos.append("objetivo = ?")
        valores.append(objetivo)
    if acciones is not None:
        campos.append("acciones = ?")
        valores.append(acciones)
    if setup_score is not None:
        campos.append("setup_score = ?")
        valores.append(setup_score)
    if contexto_ibex is not None:
        campos.append("contexto_ibex = ?")
        valores.append(contexto_ibex)
    if notas is not None:
        campos.append("notas = ?")
        valores.append(notas)
    
    if not campos:
        conn.close()
        return False
    
    valores.append(posicion_id)
    query = f"UPDATE posiciones SET {', '.join(campos)} WHERE id = ?"
    
    cursor.execute(query, valores)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected > 0:
        print(f"✅ Posición {posicion_id} actualizada")
        return True
    else:
        print(f"❌ Posición {posicion_id} no encontrada")
        return False


# Inicializar BD al importar el módulo
if not os.path.exists(DATABASE_PATH):
    init_db()
