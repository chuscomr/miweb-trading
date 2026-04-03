# cartera/cartera_db.py
import sqlite3, os, logging
from datetime import datetime
from typing import Optional

logger  = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cartera.db")


class CarteraDB:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._inicializar()

    def _inicializar(self):
        with self._conexion() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS posiciones (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT    NOT NULL,
                    nombre          TEXT,
                    sistema         TEXT    NOT NULL DEFAULT 'SWING',
                    fecha_entrada   TEXT    NOT NULL,
                    precio_entrada  REAL    NOT NULL,
                    stop_inicial    REAL,
                    stop_actual     REAL,
                    objetivo        REAL,
                    acciones        INTEGER NOT NULL,
                    fase            TEXT    NOT NULL DEFAULT 'INICIAL',
                    score_nivel     TEXT,
                    contexto_ibex   TEXT,
                    es_excepcion    INTEGER DEFAULT 0,
                    mitad_cerrada   INTEGER DEFAULT 0,
                    precio_mitad    REAL,
                    fecha_mitad     TEXT,
                    notas           TEXT,
                    estado          TEXT    DEFAULT 'ABIERTA',
                    fecha_cierre    TEXT,
                    precio_cierre   REAL,
                    motivo_cierre   TEXT,
                    r_final         REAL,
                    creado_en       TEXT    DEFAULT (datetime('now'))
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    clave TEXT PRIMARY KEY,
                    valor TEXT
                )
            """)
            for clave, valor in [
                ("capital_total",           "30000"),
                ("riesgo_pct",              "1.0"),
                ("limite_mensual_pct",      "6.0"),
                # Riesgo diferenciado por sistema
                ("riesgo_swing_pct",        "1.0"),
                ("riesgo_medio_pct",        "1.0"),
                ("riesgo_posicional_pct",   "2.0"),
            ]:
                con.execute("INSERT OR IGNORE INTO config (clave,valor) VALUES (?,?)",
                            (clave, valor))

            # Migracion automatica
            cols = [r[1] for r in con.execute("PRAGMA table_info(posiciones)").fetchall()]
            for col, tipo in [
                ("sistema",       "TEXT NOT NULL DEFAULT 'SWING'"),
                ("stop_inicial",  "REAL"),
                ("stop_actual",   "REAL"),
                ("fase",          "TEXT NOT NULL DEFAULT 'INICIAL'"),
                ("score_nivel",   "TEXT"),
                ("es_excepcion",  "INTEGER DEFAULT 0"),
                ("mitad_cerrada", "INTEGER DEFAULT 0"),
                ("precio_mitad",  "REAL"),
                ("fecha_mitad",   "TEXT"),
                ("r_final",       "REAL"),
                ("creado_en",     "TEXT"),
            ]:
                if col not in cols:
                    con.execute(f"ALTER TABLE posiciones ADD COLUMN {col} {tipo}")
            if "stop_loss" in cols:
                con.execute("UPDATE posiciones SET stop_actual=stop_loss WHERE stop_actual IS NULL")
                con.execute("UPDATE posiciones SET stop_inicial=stop_loss WHERE stop_inicial IS NULL")
            con.execute("CREATE INDEX IF NOT EXISTS idx_pos_estado ON posiciones(estado)")

    def _conexion(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    # Config
    def get_config(self) -> dict:
        with self._conexion() as con:
            rows = con.execute("SELECT clave,valor FROM config").fetchall()
        cfg = {r["clave"]: r["valor"] for r in rows}
        return {
            "capital_total":          float(cfg.get("capital_total", 30000)),
            "riesgo_pct":             float(cfg.get("riesgo_pct", 1.0)),
            "limite_mensual_pct":     float(cfg.get("limite_mensual_pct", 6.0)),
            # Riesgo diferenciado por sistema
            "riesgo_swing_pct":       float(cfg.get("riesgo_swing_pct", 1.0)),
            "riesgo_medio_pct":       float(cfg.get("riesgo_medio_pct", 1.0)),
            "riesgo_posicional_pct":  float(cfg.get("riesgo_posicional_pct", 2.0)),
        }

    def set_config(self, clave: str, valor: str):
        with self._conexion() as con:
            con.execute("INSERT OR REPLACE INTO config (clave,valor) VALUES (?,?)", (clave, str(valor)))

    # Lectura
    def obtener_posiciones_abiertas(self) -> list:
        with self._conexion() as con:
            rows = con.execute("SELECT * FROM posiciones WHERE estado='ABIERTA' ORDER BY fecha_entrada DESC").fetchall()
        return [dict(r) for r in rows]

    def obtener_posiciones_cerradas(self, limit: int = 100) -> list:
        with self._conexion() as con:
            rows = con.execute("SELECT * FROM posiciones WHERE estado='CERRADA' ORDER BY fecha_cierre DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def obtener_cerradas_mes(self, año: int, mes: int) -> list:
        prefijo = f"{año}-{mes:02d}"
        with self._conexion() as con:
            rows = con.execute("SELECT * FROM posiciones WHERE estado='CERRADA' AND fecha_cierre LIKE ? ORDER BY fecha_cierre DESC", (f"{prefijo}%",)).fetchall()
        return [dict(r) for r in rows]

    def obtener_posicion_por_id(self, pid: int) -> Optional[dict]:
        with self._conexion() as con:
            row = con.execute("SELECT * FROM posiciones WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None

    def obtener_todas(self) -> list:
        with self._conexion() as con:
            rows = con.execute("SELECT * FROM posiciones ORDER BY fecha_entrada DESC").fetchall()
        return [dict(r) for r in rows]

    # Escritura
    def agregar_posicion(self, ticker, nombre, sistema, fecha_entrada,
                         precio_entrada, stop_inicial, objetivo, acciones,
                         score_nivel=None, contexto_ibex=None,
                         es_excepcion=False, notas=None) -> int:
        # stop puede ser None para posiciones sin stop (acciones antiguas)
        stop_ini = float(stop_inicial) if stop_inicial else None
        with self._conexion() as con:
            cur = con.execute("""
                INSERT INTO posiciones
                    (ticker,nombre,sistema,fecha_entrada,precio_entrada,
                     stop_inicial,stop_actual,objetivo,acciones,fase,
                     score_nivel,contexto_ibex,es_excepcion,notas,creado_en)
                VALUES (?,?,?,?,?,?,?,?,?,'INICIAL',?,?,?,?,datetime('now'))
            """, (ticker, nombre or ticker, sistema.upper(), fecha_entrada,
                  precio_entrada, stop_ini, stop_ini, objetivo,
                  acciones, score_nivel, contexto_ibex,
                  1 if es_excepcion else 0, notas))
            pid = cur.lastrowid
        logger.info(f"Posicion creada: {ticker} {sistema} ID:{pid}")
        return pid

    def actualizar_stop_fase(self, pid: int, stop_actual: float, fase: str) -> bool:
        with self._conexion() as con:
            n = con.execute("UPDATE posiciones SET stop_actual=?,fase=? WHERE id=? AND estado='ABIERTA'",
                            (stop_actual, fase.upper(), pid)).rowcount
        return n > 0

    def registrar_mitad(self, pid: int, precio_mitad: float, fecha_mitad: str) -> bool:
        with self._conexion() as con:
            n = con.execute("UPDATE posiciones SET mitad_cerrada=1,precio_mitad=?,fecha_mitad=? WHERE id=? AND estado='ABIERTA'",
                            (precio_mitad, fecha_mitad, pid)).rowcount
        return n > 0

    def cerrar_posicion(self, pid: int, fecha_cierre: str, precio_cierre: float,
                        motivo_cierre: str = "Manual", r_final: Optional[float] = None) -> bool:
        with self._conexion() as con:
            n = con.execute("""
                UPDATE posiciones SET estado='CERRADA',fecha_cierre=?,
                    precio_cierre=?,motivo_cierre=?,r_final=?
                WHERE id=? AND estado='ABIERTA'
            """, (fecha_cierre, precio_cierre, motivo_cierre, r_final, pid)).rowcount
        if n > 0: logger.info(f"Posicion {pid} cerrada a {precio_cierre}")
        return n > 0

    def actualizar_posicion(self, pid: int, precio_entrada: float, stop_actual: float,
                            objetivo: Optional[float], acciones: int, notas: Optional[str] = None,
                            nombre: Optional[str] = None, fecha_entrada: Optional[str] = None,
                            es_excepcion: Optional[bool] = None, ticker: Optional[str] = None) -> bool:
        with self._conexion() as con:
            # Siempre actualizar nombre y fecha si se envían
            sets = "precio_entrada=?, stop_actual=?, objetivo=?, acciones=?, notas=?"
            vals = [precio_entrada, stop_actual, objetivo, acciones, notas]
            if nombre is not None:
                sets += ", nombre=?"
                vals.append(nombre)
            if fecha_entrada is not None:
                sets += ", fecha_entrada=?"
                vals.append(fecha_entrada)
            # Ticker — actualizar si se envía
            if ticker:
                sets += ", ticker=?"
                vals.append(ticker.strip().upper())
            # es_excepcion siempre se actualiza
            sets += ", es_excepcion=?"
            vals.append(1 if es_excepcion else 0)
            vals.append(pid)
            n = con.execute(f"UPDATE posiciones SET {sets} WHERE id=?", vals).rowcount
        return n > 0

    def eliminar_posicion(self, pid: int) -> bool:
        with self._conexion() as con:
            n = con.execute("DELETE FROM posiciones WHERE id=?", (pid,)).rowcount
        return n > 0
