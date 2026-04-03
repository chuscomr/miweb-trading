# alertas/alertas_db.py
# ══════════════════════════════════════════════════════════════
# BASE DE DATOS DE ALERTAS — SQLite
#
# Tipos de alerta soportados:
#   PRECIO_SOBRE   — precio cruza por encima del nivel
#   PRECIO_BAJO    — precio cruza por debajo del nivel
#   STOP_LOSS      — precio toca el stop de una posición
#   OBJETIVO       — precio alcanza el objetivo de una posición
#   RSI_ALTO       — RSI supera umbral (sobrecompra)
#   RSI_BAJO       — RSI cae bajo umbral (sobreventa)
#   BREAKOUT       — detectado setup de breakout por el scanner
#   PULLBACK       — detectado setup de pullback por el scanner
# ══════════════════════════════════════════════════════════════

import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "alertas.db")

TIPOS_VALIDOS = {
    "PRECIO_SOBRE", "PRECIO_BAJO",
    "STOP_LOSS", "OBJETIVO",
    "RSI_ALTO", "RSI_BAJO",
    "BREAKOUT", "PULLBACK",
}


class AlertasDB:
    """Capa de acceso a datos para alertas de precio y técnicas."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._inicializar()

    # ── Inicialización ─────────────────────────────────────

    def _inicializar(self):
        with self._con() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS alertas (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT    NOT NULL,
                    nombre          TEXT,
                    tipo            TEXT    NOT NULL,
                    nivel           REAL,
                    umbral          REAL,
                    descripcion     TEXT,
                    activa          INTEGER DEFAULT 1,
                    disparada       INTEGER DEFAULT 0,
                    fecha_creacion  TEXT    DEFAULT (datetime('now')),
                    fecha_disparo   TEXT,
                    precio_disparo  REAL,
                    notas           TEXT
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_alertas_activa
                ON alertas(activa, ticker)
            """)

    def _con(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    # ── Lectura ────────────────────────────────────────────

    def obtener_activas(self) -> list:
        with self._con() as con:
            rows = con.execute(
                "SELECT * FROM alertas WHERE activa = 1 ORDER BY fecha_creacion DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def obtener_disparadas(self, limit: int = 50) -> list:
        with self._con() as con:
            rows = con.execute(
                "SELECT * FROM alertas WHERE disparada = 1 "
                "ORDER BY fecha_disparo DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def obtener_por_ticker(self, ticker: str) -> list:
        with self._con() as con:
            rows = con.execute(
                "SELECT * FROM alertas WHERE ticker = ? AND activa = 1 "
                "ORDER BY fecha_creacion DESC", (ticker,)
            ).fetchall()
        return [dict(r) for r in rows]

    def obtener_por_id(self, alerta_id: int) -> Optional[dict]:
        with self._con() as con:
            row = con.execute(
                "SELECT * FROM alertas WHERE id = ?", (alerta_id,)
            ).fetchone()
        return dict(row) if row else None

    def obtener_todas(self) -> list:
        with self._con() as con:
            rows = con.execute(
                "SELECT * FROM alertas ORDER BY fecha_creacion DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Escritura ──────────────────────────────────────────

    def crear_alerta(
        self,
        ticker:      str,
        tipo:        str,
        nivel:       Optional[float] = None,
        umbral:      Optional[float] = None,
        descripcion: Optional[str]   = None,
        nombre:      Optional[str]   = None,
        notas:       Optional[str]   = None,
    ) -> int:
        """
        Crea una nueva alerta.

        Args:
            ticker:      Ej. "BBVA.MC"
            tipo:        Uno de TIPOS_VALIDOS
            nivel:       Precio objetivo (para alertas de precio)
            umbral:      Valor numérico (para RSI u otros indicadores)
            descripcion: Texto libre descriptivo
            nombre:      Nombre del valor
            notas:       Notas adicionales

        Returns:
            ID generado.
        """
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo '{tipo}' no válido. Use: {TIPOS_VALIDOS}")

        with self._con() as con:
            cursor = con.execute("""
                INSERT INTO alertas
                    (ticker, nombre, tipo, nivel, umbral, descripcion, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ticker, nombre or ticker, tipo, nivel, umbral, descripcion, notas))
            alerta_id = cursor.lastrowid

        logger.info(f"✅ Alerta creada: {ticker} {tipo} (ID: {alerta_id})")
        return alerta_id

    def marcar_disparada(
        self,
        alerta_id:     int,
        precio_disparo: float,
    ) -> bool:
        """Marca una alerta como disparada y la desactiva."""
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._con() as con:
            filas = con.execute("""
                UPDATE alertas
                SET disparada = 1, activa = 0,
                    fecha_disparo = ?, precio_disparo = ?
                WHERE id = ?
            """, (fecha, precio_disparo, alerta_id)).rowcount
        ok = filas > 0
        if ok:
            logger.info(f"🔔 Alerta {alerta_id} disparada a {precio_disparo}€")
        return ok

    def desactivar(self, alerta_id: int) -> bool:
        with self._con() as con:
            filas = con.execute(
                "UPDATE alertas SET activa = 0 WHERE id = ?", (alerta_id,)
            ).rowcount
        return filas > 0

    def reactivar(self, alerta_id: int) -> bool:
        with self._con() as con:
            filas = con.execute(
                "UPDATE alertas SET activa = 1, disparada = 0 WHERE id = ?",
                (alerta_id,)
            ).rowcount
        return filas > 0

    def eliminar(self, alerta_id: int) -> bool:
        with self._con() as con:
            filas = con.execute(
                "DELETE FROM alertas WHERE id = ?", (alerta_id,)
            ).rowcount
        ok = filas > 0
        if ok:
            logger.info(f"🗑️ Alerta {alerta_id} eliminada")
        return ok
