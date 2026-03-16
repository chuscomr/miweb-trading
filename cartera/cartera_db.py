# cartera/cartera_db.py
# ══════════════════════════════════════════════════════════════
# BASE DE DATOS DE CARTERA — SQLite
#
# Gestiona el almacenamiento de posiciones abiertas y cerradas.
# Usa SQLite para simplicidad — no requiere servidor externo.
# ══════════════════════════════════════════════════════════════

import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Ruta de la base de datos — en la raíz del proyecto
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cartera.db")


class CarteraDB:
    """
    Capa de acceso a datos para la cartera de posiciones.
    Toda interacción con la BD pasa por esta clase.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._inicializar()

    # ── Inicialización ─────────────────────────────────────

    def _inicializar(self):
        """Crea las tablas si no existen."""
        with self._conexion() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS posiciones (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT    NOT NULL,
                    nombre          TEXT,
                    fecha_entrada   TEXT    NOT NULL,
                    precio_entrada  REAL    NOT NULL,
                    stop_loss       REAL    NOT NULL,
                    objetivo        REAL    NOT NULL,
                    acciones        INTEGER NOT NULL,
                    setup_score     INTEGER,
                    contexto_ibex   TEXT,
                    notas           TEXT,
                    estado          TEXT    DEFAULT 'ABIERTA',
                    fecha_cierre    TEXT,
                    precio_cierre   REAL,
                    motivo_cierre   TEXT,
                    fecha_creacion  TEXT    DEFAULT (datetime('now')),
                    creado_en       TEXT    DEFAULT (datetime('now'))
                )
            """)
            # ── Migración: añadir columnas si la tabla ya existía sin ellas ──
            columnas_existentes = [r[1] for r in con.execute("PRAGMA table_info(posiciones)").fetchall()]
            if 'creado_en' not in columnas_existentes:
                con.execute("ALTER TABLE posiciones ADD COLUMN creado_en TEXT")
                con.execute("UPDATE posiciones SET creado_en = datetime('now') WHERE creado_en IS NULL")
            if 'fecha_creacion' not in columnas_existentes:
                con.execute("ALTER TABLE posiciones ADD COLUMN fecha_creacion TEXT")
                con.execute("UPDATE posiciones SET fecha_creacion = datetime('now') WHERE fecha_creacion IS NULL")
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_posiciones_estado
                ON posiciones(estado)
            """)

    def _conexion(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row   # devuelve dicts en lugar de tuplas
        return con

    # ── Lectura ────────────────────────────────────────────

    def obtener_posiciones_abiertas(self) -> list:
        with self._conexion() as con:
            rows = con.execute(
                "SELECT * FROM posiciones WHERE estado = 'ABIERTA' ORDER BY fecha_entrada DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def obtener_posiciones_cerradas(self, limit: int = 50) -> list:
        with self._conexion() as con:
            rows = con.execute(
                "SELECT * FROM posiciones WHERE estado = 'CERRADA' "
                "ORDER BY fecha_cierre DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def obtener_posicion_por_id(self, posicion_id: int) -> Optional[dict]:
        with self._conexion() as con:
            row = con.execute(
                "SELECT * FROM posiciones WHERE id = ?", (posicion_id,)
            ).fetchone()
        return dict(row) if row else None

    def obtener_todas(self) -> list:
        with self._conexion() as con:
            rows = con.execute(
                "SELECT * FROM posiciones ORDER BY fecha_entrada DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Escritura ──────────────────────────────────────────

    def agregar_posicion(
        self,
        ticker:         str,
        nombre:         str,
        fecha_entrada:  str,
        precio_entrada: float,
        stop_loss:      float,
        objetivo:       float,
        acciones:       int,
        setup_score:    Optional[int]  = None,
        contexto_ibex:  Optional[str]  = None,
        notas:          Optional[str]  = None,
    ) -> int:
        """Inserta una nueva posición. Devuelve el ID generado."""
        with self._conexion() as con:
            cursor = con.execute("""
                INSERT INTO posiciones
                    (ticker, nombre, fecha_entrada, precio_entrada, stop_loss,
                     objetivo, acciones, setup_score, contexto_ibex, notas,
                     creado_en, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (ticker, nombre or ticker, fecha_entrada, precio_entrada,
                  stop_loss, objetivo, acciones, setup_score, contexto_ibex, notas))
            posicion_id = cursor.lastrowid

        logger.info(f"✅ Posición creada: {ticker} (ID: {posicion_id})")
        return posicion_id

    def cerrar_posicion(
        self,
        posicion_id:   int,
        fecha_cierre:  str,
        precio_cierre: float,
        motivo_cierre: str = "Manual",
    ) -> bool:
        with self._conexion() as con:
            filas = con.execute("""
                UPDATE posiciones
                SET estado = 'CERRADA', fecha_cierre = ?, precio_cierre = ?, motivo_cierre = ?
                WHERE id = ? AND estado = 'ABIERTA'
            """, (fecha_cierre, precio_cierre, motivo_cierre, posicion_id)).rowcount

        ok = filas > 0
        if ok:
            logger.info(f"✅ Posición {posicion_id} cerrada a {precio_cierre}€")
        else:
            logger.warning(f"⚠️ No se pudo cerrar posición {posicion_id}")
        return ok

    def actualizar_posicion(
        self,
        posicion_id:    int,
        ticker:         str,
        nombre:         str,
        precio_entrada: float,
        stop_loss:      float,
        objetivo:       float,
        acciones:       int,
        setup_score:    Optional[int] = None,
        contexto_ibex:  Optional[str] = None,
        notas:          Optional[str] = None,
    ) -> bool:
        with self._conexion() as con:
            filas = con.execute("""
                UPDATE posiciones
                SET ticker = ?, nombre = ?, precio_entrada = ?, stop_loss = ?,
                    objetivo = ?, acciones = ?, setup_score = ?,
                    contexto_ibex = ?, notas = ?
                WHERE id = ?
            """, (ticker, nombre or ticker, precio_entrada, stop_loss, objetivo,
                  acciones, setup_score, contexto_ibex, notas, posicion_id)).rowcount

        ok = filas > 0
        if ok:
            logger.info(f"✅ Posición {posicion_id} actualizada")
        return ok

    def eliminar_posicion(self, posicion_id: int) -> bool:
        with self._conexion() as con:
            filas = con.execute(
                "DELETE FROM posiciones WHERE id = ?", (posicion_id,)
            ).rowcount
        ok = filas > 0
        if ok:
            logger.info(f"🗑️ Posición {posicion_id} eliminada")
        return ok
