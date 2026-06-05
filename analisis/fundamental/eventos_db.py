"""
analisis/fundamental/eventos_db.py
══════════════════════════════════════════════════════════════
BASE DE DATOS DE EVENTOS CORPORATIVOS — SQLite (v87.4)

Almacena eventos clasificados desde noticias RSS para:
- Historial persistente por ticker
- Consulta de eventos recientes en análisis fundamental
- Base para ajuste automático de scoring (futuro)

Tipos de eventos soportados (8):
  BONOS        — Emisiones de deuda
  DIVIDENDO    — Pagos a accionistas
  AMPLIACION   — Ampliaciones de capital
  EARNINGS     — Resultados trimestrales/anuales
  FUSION       — OPAs, fusiones, adquisiciones
  EJECUTIVO    — Cambios en alta dirección
  REGULATORIO  — Sanciones, multas, expedientes
  ESTRATEGICO  — Planes, contratos, alianzas
══════════════════════════════════════════════════════════════
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)

# DB en /alertas/ (junto a alertas.db) para mantener archivos persistentes agrupados
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "alertas",
    "eventos.db"
)

TIPOS_VALIDOS = {
    "BONOS", "DIVIDENDO", "AMPLIACION", "EARNINGS",
    "FUSION", "EJECUTIVO", "REGULATORIO", "ESTRATEGICO",
}

IMPACTOS_VALIDOS = {"POSITIVO", "NEGATIVO", "NEUTRAL"}


class EventosDB:
    """Capa de acceso a datos para eventos corporativos."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._inicializar()
    
    # ── Inicialización ────────────────────────────────────
    
    def _inicializar(self):
        with self._con() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS eventos (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker          TEXT    NOT NULL,
                    tipo            TEXT    NOT NULL,
                    impacto         TEXT    DEFAULT 'NEUTRAL',
                    titulo          TEXT    NOT NULL,
                    descripcion     TEXT,
                    fuente          TEXT,
                    url             TEXT,
                    fecha_evento    TEXT,
                    fecha_registro  TEXT    DEFAULT (datetime('now')),
                    relevancia      INTEGER DEFAULT 5,
                    hash_titulo     TEXT    UNIQUE
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_eventos_ticker 
                ON eventos(ticker, fecha_evento DESC)
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_eventos_tipo
                ON eventos(tipo, fecha_registro DESC)
            """)
            con.commit()
    
    def _con(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con
    
    # ── Operaciones CRUD ──────────────────────────────────
    
    def registrar_evento(self, ticker, tipo, titulo, descripcion="", 
                          fuente=None, url=None, impacto="NEUTRAL",
                          relevancia=5, fecha_evento=None):
        """
        Registra un evento. Evita duplicados via hash del titulo.
        
        Returns:
            int: ID del evento (nuevo o existente), o None si error
        """
        if tipo not in TIPOS_VALIDOS:
            logger.warning(f"Tipo de evento no válido: {tipo}")
            return None
        
        if impacto not in IMPACTOS_VALIDOS:
            impacto = "NEUTRAL"
        
        # Hash simple para detectar duplicados
        import hashlib
        hash_key = hashlib.md5(f"{ticker}:{titulo}".encode()).hexdigest()
        
        if fecha_evento is None:
            fecha_evento = datetime.now().strftime("%Y-%m-%d")
        
        try:
            with self._con() as con:
                cursor = con.execute("""
                    INSERT OR IGNORE INTO eventos
                    (ticker, tipo, impacto, titulo, descripcion, fuente, url, 
                     fecha_evento, relevancia, hash_titulo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ticker, tipo, impacto, titulo, descripcion, fuente, url,
                      fecha_evento, relevancia, hash_key))
                con.commit()
                
                if cursor.lastrowid:
                    return cursor.lastrowid
                
                # Si era duplicado, recuperar ID existente
                row = con.execute(
                    "SELECT id FROM eventos WHERE hash_titulo = ?",
                    (hash_key,)
                ).fetchone()
                return row['id'] if row else None
                
        except Exception as e:
            logger.error(f"Error registrando evento: {e}")
            return None
    
    def registrar_desde_noticia(self, noticia: dict):
        """
        Registra evento(s) desde una noticia ya clasificada.
        
        Args:
            noticia: dict con 'titulo', 'fuente', 'url', 'fecha', 'evento'
        
        Returns:
            list: IDs de eventos registrados (uno por ticker mencionado)
        """
        evento = noticia.get('evento')
        if not evento:
            return []
        
        tickers = evento.get('tickers', [])
        if not tickers:
            return []
        
        ids = []
        for ticker in tickers:
            evento_id = self.registrar_evento(
                ticker=ticker,
                tipo=evento['tipo'],
                titulo=noticia.get('titulo', ''),
                descripcion=noticia.get('descripcion', '') or noticia.get('summary', ''),
                fuente=noticia.get('fuente'),
                url=noticia.get('url'),
                impacto=evento.get('impacto', 'NEUTRAL'),
                relevancia=evento.get('relevancia', 5),
            )
            if evento_id:
                ids.append(evento_id)
        
        return ids
    
    def obtener_eventos_ticker(self, ticker, dias_atras=90, tipo=None):
        """
        Obtiene eventos de un ticker en los últimos N días.
        
        Args:
            ticker: Ticker (ej: 'IAG.MC')
            dias_atras: Ventana temporal (default 90 días)
            tipo: Filtrar por tipo específico (opcional)
        
        Returns:
            list[dict]: Eventos ordenados por fecha desc
        """
        fecha_limite = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        
        try:
            with self._con() as con:
                if tipo:
                    rows = con.execute("""
                        SELECT * FROM eventos
                        WHERE ticker = ? 
                        AND fecha_evento >= ?
                        AND tipo = ?
                        ORDER BY fecha_evento DESC, id DESC
                    """, (ticker, fecha_limite, tipo)).fetchall()
                else:
                    rows = con.execute("""
                        SELECT * FROM eventos
                        WHERE ticker = ? 
                        AND fecha_evento >= ?
                        ORDER BY fecha_evento DESC, id DESC
                    """, (ticker, fecha_limite)).fetchall()
                
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error obteniendo eventos de {ticker}: {e}")
            return []
    
    def obtener_resumen(self, ticker, dias_atras=90):
        """
        Resumen estadístico de eventos por ticker.
        
        Returns:
            dict: {
                'total': int,
                'por_tipo': {'BONOS': 2, 'EARNINGS': 1, ...},
                'por_impacto': {'POSITIVO': 3, 'NEGATIVO': 0, 'NEUTRAL': 0},
                'score_neto': int  # POSITIVO - NEGATIVO
            }
        """
        eventos = self.obtener_eventos_ticker(ticker, dias_atras)
        
        por_tipo = {}
        por_impacto = {"POSITIVO": 0, "NEGATIVO": 0, "NEUTRAL": 0}
        
        for ev in eventos:
            por_tipo[ev['tipo']] = por_tipo.get(ev['tipo'], 0) + 1
            por_impacto[ev['impacto']] = por_impacto.get(ev['impacto'], 0) + 1
        
        return {
            'total': len(eventos),
            'por_tipo': por_tipo,
            'por_impacto': por_impacto,
            'score_neto': por_impacto['POSITIVO'] - por_impacto['NEGATIVO'],
        }
    
    def obtener_eventos_recientes_globales(self, limit=20, dias_atras=7):
        """
        Eventos más recientes de cualquier ticker (para dashboard).
        """
        fecha_limite = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        
        try:
            with self._con() as con:
                rows = con.execute("""
                    SELECT * FROM eventos
                    WHERE fecha_evento >= ?
                    ORDER BY fecha_registro DESC
                    LIMIT ?
                """, (fecha_limite, limit)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error obteniendo eventos recientes: {e}")
            return []
    
    def limpiar_antiguos(self, dias_retencion=365):
        """Borra eventos más antiguos que N días."""
        fecha_limite = (datetime.now() - timedelta(days=dias_retencion)).strftime("%Y-%m-%d")
        
        try:
            with self._con() as con:
                cursor = con.execute(
                    "DELETE FROM eventos WHERE fecha_evento < ?",
                    (fecha_limite,)
                )
                con.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error limpiando eventos: {e}")
            return 0


# Singleton
_db_instance = None

def get_eventos_db():
    """Devuelve instancia singleton de EventosDB."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EventosDB()
    return _db_instance
