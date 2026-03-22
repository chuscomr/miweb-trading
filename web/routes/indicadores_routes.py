# web/routes/indicadores_routes.py
# ══════════════════════════════════════════════════════════════
# API completa para indicadores — estructura idéntica al antiguo
# ══════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, current_app
from core.universos import normalizar_ticker, IBEX35, CONTINUO
from core.data_provider import get_df
from core.indicadores import (
    calcular_rsi, calcular_macd, calcular_atr, calcular_bollinger,
)
from analisis.tecnico.soportes_resistencias import detectar_soportes_resistencias
from analisis.tecnico.patrones_velas import detectar_patrones_velas

indicadores_bp = Blueprint(
    "indicadores", __name__,
    url_prefix="/indicadores",
    static_folder="../../static",
    static_url_path="/static",
)


def _get_cache():
    return current_app.config.get("CACHE_INSTANCE")


def _safe(val):
    if val is None:
        return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 4)
    return val


# ══════════════════════════════════════════════════════════════
# CÁLCULO DE INDICADORES
# ══════════════════════════════════════════════════════════════

def _calcular_obv(df):
    direction = np.sign(df["Close"].diff().fillna(0))
    return (direction * df["Volume"]).cumsum()


def _calcular_ema(close, periodo):
    return close.ewm(span=periodo, adjust=False).mean()


def _calcular_mfi(df, periodo=14):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = tp * df["Volume"]
    pos = mf.where(tp > tp.shift(1), 0)
    neg = mf.where(tp < tp.shift(1), 0)
    pos_sum = pos.rolling(periodo).sum()
    neg_sum = neg.rolling(periodo).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, np.nan)))
    return mfi


def _calcular_adx(df, periodo=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=periodo, adjust=False).mean()
    dm_pos = (high - high.shift()).clip(lower=0)
    dm_neg = (low.shift() - low).clip(lower=0)
    dm_pos = dm_pos.where(dm_pos > dm_neg, 0)
    dm_neg = dm_neg.where(dm_neg > dm_pos, 0)
    di_pos = 100 * dm_pos.ewm(span=periodo, adjust=False).mean() / atr
    di_neg = 100 * dm_neg.ewm(span=periodo, adjust=False).mean() / atr
    dx = 100 * (di_pos - di_neg).abs() / (di_pos + di_neg).replace(0, np.nan)
    adx = dx.ewm(span=periodo, adjust=False).mean()
    return adx, di_pos, di_neg


def _calcular_keltner(df, periodo=20, mult=2.0):
    ema = _calcular_ema(df["Close"], periodo)
    atr = calcular_atr(df, periodo)
    return ema + mult * atr, ema, ema - mult * atr


def _calcular_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


def _calcular_psar(df, af=0.02, max_af=0.2):
    high, low = df["High"].values, df["Low"].values
    n = len(high)
    psar = np.full(n, np.nan)
    trend = 1
    ep = low[0]
    af_cur = af
    psar[0] = high[0]
    for i in range(1, n):
        if trend == 1:
            psar[i] = psar[i-1] + af_cur * (ep - psar[i-1])
            psar[i] = min(psar[i], low[i-1], low[max(0, i-2)])
            if low[i] < psar[i]:
                trend = -1
                psar[i] = ep
                ep = low[i]
                af_cur = af
            else:
                if high[i] > ep:
                    ep = high[i]
                    af_cur = min(af_cur + af, max_af)
        else:
            psar[i] = psar[i-1] + af_cur * (ep - psar[i-1])
            psar[i] = max(psar[i], high[i-1], high[max(0, i-2)])
            if high[i] > psar[i]:
                trend = 1
                psar[i] = ep
                ep = high[i]
                af_cur = af
            else:
                if low[i] < ep:
                    ep = low[i]
                    af_cur = min(af_cur + af, max_af)
    return pd.Series(psar, index=df.index)


def _calcular_pivot_points(df):
    """Pivot Points clásicos basados en la última vela completa."""
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    H, L, C = float(last["High"]), float(last["Low"]), float(last["Close"])
    PP = (H + L + C) / 3
    R1 = 2 * PP - L
    S1 = 2 * PP - H
    R2 = PP + (H - L)
    S2 = PP - (H - L)
    R3 = H + 2 * (PP - L)
    S3 = L - 2 * (H - PP)
    return {k: round(v, 4) for k, v in {
        "PIVOT_PP": PP, "PIVOT_R1": R1, "PIVOT_R2": R2, "PIVOT_R3": R3,
        "PIVOT_S1": S1, "PIVOT_S2": S2, "PIVOT_S3": S3
    }.items()}


def _detectar_patrones_chartistas(df, n=200):
    """
    Detecta patrones chartistas clásicos en las últimas n velas.
    Los patrones en formación caducan si el 2º punto tiene más de 20 sesiones.
    """
    patrones = []
    sub = df.tail(n).copy()
    closes = sub["Close"].values
    highs  = sub["High"].values
    lows   = sub["Low"].values
    fechas = [str(f)[:10] for f in sub.index]  # fechas para el gráfico
    precio_actual = float(closes[-1])
    n_total = len(closes)
    CADUCIDAD_SESIONES = 20  # patrón en formación caduca si el 2º punto > 20 sesiones
    tol = 0.02  # 2% tolerancia máxima — los dos puntos deben ser muy similares

    def _maximos_locales(serie, orden=5):
        idx = []
        for i in range(orden, len(serie) - orden):
            if serie[i] == max(serie[i-orden:i+orden+1]):
                idx.append(i)
        return idx

    def _minimos_locales(serie, orden=5):
        idx = []
        for i in range(orden, len(serie) - orden):
            if serie[i] == min(serie[i-orden:i+orden+1]):
                idx.append(i)
        return idx

    maximos = _maximos_locales(highs)
    minimos = _minimos_locales(lows)

    # ── Doble Techo ──────────────────────────────────────────
    # Los dos techos deben: (1) estar al mismo nivel ±2%, (2) tener un valle
    # intermedio que baje al menos 3% desde los techos, (3) separación mínima
    if len(maximos) >= 2:
        m1, m2 = maximos[-2], maximos[-1]
        p1, p2 = highs[m1], highs[m2]
        nivel_medio = (p1 + p2) / 2
        if abs(p1 - p2) / nivel_medio <= tol and m2 > m1:
            valle = min(lows[m1:m2+1])  # usar lows para el valle real
            profundidad = (nivel_medio - valle) / nivel_medio
            separacion = m2 - m1
            # El valle debe bajar al menos 3% y haber separación mínima de 10 velas
            if profundidad >= 0.03 and separacion >= 10:
                neckline = round(float(valle), 2)
                objetivo = round(float(nivel_medio - (nivel_medio - valle)), 2)
                confirmado = precio_actual < neckline
                patrones.append({
                    "tipo": "doble_techo",
                    "direccion": "bajista",
                    "precio1": round(float(p1), 2),
                    "precio2": round(float(p2), 2),
                    "fecha1": fechas[m1],
                    "fecha2": fechas[m2],
                    "neckline": neckline,
                    "objetivo": objetivo,
                    "confirmado": confirmado,
                    "descripcion": f"Resistencia doble en {round(nivel_medio,2)}€ (±{round(abs(p1-p2)/nivel_medio*100,1)}%). {'Rotura confirmada.' if confirmado else 'Pendiente rotura de neckline.'}",
                })

    # ── Doble Suelo ──────────────────────────────────────────
    # Los dos suelos deben: (1) estar al mismo nivel ±2%, (2) tener un pico
    # intermedio que suba al menos 3% desde los suelos, (3) separación mínima
    if len(minimos) >= 2:
        m1, m2 = minimos[-2], minimos[-1]
        p1, p2 = lows[m1], lows[m2]
        nivel_medio = (p1 + p2) / 2
        if abs(p1 - p2) / nivel_medio <= tol and m2 > m1:
            pico = max(highs[m1:m2+1])  # usar highs para el pico real
            rebote = (pico - nivel_medio) / nivel_medio
            separacion = m2 - m1
            # El pico debe subir al menos 3% y haber separación mínima de 10 velas
            if rebote >= 0.03 and separacion >= 10:
                neckline = round(float(pico), 2)
                objetivo = round(float(neckline) + (neckline - nivel_medio), 2)
                confirmado = precio_actual > neckline
                patrones.append({
                    "tipo": "doble_suelo",
                    "direccion": "alcista",
                    "precio1": round(float(p1), 2),
                    "precio2": round(float(p2), 2),
                    "fecha1": fechas[m1],
                    "fecha2": fechas[m2],
                    "neckline": neckline,
                    "objetivo": objetivo,
                    "confirmado": confirmado,
                    "descripcion": f"Soporte doble en {round(nivel_medio,2)}€ (±{round(abs(p1-p2)/nivel_medio*100,1)}%). {'Rotura confirmada.' if confirmado else 'Pendiente rotura de neckline.'}",
                })

    # ── HCH (Hombro-Cabeza-Hombro) ───────────────────────────
    # Buscar entre todos los tríos posibles de máximos, no solo los últimos 3
    mejor_hch = None
    if len(maximos) >= 3:
        for i in range(len(maximos) - 2):
            h1, c, h2 = maximos[i], maximos[i+1], maximos[i+2]
            ph1, pc, ph2 = highs[h1], highs[c], highs[h2]
            # Cabeza más alta que ambos hombros y hombros similares ±8%
            if pc > ph1 and pc > ph2 and abs(ph1 - ph2) / max(ph1, ph2) <= tol * 4:
                # Separación mínima entre puntos
                if (c - h1) < 8 or (h2 - c) < 8:
                    continue
                v1 = min(closes[h1:c+1])
                v2 = min(closes[c:h2+1])
                neckline = round(float((v1 + v2) / 2), 2)
                objetivo = round(float(neckline) - (pc - neckline), 2)
                confirmado = precio_actual < neckline
                # Preferir el patrón más reciente y más pronunciado
                amplitud = pc - neckline
                if mejor_hch is None or h2 > mejor_hch['_h2'] or amplitud > mejor_hch['_amplitud']:
                    mejor_hch = {
                        'tipo': 'hch', 'direccion': 'bajista',
                        'hombro1': round(float(ph1), 2), 'cabeza': round(float(pc), 2),
                        'hombro2': round(float(ph2), 2),
                        'fecha1': fechas[h1], 'fecha_cabeza': fechas[c], 'fecha2': fechas[h2],
                        'neckline': neckline, 'objetivo': objetivo, 'confirmado': confirmado,
                        'descripcion': f"Patrón de techo. Cabeza en {round(pc,2)}€. {'Rotura confirmada.' if confirmado else 'Vigilar neckline ' + str(neckline) + '€.'}",
                        '_h2': h2, '_amplitud': amplitud
                    }
    if mejor_hch:
        mejor_hch.pop('_h2'); mejor_hch.pop('_amplitud')
        patrones.append(mejor_hch)

    # ── HCH Invertido ─────────────────────────────────────────
    mejor_hchi = None
    if len(minimos) >= 3:
        for i in range(len(minimos) - 2):
            h1, c, h2 = minimos[i], minimos[i+1], minimos[i+2]
            ph1, pc, ph2 = lows[h1], lows[c], lows[h2]
            # Cabeza más baja que ambos hombros y hombros similares ±8%
            if pc < ph1 and pc < ph2 and abs(ph1 - ph2) / max(abs(ph1), abs(ph2)) <= tol * 4:
                if (c - h1) < 8 or (h2 - c) < 8:
                    continue
                v1 = max(closes[h1:c+1])
                v2 = max(closes[c:h2+1])
                neckline = round(float((v1 + v2) / 2), 2)
                objetivo = round(float(neckline) + (neckline - pc), 2)
                confirmado = precio_actual > neckline
                amplitud = neckline - pc
                if mejor_hchi is None or h2 > mejor_hchi['_h2'] or amplitud > mejor_hchi['_amplitud']:
                    mejor_hchi = {
                        'tipo': 'hch_invertido', 'direccion': 'alcista',
                        'hombro1': round(float(ph1), 2), 'cabeza': round(float(pc), 2),
                        'hombro2': round(float(ph2), 2),
                        'fecha1': fechas[h1], 'fecha_cabeza': fechas[c], 'fecha2': fechas[h2],
                        'neckline': neckline, 'objetivo': objetivo, 'confirmado': confirmado,
                        'descripcion': f"Patrón de suelo. Cabeza en {round(pc,2)}€. {'Rotura confirmada.' if confirmado else 'Vigilar neckline ' + str(neckline) + '€.'}",
                        '_h2': h2, '_amplitud': amplitud
                    }
    if mejor_hchi:
        mejor_hchi.pop('_h2'); mejor_hchi.pop('_amplitud')
        patrones.append(mejor_hchi)

    # ── Triángulo Ascendente ─────────────────────────────────
    # Resistencia horizontal + soporte creciente
    if len(maximos) >= 3 and len(minimos) >= 3:
        # Resistencia: últimos 3 máximos similares
        ultimos_max = [highs[i] for i in maximos[-3:]]
        rango_max = max(ultimos_max) - min(ultimos_max)
        if rango_max / max(ultimos_max) <= tol:
            resistencia = round(float(np.mean(ultimos_max)), 2)
            # Soporte creciente: mínimos subiendo
            mins = [lows[i] for i in minimos[-3:]]
            if mins[-1] > mins[-2] > mins[0]:
                objetivo = round(resistencia + (resistencia - mins[0]), 2)
                confirmado = precio_actual > resistencia
                patrones.append({
                    "tipo": "triangulo_ascendente",
                    "direccion": "alcista",
                    "resistencia": resistencia,
                    "soporte_inicio": round(float(mins[0]), 2),
                    "soporte_fin": round(float(mins[-1]), 2),
                    "objetivo": objetivo,
                    "confirmado": confirmado,
                    "descripcion": f"Resistencia en {resistencia}€ con soporte ascendente. {'Rotura confirmada.' if confirmado else 'Vigilar rotura de ' + str(resistencia) + '€.'}",
                })

    # ── Triángulo Descendente ─────────────────────────────────
    if len(minimos) >= 3 and len(maximos) >= 3:
        ultimos_min = [lows[i] for i in minimos[-3:]]
        rango_min = max(ultimos_min) - min(ultimos_min)
        if rango_min / max(ultimos_min) <= tol:
            soporte = round(float(np.mean(ultimos_min)), 2)
            maxs = [highs[i] for i in maximos[-3:]]
            if maxs[-1] < maxs[-2] < maxs[0]:
                objetivo = round(soporte - (maxs[0] - soporte), 2)
                confirmado = precio_actual < soporte
                patrones.append({
                    "tipo": "triangulo_descendente",
                    "direccion": "bajista",
                    "soporte": soporte,
                    "resist_inicio": round(float(maxs[0]), 2),
                    "resist_fin": round(float(maxs[-1]), 2),
                    "objetivo": objetivo,
                    "confirmado": confirmado,
                    "descripcion": f"Soporte en {soporte}€ con resistencia descendente. {'Rotura confirmada.' if confirmado else 'Vigilar pérdida de ' + str(soporte) + '€.'}",
                })

    # ── Triángulo Simétrico ───────────────────────────────────
    if len(maximos) >= 3 and len(minimos) >= 3:
        maxs = [highs[i] for i in maximos[-3:]]
        mins = [lows[i] for i in minimos[-3:]]
        # Máximos bajando y mínimos subiendo
        if maxs[-1] < maxs[0] and mins[-1] > mins[0]:
            vertice = round(float((maxs[-1] + mins[-1]) / 2), 2)
            amplitud = round(float(maxs[0] - mins[0]), 2)
            dir_actual = "alcista" if precio_actual > vertice else "bajista"
            objetivo = round(vertice + amplitud if dir_actual == "alcista" else vertice - amplitud, 2)
            confirmado = precio_actual > maxs[-1] or precio_actual < mins[-1]
            patrones.append({
                "tipo": "triangulo_simetrico",
                "direccion": dir_actual,
                "resistencia": round(float(maxs[-1]), 2),
                "soporte": round(float(mins[-1]), 2),
                "vertice": vertice,
                "objetivo": objetivo,
                "confirmado": confirmado,
                "descripcion": f"Compresión entre {round(float(mins[-1]),2)}€ y {round(float(maxs[-1]),2)}€. {'Rotura al ' + dir_actual + '.' if confirmado else 'Pendiente de definir dirección.'}",
            })

    # ── Bandera Alcista ───────────────────────────────────────
    # Subida fuerte (asta) + consolidación lateral/bajista corta
    if len(closes) >= 20:
        # Buscar asta: subida >5% en las últimas 5-15 velas antes de la consolidación
        for asta_len in range(5, 15):
            if len(closes) < asta_len + 10:
                break
            inicio_asta = len(closes) - asta_len - 10
            fin_asta = len(closes) - 10
            if inicio_asta < 0:
                break
            subida = (closes[fin_asta] - closes[inicio_asta]) / closes[inicio_asta] * 100
            if subida >= 5:
                # Consolidación: últimas 10 velas con rango < 3%
                consol = closes[fin_asta:]
                rango_consol = (max(consol) - min(consol)) / min(consol) * 100
                if rango_consol <= 4:
                    objetivo = round(float(precio_actual + (closes[fin_asta] - closes[inicio_asta])), 2)
                    confirmado = precio_actual > max(consol[:-1]) if len(consol) > 1 else False
                    patrones.append({
                        "tipo": "bandera_alcista",
                        "direccion": "alcista",
                        "inicio_asta": round(float(closes[inicio_asta]), 2),
                        "fin_asta": round(float(closes[fin_asta]), 2),
                        "subida_pct": round(subida, 1),
                        "semanas_consolidacion": len(consol),
                        "objetivo": objetivo,
                        "confirmado": confirmado,
                        "descripcion": f"Asta alcista +{round(subida,1)}% seguida de pausa. {'Rotura al alza confirmada.' if confirmado else 'Esperando rotura de la consolidación.'}",
                    })
                break

    # ── Bandera Bajista ───────────────────────────────────────
    if len(closes) >= 20:
        for asta_len in range(5, 15):
            if len(closes) < asta_len + 10:
                break
            inicio_asta = len(closes) - asta_len - 10
            fin_asta = len(closes) - 10
            if inicio_asta < 0:
                break
            caida = (closes[fin_asta] - closes[inicio_asta]) / closes[inicio_asta] * 100
            if caida <= -5:
                consol = closes[fin_asta:]
                rango_consol = (max(consol) - min(consol)) / min(consol) * 100
                if rango_consol <= 4:
                    # Proyectar amplitud del asta HACIA ABAJO desde precio actual
                    amplitud_asta = closes[inicio_asta] - closes[fin_asta]  # positivo
                    objetivo = round(float(precio_actual - amplitud_asta), 2)
                    confirmado = precio_actual < min(consol[:-1]) if len(consol) > 1 else False
                    patrones.append({
                        "tipo": "bandera_bajista",
                        "direccion": "bajista",
                        "inicio_asta": round(float(closes[inicio_asta]), 2),
                        "fin_asta": round(float(closes[fin_asta]), 2),
                        "caida_pct": round(caida, 1),
                        "semanas_consolidacion": len(consol),
                        "objetivo": objetivo,
                        "confirmado": confirmado,
                        "descripcion": f"Asta bajista {round(caida,1)}% seguida de pausa. {'Rotura a la baja confirmada.' if confirmado else 'Esperando rotura de la consolidación.'}",
                    })
                break

    # ── Filtrar patrones caducados ────────────────────────────
    from datetime import date, datetime
    hoy = date.today()
    patrones_validos = []
    for pat in patrones:
        if pat.get("confirmado"):
            patrones_validos.append(pat)
        else:
            # Fecha más reciente del patrón
            f2 = pat.get("fecha2") or pat.get("fecha_cabeza") or ""
            if f2:
                try:
                    fecha_patron = datetime.strptime(f2[:10], "%Y-%m-%d").date()
                    dias = (hoy - fecha_patron).days
                    # Aprox 20 sesiones = 28 días naturales
                    if dias <= 28:
                        pat["sesiones_formacion"] = dias
                        patrones_validos.append(pat)
                    # else: descartado por antigüedad
                except Exception:
                    patrones_validos.append(pat)
            else:
                patrones_validos.append(pat)

    return patrones_validos


def _detectar_contexto_trading(df, soportes, resistencias, patrones_velas) -> dict:
    """
    Detecta si el precio está en un setup de Breakout, Pullback o Reversión.
    Devuelve un dict con tipo_setup, madurez, descripcion y frases de contexto.
    """
    try:
        import math
        from core.indicadores import calcular_rsi, calcular_atr

        close  = df["Close"]
        precio = float(close.iloc[-1])

        # ── Indicadores base ──────────────────────────────────
        mm20_s = close.rolling(20).mean()
        mm50_s = close.rolling(50).mean()
        mm200_s= close.rolling(200).mean()
        rsi_s  = calcular_rsi(close, 14)
        vol_s  = df["Volume"]

        mm20  = float(mm20_s.iloc[-1])  if not mm20_s.isna().iloc[-1]  else None
        mm50  = float(mm50_s.iloc[-1])  if not mm50_s.isna().iloc[-1]  else None
        mm200 = float(mm200_s.iloc[-1]) if not mm200_s.isna().iloc[-1] else None
        rsi   = float(rsi_s.dropna().iloc[-1]) if not rsi_s.dropna().empty else None

        max_52  = float(close.tail(252).max())
        dist_max_pct = ((precio - max_52) / max_52) * 100  # negativo = por debajo

        # Retroceso desde máximo reciente 60 días
        max_60  = float(close.tail(60).max())
        retroceso_pct = ((max_60 - precio) / max_60) * 100

        # Volumen: ¿creciente o decreciente en los últimos 5 días?
        vol_media20 = float(vol_s.rolling(20).mean().iloc[-1])
        vol_5d      = float(vol_s.tail(5).mean())
        vol_ratio   = vol_5d / vol_media20 if vol_media20 > 0 else 1.0
        vol_decreciente = vol_s.tail(5).is_monotonic_decreasing

        # Consolidación: rango de las últimas 10 velas
        rango_10 = (float(df["High"].tail(10).max()) - float(df["Low"].tail(10).min()))
        rango_10_pct = rango_10 / precio * 100

        # Pendiente MM20
        mm20_serie = mm20_s.dropna()
        mm20_pendiente = (float(mm20_serie.iloc[-1]) >= float(mm20_serie.iloc[-4])
                         if len(mm20_serie) >= 4 else True)

        # Patrón de vela de giro alcista en últimas 5 velas
        PATRONES_GIRO = {"Martillo","Envolvente Alcista","Estrella de Mañana",
                         "Piercing Line","Harami Alcista"}
        vela_giro = any(p.get("tipo") == "alcista" and p.get("nombre") in PATRONES_GIRO
                       for p in patrones_velas)

        # Soporte más cercano por debajo
        sop_cercano = None
        for s in sorted(soportes, key=lambda x: abs(x["precio"] - precio)):
            if s["precio"] < precio:
                sop_cercano = s
                break

        # Resistencia más cercana por encima
        res_cercana = None
        for r in sorted(resistencias, key=lambda x: abs(x["precio"] - precio)):
            if r["precio"] > precio:
                res_cercana = r
                break

        dist_soporte   = ((precio - sop_cercano["precio"]) / precio * 100) if sop_cercano else None
        dist_resistencia = ((res_cercana["precio"] - precio) / precio * 100) if res_cercana else None

        # ── SCORING DE SETUPS ─────────────────────────────────
        score_breakout  = 0
        score_pullback  = 0
        score_reversion = 0
        frases = []

        # ─ BREAKOUT ─
        if dist_max_pct >= -3.0:
            score_breakout += 2
            frases.append(f"Precio cerca del máximo anual ({dist_max_pct:.1f}%)")
        if rango_10_pct <= 5.0:
            score_breakout += 2
            frases.append(f"Consolidación estrecha ({rango_10_pct:.1f}% rango 10d)")
        if vol_decreciente:
            score_breakout += 1
            frases.append("Volumen decreciente en consolidación (VCP)")
        if rsi and 55 <= rsi <= 70:
            score_breakout += 1
            frases.append(f"RSI en zona de momentum ({rsi:.0f})")
        if mm20 and mm50 and mm20 > mm50:
            score_breakout += 1
            frases.append("MM20 > MM50 — estructura alcista")
        if res_cercana and dist_resistencia and dist_resistencia <= 3.0:
            score_breakout += 2
            frases.append(f"Resistencia a {dist_resistencia:.1f}% — zona clave próxima")

        # ─ PULLBACK ─
        if 5.0 <= retroceso_pct <= 12.0:
            score_pullback += 2
            frases.append(f"Retroceso saludable {retroceso_pct:.1f}% desde máximos")
        if rsi and rsi <= 50:
            score_pullback += 2
            frases.append(f"RSI en sobreventa moderada ({rsi:.0f})")
        if mm50 and precio > mm50:
            score_pullback += 1
            frases.append(f"Por encima de MM50 ({mm50:.2f}€) — tendencia intacta")
        if mm20_pendiente:
            score_pullback += 1
            frases.append("MM20 con pendiente positiva")
        if sop_cercano and dist_soporte and 2.0 <= dist_soporte <= 8.0:
            score_pullback += 2
            frases.append(f"Soporte cercano a {dist_soporte:.1f}% — zona de rebote")
        if vela_giro:
            score_pullback += 2
            frases.append("Patrón de vela de giro alcista detectado")

        # ─ REVERSIÓN ─
        if retroceso_pct > 15.0:
            score_reversion += 2
            frases.append(f"⚠️ Caída del {retroceso_pct:.1f}% — posible cambio de tendencia")
        if mm50 and precio < mm50:
            score_reversion += 2
            frases.append(f"⚠️ Por debajo de MM50 ({mm50:.2f}€) — estructura deteriorada")
        if rsi and rsi < 30:
            score_reversion += 1
            frases.append(f"⚠️ RSI en sobreventa extrema ({rsi:.0f})")
        if vol_ratio > 1.5:
            score_reversion += 1
            frases.append(f"⚠️ Volumen de venta elevado ({vol_ratio:.1f}x media)")
        if mm200 and precio < mm200:
            score_reversion += 2
            frases.append(f"⚠️ Por debajo de MM200 — tendencia bajista macro")

        # ── DECISIÓN ─────────────────────────────────────────
        max_score = max(score_breakout, score_pullback, score_reversion)

        if max_score == 0:
            tipo    = "neutral"
            madurez = "sin_setup"
            titulo  = "Sin setup claro"
            color   = "#64748b"
        elif score_reversion >= 4 and score_reversion >= score_pullback:
            tipo    = "reversion"
            madurez = "alerta" if score_reversion >= 5 else "formandose"
            titulo  = "Posible reversión bajista"
            color   = "#ef4444"
        elif score_breakout > score_pullback:
            if score_breakout >= 7:
                madurez, titulo = "listo",       "Breakout casi listo"
                color = "#22c55e"
            elif score_breakout >= 4:
                madurez, titulo = "formandose",  "Breakout en formación"
                color = "#f59e0b"
            else:
                madurez, titulo = "incipiente",  "Posible breakout"
                color = "#94a3b8"
            tipo = "breakout"
        else:
            if score_pullback >= 7:
                madurez, titulo = "listo", "Pullback en vigilancia"
                color = "#3b82f6"
            elif score_pullback >= 4:
                madurez, titulo = "formandose", "Pullback en desarrollo"
                color = "#f59e0b"
            else:
                madurez, titulo = "incipiente", "Posible pullback"
                color = "#94a3b8"
            tipo = "pullback"

        # Limitar frases a las más relevantes (máx 5)
        frases_unicas = list(dict.fromkeys(frases))[:5]

        return {
            "tipo":         tipo,
            "titulo":       titulo,
            "madurez":      madurez,
            "color":        color,
            "score":        max_score,
            "frases":       frases_unicas,
            "scores": {
                "breakout":  score_breakout,
                "pullback":  score_pullback,
                "reversion": score_reversion,
            }
        }

    except Exception as e:
        return {"tipo": "neutral", "titulo": "Sin datos suficientes",
                "madurez": "sin_setup", "color": "#64748b",
                "frases": [], "scores": {}}


def _calcular_fibonacci(df, n=100):
    """Fibonacci sobre el swing más reciente."""
    sub = df.tail(n)
    max_idx = sub["High"].idxmax()
    min_idx = sub["Low"].idxmin()
    H = float(sub["High"].max())
    L = float(sub["Low"].min())
    es_alcista = min_idx < max_idx
    inicio = L if es_alcista else H
    fin    = H if es_alcista else L
    swing  = H - L
    ratios = [
        ("0%",    0.0,   "clave"),
        ("23.6%", 0.236, "menor"),
        ("38.2%", 0.382, "clave"),
        ("50%",   0.5,   "clave"),
        ("61.8%", 0.618, "clave"),
        ("78.6%", 0.786, "menor"),
        ("100%",  1.0,   "clave"),
    ]
    precio_actual = float(df["Close"].iloc[-1])
    niveles = []
    for nombre, ratio, imp in ratios:
        precio = H - ratio * swing if es_alcista else L + ratio * swing
        cerca = abs(precio - precio_actual) / precio_actual < 0.02
        distancia = round((precio - precio_actual) / precio_actual * 100, 1)
        niveles.append({"nombre": nombre, "precio": round(precio, 4),
                        "importancia": imp, "cerca": cerca,
                        "distancia_pct": distancia})
    return {
        "direccion":   "alcista" if es_alcista else "bajista",
        "punto_inicio": round(inicio, 4),
        "punto_final":  round(fin, 4),
        "swing_pct":    round(swing / L * 100, 1),
        "niveles":      niveles,
    }


# ══════════════════════════════════════════════════════════════
# DIVERGENCIAS
# ══════════════════════════════════════════════════════════════

def _calcular_divergencias(df, inds):
    divergencias = []
    close = df["Close"]
    fechas = df.index

    def _div(ind_serie, nombre):
        n = min(60, len(close))
        p = close.iloc[-n:].values
        i = ind_serie.iloc[-n:].values
        f = fechas[-n:]
        maximos_p = [k for k in range(1, n-1) if p[k] > p[k-1] and p[k] > p[k+1]]
        minimos_p = [k for k in range(1, n-1) if p[k] < p[k-1] and p[k] < p[k+1]]
        if len(maximos_p) >= 2:
            m1, m2 = maximos_p[-2], maximos_p[-1]
            if (p[m2] > p[m1] * 1.005 and not np.isnan(i[m1]) and not np.isnan(i[m2])
                    and i[m2] < i[m1] * 0.995):
                divergencias.append({
                    "indicador": nombre, "tipo": "bajista", "señal": "VENTA",
                    "descripcion": f"Precio ↑{p[m1]:.2f}→{p[m2]:.2f}, {nombre} ↓{i[m1]:.2f}→{i[m2]:.2f}",
                    "fecha1": str(f[m1])[:10], "fecha2": str(f[m2])[:10],
                    "precio1": round(float(p[m1]), 4), "precio2": round(float(p[m2]), 4),
                    "ind1":    round(float(i[m1]), 4), "ind2":    round(float(i[m2]), 4),
                })
        if len(minimos_p) >= 2:
            m1, m2 = minimos_p[-2], minimos_p[-1]
            if (p[m2] < p[m1] * 0.995 and not np.isnan(i[m1]) and not np.isnan(i[m2])
                    and i[m2] > i[m1] * 1.005):
                divergencias.append({
                    "indicador": nombre, "tipo": "alcista", "señal": "COMPRA",
                    "descripcion": f"Precio ↓{p[m1]:.2f}→{p[m2]:.2f}, {nombre} ↑{i[m1]:.2f}→{i[m2]:.2f}",
                    "fecha1": str(f[m1])[:10], "fecha2": str(f[m2])[:10],
                    "precio1": round(float(p[m1]), 4), "precio2": round(float(p[m2]), 4),
                    "ind1":    round(float(i[m1]), 4), "ind2":    round(float(i[m2]), 4),
                })

    try:
        if "RSI" in inds and "RSI" in df.columns:
            _div(df["RSI"], "RSI")
        if "MACD" in inds and "MACD" in df.columns:
            _div(df["MACD"], "MACD")
        if "OBV" in inds and "OBV" in df.columns:
            _div(df["OBV"], "OBV")
    except Exception:
        pass
    return divergencias


# ══════════════════════════════════════════════════════════════
# RESUMEN TÉCNICO
# ══════════════════════════════════════════════════════════════

def _calcular_resumen_tecnico(df, inds):
    """
    Resumen técnico idéntico al antiguo:
    - Pesos calibrados por indicador
    - Medias móviles siempre evaluadas (aunque no estén en inds)
    - Estocástico calculado internamente
    - Volumen como señal de media
    - Texto 'Faltan X pts para ...'
    """
    close  = df["Close"]
    precio = float(close.iloc[-1])
    señales_ind = {"compra": [], "venta": [], "neutral": []}
    señales_mm  = {"compra": [], "venta": [], "neutral": []}

    def _s(nombre, peso=1.0):
        return {"indicador": nombre, "peso": round(peso, 1)}

    # ── RSI (peso 0.5 neutral, 1.0 extremo) ──────────────────
    if "RSI" in df.columns:
        v = float(df["RSI"].iloc[-1])
        if not np.isnan(v):
            if v < 30:   señales_ind["compra"].append(_s("RSI", 1.0))
            elif v > 70: señales_ind["venta"].append(_s("RSI", 1.0))
            else:        señales_ind["neutral"].append(_s("RSI : Zona neutral", 0.2))

    # ── MACD (peso 0.5 cruce, basado en distancia) ───────────
    if "MACD" in df.columns and "MACD_SEÑAL" in df.columns:
        m = float(df["MACD"].iloc[-1])
        s = float(df["MACD_SEÑAL"].iloc[-1])
        if not np.isnan(m) and not np.isnan(s):
            if m > s:   señales_ind["compra"].append(_s("MACD : Cruce alcista", 0.5))
            elif m < s: señales_ind["venta"].append(_s("MACD : Cruce bajista", 0.5))
            else:       señales_ind["neutral"].append(_s("MACD", 0.3))

    # ── OBV ──────────────────────────────────────────────────
    if "OBV" in df.columns:
        obv = df["OBV"].tail(10)
        if len(obv) >= 2:
            if obv.iloc[-1] > obv.iloc[0]:   señales_ind["compra"].append(_s("OBV", 0.8))
            elif obv.iloc[-1] < obv.iloc[0]: señales_ind["venta"].append(_s("OBV", 0.8))
            else:                             señales_ind["neutral"].append(_s("OBV", 0.3))

    # ── ADX/DI (peso 0.6) ────────────────────────────────────
    if "ADX" in df.columns:
        adx = float(df["ADX"].iloc[-1])
        if not np.isnan(adx):
            if adx > 25:
                # DI+ vs DI- para dirección
                if "DI_POS" in df.columns and "DI_NEG" in df.columns:
                    di_pos = float(df["DI_POS"].iloc[-1])
                    di_neg = float(df["DI_NEG"].iloc[-1])
                    if di_pos > di_neg:
                        señales_ind["compra"].append(_s("DI± : DI+ dominante", 0.6))
                    else:
                        señales_ind["venta"].append(_s("DI± : DI- dominante", 0.6))
                else:
                    señales_ind["neutral"].append(_s("ADX", 0.3))
            else:
                señales_ind["neutral"].append(_s("ADX", 0.3))

    # ── MFI ──────────────────────────────────────────────────
    if "MFI" in df.columns:
        v = float(df["MFI"].iloc[-1])
        if not np.isnan(v):
            if v < 20:   señales_ind["compra"].append(_s("MFI", 1.0))
            elif v > 80: señales_ind["venta"].append(_s("MFI", 1.0))
            else:        señales_ind["neutral"].append(_s("MFI", 0.3))

    # ── Bollinger Media (precio vs BB media) ─────────────────
    if "BB_MEDIO" not in df.columns:
        try:
            bb_tmp = calcular_bollinger(df["Close"])
            df["BB_MEDIO"]    = pd.Series(bb_tmp["media"].values,    index=df.index).bfill()
            df["BB_SUPERIOR"] = pd.Series(bb_tmp["superior"].values, index=df.index).bfill()
            df["BB_INFERIOR"] = pd.Series(bb_tmp["inferior"].values, index=df.index).bfill()
        except Exception:
            pass
    if "BB_MEDIO" in df.columns:
        bb_mid = float(df["BB_MEDIO"].iloc[-1])
        bb_sup = float(df["BB_SUPERIOR"].iloc[-1]) if "BB_SUPERIOR" in df.columns else None
        bb_inf = float(df["BB_INFERIOR"].iloc[-1]) if "BB_INFERIOR" in df.columns else None
        if not np.isnan(bb_mid):
            if precio > bb_mid:
                señales_ind["compra"].append(_s("BB : Precio sobre MM20 (media Bollinger)", 0.4))
            else:
                señales_ind["venta"].append(_s("BB : Precio bajo MM20 (media Bollinger)", 0.4))
            if bb_sup and bb_inf and not np.isnan(bb_sup) and not np.isnan(bb_inf):
                ancho = bb_sup - bb_inf
                if ancho > 0:
                    pos = (precio - bb_inf) / ancho
                    if pos > 0.85:
                        señales_ind["venta"].append(_s("BB : Precio en banda superior (sobreextensión)", 0.3))
                    elif pos < 0.15:
                        señales_ind["compra"].append(_s("BB : Precio en banda inferior (sobreextensión)", 0.3))

    # ── Estocástico (siempre calculado) ──────────────────────
    try:
        high14 = df["High"].rolling(14).max()
        low14  = df["Low"].rolling(14).min()
        k_pct  = 100 * (close - low14) / (high14 - low14).replace(0, np.nan)
        k_val  = float(k_pct.iloc[-1]) if not np.isnan(k_pct.iloc[-1]) else 50.0
        if k_val < 20:   señales_ind["compra"].append(_s("Estocástico : Sobreventa", 0.5))
        elif k_val > 80: señales_ind["venta"].append(_s("Estocástico : Sobrecompra", 0.5))
        else:            señales_ind["neutral"].append(_s("Estocástico : Zona media", 0.2))
    except Exception:
        pass

    # ── Medias móviles — siempre evaluadas ───────────────────
    mm200_ok     = False
    mms_alcistas = 0
    mms_bajistas = 0
    mms_bajo     = []   # nombres de MMs por debajo del precio
    mms_sobre    = []   # nombres de MMs por encima del precio
    for mm_col, periodo in [("MM20",20),("MM50",50),("MM200",200)]:
        if mm_col not in df.columns:
            try:
                df[mm_col] = pd.Series(
                    close.rolling(periodo).mean().bfill().values,
                    index=df.index
                )
            except Exception:
                continue
        v = float(df[mm_col].iloc[-1])
        if not np.isnan(v):
            if precio > v:
                mms_alcistas += 1
                mms_sobre.append(mm_col)
                if mm_col == "MM200":
                    mm200_ok = True
                    señales_mm["compra"].append(_s("MM200 : Precio por encima", 0.7))
            else:
                mms_bajistas += 1
                mms_bajo.append(mm_col)
                if mm_col == "MM200":
                    señales_mm["venta"].append(_s("MM200 : Precio por debajo", 0.7))

    # Señal agregada de MMs cortas/medias con detalle
    if mms_alcistas > mms_bajistas:
        detalle = " + ".join(mms_sobre) if mms_sobre else "MMs"
        señales_mm["compra"].append(_s(f"MMs alcistas: {detalle}", 0.6))
    elif mms_bajistas > mms_alcistas:
        detalle = " + ".join(mms_bajo) if mms_bajo else "MMs"
        señales_mm["venta"].append(_s(f"MMs bajistas: {detalle}", 0.6))
    else:
        señales_mm["neutral"].append(_s("MMs : Mix", 0.3))

    # ── Golden Cross MM50 > MM200 (clave para posicional) ─────
    if "MM50" in df.columns and "MM200" in df.columns:
        try:
            mm50_v  = float(df["MM50"].iloc[-1])
            mm200_v = float(df["MM200"].iloc[-1])
            if not np.isnan(mm50_v) and not np.isnan(mm200_v):
                if mm50_v > mm200_v:
                    señales_mm["compra"].append(_s("Golden Cross: MM50 > MM200", 0.8))
                else:
                    señales_mm["venta"].append(_s("Death Cross: MM50 < MM200", 0.8))
        except Exception:
            pass

    # ── Pendiente MM50 (últimas 10 velas) — para posicional ───
    if "MM50" in df.columns:
        try:
            mm50_serie = df["MM50"].dropna()
            if len(mm50_serie) >= 10:
                mm50_ahora   = float(mm50_serie.iloc[-1])
                mm50_hace10  = float(mm50_serie.iloc[-10])
                pendiente_pct = (mm50_ahora - mm50_hace10) / mm50_hace10 * 100
                if pendiente_pct > 0.5:
                    señales_mm["compra"].append(_s(f"MM50 pendiente alcista (+{pendiente_pct:.1f}%)", 0.7))
                elif pendiente_pct < -0.5:
                    señales_mm["venta"].append(_s(f"MM50 pendiente bajista ({pendiente_pct:.1f}%)", 0.7))
                else:
                    señales_mm["neutral"].append(_s("MM50 pendiente plana", 0.2))
        except Exception:
            pass

    # ── Volumen como señal de media ───────────────────────────
    if "Volume" in df.columns:
        vol_actual = float(df["Volume"].iloc[-1])
        vol_medio  = float(df["Volume"].tail(20).mean())
        ratio_volumen = round(vol_actual / vol_medio, 2) if vol_medio > 0 else 1.0
        if ratio_volumen >= 1.5:
            señales_mm["compra"].append(_s("Volumen", 0.4))
        elif ratio_volumen <= 0.6:
            señales_mm["venta"].append(_s("Volumen", 0.4))
        else:
            señales_mm["neutral"].append(_s("Volumen", -0.3))
    else:
        ratio_volumen = 1.0

    # ── Cálculo de puntuaciones ───────────────────────────────
    ci = len(señales_ind["compra"]); vi = len(señales_ind["venta"]); ni = len(señales_ind["neutral"])
    cm = len(señales_mm["compra"]);  vm = len(señales_mm["venta"]);  nm = len(señales_mm["neutral"])
    compras = ci + cm; ventas = vi + vm; total = compras + ventas + ni + nm

    # Puntuación ponderada — neutrales no diluyen el resultado
    sum_compra = sum(s["peso"] for s in señales_ind["compra"] + señales_mm["compra"])
    sum_venta  = sum(s["peso"] for s in señales_ind["venta"]  + señales_mm["venta"])
    sum_total  = max(sum_compra + sum_venta, 0.1)
    puntuacion = round((sum_compra - sum_venta) / sum_total, 2)
    puntuacion = max(-1.0, min(1.0, puntuacion))  # clampear a [-1, +1]
    puntuacion_global = puntuacion

    if puntuacion >= 0.5:    rec, color = "Compra fuerte", "compra"
    elif puntuacion >= 0.2:  rec, color = "Compra",        "compra"
    elif puntuacion <= -0.5: rec, color = "Venta fuerte",  "venta"
    elif puntuacion <= -0.2: rec, color = "Venta",         "venta"
    else:                    rec, color = "Neutral",        "neutral"

    # Texto "Faltan X pts para ..."
    if puntuacion > -0.2 and puntuacion < 0.2:
        pts_para_venta  = round(-0.2 - puntuacion, 1)
        pts_para_compra = round(0.2 - puntuacion, 1)
        proximidad = f"Faltan {min(pts_para_venta, pts_para_compra):.1f} pts para {'VENTA' if pts_para_venta < pts_para_compra else 'COMPRA'}"
    elif puntuacion >= 0.2 and puntuacion < 0.5:
        proximidad = f"Faltan {round(0.5 - puntuacion, 1):.1f} pts para COMPRA FUERTE"
    elif puntuacion <= -0.2 and puntuacion > -0.5:
        proximidad = f"Faltan {round(abs(-0.5 - puntuacion), 1):.1f} pts para VENTA FUERTE"
    else:
        proximidad = None

    # gauge_volumen y gauge_momentum
    gauge_volumen  = round((ratio_volumen - 1) * 100, 1)
    rsi_m = macd_m = tend_m = 0
    if "RSI" in df.columns:
        rsi_v = float(df["RSI"].iloc[-1])
        if not np.isnan(rsi_v): rsi_m = (rsi_v - 50) * 2
    if "MACD" in df.columns and "MACD_SEÑAL" in df.columns:
        m_v = float(df["MACD"].iloc[-1]); s_v = float(df["MACD_SEÑAL"].iloc[-1])
        if not np.isnan(m_v) and not np.isnan(s_v):
            macd_m = 100 if m_v > s_v else -100
    tend_m = 100 if compras > ventas else (-100 if ventas > compras else 0)
    gauge_momentum = round(rsi_m * 0.4 + macd_m * 0.3 + tend_m * 0.3, 1)

    nivel = "alto" if total >= 7 else "medio" if total >= 4 else "bajo"

    ind_punt = round((sum(s["peso"] for s in señales_ind["compra"]) -
                      sum(s["peso"] for s in señales_ind["venta"])) /
                     max(sum(abs(s["peso"]) for s in señales_ind["compra"] +
                             señales_ind["venta"] + señales_ind["neutral"]), 0.1), 2)
    mm_punt  = round((sum(s["peso"] for s in señales_mm["compra"]) -
                      sum(s["peso"] for s in señales_mm["venta"])) /
                     max(sum(abs(s["peso"]) for s in señales_mm["compra"] +
                             señales_mm["venta"] + señales_mm["neutral"]), 0.1), 2)

    return {
        "puntuacion":         puntuacion,
        "puntuacion_global":  puntuacion_global,
        "recomendacion":      rec,
        "color":              color,
        "contexto_favorable": compras > ventas,
        "contexto_mm200":     "en tendencia alcista" if mm200_ok else "Por debajo MM200",
        "nivel_confianza":    nivel,
        "puntos_compra":      round(sum_compra, 1),
        "puntos_venta":       round(sum_venta, 1),
        "ratio_volumen":      ratio_volumen,
        "gauge_volumen":      gauge_volumen,
        "gauge_momentum":     gauge_momentum,
        "proximidad":         proximidad,
        "warnings":           [],
        "indicadores": {
            "puntuacion":       ind_punt,
            "compras": ci, "ventas": vi, "neutrales": ni,
            "desglose_compra":  señales_ind["compra"],
            "desglose_venta":   señales_ind["venta"],
            "desglose_neutral": señales_ind["neutral"],
        },
        "medias_moviles": {
            "puntuacion":       mm_punt,
            "compras": cm, "ventas": vm, "neutrales": nm,
            "desglose_compra":  señales_mm["compra"],
            "desglose_venta":   señales_mm["venta"],
            "desglose_neutral": señales_mm["neutral"],
        },
    }


# ══════════════════════════════════════════════════════════════
# PANEL PRINCIPAL
# ══════════════════════════════════════════════════════════════

@indicadores_bp.route("/", methods=["GET"])
def panel():
    return render_template("indicadores.html", tickers_ibex=IBEX35, tickers_continuo=CONTINUO)


# ══════════════════════════════════════════════════════════════
# API JSON
# GET /indicadores/api?ticker=SAN.MC&tf=1d&ind=RSI,MACD,MM20,SR,OBV,BB,PIVOT,FIBO
# ══════════════════════════════════════════════════════════════

@indicadores_bp.route("/api", methods=["GET"])
def api_datos():
    ticker    = normalizar_ticker(request.args.get("ticker", ""))
    tf        = request.args.get("tf", "1d")
    ind_param = request.args.get("ind", "")
    inds      = {i.strip().upper() for i in ind_param.split(",") if i.strip()}

    if not ticker:
        return jsonify({"error": "Ticker requerido"}), 400

    periodos = {"1d": "1y", "1wk": "5y", "1mo": "10y"}   # 1y para diario = niveles relevantes
    periodo  = periodos.get(tf, "1y")

    cache = _get_cache()
    df    = get_df(ticker, periodo=periodo, cache=cache)

    if df is None or df.empty:
        return jsonify({"error": f"Sin datos para {ticker}"}), 404

    if tf == "1wk":
        df = df.resample("W-FRI").agg({
            "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
        }).dropna()
        df = df[df["Close"] > 0]
    elif tf == "1mo":
        df = df.resample("ME").agg({
            "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
        }).dropna()
        df = df[df["Close"] > 0]

    if df is None or df.empty:
        return jsonify({"error": f"Sin datos para {ticker}"}), 404

    # ── Eliminar vela fantasma de hoy si el mercado aún no ha abierto ──
    try:
        if len(df) > 1:
            from datetime import date as _date, datetime as _dt
            ultima = df.iloc[-1]
            open_v  = float(ultima["Open"])
            high_v  = float(ultima["High"])
            low_v   = float(ultima["Low"])
            # Solo eliminar si Open Y High son 0 o NaN (vela claramente fantasma)
            if (open_v == 0 or pd.isna(open_v)) and (high_v == 0 or pd.isna(high_v)):
                # Verificar que es de hoy
                idx_last = df.index[-1]
                if hasattr(idx_last, 'date'):
                    fecha_ultima = idx_last.date()
                elif hasattr(idx_last, 'to_pydatetime'):
                    fecha_ultima = idx_last.to_pydatetime().date()
                else:
                    fecha_ultima = _dt.strptime(str(idx_last)[:10], '%Y-%m-%d').date()
                if fecha_ultima == _date.today():
                    df = df.iloc[:-1]
                    print(f"[VELA HOY] {ticker}: vela fantasma eliminada (Open={open_v}, High={high_v})")
    except Exception as e:
        print(f"[VELA HOY] {ticker}: {e}")

    if df is None or df.empty:
        return jsonify({"error": f"Sin datos para {ticker}"}), 404

    # ── Calcular indicadores como columnas (cada uno con su propio try) ──
    # ATR siempre — necesario para panel lateral
    try:
        df["ATR"] = pd.Series(calcular_atr(df, 14).values, index=df.index).bfill()
    except Exception: pass

    # ── Indicadores siempre calculados para el resumen técnico ──
    inds_base = {"MM20", "MM50", "MM200", "RSI", "MACD", "BB", "OBV", "ADX"}
    inds_calc  = inds | inds_base  # unión de los seleccionados + los base

    if "MM20" in inds_calc:
        try: df["MM20"] = df["Close"].rolling(20).mean().bfill()
        except Exception: pass
    if "MM50" in inds_calc:
        try: df["MM50"] = df["Close"].rolling(50).mean().bfill()
        except Exception: pass
    if "MM200" in inds_calc:
        try: df["MM200"] = df["Close"].rolling(200).mean().bfill()
        except Exception: pass
    if "EMA9" in inds:
        try: df["EMA9"] = _calcular_ema(df["Close"], 9)
        except Exception: pass
    if "EMA21" in inds:
        try: df["EMA21"] = _calcular_ema(df["Close"], 21)
        except Exception: pass
    if "EMA50" in inds:
        try: df["EMA50"] = _calcular_ema(df["Close"], 50)
        except Exception: pass
    if "RSI" in inds_calc:
        try:
            rsi_vals = calcular_rsi(df["Close"], 14).values
            df["RSI"] = pd.Series(rsi_vals, index=df.index).bfill()
        except Exception as e: print(f"RSI error: {e}")
    if "MFI" in inds_calc:
        try: df["MFI"] = _calcular_mfi(df).bfill()
        except Exception: pass
    if "MACD" in inds_calc:
        try:
            m = calcular_macd(df["Close"])
            df["MACD"]       = pd.Series(m["macd"].values,       index=df.index).bfill()
            df["MACD_SEÑAL"] = pd.Series(m["señal"].values,      index=df.index).bfill()
            df["MACD_HIST"]  = pd.Series(m["histograma"].values, index=df.index).bfill()
        except Exception as e: print(f"MACD error: {e}")
    if "BB" in inds_calc:
        try:
            bb = calcular_bollinger(df["Close"])
            df["BB_SUPERIOR"] = pd.Series(bb["superior"].values, index=df.index).bfill()
            df["BB_INFERIOR"] = pd.Series(bb["inferior"].values, index=df.index).bfill()
            df["BB_MEDIO"]    = pd.Series(bb["media"].values,    index=df.index).bfill()
        except Exception as e: print(f"BB error: {e}")
    if "OBV" in inds_calc:
        try: df["OBV"] = _calcular_obv(df)
        except Exception: pass
    if "ADX" in inds_calc:
        try:
            adx, di_pos, di_neg = _calcular_adx(df)
            df["ADX"]    = adx.bfill()
            df["DI_POS"] = di_pos.bfill()
            df["DI_NEG"] = di_neg.bfill()
        except Exception as e: print(f"ADX error: {e}")
    if "KELTNER" in inds:
        try:
            ku, km, kl = _calcular_keltner(df)
            df["KELTNER_UPPER"] = ku; df["KELTNER_MIDDLE"] = km; df["KELTNER_LOWER"] = kl
        except Exception: pass
    if "VWAP" in inds:
        try: df["VWAP"] = _calcular_vwap(df)
        except Exception: pass
    if "PSAR" in inds:
        try: df["PSAR"] = _calcular_psar(df)
        except Exception: pass
    if "PIVOT" in inds:
        try:
            pivots = _calcular_pivot_points(df)
            for k, v in pivots.items():
                df[k] = v
        except Exception: pass

    # ── Serializar data con indicadores embebidos ──
    df_reset = df.reset_index()
    idx_col  = df_reset.columns[0]
    if idx_col != "Date":
        df_reset = df_reset.rename(columns={idx_col: "Date"})
    df_reset["Date"] = df_reset["Date"].astype(str).str[:10]

    # Solo devolver las últimas 260 velas para diario (igual que el antiguo)
    if tf == "1d" and len(df_reset) > 260:
        df_reset = df_reset.tail(260)

    data_json = []
    for _, row in df_reset.iterrows():
        obj = {col: (row[col] if isinstance(row[col], str) else _safe(row[col]))
               for col in df_reset.columns}
        data_json.append(obj)

    # ── Soportes y resistencias — usar más histórico para mejor detección ──
    precio_actual = float(df["Close"].iloc[-1])
    soportes_json = []
    resistencias_json = []
    try:
        # Intentar con df completo primero, si no hay soportes bajar min_toques
        sr = detectar_soportes_resistencias(df, periodo=10, tolerancia_pct=3.0, min_toques=1)
        soportes_json = [{
            "precio":        s["nivel"],
            "fuerza":        s["toques"],
            "toques":        s["toques"],
            "distancia_pct": round(abs(precio_actual - s["nivel"]) / precio_actual * 100, 1),
        } for s in sr.get("soportes", [])]
        resistencias_json = [{
            "precio":        r["nivel"],
            "fuerza":        r["toques"],
            "toques":        r["toques"],
            "distancia_pct": round(abs(r["nivel"] - precio_actual) / precio_actual * 100, 1),
        } for r in sr.get("resistencias", [])]
    except Exception:
        pass

    # ── Patrones de velas ──
    patrones_json = []
    try:
        raw = detectar_patrones_velas(df, ultimas_n=50)
        patrones_json = [{
            "nombre":      p["nombre"],
            "tipo":        p["tipo"],
            "confianza":   p["confianza"],
            "descripcion": p.get("descripcion", ""),
            "fecha":       str(p["fecha"])[:10] if p.get("fecha") is not None else "",
        } for p in raw]
    except Exception:
        pass

    # ── Divergencias ──
    divergencias_json = _calcular_divergencias(df, inds)

    # ── Fibonacci ──
    fibonacci_json = {}
    if "FIBO" in inds:
        try:
            fibonacci_json = _calcular_fibonacci(df)
        except Exception:
            pass

    # ── Resumen técnico — siempre con todos los indicadores ──
    # El resumen se calcula independientemente de los indicadores seleccionados
    resumen = {}
    try:
        inds_resumen = inds | {"RSI", "MACD", "OBV", "BB", "ADX", "MM20", "MM50", "MM200"}
        resumen = _calcular_resumen_tecnico(df, inds_resumen)
    except Exception:
        pass

    # ── Patrones chartistas ──
    patrones_chartistas_json = []
    if "PATRONES" in inds:
        try:
            raw = _detectar_patrones_chartistas(df, n=200)
            # Convertir numpy bools/floats a tipos Python nativos
            def _san(o):
                if isinstance(o, dict): return {k: _san(v) for k,v in o.items()}
                if isinstance(o, list): return [_san(v) for v in o]
                if hasattr(o, 'item'): return o.item()
                return o
            patrones_chartistas_json = _san(raw)
            print(f"[PATRONES] {ticker}: {len(patrones_chartistas_json)} patrones chartistas detectados")
        except Exception as e:
            print(f"Patrones chartistas error: {e}")

    # ── Contexto de trading ──
    contexto_trading = {}
    try:
        contexto_trading = _detectar_contexto_trading(
            df, soportes_json, resistencias_json, patrones_json
        )
    except Exception:
        pass

    # ── Contexto del patrón (para patrones de vela) ──
    contexto_patron = {}
    try:
        from estrategias.swing.pullback import _evaluar_contexto_patron
        closes = df["Close"].values
        lows   = df["Low"].values
        mm50_s = pd.Series(closes).rolling(50).mean()
        mm20_s = pd.Series(closes).rolling(20).mean()
        rsi_s  = pd.Series(closes).diff()
        avg_g  = rsi_s.clip(lower=0).ewm(com=13, adjust=False).mean()
        avg_p  = (-rsi_s).clip(lower=0).ewm(com=13, adjust=False).mean()
        rsi_val = float(100 - 100 / (1 + avg_g.iloc[-1] / avg_p.iloc[-1])) if float(avg_p.iloc[-1]) > 0 else 50.0
        precio  = float(closes[-1])
        mm50_v  = float(mm50_s.iloc[-1]) if not pd.isna(mm50_s.iloc[-1]) else None
        mm20_v  = float(mm20_s.iloc[-1]) if not pd.isna(mm20_s.iloc[-1]) else None
        mm20_ant = float(mm20_s.iloc[-6]) if len(mm20_s) >= 6 and not pd.isna(mm20_s.iloc[-6]) else None
        min30   = float(pd.Series(lows).tail(30).min())

        soporte_ok   = 2.0 <= ((precio - min30) / precio * 100) <= 8.0
        rsi_ok       = 38 <= rsi_val <= 57
        estructura_ok = (mm50_v is not None and precio > mm50_v and
                         mm20_v is not None and mm20_ant is not None and mm20_v >= mm20_ant)
        contexto_patron = _evaluar_contexto_patron(soporte_ok, rsi_ok, estructura_ok)
    except Exception as e:
        print(f"[CONTEXTO_PATRON ERROR] {e}")

    return jsonify({
        "data":                data_json,
        "soportes":            soportes_json,
        "resistencias":        resistencias_json,
        "patrones":            patrones_json,
        "divergencias":        divergencias_json,
        "resumenTecnico":      resumen,
        "fibonacci":           fibonacci_json,
        "patrones_chartistas": patrones_chartistas_json,
        "contextoTrading":     contexto_trading,
        "contexto_patron":     contexto_patron,
    })


def _calcular_fiabilidad_patron(df, patron):
    """
    Calcula una puntuación de fiabilidad (0-5 estrellas) cruzando el patrón
    chartista con: volumen, RSI, MM200, divergencia RSI, vela de confirmación.
    Devuelve dict con estrellas, puntuacion_num y detalles de cada confirmación.
    """
    confirmaciones = []
    puntos = 0

    try:
        closes = df["Close"].values
        highs  = df["High"].values
        lows   = df["Low"].values
        vols   = df["Volume"].values if "Volume" in df.columns else None
        precio = float(closes[-1])
        n      = len(closes)
        tipo   = patron.get("tipo", "")
        es_alcista = patron.get("direccion") == "alcista"

        # ── 1. VOLUMEN EN ROTURA ─────────────────────────────
        if vols is not None and len(vols) > 20:
            vol_actual  = float(vols[-1])
            vol_medio20 = float(np.mean(vols[-20:]))
            if vol_medio20 > 0:
                ratio_vol = vol_actual / vol_medio20
                if ratio_vol >= 1.5:
                    confirmaciones.append({"icono": "📊", "texto": f"Volumen {round(ratio_vol,1)}x — rotura con fuerza", "ok": True})
                    puntos += 1
                elif ratio_vol >= 1.0:
                    confirmaciones.append({"icono": "📊", "texto": f"Volumen {round(ratio_vol,1)}x — normal", "ok": None})
                else:
                    confirmaciones.append({"icono": "📊", "texto": f"Volumen {round(ratio_vol,1)}x — rotura débil", "ok": False})

        # ── 2. MM200 ALINEADA ────────────────────────────────
        if n >= 200:
            mm200 = float(np.mean(closes[-200:]))
            if es_alcista and precio > mm200:
                confirmaciones.append({"icono": "📈", "texto": f"Precio sobre MM200 ({round(mm200,2)}€) — tendencia alcista", "ok": True})
                puntos += 1
            elif not es_alcista and precio < mm200:
                confirmaciones.append({"icono": "📉", "texto": f"Precio bajo MM200 ({round(mm200,2)}€) — tendencia bajista", "ok": True})
                puntos += 1
            else:
                dir_txt = "alcista" if es_alcista else "bajista"
                confirmaciones.append({"icono": "⚠️", "texto": f"Patrón {dir_txt} contra tendencia MM200", "ok": False})

        # ── 3. RSI Y DIVERGENCIA ─────────────────────────────
        if n >= 14:
            delta  = np.diff(closes[-15:])
            gains  = np.where(delta > 0, delta, 0)
            losses = np.where(delta < 0, -delta, 0)
            avg_g  = np.mean(gains[-14:])
            avg_l  = np.mean(losses[-14:])
            rsi    = 100 - (100 / (1 + avg_g / avg_l)) if avg_l > 0 else 50

            if es_alcista and rsi < 40:
                confirmaciones.append({"icono": "🔵", "texto": f"RSI {round(rsi,1)} — zona de sobreventa, impulso probable", "ok": True})
                puntos += 1
            elif not es_alcista and rsi > 60:
                confirmaciones.append({"icono": "🔴", "texto": f"RSI {round(rsi,1)} — zona de sobrecompra, caída probable", "ok": True})
                puntos += 1
            elif es_alcista and rsi > 60:
                confirmaciones.append({"icono": "⚠️", "texto": f"RSI {round(rsi,1)} — sobrecomprado para patrón alcista", "ok": False})
            else:
                confirmaciones.append({"icono": "⚪", "texto": f"RSI {round(rsi,1)} — zona neutral", "ok": None})

            # Divergencia alcista en doble suelo / HCH invertido
            if es_alcista and n >= 30 and tipo in ["doble_suelo", "hch_invertido"]:
                rsi_hace20 = 50  # simplificado
                delta2     = np.diff(closes[-29:-15])
                g2 = np.where(delta2>0,delta2,0); l2 = np.where(delta2<0,-delta2,0)
                ag2 = np.mean(g2[-14:]); al2 = np.mean(l2[-14:])
                rsi_prev = 100-(100/(1+ag2/al2)) if al2 > 0 else 50
                precio_prev = float(closes[-20])
                if rsi > rsi_prev and precio <= precio_prev * 1.02:
                    confirmaciones.append({"icono": "✨", "texto": "Divergencia alcista RSI — momentum girando", "ok": True})
                    puntos += 1

        # ── 4. VELA DE CONFIRMACIÓN ──────────────────────────
        if n >= 3:
            c0, c1, o0, o1 = float(closes[-1]), float(closes[-2]), float(df["Open"].values[-1]), float(df["Open"].values[-2])
            cuerpo0 = abs(c0 - o0)
            rango0  = float(highs[-1]) - float(lows[-1])
            if rango0 > 0:
                ratio_cuerpo = cuerpo0 / rango0
                if es_alcista and c0 > o0 and ratio_cuerpo > 0.6:
                    confirmaciones.append({"icono": "🕯️", "texto": "Vela alcista sólida — confirmación de momentum", "ok": True})
                    puntos += 1
                elif not es_alcista and c0 < o0 and ratio_cuerpo > 0.6:
                    confirmaciones.append({"icono": "🕯️", "texto": "Vela bajista sólida — confirmación de momentum", "ok": True})
                    puntos += 1
                else:
                    confirmaciones.append({"icono": "🕯️", "texto": "Vela sin confirmación clara", "ok": None})

        # ── 5. PATRÓN EN ZONA CLAVE (S/R) ───────────────────
        neckline = patron.get("neckline")
        if neckline:
            dist_pct = abs(precio - neckline) / neckline * 100
            if dist_pct <= 1.5:
                confirmaciones.append({"icono": "🎯", "texto": f"Precio a {round(dist_pct,1)}% de la neckline — zona clave", "ok": True})
                puntos += 1
            elif dist_pct <= 3:
                confirmaciones.append({"icono": "🎯", "texto": f"Precio a {round(dist_pct,1)}% de la neckline", "ok": None})

    except Exception as e:
        pass

    # Convertir puntos a estrellas (max 5)
    estrellas = min(5, puntos)
    stars_str = "⭐" * estrellas + "☆" * (5 - estrellas)

    return {
        "fiabilidad_estrellas": estrellas,
        "fiabilidad_str": stars_str,
        "fiabilidad_detalle": confirmaciones,
    }


@indicadores_bp.route("/scan_patrones", methods=["GET"])
def scan_patrones():
    """Escanea patrones chartistas en IBEX35 o Mercado Continuo."""
    from core.universos import IBEX35, CONTINUO, get_nombre
    mercado  = request.args.get("mercado", "ibex35").lower()
    universe = IBEX35 if mercado == "ibex35" else CONTINUO
    cache    = current_app.extensions.get("cache")  # objeto cache real, no booleano

    resultados = []
    for ticker in universe:
        try:
            df = get_df(ticker, periodo="1y", cache=None)
            if df is None or not hasattr(df, "__len__") or len(df) < 60:
                continue
            patrones = _detectar_patrones_chartistas(df, n=200)
            if patrones:
                nombre = get_nombre(ticker)
                precio = round(float(df["Close"].iloc[-1]), 2)
                for p in patrones:
                    fiabilidad = _calcular_fiabilidad_patron(df, p)
                    resultados.append({
                        "ticker": ticker,
                        "nombre": nombre,
                        "precio": precio,
                        **p,
                        **fiabilidad
                    })
        except Exception as e:
            print(f"[SCAN] Error {ticker}: {e}")
            continue

    # Enriquecer cada resultado con distancia a neckline y rotura reciente
    from datetime import date, datetime
    hoy = date.today()
    for r in resultados:
        neckline = r.get("neckline")
        precio   = r.get("precio")
        if neckline and precio and neckline > 0:
            dist = round((precio - neckline) / neckline * 100, 1)
            r["dist_neck_pct"] = dist
        else:
            r["dist_neck_pct"] = None

        # Rotura reciente: confirmado Y fecha2 dentro de los últimos 5 días
        r["rotura_reciente"] = False
        if r.get("confirmado"):
            f2 = r.get("fecha2") or r.get("fecha_cabeza") or ""
            if f2:
                try:
                    dias = (hoy - datetime.strptime(f2[:10], "%Y-%m-%d").date()).days
                    if dias <= 5:
                        r["rotura_reciente"] = True
                except Exception:
                    pass

    resultados.sort(key=lambda x: (
        0 if x.get("rotura_reciente") else 1,
        -int((x.get("fecha2") or x.get("fecha_cabeza") or "0000-00-00").replace("-", "")),
        0 if x.get("confirmado") else 1,
        -(x.get("fiabilidad_estrellas") or 0),  # más estrellas primero
        abs(x.get("dist_neck_pct") or 999),
    ))

    # Convertir tipos numpy a tipos Python nativos para JSON serialization
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        if isinstance(obj, (bool,)):
            return bool(obj)
        return obj

    resultados = _sanitize(resultados)
    return jsonify({"resultados": resultados, "mercado": mercado, "total": len(resultados)})
