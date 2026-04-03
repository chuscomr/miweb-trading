"""
sentimiento_mercado.py
──────────────────────────────────────────────────────────────
Sentimiento REAL de mercado para empresas del IBEX/Continuo.

Componentes (sin indicadores técnicos):
  1. Short Interest      — % acciones vendidas en corto (bearish signal)
  2. Recomendación anal. — consenso analistas (1=compra fuerte..5=venta)
  3. Precio vs objetivo  — distancia al precio objetivo de analistas
  4. Tendencia precio    — variación 1m, 3m, 6m (voto real del mercado)
  5. Tendencia volumen   — ¿crece o decrece el interés?
  6. Sentimiento prensa  — tono RSS últimos titulares
"""

import time
import re
import requests
import feedparser
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# 1. DATOS DE MERCADO (yfinance via data_provider)
# ─────────────────────────────────────────────────────────────

def _get_info(ticker: str, cache=None) -> dict:
    """Obtiene info de yfinance con cache."""
    key = f"yf_info_{ticker}"
    if cache:
        cached = cache.get(key)
        if cached:
            return cached
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        if cache and info.get("regularMarketPrice"):
            cache.set(key, info, timeout=1800)
        return info
    except Exception as e:
        print(f"[sentimiento] yfinance error {ticker}: {e}")
        return {}


def _get_historial(ticker: str, cache=None):
    """Obtiene historial de precios (1 año) con cache."""
    key = f"yf_hist_{ticker}"
    if cache:
        cached = cache.get(key)
        if cached is not None:
            return cached
    try:
        from core.data_provider import get_df
        df = get_df(ticker, periodo="1y", cache=cache)
        return df
    except Exception as e:
        print(f"[sentimiento] historial error {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 2. COMPONENTES DEL SENTIMIENTO
# ─────────────────────────────────────────────────────────────

def _comp_short_interest(info: dict) -> dict:
    """Short Interest: % de float vendido en corto. Alto = bajista."""
    short_pct = info.get("shortPercentOfFloat")  # 0.0 a 1.0
    short_ratio = info.get("shortRatio")          # días para cubrir

    if short_pct is None:
        return {"score": 0, "peso": 0, "texto": "Sin datos de short interest",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    pct = short_pct * 100  # convertir a porcentaje

    if pct < 2:
        sc, emoji, color, txt = 25, "🐂", "#22c55e", f"Short muy bajo ({pct:.1f}%) — pocos bajistas"
    elif pct < 5:
        sc, emoji, color, txt = 15, "🐂", "#86efac", f"Short bajo ({pct:.1f}%) — mercado confiado"
    elif pct < 10:
        sc, emoji, color, txt = 0,  "➡️", "#f59e0b", f"Short moderado ({pct:.1f}%)"
    elif pct < 20:
        sc, emoji, color, txt = -15, "🐻", "#fca5a5", f"Short elevado ({pct:.1f}%) — presión bajista"
    else:
        sc, emoji, color, txt = -25, "🐻", "#ef4444", f"Short muy alto ({pct:.1f}%) — fuerte apuesta bajista"

    if short_ratio and short_ratio > 5:
        txt += f" · {short_ratio:.1f} días para cubrir"

    return {"score": sc, "peso": 20, "texto": txt,
            "valor": f"{pct:.1f}%", "emoji": emoji, "color": color}


def _comp_analistas_recomendacion(info: dict) -> dict:
    """Recomendación media de analistas. 1=Compra Fuerte, 5=Venta Fuerte."""
    rec = info.get("recommendationMean")
    n   = info.get("numberOfAnalystOpinions", 0)

    if rec is None:
        return {"score": 0, "peso": 0, "texto": "Sin cobertura de analistas",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    if rec <= 1.5:
        sc, emoji, color, lbl = 25, "🐂", "#22c55e", "Compra Fuerte"
    elif rec <= 2.2:
        sc, emoji, color, lbl = 18, "🐂", "#86efac", "Compra"
    elif rec <= 2.8:
        sc, emoji, color, lbl = 5,  "➡️", "#f59e0b", "Sobreponderar"
    elif rec <= 3.5:
        sc, emoji, color, lbl = -5, "➡️", "#f59e0b", "Neutral / Mantener"
    elif rec <= 4.2:
        sc, emoji, color, lbl = -18, "🐻", "#fca5a5", "Infraponderar"
    else:
        sc, emoji, color, lbl = -25, "🐻", "#ef4444", "Venta / Venta Fuerte"

    txt = f"{lbl} ({n} analistas)" if n else lbl

    return {"score": sc, "peso": 25, "texto": txt,
            "valor": f"{rec:.1f}/5", "emoji": emoji, "color": color}


def _comp_precio_vs_objetivo(info: dict) -> dict:
    """Distancia del precio actual al precio objetivo de analistas."""
    precio   = info.get("regularMarketPrice")
    objetivo = info.get("targetMeanPrice")
    t_high   = info.get("targetHighPrice")
    t_low    = info.get("targetLowPrice")

    if not precio or not objetivo:
        return {"score": 0, "peso": 0, "texto": "Sin precio objetivo disponible",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    upside = (objetivo - precio) / precio * 100

    if upside >= 30:
        sc, emoji, color = 25, "🐂", "#22c55e"
    elif upside >= 15:
        sc, emoji, color = 18, "🐂", "#86efac"
    elif upside >= 5:
        sc, emoji, color = 10, "🐂", "#86efac"
    elif upside >= -5:
        sc, emoji, color = 0,  "➡️", "#f59e0b"
    elif upside >= -15:
        sc, emoji, color = -10, "🐻", "#fca5a5"
    else:
        sc, emoji, color = -20, "🐻", "#ef4444"

    rango = f" · Rango: {t_low:.2f}€–{t_high:.2f}€" if t_high and t_low else ""
    txt = f"Objetivo: {objetivo:.2f}€ ({upside:+.1f}% potencial){rango}"

    return {"score": sc, "peso": 25, "texto": txt,
            "valor": f"{upside:+.1f}%", "emoji": emoji, "color": color}


def _comp_tendencia_precio(df) -> dict:
    """Tendencia del precio: retornos a 1m, 3m, 6m."""
    if df is None or len(df) < 20:
        return {"score": 0, "peso": 0, "texto": "Datos insuficientes",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    close = df["Close"]
    precio_actual = float(close.iloc[-1])

    def retorno(dias):
        if len(close) > dias:
            return (precio_actual - float(close.iloc[-dias])) / float(close.iloc[-dias]) * 100
        return None

    r1m  = retorno(21)
    r3m  = retorno(63)
    r6m  = retorno(126)

    score = 0
    partes = []

    for r, label, peso_r in [(r1m, "1m", 0.5), (r3m, "3m", 0.3), (r6m, "6m", 0.2)]:
        if r is not None:
            partes.append(f"{label}: {r:+.1f}%")
            if r >= 10:   score += 15 * peso_r
            elif r >= 5:  score += 10 * peso_r
            elif r >= 2:  score +=  5 * peso_r
            elif r >= -2: score +=  0
            elif r >= -5: score -=  5 * peso_r
            elif r >= -10:score -= 10 * peso_r
            else:         score -= 15 * peso_r

    score = round(score)
    emoji = "🐂" if score > 3 else "🐻" if score < -3 else "➡️"
    color = "#22c55e" if score > 3 else "#ef4444" if score < -3 else "#f59e0b"
    txt   = " · ".join(partes) if partes else "Sin datos"

    return {"score": score, "peso": 15, "texto": txt,
            "valor": f"{r1m:+.1f}%" if r1m else "—", "emoji": emoji, "color": color}


def _comp_tendencia_volumen(df) -> dict:
    """Tendencia del volumen: ¿crece o decrece el interés?"""
    if df is None or "Volume" not in df.columns or len(df) < 40:
        return {"score": 0, "peso": 0, "texto": "Datos insuficientes",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    vol = df["Volume"]
    close = df["Close"]

    vol_reciente = float(vol.iloc[-10:].mean())
    vol_anterior = float(vol.iloc[-40:-10].mean())

    if vol_anterior == 0:
        return {"score": 0, "peso": 0, "texto": "Sin datos de volumen",
                "valor": None, "emoji": "➡️", "color": "#94a3b8"}

    ratio = vol_reciente / vol_anterior
    precio_sube = float(close.iloc[-1]) > float(close.iloc[-10])

    if ratio >= 1.5 and precio_sube:
        sc, emoji, color, txt = 15, "🐂", "#22c55e", f"Volumen {ratio:.1f}x con subida — acumulación"
    elif ratio >= 1.5 and not precio_sube:
        sc, emoji, color, txt = -15, "🐻", "#ef4444", f"Volumen {ratio:.1f}x con caída — distribución"
    elif ratio >= 1.2 and precio_sube:
        sc, emoji, color, txt = 8, "🐂", "#86efac", f"Volumen creciente ({ratio:.1f}x) acompaña subida"
    elif ratio >= 1.2 and not precio_sube:
        sc, emoji, color, txt = -8, "🐻", "#fca5a5", f"Volumen creciente ({ratio:.1f}x) en caída"
    elif ratio < 0.7:
        sc, emoji, color, txt = -5, "➡️", "#f59e0b", f"Volumen decreciente ({ratio:.1f}x) — desinterés"
    else:
        sc, emoji, color, txt = 0, "➡️", "#f59e0b", f"Volumen estable ({ratio:.1f}x)"

    return {"score": sc, "peso": 10, "texto": txt,
            "valor": f"{ratio:.1f}x", "emoji": emoji, "color": color}


def _comp_noticias(ticker: str) -> dict:
    """Tono de noticias RSS recientes — usa fuentes financieras españolas especializadas."""
    _POS = {
        'récord':0.9,'record':0.9,'máximos':0.8,'supera':0.7,'bate':0.7,
        'sube':0.6,'rebota':0.6,'dispara':0.8,'avanza':0.6,'rally':0.7,
        'alcista':0.8,'beneficio':0.5,'ganancias':0.6,'crecimiento':0.6,
        'mejora':0.6,'acuerdo':0.4,'upgrade':0.8,'sobrepondera':0.7,
        'comprar':0.6,'dividendo':0.4,'recompra':0.5,'fuerte':0.4,
        'optimismo':0.6,'positivo':0.5,
    }
    _NEG = {
        'cae':-0.7,'baja':-0.5,'desplome':-0.9,'pierde':-0.7,
        'caida':-0.7,'bajista':-0.8,'minimos':-0.7,'retrocede':-0.5,
        'perdida':-0.8,'rebaja':-0.7,'downgrade':-0.8,'infrapondera':-0.7,
        'vender':-0.6,'presion':-0.4,'crisis':-0.9,'riesgo':-0.5,
        'alerta':-0.6,'multa':-0.7,'fraude':-0.9,'investigacion':-0.5,
        'quiebra':-1.0,'decepcion':-0.6,'recesion':-0.8,'debil':-0.5,
    }

    def score_texto(texto):
        t = texto.lower()
        for orig, rep in zip('áéíóúñ', 'aeioun'):
            t = t.replace(orig, rep)
        scores = []
        for p in re.findall(r'\b\w+\b', t):
            if p in _POS: scores.append(_POS[p])
            elif p in _NEG: scores.append(_NEG[p])
        if not scores: return 0.0
        top = sorted(scores, key=abs, reverse=True)[:5]
        return round(max(-1.0, min(1.0, sum(top)/len(top))), 3)

    # Fuentes RSS financieras españolas especializadas (mismas que noticias.py)
    FUENTES_RSS = [
        ("Expansión",       "https://www.expansion.com/rss/mercados/bolsa.xml"),
        ("Expansión Emp.",  "https://www.expansion.com/rss/empresas.xml"),
        ("Cinco Días",      "https://cincodias.elpais.com/rss/cincodias/mercados.xml"),
        ("El Economista",   "https://www.eleconomista.es/rss/rss-mercado-de-valores.php"),
        ("Bolsamanía",      "https://www.bolsamania.com/noticias/rss"),
        ("Invertia",        "https://www.invertia.com/es/rss"),
    ]

    # Nombre de empresa para buscar en titulares
    nombre_base = ticker.replace(".MC", "").upper()
    from core.universos import get_nombre
    try:
        nombre_largo = get_nombre(ticker).lower()
        palabras_clave = {nombre_base.lower(), nombre_largo.split()[0].lower()}
    except:
        palabras_clave = {nombre_base.lower()}

    noticias = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for fuente, url in FUENTES_RSS:
        try:
            resp = feedparser.parse(
                requests.get(url, headers=headers, timeout=6).content
            )
            for e in resp.entries[:20]:
                titulo = e.get('title', '').strip()
                if not titulo: continue
                titulo_lower = titulo.lower()
                # Filtrar solo noticias que mencionan la empresa
                if any(kw in titulo_lower for kw in palabras_clave):
                    noticias.append({
                        "titulo": titulo,
                        "fuente": fuente,
                        "url": e.get('link', '')
                    })
        except:
            continue

    if not noticias:
        return {"score": 0, "peso": 0,
                "texto": f"Sin noticias recientes de {ticker.replace('.MC','')} en prensa financiera española",
                "valor": None, "emoji": "➡️", "color": "#94a3b8", "noticias": []}

    scores = [score_texto(n["titulo"]) for n in noticias]
    media = sum(scores) / len(scores)
    sc_norm = round(media * 15)  # escala -15..+15

    emoji = "🐂" if sc_norm > 3 else "🐻" if sc_norm < -3 else "➡️"
    color = "#22c55e" if sc_norm > 3 else "#ef4444" if sc_norm < -3 else "#f59e0b"
    txt = f"{'Tono positivo' if sc_norm > 3 else 'Tono negativo' if sc_norm < -3 else 'Tono neutro'} · {len(noticias)} noticias en Expansión, Cinco Días, Bolsamanía..."

    # Devolver con url para enlazar
    return {"score": sc_norm, "peso": 5, "texto": txt,
            "valor": f"{sc_norm:+d}", "emoji": emoji, "color": color,
            "noticias": noticias[:3]}


# ─────────────────────────────────────────────────────────────
# 3. FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

NOMBRES_COMPONENTES = {
    "short_interest":     "📉 Short Interest",
    "analistas_rec":      "🎯 Recomendación Analistas",
    "precio_vs_objetivo": "📌 Precio vs Objetivo",
    "tendencia_precio":   "📈 Tendencia del Precio",
    "tendencia_volumen":  "📦 Tendencia del Volumen",
    "noticias":           "📰 Sentimiento Prensa",
}


def calcular_sentimiento_mercado(ticker: str, cache=None) -> dict:
    """
    Calcula el sentimiento REAL de mercado para un ticker.
    Score ponderado: -100 (muy bajista) a +100 (muy alcista).
    """
    resultado = {
        "ticker": ticker, "score": 0, "veredicto": "NEUTRO",
        "emoji": "➡️", "componentes": [], "error": None
    }

    try:
        info = _get_info(ticker, cache)
        df   = _get_historial(ticker, cache)

        componentes_raw = {
            "short_interest":     _comp_short_interest(info),
            "analistas_rec":      _comp_analistas_recomendacion(info),
            "precio_vs_objetivo": _comp_precio_vs_objetivo(info),
            "tendencia_precio":   _comp_tendencia_precio(df),
            "tendencia_volumen":  _comp_tendencia_volumen(df),
            "noticias":           _comp_noticias(ticker),
        }

        # Score ponderado
        score_total = 0
        peso_total  = 0
        componentes = []

        for key, comp in componentes_raw.items():
            peso = comp["peso"]
            if peso == 0:
                continue
            score_total += comp["score"] * (peso / 100)
            peso_total  += peso
            componentes.append({
                "nombre": NOMBRES_COMPONENTES[key],
                "score":  comp["score"],
                "peso":   peso,
                "texto":  comp["texto"],
                "valor":  comp["valor"],
                "emoji":  comp["emoji"],
                "color":  comp["color"],
                "noticias": comp.get("noticias", []),
            })

        # Normalizar si el peso total no es 100
        if peso_total > 0 and peso_total != 100:
            score_total = score_total * (100 / peso_total)

        score_norm = round(max(-100, min(100, score_total)))

        if score_norm >= 40:   veredicto, emoji = "ALCISTA",             "🐂"
        elif score_norm >= 15: veredicto, emoji = "LIGERAMENTE ALCISTA", "🐂"
        elif score_norm >= -15:veredicto, emoji = "NEUTRO",              "➡️"
        elif score_norm >= -40:veredicto, emoji = "LIGERAMENTE BAJISTA", "🐻"
        else:                  veredicto, emoji = "BAJISTA",             "🐻"

        precio = info.get("regularMarketPrice")
        nombre = info.get("longName") or info.get("shortName") or ticker

        resultado.update({
            "score":       score_norm,
            "veredicto":   veredicto,
            "emoji":       emoji,
            "precio":      round(precio, 2) if precio else None,
            "nombre":      nombre,
            "componentes": componentes,
            "n_analistas": info.get("numberOfAnalystOpinions"),
            "objetivo":    info.get("targetMeanPrice"),
            "rec_key":     info.get("recommendationKey"),
        })

    except Exception as e:
        import traceback
        resultado["error"] = str(e)
        resultado["traceback"] = traceback.format_exc()

    return resultado
