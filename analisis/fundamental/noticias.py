"""
analisis/fundamental/noticias.py
Recoge noticias financieras españolas desde RSS públicos.
"""

import feedparser
import time
from datetime import datetime, date, timedelta

FUENTES_RSS = [
    ("Expansión",        "https://www.expansion.com/rss/mercados/bolsa.xml"),
    ("Expansión Emp.",   "https://www.expansion.com/rss/empresas.xml"),
    ("Cinco Días",       "https://cincodias.elpais.com/rss/cincodias/mercados.xml"),
    ("Cinco Días Emp.",  "https://cincodias.elpais.com/rss/cincodias/empresas.xml"),
    ("El Economista",    "https://www.eleconomista.es/rss/rss-mercado-de-valores.php"),
    ("El Economista E.", "https://www.eleconomista.es/rss/rss-empresas-finanzas.php"),
    ("Bolsamanía",       "https://www.bolsamania.com/noticias/rss"),
    ("Capital Bolsa",    "https://www.bolsamania.com/capitalbolsa/feed/"),
    ("Invertia",         "https://www.invertia.com/es/rss"),
    ("El País Eco.",     "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
    ("El Mundo Eco.",    "https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml"),
    ("Benzinga ES",      "https://es.benzinga.com/feed/"),
    ("Bolsa Hoy",        "https://bolsa-hoy.com/feed/"),
]


def _parsear_fecha(entry):
    """Devuelve (fecha_str, timestamp) para poder ordenar."""
    try:
        ts = time.mktime(entry.published_parsed)
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M"), ts
    except Exception:
        return "", 0


def obtener_noticias_del_dia() -> list:
    """
    Recoge noticias de todos los medios RSS.
    Devuelve las de hoy y ayer, ordenadas por fecha descendente.
    """
    noticias = []
    seen = set()

    for fuente, url in FUENTES_RSS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:15]:
                titulo = entry.get("title", "").strip()
                link   = entry.get("link", "")
                if not titulo or titulo in seen:
                    continue
                seen.add(titulo)
                fecha_str, ts = _parsear_fecha(entry)
                noticias.append({
                    "titulo": titulo,
                    "fuente": fuente.replace(" E.", "").replace(" Emp.", ""),
                    "url":    link,
                    "fecha":  fecha_str,
                    "ts":     ts,
                })
                count += 1
            print(f"[noticias] {fuente}: {count} entradas")
        except Exception as e:
            print(f"[noticias] Error {fuente}: {e}")

    # Solo hoy y ayer
    ayer = date.today() - timedelta(days=1)
    noticias = [
        n for n in noticias
        if n["ts"] > 0 and datetime.fromtimestamp(n["ts"]).date() >= ayer
    ]

    noticias.sort(key=lambda x: x["ts"], reverse=True)

    for n in noticias:
        n.pop("ts", None)

    print(f"[noticias] Total tras filtro hoy/ayer: {len(noticias)}")
    return noticias


# Alias de compatibilidad
def obtener_noticias(ticker=None, tk=None) -> list:
    return obtener_noticias_del_dia()
