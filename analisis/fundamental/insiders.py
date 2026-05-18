"""
analisis/fundamental/insiders.py
══════════════════════════════════════════════════════════════
MÓDULO DE INSIDERS
══════════════════════════════════════════════════════════════

Fuentes (en orden de prioridad):
  1. MarketScreener  — HTML estable, cobertura europea buena
  2. CNMV            — Fuente oficial española, ASP.NET difícil
  3. DB local        — Fallback si ambas fallan

Arquitectura:
  - Scraping SEPARADO de la app (no bloquea peticiones)
  - Persistencia SQLite en data/insiders.db
  - Caducidad 24h configurable
  - Evaluador: fuerte / débil / nulo
  - Uso como REFUERZO, nunca como score duro
"""

import logging
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────

DB_PATH          = Path(__file__).parent.parent.parent / "data" / "insiders.db"
CADUCIDAD_HORAS  = 24
UMBRAL_FUERTE    = 500_000   # €
UMBRAL_DEBIL     = 100_000   # €
VENTANA_DIAS     = 60
TIMEOUT_HTTP     = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# ─────────────────────────────────────────────────────────────
# MAPPING ticker → IDs de fuentes
# ─────────────────────────────────────────────────────────────

# MarketScreener: URL slug de cada empresa española
# Formato: https://www.marketscreener.com/quote/stock/{SLUG}/insider/
MARKETSCREENER_SLUGS = {
    "ACS.MC":   "ACS-ACTIVIDADES-DE-CONSTRUCCI-4822",
    "ACX.MC":   "ACERINOX-4823",
    "ANA.MC":   "ACCIONA-SA-4820",
    "BBVA.MC":  "BANCO-BILBAO-VIZCAYA-ARGENTA-4833",
    "BKT.MC":   "BANKINTER-4836",
    "CABK.MC":  "CAIXABANK-17489",
    "CLNX.MC":  "CELLNEX-TELECOM-37759",
    "COL.MC":   "COLONIAL-4840",
    "ELE.MC":   "ENDESA-4843",
    "ENG.MC":   "ENAGAS-4844",
    "FCC.MC":   "FCC-4847",
    "GRF.MC":   "GRIFOLS-SA-49124",
    "IAG.MC":   "INTERNATIONAL-AIRLINES-GROUP-50917",
    "IBE.MC":   "IBERDROLA-SA-4832",
    "IDR.MC":   "INDRA-SISTEMAS-4855",
    "ITX.MC":   "INDUSTRIA-DE-DISENO-TEXTIL-4857",
    "LOG.MC":   "COMPANIA-DE-DISTRIBUCION-INT-19479",
    "MAP.MC":   "MAPFRE-SA-4862",
    "MEL.MC":   "MELIA-HOTELS-INTERNATIONAL-4864",
    "MRL.MC":   "MERLIN-PROPERTIES-38067",
    "MTS.MC":   "ARCELORMITTAL-4829",
    "NTGY.MC":  "NATURGY-ENERGY-GROUP-4866",
    "PHM.MC":   "PUIG-BRANDS-SA-151982",
    "RED.MC":   "RED-ELECTRICA-CORPORACION-4871",
    "REP.MC":   "REPSOL-SA-4872",
    "ROVI.MC":  "LABORATORIOS-FARMACEUTICOS-66399",
    "SAB.MC":   "BANCO-DE-SABADELL-4831",
    "SAN.MC":   "BANCO-SANTANDER-SA-4834",
    "SLR.MC":   "SOLARIA-ENERGIA-Y-MEDIO-AMB-50682",
    "TEF.MC":   "TELEFONICA-SA-4876",
    "UNI.MC":   "UNICAJA-BANCO-94847",
    "VIS.MC":   "VISCOFAN-4879",
    "R4.MC":    "RENTA-4-SERVICIOS-DE-INVERS-4870",
    "AEB.MC":   "AEDAS-HOMES-95530",
    "AMS.MC":   "AMADEUS-IT-GROUP-SA-49127",
}

# CNMV: ISIN de cada empresa
TICKER_ISIN = {
    "ACS.MC":   "ES0167050915",
    "ACX.MC":   "ES0132105018",
    "ANA.MC":   "ES0111845014",
    "BBVA.MC":  "ES0113211835",
    "BKT.MC":   "ES0113307062",
    "CABK.MC":  "ES0140609019",
    "CLNX.MC":  "ES0105066007",
    "COL.MC":   "ES0119259019",
    "ELE.MC":   "ES0130670112",
    "ENG.MC":   "ES0116870314",
    "FCC.MC":   "ES0122060314",
    "GRF.MC":   "ES0171996012",
    "IAG.MC":   "ES0177542018",
    "IBE.MC":   "ES0144580Y14",
    "IDR.MC":   "ES0148396014",
    "ITX.MC":   "ES0148396014",
    "LOG.MC":   "ES0170432115",
    "MAP.MC":   "ES0124244E34",
    "MEL.MC":   "ES0176252718",
    "MRL.MC":   "ES0105765018",
    "MTS.MC":   "ES0113860A34",
    "NTGY.MC":  "ES0116870314",
    "PHM.MC":   "ES0150902025",
    "RED.MC":   "ES0173093024",
    "REP.MC":   "ES0173516115",
    "ROVI.MC":  "ES0180709019",
    "SAB.MC":   "ES0113860A34",
    "SAN.MC":   "ES0113900J37",
    "SLR.MC":   "ES0165386014",
    "TEF.MC":   "ES0178430E18",
    "UNI.MC":   "ES0127797019",
    "VIS.MC":   "ES0184262017",
    "R4.MC":    "ES0173516115",
    "AEB.MC":   "ES0105065009",
    "AMS.MC":   "ES0109067019",
}


# ─────────────────────────────────────────────────────────────
# BASE DE DATOS SQLite
# ─────────────────────────────────────────────────────────────

def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operaciones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            isin        TEXT,
            fecha_op    TEXT,
            tipo        TEXT,
            importe     REAL,
            volumen     REAL,
            insider     TEXT,
            cargo       TEXT,
            fuente      TEXT,
            scraped_at  TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            ticker      TEXT PRIMARY KEY,
            last_scrape TEXT,
            status      TEXT,
            mensaje     TEXT,
            fuente_ok   TEXT
        )
    """)
    # Migración: añadir fuente_ok si la tabla ya existía sin esa columna
    try:
        conn.execute("ALTER TABLE scrape_log ADD COLUMN fuente_ok TEXT")
        conn.commit()
    except Exception:
        pass  # columna ya existe — normal
    conn.commit()
    conn.close()


def _guardar_operaciones(ticker: str, operaciones: list,
                         status: str = "ok", msg: str = "",
                         fuente_ok: str = ""):
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        ahora = datetime.now().isoformat()
        conn.execute("DELETE FROM operaciones WHERE ticker = ?", (ticker,))
        for op in operaciones:
            conn.execute("""
                INSERT INTO operaciones
                    (ticker, isin, fecha_op, tipo, importe, volumen,
                     insider, cargo, fuente, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                op.get("isin", ""),
                op.get("fecha", ""),
                op.get("tipo", ""),
                float(op.get("importe", 0) or 0),
                float(op.get("volumen", 0) or 0),
                op.get("insider", ""),
                op.get("cargo", ""),
                op.get("fuente", ""),
                ahora,
            ))
        conn.execute("""
            INSERT OR REPLACE INTO scrape_log
                (ticker, last_scrape, status, mensaje, fuente_ok)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, ahora, status, msg, fuente_ok))
        conn.commit()
    finally:
        conn.close()


def _leer_operaciones(ticker: str) -> dict:
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM operaciones WHERE ticker = ? ORDER BY fecha_op DESC",
            (ticker,)
        ).fetchall()
        log = conn.execute(
            "SELECT * FROM scrape_log WHERE ticker = ?",
            (ticker,)
        ).fetchone()
    finally:
        conn.close()

    operaciones = [dict(r) for r in rows]
    last_scrape = caducado = None
    status    = "sin_datos"
    fuente_ok = ""

    if log:
        try:
            last_scrape = datetime.fromisoformat(log["last_scrape"])
            caducado    = (datetime.now() - last_scrape) > timedelta(hours=CADUCIDAD_HORAS)
            status      = log["status"]
            fuente_ok   = log["fuente_ok"] or ""
        except Exception:
            caducado = True

    return {
        "operaciones": operaciones,
        "last_scrape": last_scrape,
        "caducado":    caducado if caducado is not None else True,
        "status":      status,
        "fuente_ok":   fuente_ok,
    }


# ─────────────────────────────────────────────────────────────
# FUENTE 1: MarketScreener
# ─────────────────────────────────────────────────────────────

def _scrape_marketscreener(ticker: str) -> list:
    """
    Scraping de MarketScreener — fuente primaria.

    URL: https://www.marketscreener.com/quote/stock/{SLUG}/insider/

    Estructura HTML esperada:
    <table> con columnas:
      Date | Name | Position | Type | Volume | Price | Amount
    """
    slug = MARKETSCREENER_SLUGS.get(ticker.upper())
    if not slug:
        logger.info(f"MS: slug no encontrado para {ticker}")
        return []

    url = f"https://www.marketscreener.com/quote/stock/{slug}/insider/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_HTTP)
        if r.status_code != 200:
            logger.warning(f"MS {ticker}: HTTP {r.status_code}")
            return []

        return _parsear_ms(r.text, ticker)

    except Exception as e:
        logger.warning(f"MS {ticker}: {type(e).__name__}: {e}")
        return []


def _parsear_ms(html: str, ticker: str) -> list:
    """
    Parsea la tabla de insiders de MarketScreener.

    Columnas típicas (pueden variar por idioma/versión):
    Date | Insider | Position | Operation | Volume | Price | Amount
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 no instalado")
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
        operaciones = []

        # MS usa tablas con clase específica o data-table
        tablas = soup.find_all("table")
        for tabla in tablas:
            # Buscar cabecera que indique tabla de insiders
            ths = [th.get_text(strip=True).lower() for th in tabla.find_all("th")]
            if not any(k in " ".join(ths) for k in
                       ["date", "fecha", "insider", "operation", "operación", "amount"]):
                continue

            # Mapear posición de columnas
            col_fecha   = _col_idx(ths, ["date", "fecha"])
            col_insider = _col_idx(ths, ["insider", "name", "nombre"])
            col_cargo   = _col_idx(ths, ["position", "cargo", "title"])
            col_tipo    = _col_idx(ths, ["operation", "operación", "type", "tipo"])
            col_importe = _col_idx(ths, ["amount", "importe", "value"])
            col_volumen = _col_idx(ths, ["volume", "shares", "volumen", "títulos"])

            filas = tabla.find_all("tr")[1:]  # saltar cabecera
            for fila in filas:
                celdas = [td.get_text(strip=True) for td in fila.find_all("td")]
                if len(celdas) < 3:
                    continue

                op = _extraer_op_ms(
                    celdas, col_fecha, col_insider, col_cargo,
                    col_tipo, col_importe, col_volumen, ticker
                )
                if op:
                    operaciones.append(op)

        logger.info(f"MS {ticker}: {len(operaciones)} operaciones parseadas")
        return operaciones

    except Exception as e:
        logger.warning(f"MS parser error {ticker}: {e}")
        return []


def _col_idx(headers: list, nombres: list) -> int:
    """Devuelve el índice de la columna que coincida con algún nombre."""
    for i, h in enumerate(headers):
        if any(n in h for n in nombres):
            return i
    return -1


def _extraer_op_ms(celdas, ci_fecha, ci_insider, ci_cargo,
                   ci_tipo, ci_importe, ci_volumen, ticker) -> dict | None:
    """Extrae una operación de una fila de MarketScreener."""
    try:
        # Fecha
        fecha_raw = celdas[ci_fecha] if ci_fecha >= 0 and ci_fecha < len(celdas) else ""
        fecha = _parsear_fecha(fecha_raw)
        if not fecha:
            return None

        # Tipo de operación
        tipo_raw = celdas[ci_tipo].lower() if ci_tipo >= 0 and ci_tipo < len(celdas) else ""
        if any(k in tipo_raw for k in ["buy", "acqui", "compra", "adquis", "purchase"]):
            tipo = "compra"
        elif any(k in tipo_raw for k in ["sell", "sale", "venta", "transm", "disposal"]):
            tipo = "venta"
        else:
            return None

        # Importe
        importe = _parsear_numero(
            celdas[ci_importe] if ci_importe >= 0 and ci_importe < len(celdas) else "0"
        )

        # Volumen
        volumen = _parsear_numero(
            celdas[ci_volumen] if ci_volumen >= 0 and ci_volumen < len(celdas) else "0"
        )

        # Insider y cargo
        insider = celdas[ci_insider].strip() if ci_insider >= 0 and ci_insider < len(celdas) else ""
        cargo   = celdas[ci_cargo].strip()   if ci_cargo   >= 0 and ci_cargo   < len(celdas) else ""

        return {
            "fecha":   fecha,
            "tipo":    tipo,
            "importe": importe,
            "volumen": volumen,
            "insider": insider[:80],
            "cargo":   cargo[:60],
            "fuente":  "marketscreener",
            "isin":    TICKER_ISIN.get(ticker.upper(), ""),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# FUENTE 2: CNMV (fallback oficial)
# ─────────────────────────────────────────────────────────────

def _scrape_cnmv(ticker: str) -> list:
    """
    Scraping CNMV — fallback oficial.
    ASP.NET difícil de parsear — hacemos lo que podemos.
    """
    isin = TICKER_ISIN.get(ticker.upper())
    if not isin:
        return []

    urls = [
        f"https://www.cnmv.es/portal/Consultas/EE/Operaciones.aspx?isin={isin}",
        f"https://www.cnmv.es/portal/Consultas/EE/Participaciones.aspx?isin={isin}&tipo=2",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_HTTP)
            if r.status_code == 200 and len(r.text) > 5000:
                ops = _parsear_cnmv(r.text, ticker, isin)
                if ops:
                    logger.info(f"CNMV {ticker}: {len(ops)} operaciones")
                    return ops
            time.sleep(1)
        except Exception as e:
            logger.warning(f"CNMV {ticker}: {e}")

    return []


def _parsear_cnmv(html: str, ticker: str, isin: str) -> list:
    """Parsea HTML del portal CNMV."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        operaciones = []

        for tabla in soup.find_all("table"):
            ths = [th.get_text(strip=True).lower() for th in tabla.find_all("th")]
            if not any(k in " ".join(ths) for k in ["fecha", "operaci", "importe", "tipo"]):
                continue

            for fila in tabla.find_all("tr")[1:]:
                celdas = [td.get_text(strip=True) for td in fila.find_all("td")]
                if len(celdas) < 3:
                    continue

                # Buscar fecha
                fecha = None
                for c in celdas:
                    f = _parsear_fecha(c)
                    if f:
                        fecha = f
                        break
                if not fecha:
                    continue

                # Tipo
                texto = " ".join(celdas).upper()
                if any(k in texto for k in ["ADQUIS", "COMPRA", "SUSCR"]):
                    tipo = "compra"
                elif any(k in texto for k in ["TRANSMIS", "VENTA", "ENAJ"]):
                    tipo = "venta"
                else:
                    continue

                # Importe
                importe = max((_parsear_numero(c) for c in celdas), default=0)
                if importe < 1000:
                    continue

                operaciones.append({
                    "fecha":   fecha,
                    "tipo":    tipo,
                    "importe": importe,
                    "volumen": 0.0,
                    "insider": _extraer_insider_cnmv(celdas),
                    "cargo":   "",
                    "fuente":  "cnmv",
                    "isin":    isin,
                })

        return operaciones
    except Exception as e:
        logger.warning(f"CNMV parser {ticker}: {e}")
        return []


def _extraer_insider_cnmv(celdas: list) -> str:
    for c in reversed(celdas):
        limpio = c.strip()
        if (len(limpio) > 6
                and not limpio.replace(".", "").replace(",", "").replace(" ", "").isnumeric()
                and not re.match(r"\d{2}/\d{2}/\d{4}", limpio)):
            return limpio[:60]
    return ""


# ─────────────────────────────────────────────────────────────
# ORQUESTADOR — intenta MS primero, luego CNMV
# ─────────────────────────────────────────────────────────────

def scrape_insiders(ticker: str, forzar: bool = False) -> dict:
    """
    Punto de entrada del scraping.
    1. Comprueba caducidad en DB
    2. Intenta MarketScreener
    3. Fallback a CNMV
    4. Guarda en DB

    Args:
        ticker: Ej "SAN.MC"
        forzar: Ignora caducidad y fuerza scraping

    Returns:
        dict {operaciones, status, mensaje, fuente}
    """
    ticker = ticker.upper()
    if not ticker.endswith(".MC"):
        ticker += ".MC"

    # Datos frescos en DB → no scraping
    if not forzar:
        datos = _leer_operaciones(ticker)
        if not datos["caducado"] and datos["status"] == "ok":
            logger.info(f"Insiders {ticker}: datos frescos en DB")
            return {
                "operaciones": datos["operaciones"],
                "status":      "cache",
                "mensaje":     f"Datos desde BD local ({datos['fuente_ok']})",
                "fuente":      datos["fuente_ok"],
            }

    operaciones = []
    fuente_ok   = ""

    # ── Intento 1: MarketScreener ────────────────────────────
    logger.info(f"Insiders {ticker}: intentando MarketScreener...")
    ops_ms = _scrape_marketscreener(ticker)
    if ops_ms:
        operaciones = ops_ms
        fuente_ok   = "marketscreener"
        logger.info(f"Insiders {ticker}: {len(ops_ms)} ops desde MarketScreener ✅")

    # ── Intento 2: CNMV (fallback) ───────────────────────────
    if not operaciones:
        logger.info(f"Insiders {ticker}: fallback a CNMV...")
        time.sleep(1)
        ops_cnmv = _scrape_cnmv(ticker)
        if ops_cnmv:
            operaciones = ops_cnmv
            fuente_ok   = "cnmv"
            logger.info(f"Insiders {ticker}: {len(ops_cnmv)} ops desde CNMV ✅")

    # ── Guardar en DB ────────────────────────────────────────
    if operaciones:
        status  = "ok"
        mensaje = f"{len(operaciones)} operaciones ({fuente_ok})"
    else:
        status  = "vacio"
        mensaje = "Sin datos en MarketScreener ni CNMV"
        fuente_ok = "ninguna"

    _guardar_operaciones(ticker, operaciones, status=status,
                         msg=mensaje, fuente_ok=fuente_ok)

    return {
        "operaciones": operaciones,
        "status":      status,
        "mensaje":     mensaje,
        "fuente":      fuente_ok,
    }


# ─────────────────────────────────────────────────────────────
# EVALUADOR
# ─────────────────────────────────────────────────────────────

def evaluar_insiders(operaciones: list) -> dict:
    """
    Evalúa insiders como señal de REFUERZO.
    Devuelve: fuerte / débil / nulo
    """
    if not operaciones:
        return {
            "señal":         "nulo",
            "etiqueta":      "⚪ Sin datos de insiders",
            "compras_60d":   0,
            "importe_60d":   0,
            "ultima_compra": None,
            "detalle":       [],
        }

    hace_60d = datetime.now() - timedelta(days=VENTANA_DIAS)
    compras_recientes = []

    for op in operaciones:
        if op.get("tipo") != "compra":
            continue
        try:
            fop = op.get("fecha_op") or op.get("fecha", "")
            if datetime.strptime(fop[:10], "%Y-%m-%d") >= hace_60d:
                compras_recientes.append(op)
        except Exception:
            pass

    importe_total = sum(float(op.get("importe", 0) or 0) for op in compras_recientes)
    n_compras     = len(compras_recientes)

    todas_compras = [op for op in operaciones if op.get("tipo") == "compra"]
    ultima_compra = None
    if todas_compras:
        fechas = [op.get("fecha_op") or op.get("fecha","") for op in todas_compras]
        fechas = [f for f in fechas if f]
        if fechas:
            ultima_compra = max(fechas)

    if importe_total >= UMBRAL_FUERTE:
        señal    = "fuerte"
        etiqueta = (f"🟢 Compra fuerte — "
                    f"{n_compras} insider{'s' if n_compras > 1 else ''}, "
                    f"{_fmt_eur(importe_total)} en 60 días")
    elif importe_total >= UMBRAL_DEBIL:
        señal    = "débil"
        etiqueta = f"🟡 Actividad leve — {_fmt_eur(importe_total)} en 60 días"
    else:
        señal    = "nulo"
        etiqueta = "⚪ Sin actividad insider relevante (últimos 60 días)"

    # Preparar detalle para UI
    detalle = []
    for op in compras_recientes[:5]:
        detalle.append({
            "fecha":   op.get("fecha_op") or op.get("fecha", ""),
            "insider": op.get("insider", "Directivo"),
            "cargo":   op.get("cargo", ""),
            "importe": float(op.get("importe", 0) or 0),
            "fuente":  op.get("fuente", ""),
        })

    return {
        "señal":         señal,
        "etiqueta":      etiqueta,
        "compras_60d":   n_compras,
        "importe_60d":   importe_total,
        "ultima_compra": ultima_compra,
        "detalle":       detalle,
    }


def get_insiders(ticker: str) -> dict:
    """Lee insiders desde DB. No hace scraping."""
    ticker = ticker.upper()
    if not ticker.endswith(".MC"):
        ticker += ".MC"
    datos      = _leer_operaciones(ticker)
    evaluacion = evaluar_insiders(datos["operaciones"])
    return {
        "evaluacion":  evaluacion,
        "last_scrape": datos["last_scrape"].isoformat() if datos["last_scrape"] else None,
        "caducado":    datos["caducado"],
        "status":      datos["status"],
        "fuente_ok":   datos["fuente_ok"],
        "n_ops_total": len(datos["operaciones"]),
    }


def get_tickers_con_datos() -> list:
    return list(set(list(MARKETSCREENER_SLUGS.keys()) + list(TICKER_ISIN.keys())))


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _parsear_fecha(texto: str) -> str | None:
    """Intenta parsear una fecha en múltiples formatos."""
    if not texto:
        return None
    formatos = [
        "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y",
        "%d-%m-%Y", "%b %d, %Y", "%d %b %Y",
        "%B %d, %Y", "%d %B %Y",
    ]
    texto = texto.strip()
    # Extraer solo la parte de fecha si hay más texto
    m = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", texto)
    if m:
        texto = m.group(0)
    m2 = re.search(r"\d{4}-\d{2}-\d{2}", texto)
    if m2:
        texto = m2.group(0)

    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return None


def _parsear_numero(texto: str) -> float:
    """Parsea un número con formato europeo o anglosajón."""
    if not texto:
        return 0.0
    try:
        # Eliminar símbolos de moneda y espacios
        limpio = re.sub(r"[€$£\s]", "", texto.strip())
        # Detectar formato: si hay coma como decimal (europeo)
        if re.match(r"^\d{1,3}(\.\d{3})*(,\d+)?$", limpio):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
        # Sufijos k/M
        if limpio.upper().endswith("K"):
            return float(limpio[:-1]) * 1_000
        if limpio.upper().endswith("M"):
            return float(limpio[:-1]) * 1_000_000
        return float(limpio)
    except Exception:
        return 0.0


def _fmt_eur(valor: float) -> str:
    if valor >= 1_000_000:
        return f"{valor/1_000_000:.1f}M€"
    if valor >= 1_000:
        return f"{valor/1_000:.0f}k€"
    return f"{valor:.0f}€"
