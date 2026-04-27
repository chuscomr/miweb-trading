"""
sentimiento_ibex.py
─────────────────────────────────────────────────────────────────
Análisis de sentimiento IBEX 35 — Mercado español.

Estrategia de fuentes:
  1. RSS españoles (principal): Expansión, Cinco Días, El Economista,
     Bolsamanía — filtrados por nombre de empresa
  2. FMP stock_news (complemento internacional): para grandes empresas
     con cobertura global (BBVA, SAN, ITX, IBE, REP, FER, IAG, MTS...)
  3. Google News en español (fallback)

Motor: Diccionario financiero español/inglés (sin TextBlob)
Coste: 0€
"""

import feedparser
import requests
import re
import os
import time
from datetime import datetime, timedelta, date
from urllib.parse import quote

# ─ Fuentes a ignorar (contenido publicitario / broker)
_FUENTES_EXCLUIDAS = {'xtb', 'xtb.com', 'xtb es', 'xtb.com/es'}

# ─ Sólo noticias de los últimos N días
_MAX_DIAS_NOTICIA = 7


def _es_reciente(entry) -> bool:
    """True si la noticia tiene menos de _MAX_DIAS_NOTICIA días."""
    try:
        ts = entry.get('published_parsed') or entry.get('updated_parsed')
        if ts:
            fecha = datetime(*ts[:6])
            return (datetime.now() - fecha).days <= _MAX_DIAS_NOTICIA
    except Exception:
        pass
    return True  # si no hay fecha la dejamos pasar


def _es_de_xtb(titulo: str, fuente: str = '') -> bool:
    """True si el título o fuente pertenece a XTB."""
    t = titulo.lower()
    f = fuente.lower()
    return 'xtb' in t or any(x in f for x in _FUENTES_EXCLUIDAS)

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

# ─────────────────────────────────────────────────────────────────
# DICCIONARIO FINANCIERO BÁSICO (POSITIVO / NEGATIVO)
# ─────────────────────────────────────────────────────────────────

_POS = {
    'récord': 0.9, 'record': 0.9, 'máximos': 0.8, 'historico': 0.7,
    'supera': 0.7, 'bate': 0.7, 'beats': 0.7, 'rebasa': 0.7,
    'sube': 0.6, 'suba': 0.6, 'rebota': 0.6, 'dispara': 0.8,
    'avanza': 0.6, 'rally': 0.7, 'alcista': 0.8, 'soars': 0.8,
    'surges': 0.8, 'rises': 0.6, 'climbs': 0.5, 'gains': 0.6,
    'beneficio': 0.5, 'profit': 0.5, 'ganancias': 0.6,
    'crecimiento': 0.6, 'growth': 0.6, 'mejora': 0.6, 'expansion': 0.5,
    'acuerdo': 0.4, 'contrato': 0.4, 'compra': 0.4, 'adquisicion': 0.5,
    'upgrade': 0.8, 'sobrepondera': 0.7, 'comprar': 0.6, 'buy': 0.6,
    'dividendo': 0.4, 'recompra': 0.5, 'buyback': 0.5,
    'fuerte': 0.4, 'strong': 0.4, 'solido': 0.5, 'solid': 0.5,
    'optimismo': 0.6, 'confianza': 0.5, 'positivo': 0.5,
}

_NEG = {
    'cae': -0.7, 'baja': -0.5, 'falls': -0.7, 'drops': -0.7,
    'desplome': -0.9, 'plunge': -0.9, 'pierde': -0.7, 'loses': -0.6,
    'caida': -0.7, 'decline': -0.6, 'bajista': -0.8, 'bearish': -0.8,
    'minimos': -0.7, 'retrocede': -0.5, 'recorta': -0.6, 'cut': -0.5,
    'perdida': -0.8, 'loss': -0.7, 'rebaja': -0.7, 'downgrade': -0.8,
    'infrapondera': -0.7, 'vender': -0.6, 'sell': -0.6,
    'presion': -0.4, 'tension': -0.4, 'preocupacion': -0.5,
    'deuda': -0.4, 'debt': -0.4, 'crisis': -0.9, 'riesgo': -0.5,
    'alerta': -0.6, 'warning': -0.6, 'multa': -0.7, 'sancion': -0.7,
    'fraude': -0.9, 'fraud': -0.9, 'investigacion': -0.5,
    'quiebra': -1.0, 'bankruptcy': -1.0, 'reestructuracion': -0.5,
    'incertidumbre': -0.4, 'negativo': -0.5, 'debil': -0.5, 'weak': -0.5,
    'decepcion': -0.6, 'decepciona': -0.7, 'recesion': -0.8,
}

def _score_texto(texto: str) -> float:
    t = texto.lower()
    t = (
        t.replace('á','a').replace('é','e').replace('í','i')
         .replace('ó','o').replace('ú','u').replace('ñ','n')
    )
    scores = []

    # Expresiones de varias palabras
    for frase, val in {**_POS, **_NEG}.items():
        if ' ' in frase and frase in t:
            scores.append(val)

    # Palabras sueltas
    for palabra in re.findall(r'\b\w+\b', t):
        if palabra in _POS:
            scores.append(_POS[palabra])
        elif palabra in _NEG:
            scores.append(_NEG[palabra])

    if not scores:
        return 0.0

    top = sorted(scores, key=abs, reverse=True)[:5]
    return round(max(-1.0, min(1.0, sum(top) / len(top))), 3)

# ─────────────────────────────────────────────────────────────────
# DESCARGA RSS (BING / GOOGLE) CON TÍTULO + URL
# ─────────────────────────────────────────────────────────────────

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
}

def _fetch_bing(query: str, max_items: int = 6) -> list:
    try:
        q = quote(query)
        url = f'https://www.bing.com/news/search?q={q}&format=rss&setlang=es-ES&setmkt=es-ES'
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            return []

        feed = feedparser.parse(resp.content)
        resultados = []

        for e in feed.entries:
            if len(resultados) >= max_items:
                break
            titulo = e.get('title', '')
            link   = e.get('link', '')
            if not titulo or not link:
                continue
            if _es_de_xtb(titulo):
                continue
            if not _es_reciente(e):
                continue
            titulo_limpio = re.sub(r'\s*-\s*[^-]{2,30}$', '', titulo).strip()
            resultados.append({"titulo": titulo_limpio, "url": link})

        return resultados

    except Exception as ex:
        print(f" ⚠ Bing error: {ex}")
        return []

def _fetch_google(query: str, max_items: int = 6) -> list:
    try:
        q = quote(query)
        url = f'https://news.google.com/rss/search?q={q}&hl=es&gl=ES&ceid=ES:es'
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            return []

        feed = feedparser.parse(resp.content)
        resultados = []

        for e in feed.entries:
            if len(resultados) >= max_items:
                break
            titulo = e.get('title', '')
            link   = e.get('link', '')
            fuente = e.get('source', {}).get('title', '') if hasattr(e.get('source',''), 'get') else ''
            if not titulo or not link:
                continue
            if _es_de_xtb(titulo, fuente):
                continue
            if not _es_reciente(e):
                continue
            titulo_limpio = re.sub(r'\s*-\s*[^-]{2,30}$', '', titulo).strip()
            resultados.append({"titulo": titulo_limpio, "url": link})

        return resultados

    except Exception as ex:
        print(f" ⚠ Google error: {ex}")
        return []

# ─────────────────────────────────────────────────────────────────
# RSS ESPAÑOLES — fuentes financieras en español
# ─────────────────────────────────────────────────────────────────

# RSS que sí devuelven contenido válido (verificados)
_RSS_ES = [
    "https://www.expansion.com/rss/mercados/bolsa.xml",
    "https://www.expansion.com/rss/empresas.xml",
    "https://cincodias.elpais.com/rss/cincodias/mercados.xml",
    "https://cincodias.elpais.com/rss/cincodias/empresas.xml",
    "https://www.elespanol.com/rss/invertia/mercados",
    "https://es.investing.com/rss/news_285.rss",
]

# Cache del RSS para no descargar 7 feeds por cada empresa
_rss_cache: dict = {}

def _cargar_rss_espanol() -> list:
    """Descarga todos los RSS españoles una sola vez y los guarda en caché."""
    if _rss_cache.get('titulares'):
        return _rss_cache['titulares']
    titulares = []
    for url in _RSS_ES:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=8)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for e in feed.entries[:30]:
                titulo = e.get('title', '').strip()
                link   = e.get('link', '')
                if not titulo:
                    continue
                if _es_de_xtb(titulo):
                    continue
                if not _es_reciente(e):
                    continue
                titulares.append({'titulo': titulo, 'url': link})
        except Exception:
            pass
    _rss_cache['titulares'] = titulares
    print(f"[RSS-ES] {len(titulares)} titulares cargados")
    return titulares


def _fetch_rss_espanol(nombre: str, ticker: str, max_items: int = 6) -> list:
    """Filtra del RSS español los titulares que mencionan la empresa."""
    todos = _cargar_rss_espanol()
    # Términos de búsqueda: nombre completo, nombre corto, ticker sin .MC
    terminos = [
        nombre.lower(),
        nombre.split()[0].lower(),  # primera palabra del nombre
        ticker.replace('.MC', '').lower(),
    ]
    resultados = []
    seen = set()
    for n in todos:
        t = n['titulo'].lower()
        if any(term in t for term in terminos) and n['titulo'] not in seen:
            seen.add(n['titulo'])
            resultados.append(n)
            if len(resultados) >= max_items:
                break
    return resultados


# Tickers con cobertura internacional relevante en FMP
_TICKERS_INTERNACIONALES = {
    'BBVA', 'SAN', 'ITX', 'IBE', 'REP', 'FER', 'IAG',
    'MTS', 'TEF', 'AMS', 'CLNX', 'ANA', 'GRF'
}


def _fetch_fmp(ticker: str, max_items: int = 6) -> list:
    """Noticias desde FMP stock_news API. Más fiables que RSS."""
    if not FMP_API_KEY:
        return []
    try:
        # FMP usa ticker con sufijo de mercado — convertir a formato FMP
        ticker_fmp = ticker.replace('.MC', '') + '.MC'
        url = (
            f"https://financialmodelingprep.com/api/v3/stock_news"
            f"?tickers={ticker_fmp}&limit={max_items}&apikey={FMP_API_KEY}"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []
        resultados = []
        for item in data[:max_items]:
            titulo = item.get('title', '').strip()
            url_noticia = item.get('url', '')
            if not titulo:
                continue
            resultados.append({
                "titulo": titulo,
                "url": url_noticia
            })
        return resultados
    except Exception as ex:
        print(f" ⚠ FMP news error ({ticker}): {ex}")
        return []


def _fetch_noticias(emp: dict) -> list:
    nombre  = emp['nombre']
    ticker  = emp['ticker']
    ticker_base = ticker.replace('.MC', '')
    titulos_vistos = set()
    noticias = []

    def _add(lista):
        for n in lista:
            t = n.get('titulo', '').strip()
            if t and t.lower() not in titulos_vistos:
                titulos_vistos.add(t.lower())
                noticias.append({'titulo': t, 'url': n.get('url', '')})

    # 1. Google News en español — fuente principal (cubre todas las empresas)
    _add(_fetch_google(f"{nombre} bolsa"))

    # 2. RSS españoles — complemento con medios especializados
    _add(_fetch_rss_espanol(nombre, ticker))

    # 3. FMP — noticias internacionales para grandes empresas
    if ticker_base in _TICKERS_INTERNACIONALES and FMP_API_KEY:
        _add(_fetch_fmp(ticker))

    # 4. Fallback si sigue sin noticias
    if not noticias:
        _add(_fetch_google(f"{nombre} acciones bolsa españa"))
    if not noticias:
        _add(_fetch_bing(f"{nombre} bolsa españa"))

    return [n for n in noticias if n.get('titulo') and n.get('url')]

# ─────────────────────────────────────────────────────────────────
# LISTA DE EMPRESAS IBEX 35
# ─────────────────────────────────────────────────────────────────

IBEX35_EMPRESAS = [
    {'ticker': 'ACX', 'nombre': 'Acerinox', 'sector': 'Materiales'},
    {'ticker': 'ACS', 'nombre': 'ACS', 'sector': 'Construcción'},
    {'ticker': 'AENA', 'nombre': 'Aena', 'sector': 'Infraestructuras'},
    {'ticker': 'AMS', 'nombre': 'Amadeus', 'sector': 'Tecnología'},
    {'ticker': 'ANA', 'nombre': 'Acciona', 'sector': 'Energía'},
    {'ticker': 'ANE', 'nombre': 'Atresmedia', 'sector': 'Media'},
    {'ticker': 'BBVA', 'nombre': 'BBVA', 'sector': 'Banca'},
    {'ticker': 'BKT', 'nombre': 'Bankinter', 'sector': 'Banca'},
    {'ticker': 'CABK', 'nombre': 'CaixaBank', 'sector': 'Banca'},
    {'ticker': 'CLNX', 'nombre': 'Cellnex', 'sector': 'Telecomunicaciones'},
    {'ticker': 'COL', 'nombre': 'Colonial', 'sector': 'Inmobiliario'},
    {'ticker': 'ELE', 'nombre': 'Endesa', 'sector': 'Energía'},
    {'ticker': 'ENG', 'nombre': 'Enagás', 'sector': 'Energía'},
    {'ticker': 'FCC', 'nombre': 'FCC', 'sector': 'Construcción'},
    {'ticker': 'FER', 'nombre': 'Ferrovial', 'sector': 'Construcción'},
    {'ticker': 'GRF', 'nombre': 'Grifols', 'sector': 'Salud'},
    {'ticker': 'IAG', 'nombre': 'IAG Iberia', 'sector': 'Aviación'},
    {'ticker': 'IBE', 'nombre': 'Iberdrola', 'sector': 'Energía'},
    {'ticker': 'IDR', 'nombre': 'Indra', 'sector': 'Tecnología'},
    {'ticker': 'ITX', 'nombre': 'Inditex', 'sector': 'Consumo'},
    {'ticker': 'LOG', 'nombre': 'Logista', 'sector': 'Distribución'},
    {'ticker': 'MAP', 'nombre': 'Mapfre', 'sector': 'Seguros'},
    {'ticker': 'MRL', 'nombre': 'Merlin Properties','sector': 'Inmobiliario'},
    {'ticker': 'MTS', 'nombre': 'ArcelorMittal', 'sector': 'Materiales'},
    {'ticker': 'NTGY', 'nombre': 'Naturgy', 'sector': 'Energía'},
    {'ticker': 'PUIG', 'nombre': 'Puig', 'sector': 'Consumo'},
    {'ticker': 'RED', 'nombre': 'Red Electrica', 'sector': 'Energía'},
    {'ticker': 'REP', 'nombre': 'Repsol', 'sector': 'Energía'},
    {'ticker': 'ROVI', 'nombre': 'Rovi', 'sector': 'Salud'},
    {'ticker': 'SAB', 'nombre': 'Sabadell', 'sector': 'Banca'},
    {'ticker': 'SAN', 'nombre': 'Santander', 'sector': 'Banca'},
    {'ticker': 'SCYR', 'nombre': 'Sacyr', 'sector': 'Construcción'},
    {'ticker': 'SLR', 'nombre': 'Solaria', 'sector': 'Energía'},
    {'ticker': 'TEF', 'nombre': 'Telefonica', 'sector': 'Telecomunicaciones'},
    {'ticker': 'UNI', 'nombre': 'Unicaja', 'sector': 'Banca'},
]

# ─────────────────────────────────────────────────────────────────
# UTILIDADES DE SCORE
# ─────────────────────────────────────────────────────────────────

def _trend(s): 
    return 'alcista' if s > 0.25 else 'bajista' if s < -0.25 else 'lateral'

def _alert(s, n):
    if s >= 0.65: 
        return '📈 MOMENTUM'
    if s <= -0.65: 
        return '⚡ RUPTURA'
    if s <= -0.45 and n >= 3: 
        return '⚠️ ALERTA'
    return None

# ─────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def analizar_sentimiento_ibex(tickers=None, delay=0.3):
    # Limpiar caché RSS para obtener noticias frescas
    _rss_cache.clear()

    empresas = IBEX35_EMPRESAS
    if tickers:
        empresas = [e for e in IBEX35_EMPRESAS if e['ticker'] in tickers]

    resultados = []
    total = len(empresas)
    print(f"📊 Analizando {total} empresas IBEX 35...")

    for i, emp in enumerate(empresas):
        print(f" [{i+1}/{total}] {emp['ticker']}")
        titulares = _fetch_noticias(emp)
        time.sleep(delay)

        if not titulares:
            resultados.append({
                'ticker': emp['ticker'],
                'nombre': emp['nombre'],
                'sector': emp['sector'],
                'score': 0.0,
                'señal': 'neutral',
                'trend': 'lateral',
                'alert': None,
                'noticias': [],
                'num_noticias': 0,
                'sin_datos': True,
            })
            continue

        # score usando solo el título
        scores = [_score_texto(n["titulo"]) for n in titulares]
        pesos = [1.0 / (j + 1) for j in range(len(scores))]
        score = round(
            max(-1.0, min(1.0, sum(s * p for s, p in zip(scores, pesos)) / sum(pesos))),
            3
        )

        resultados.append({
            'ticker': emp['ticker'],
            'nombre': emp['nombre'],
            'sector': emp['sector'],
            'score': score,
            'señal': 'bull' if score > 0.2 else 'bear' if score < -0.2 else 'neutral',
            'trend': _trend(score),
            'alert': _alert(score, len(titulares)),
            'noticias': titulares[:3],   # cada noticia = {"titulo","url"}
            'num_noticias': len(titulares),
            'sin_datos': False,
        })

    scores_v = [r['score'] for r in resultados if not r['sin_datos']]
    ibex_score = round(sum(scores_v) / len(scores_v), 3) if scores_v else 0.0
    alcistas = sum(1 for r in resultados if r['score'] > 0.2)
    bajistas = sum(1 for r in resultados if r['score'] < -0.2)
    neutras = len(resultados) - alcistas - bajistas

    if ibex_score > 0.3:
        resumen = f"Mercado con sesgo alcista · {alcistas} empresas positivas"
    elif ibex_score < -0.3:
        resumen = f"Mercado bajo presión · {bajistas} empresas negativas"
    else:
        resumen = f"Mercado mixto · {alcistas} alcistas · {bajistas} bajistas · {neutras} neutras"

    return {
        'ok': True,
        'empresas': sorted(resultados, key=lambda x: x['score'], reverse=True),
        'ibex_score': ibex_score,
        'ibex_summary': resumen,
        'alcistas': alcistas,
        'bajistas': bajistas,
        'neutras': neutras,
        'timestamp': datetime.now().strftime('%H:%M'),
        'total_analizadas': total,
    }
