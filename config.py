# ==========================================================
# config.py — Configuración central de MiWeb
# Las variables sensibles se leen desde .env o variables
# de entorno de Render. NUNCA poner claves aquí directamente.
# ==========================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ── APIs externas ──────────────────────────────────────────
EODHD_API_KEY      = os.environ.get("EODHD_API_KEY", "")
FMP_API_KEY        = os.environ.get("FMP_API_KEY", "")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Flask ──────────────────────────────────────────────────
SECRET_KEY  = os.environ.get("SECRET_KEY", "dev-key-local-cambiar-en-produccion")
DEBUG       = os.environ.get("FLASK_DEBUG", "0") == "1"

# ── Cache ──────────────────────────────────────────────────
CACHE_TYPE            = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 600   # segundos

# ── Rutas del proyecto ─────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_CACHE_DIR  = os.path.join(BASE_DIR, "data_cache")
POSICIONAL_DIR  = os.path.join(DATA_CACHE_DIR, "posicional")

# Crear directorios si no existen
os.makedirs(POSICIONAL_DIR, exist_ok=True)

# ── Parámetros globales de mercado ─────────────────────────
MERCADO_TIMEZONE = "Europe/Madrid"
HORA_APERTURA    = "09:00"
HORA_CIERRE      = "17:35"

# ── Backtesting ────────────────────────────────────────────
CAPITAL_INICIAL      = 50_000
RIESGO_POR_TRADE_PCT = 1.0     # % del capital por operación
COMISION_PCT         = 0.1     # ida
SLIPPAGE_PCT         = 0.05    # por lado

# ── Render / producción ────────────────────────────────────
# En Render, PORT lo asigna la plataforma automáticamente
PORT = int(os.environ.get("PORT", 5001))
