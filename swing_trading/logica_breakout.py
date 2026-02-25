"""
═══════════════════════════════════════════════════════════════
MÓDULO: DETECCIÓN DE BREAKOUTS (RUPTURAS)
Sistema Swing Trading - Estrategia de Impulsos
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio rompe resistencias
y entra en nueva fase de tendencia alcista.

Filosofía: "Comprar caro para vender más caro"

Criterios ajustados por Salva:
- Precio cerca del máximo (-3%)
- Resistencia clara identificada (2+ toques)
- Consolidación previa (≥ 8 días)
- Volumen en ruptura (1.2x IBEX, 1.1x Continuo)
- RSI momentum fuerte (50–82)
- Estructura alcista (precio > MM20 > MM50)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def detectar_breakout_swing(ticker, periodo='6mo'):

    motivos = []

    try:
        df = yf.download(ticker, period=periodo, progress=False)

        if df is None or len(df) < 60:
            return _respuesta_invalida(ticker, "Datos insuficientes")

        # Variación 1 día
        variacion_1d = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) /
                        df['Close'].iloc[-2]) * 100
        variacion_1d = variacion_1d.item() if hasattr(variacion_1d, "item") else float(variacion_1d)


        # Indicadores
        df['MM20'] = df['Close'].rolling(20).mean()
        df['MM50'] = df['Close'].rolling(50).mean()
        df['ATR'] = calcular_atr(df, periodo=14)
        df['RSI'] = calcular_rsi(df['Close'], periodo=14)

        precio_actual = df['Close'].iloc[-1].item()
        rsi_actual = df['RSI'].iloc[-1].item()
        atr_actual = df['ATR'].iloc[-1].item()
        mm20_actual = df['MM20'].iloc[-1].item()
        mm50_actual = df['MM50'].iloc[-1].item() if not pd.isna(df['MM50'].iloc[-1]) else None

        # ============================================================
        # 1️⃣ PRECIO CERCA DEL MÁXIMO (ajustado -3%)
        # ============================================================

        maximo_20 = df['Close'].tail(20).max().item()
        distancia_maximo_pct = ((precio_actual - maximo_20) / maximo_20) * 100

        precio_max_ok = distancia_maximo_pct >= -3.0
        motivos.append({
            "ok": precio_max_ok,
            "texto": f"Precio cerca máximo 20d ({distancia_maximo_pct:.2f}%)"
        })

        # ============================================================
        # 2️⃣ RESISTENCIA PRINCIPAL (ajustado +6%)
        # ============================================================

        resistencias = identificar_resistencias(df.tail(60))

        if not resistencias:
            return _respuesta_invalida(ticker, "No se detectaron resistencias claras",
                                       variacion_1d, precio_actual, motivos)

        resistencia_principal = resistencias[0]
        distancia_resistencia_pct = ((precio_actual - resistencia_principal) /
                                     resistencia_principal) * 100

        resistencia_ok = -3.0 <= distancia_resistencia_pct <= 6.0
        motivos.append({
            "ok": resistencia_ok,
            "texto": f"Distancia a resistencia ({distancia_resistencia_pct:.2f}%)"
        })

        # ============================================================
        # 3️⃣ CONSOLIDACIÓN (ajustado ≥ 8 días)
        # ============================================================

        consolidacion_dias = detectar_consolidacion(df.tail(40))
        consolidacion_ok = consolidacion_dias >= 8

        motivos.append({
            "ok": consolidacion_ok,
            "texto": f"Consolidación {consolidacion_dias} días"
        })

        # ============================================================
        # 4️⃣ VOLUMEN (1.2x IBEX, 1.1x Continuo)
        # ============================================================

        volumen_promedio = df['Volume'].rolling(20).mean().iloc[-1].item()
        volumen_3_velas = df['Volume'].tail(3).mean().item()
        ratio_volumen_3 = volumen_3_velas / volumen_promedio if volumen_promedio > 0 else 0

        # Continuo = tickers largos tipo "APAM.MC", IBEX = tickers cortos tipo "BBVA.MC"
        umbral_volumen = 1.1 if len(ticker.replace(".MC", "")) > 4 else 1.2

        volumen_ok = ratio_volumen_3 >= umbral_volumen
        motivos.append({
            "ok": volumen_ok,
            "texto": f"Volumen ruptura {ratio_volumen_3:.2f}x"
        })

        # ============================================================
        # 5️⃣ RSI (ajustado 50–82)
        # ============================================================

        rsi_ok = 50 <= rsi_actual <= 82
        motivos.append({
            "ok": rsi_ok,
            "texto": f"RSI momentum ({rsi_actual:.1f})"
        })

        # ============================================================
        # 6️⃣ ESTRUCTURA ALCISTA (sin cambios)
        # ============================================================

        estructura_ok = precio_actual >= mm20_actual * 0.98
        motivos.append({
            "ok": estructura_ok,
            "texto": "Precio > MM20"
        })

        if mm50_actual:
            estructura2_ok = mm20_actual >= mm50_actual * 0.98
            motivos.append({
                "ok": estructura2_ok,
                "texto": "MM20 > MM50"
            })
        else:
            estructura2_ok = True

        # ============================================================
        # VEREDICTO FINAL
        # ============================================================

        valido = all([m["ok"] for m in motivos])

        if not valido:
            return _respuesta_invalida(ticker, "Criterios técnicos no cumplidos",
                                       variacion_1d, precio_actual, motivos)

        # ============================================================
        # PLAN DE TRADING (RR 2.5 mantenido)
        # ============================================================

        minimo_consolidacion = df['Low'].tail(consolidacion_dias).min().item()
        stop_loss = minimo_consolidacion * 0.98
        riesgo_pct = ((precio_actual - stop_loss) / precio_actual) * 100

        objetivo = precio_actual + ((precio_actual - stop_loss) * 2.5)
        beneficio_pct = ((objetivo - precio_actual) / precio_actual) * 100
        rr = beneficio_pct / riesgo_pct if riesgo_pct > 0 else 0

        return {
            "valido": True,
            "variacion_1d": round(variacion_1d, 2),
            "ticker": ticker,
            "precio_actual": round(precio_actual, 2),
            "entrada": round(precio_actual, 2),
            "stop": round(stop_loss, 2),
            "objetivo": round(objetivo, 2),
            "riesgo_pct": round(riesgo_pct, 2),
            "beneficio_pct": round(beneficio_pct, 2),
            "rr": round(rr, 2),
            "setup_score": sum([m["ok"] for m in motivos]),
            "tipo": "BREAKOUT",
            "resistencia_rota": round(resistencia_principal, 2),
            "consolidacion_dias": consolidacion_dias,
            "volumen_ruptura": round(ratio_volumen_3, 2),
            "rsi": round(rsi_actual, 1),
            "atr": round(atr_actual, 2),
            "mm20": round(mm20_actual, 2),
            "mm50": round(mm50_actual, 2) if mm50_actual else None,
            "distancia_maximo_pct": round(distancia_maximo_pct, 2),
            "fecha": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "motivos": motivos
        }

    except Exception as e:
        return _respuesta_invalida(ticker, f"Error interno: {str(e)}")


# ============================================================
# RESPUESTA INVALIDA (coherente con escáner masivo)
# ============================================================

def _respuesta_invalida(ticker, motivo, variacion_1d=0, precio_actual=0, motivos_extra=None):
    motivos = motivos_extra if motivos_extra else []
    motivos.append({"ok": False, "texto": motivo})

    return {
        "valido": False,
        "ticker": ticker,
        "variacion_1d": round(variacion_1d, 2),
        "tipo": "BREAKOUT",
        "setup_score": 0,
        "rr": 0,
        "precio_actual": round(precio_actual, 2),
        "entrada": 0,
        "stop": 0,
        "objetivo": 0,
        "motivos": motivos
    }


# ============================================================
# FUNCIONES AUXILIARES (corregidas con .item())
# ============================================================

def identificar_resistencias(df, ventana=5, tolerancia=2.5):
    resistencias = []
    for i in range(ventana, len(df) - ventana):
        ventana_high = df['High'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['High'].iloc[i].item()
        if valor_actual == ventana_high.max().item():
            resistencias.append(valor_actual)

    if not resistencias:
        return []

    resistencias.sort(reverse=True)
    agrupadas = []

    for r in resistencias:
        if not agrupadas:
            agrupadas.append(r)
        else:
            if all(abs(r - ex) / ex * 100 >= tolerancia for ex in agrupadas):
                agrupadas.append(r)

    return agrupadas[:5]


def detectar_consolidacion(df):
    if len(df) < 10:
        return 0
    for ventana in range(min(30, len(df)), 9, -1):
        datos = df.tail(ventana)
        maximo = datos['High'].max().item()
        minimo = datos['Low'].min().item()
        if minimo == 0:
            continue
        rango_pct = ((maximo - minimo) / minimo) * 100
        if rango_pct <= 10:
            return ventana
    return 0


def calcular_atr(df, periodo=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(window=periodo).mean()


def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    avg_g = ganancia.rolling(window=periodo).mean()
    avg_p = perdida.rolling(window=periodo).mean()
    rs = avg_g / avg_p
    return 100 - (100 / (1 + rs))
