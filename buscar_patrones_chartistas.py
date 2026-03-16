"""
buscar_patrones_chartistas.py
Ejecutar desde la carpeta raíz de MiWeb:
  python buscar_patrones_chartistas.py

Detecta patrones chartistas en todos los valores del IBEX35 y Mercado Continuo
y muestra los resultados ordenados por relevancia.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Universo
IBEX35 = [
    "ACX.MC","AENA.MC","AMS.MC","ANA.MC","ANE.MC","BKT.MC","BBVA.MC",
    "CABK.MC","CLNX.MC","COL.MC","ELE.MC","ENG.MC","FCC.MC","FER.MC",
    "GRF.MC","IAG.MC","IBE.MC","IDR.MC","ITX.MC","LOG.MC","MAP.MC",
    "MRL.MC","MTS.MC","NTGY.MC","PUIG.MC","RED.MC","REP.MC","ROVI.MC",
    "SAB.MC","SAN.MC","SCYR.MC","SLR.MC","TEF.MC","UNI.MC","ACS.MC"
]
CONTINUO = [
    "A3M.MC","CAF.MC","CIE.MC","DOM.MC","ECR.MC","ENC.MC","FAE.MC",
    "GRE.MC","HOME.MC","IMC.MC","LDA.MC","LIB.MC","MEL.MC","MVC.MC",
    "NEA.MC","OHLA.MC","PHM.MC","PSG.MC","R4.MC","TRE.MC","TUB.MC","VID.MC"
]

TOL = 0.03  # 3% tolerancia

def maximos_loc(serie, orden=5):
    return [i for i in range(orden, len(serie)-orden)
            if serie[i] == max(serie[i-orden:i+orden+1])]

def minimos_loc(serie, orden=5):
    return [i for i in range(orden, len(serie)-orden)
            if serie[i] == min(serie[i-orden:i+orden+1])]

def detectar(df, n=120):
    patrones = []
    sub = df.tail(n)
    closes = sub["Close"].values
    highs  = sub["High"].values
    lows   = sub["Low"].values
    precio = float(closes[-1])

    maximos = maximos_loc(highs)
    minimos = minimos_loc(lows)

    # Doble Techo
    if len(maximos) >= 2:
        m1, m2 = maximos[-2], maximos[-1]
        p1, p2 = highs[m1], highs[m2]
        if abs(p1-p2)/max(p1,p2) <= TOL:
            nk = round(float(min(closes[m1:m2+1])), 2)
            conf = "✓ CONFIRMADO" if precio < nk else "⏱ En formación"
            patrones.append(("🔴 Doble Techo", conf, f"Techos ~{round((p1+p2)/2,2)}€ | Neckline {nk}€"))

    # Doble Suelo
    if len(minimos) >= 2:
        m1, m2 = minimos[-2], minimos[-1]
        p1, p2 = lows[m1], lows[m2]
        if abs(p1-p2)/max(p1,p2) <= TOL:
            nk = round(float(max(closes[m1:m2+1])), 2)
            conf = "✓ CONFIRMADO" if precio > nk else "⏱ En formación"
            patrones.append(("🟢 Doble Suelo", conf, f"Suelos ~{round((p1+p2)/2,2)}€ | Neckline {nk}€"))

    # HCH
    if len(maximos) >= 3:
        h1,c,h2 = maximos[-3],maximos[-2],maximos[-1]
        ph1,pc,ph2 = highs[h1],highs[c],highs[h2]
        if pc > ph1 and pc > ph2 and abs(ph1-ph2)/max(ph1,ph2) <= TOL*2:
            nk = round(float((min(closes[h1:c+1])+min(closes[c:h2+1]))/2), 2)
            conf = "✓ CONFIRMADO" if precio < nk else "⏱ En formación"
            patrones.append(("🔴 HCH", conf, f"Cabeza {round(pc,2)}€ | Neckline {nk}€"))

    # HCH Invertido
    if len(minimos) >= 3:
        h1,c,h2 = minimos[-3],minimos[-2],minimos[-1]
        ph1,pc,ph2 = lows[h1],lows[c],lows[h2]
        if pc < ph1 and pc < ph2 and abs(ph1-ph2)/max(abs(ph1),abs(ph2)) <= TOL*2:
            nk = round(float((max(closes[h1:c+1])+max(closes[c:h2+1]))/2), 2)
            conf = "✓ CONFIRMADO" if precio > nk else "⏱ En formación"
            patrones.append(("🟢 HCH Invertido", conf, f"Cabeza {round(pc,2)}€ | Neckline {nk}€"))

    # Triángulo Ascendente
    if len(maximos) >= 3 and len(minimos) >= 3:
        ult_max = [highs[i] for i in maximos[-3:]]
        if (max(ult_max)-min(ult_max))/max(ult_max) <= TOL:
            mins = [lows[i] for i in minimos[-3:]]
            if mins[-1] > mins[-2] > mins[0]:
                resist = round(float(np.mean(ult_max)),2)
                conf = "✓ CONFIRMADO" if precio > resist else "⏱ En formación"
                patrones.append(("🟢 Triángulo Ascendente", conf, f"Resistencia {resist}€"))

    # Triángulo Descendente
    if len(minimos) >= 3 and len(maximos) >= 3:
        ult_min = [lows[i] for i in minimos[-3:]]
        if (max(ult_min)-min(ult_min))/max(ult_min) <= TOL:
            maxs = [highs[i] for i in maximos[-3:]]
            if maxs[-1] < maxs[-2] < maxs[0]:
                sop = round(float(np.mean(ult_min)),2)
                conf = "✓ CONFIRMADO" if precio < sop else "⏱ En formación"
                patrones.append(("🔴 Triángulo Descendente", conf, f"Soporte {sop}€"))

    # Triángulo Simétrico
    if len(maximos) >= 3 and len(minimos) >= 3:
        maxs = [highs[i] for i in maximos[-3:]]
        mins = [lows[i] for i in minimos[-3:]]
        if maxs[-1] < maxs[0] and mins[-1] > mins[0]:
            conf = "✓ CONFIRMADO" if precio > maxs[-1] or precio < mins[-1] else "⏱ En formación"
            patrones.append(("⚡ Triángulo Simétrico", conf, f"Rango {round(mins[-1],2)}€-{round(maxs[-1],2)}€"))

    # Bandera Alcista
    for asta_len in range(5, 15):
        if len(closes) < asta_len + 8: break
        i0 = len(closes)-asta_len-8; i1 = len(closes)-8
        if i0 < 0: break
        subida = (closes[i1]-closes[i0])/closes[i0]*100
        if subida >= 6:
            consol = closes[i1:]
            if len(consol) > 0 and (max(consol)-min(consol))/min(consol)*100 <= 4:
                conf = "✓ CONFIRMADO" if precio > max(consol) else "⏱ En formación"
                patrones.append(("🟢 Bandera Alcista", conf, f"Asta +{round(subida,1)}% | {len(consol)} velas pausa"))
            break

    return patrones

# ── EJECUTAR ──────────────────────────────────────────────────
print("\n" + "="*65)
print("🔍 BUSCANDO PATRONES CHARTISTAS — IBEX35 + MERCADO CONTINUO")
print("="*65)

resultados = []
universo = [(t, "IBEX35") for t in IBEX35] + [(t, "CONTINUO") for t in CONTINUO]

for i, (ticker, mercado) in enumerate(universo):
    print(f"  Analizando {ticker}... ({i+1}/{len(universo)})", end='\r')
    try:
        tick = yf.Ticker(ticker)
        df = tick.history(period='1y', interval='1d')
        if df.index.tz: df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.title)
        df = df[df['Close'] > 0].dropna()
        if len(df) < 60: continue

        pats = detectar(df)
        if pats:
            precio = round(float(df['Close'].iloc[-1]), 2)
            resultados.append((ticker, mercado, precio, pats))
    except Exception as e:
        pass

# Mostrar resultados
print(f"\n\n{'='*65}")
print(f"✅ PATRONES DETECTADOS: {sum(len(r[3]) for r in resultados)} en {len(resultados)} valores")
print(f"{'='*65}")

# Primero confirmados, luego en formación
for ticker, mercado, precio, pats in sorted(resultados, key=lambda x: x[0]):
    print(f"\n📊 {ticker} ({mercado}) — {precio}€")
    for nombre, estado, detalle in pats:
        estado_color = "⭐" if "CONFIRMADO" in estado else "  "
        print(f"  {estado_color} {nombre}: {detalle} [{estado}]")

# Resumen de confirmados
confirmados = [(t, m, p, n, d) for t,m,pr,pats in resultados 
               for n,e,d in pats if "CONFIRMADO" in e]
if confirmados:
    print(f"\n{'='*65}")
    print(f"⭐ PATRONES CONFIRMADOS ({len(confirmados)}) — PRIORIDAD MÁXIMA")
    print(f"{'='*65}")
    for t,m,p,n,d in confirmados:
        print(f"  {t} ({m}): {n} — {d}")

print(f"\n{'='*65}")
print("Abre la sección de Análisis Técnico con PATRONES activado")
print("para ver la representación visual en el gráfico.")
print(f"{'='*65}\n")
