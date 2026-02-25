"""
═══════════════════════════════════════════════════════════════
MÓDULO: DETECCIÓN DE PULLBACKS (REBOTES)
Sistema Swing Trading - Estrategia de Retrocesos
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio retrocede a un soporte
en una tendencia alcista establecida.

Filosofía: "Comprar barato en soporte"

Criterios específicos:
- Precio cerca de soporte (2-8%)
- Retroceso desde máximo reciente (5-15%)
- RSI bajo (< 45, sobreventa)
- Tendencia alcista macro (precio > MM200)
- Soporte histórico fuerte (3+ toques)
- Volumen decreciendo en caída
- Estructura alcista mantenida
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def f(x):
    return float(x.item() if hasattr(x, "item") else x)

def detectar_pullback_swing(ticker, periodo='1y'):

    motivos = []

    try:
        df = yf.download(ticker, period=periodo, progress=False)
        df = df.dropna()

        if df is None or len(df) < 100:
            return {
                "valido": False,
                "motivos": [{"ok": False, "texto": "Datos insuficientes (requiere 100+ días)"}],
                "tipo": "PULLBACK",
                "ticker": ticker,
                "variacion_1d": 0,
                "setup_score": 0,
                "rr": 0,
                "precio_actual": 0,
                "entrada": 0,
                "stop": 0,
                "objetivo": 0
            }
        if len(df) < 2:
            variacion_1d = 0
        else:
            variacion_1d = f((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100)

        # ─────────────────────────────
        # INDICADORES
        # ─────────────────────────────
        df['MM20'] = df['Close'].rolling(20).mean()
        df['MM50'] = df['Close'].rolling(50).mean()
        df['MM200'] = df['Close'].rolling(200).mean()
        df['ATR'] = calcular_atr(df, periodo=14)
        df['RSI'] = calcular_rsi(df['Close'], periodo=14)

        precio_actual = f(df['Close'].iloc[-1])
        rsi_actual = f(df['RSI'].iloc[-1])
        mm200_actual = f(df['MM200'].iloc[-1])
        mm20_actual = f(df['MM20'].iloc[-1])
        mm50_actual = f(df['MM50'].iloc[-1])

        # ─────────────────────────────
        # 1️⃣ Tendencia alcista macro
              # ─────────────────────────────
        tendencia_ok = precio_actual > mm200_actual * 0.95
        motivos.append({
            "ok": tendencia_ok,
            "texto": f"Precio vs MM200 ({precio_actual:.2f}€ vs {mm200_actual:.2f}€)"
        })

        # ─────────────────────────────
        # 2️⃣ Retroceso desde máximo
        # ─────────────────────────────
        maximo_60 = float(df['Close'].tail(60).max().item())
        retroceso_pct = ((maximo_60 - precio_actual) / maximo_60) * 100

        retroceso_ok = 5 <= retroceso_pct <= 20
        motivos.append({
            "ok": retroceso_ok,
            "texto": f"Retroceso {retroceso_pct:.2f}% desde máximo"
        })

        # ─────────────────────────────
        # 3️⃣ RSI sobreventa moderada
              # ─────────────────────────────
        rsi_ok = rsi_actual <= 50
        motivos.append({
            "ok": rsi_ok,
            "texto": f"RSI {rsi_actual:.1f}"
        })

        # ─────────────────────────────
        # 4️⃣ Soporte cercano
              # ─────────────────────────────
        minimo_30 = f(df['Low'].tail(30).min())
        distancia_soporte_pct = ((precio_actual - minimo_30) / precio_actual) * 100

        soporte_ok = 2 <= distancia_soporte_pct <= 8
        motivos.append({
            "ok": soporte_ok,
            "texto": f"Distancia a soporte {distancia_soporte_pct:.2f}%"
        })

        # ─────────────────────────────
        # 5️⃣ Estructura alcista
              # ─────────────────────────────
        estructura_ok = precio_actual > mm20_actual > mm50_actual
        motivos.append({
            "ok": estructura_ok,
            "texto": "Estructura: Precio > MM20 > MM50"
        })

        # ─────────────────────────────
        # VEREDICTO FINAL
        # ─────────────────────────────
        valido = all([m["ok"] for m in motivos])

        if not valido:
            return {
                "valido": False,
                "ticker": ticker,
                "variacion_1d": round(variacion_1d, 2),
                "tipo": "PULLBACK",
                "setup_score": 0,
                "rr": 0,
                "precio_actual": round(precio_actual, 2),
                "entrada": 0,
                "stop": 0,
                "objetivo": 0,
                "motivos": motivos
            }

        # ─────────────────────────────
        # PLAN DE TRADING
        # ─────────────────────────────
        stop_loss = minimo_30 * 0.98
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
            "tipo": "PULLBACK",
            "motivos": motivos
        }

    except Exception as e:
        return {
            "valido": False,
            "motivos": [{"ok": False, "texto": f"Error interno: {str(e)}"}],
            "ticker": ticker,
            "variacion_1d": 0,
            "tipo": "PULLBACK",
            "setup_score": 0,
            "rr": 0,
            "precio_actual": 0,
            "entrada": 0,
            "stop": 0,
            "objetivo": 0
        }


def identificar_soportes(df, ventana=5, tolerancia=2.5):
    """
    Identifica niveles de soporte (mínimos locales)
    
    Args:
        df: DataFrame con precios
        ventana: Ventana para detectar mínimos locales
        tolerancia: % para agrupar niveles cercanos
    
    Returns:
        Lista de dict con soportes {nivel, toques}
    """
    soportes = []
    
    # Detectar mínimos locales
    for i in range(ventana, len(df) - ventana):
        ventana_low = df['Low'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['Low'].iloc[i]
        
        if isinstance(valor_actual, pd.Series):
            valor_actual = valor_actual.item()
        
        min_ventana = ventana_low.min()
        if isinstance(min_ventana, pd.Series):
            min_ventana = min_ventana.item()
        
        if float(valor_actual) == float(min_ventana):
            soportes.append(float(valor_actual))
    
    if not soportes:
        return []
    
    # Agrupar soportes cercanos y contar toques
    soportes.sort()
    soportes_agrupados = []
    
    for s in soportes:
        if not soportes_agrupados:
            soportes_agrupados.append({'nivel': s, 'toques': 1})
        else:
            # Verificar si está cerca de algún soporte ya agrupado
            encontrado = False
            for s_grupo in soportes_agrupados:
                distancia = abs(s - s_grupo['nivel']) / s_grupo['nivel'] * 100
                if distancia < tolerancia:
                    # Actualizar nivel promedio y sumar toque
                    s_grupo['nivel'] = (s_grupo['nivel'] * s_grupo['toques'] + s) / (s_grupo['toques'] + 1)
                    s_grupo['toques'] += 1
                    encontrado = True
                    break
            
            if not encontrado:
                soportes_agrupados.append({'nivel': s, 'toques': 1})
    
    # Ordenar por número de toques (más fuertes primero)
    soportes_agrupados.sort(key=lambda x: x['toques'], reverse=True)
    
    return soportes_agrupados[:5]  # Top 5


def identificar_resistencias(df, ventana=5, tolerancia=2.5):
    """
    Identifica niveles de resistencia (máximos locales)
    Similar a identificar_soportes pero con máximos
    """
    resistencias = []
    
    for i in range(ventana, len(df) - ventana):
        ventana_high = df['High'].iloc[i-ventana:i+ventana+1]
        valor_actual = df['High'].iloc[i]
        
        if isinstance(valor_actual, pd.Series):
            valor_actual = valor_actual.item()
        
        max_ventana = ventana_high.max()
        if isinstance(max_ventana, pd.Series):
            max_ventana = max_ventana.item()
        
        if float(valor_actual) == float(max_ventana):
            resistencias.append(float(valor_actual))
    
    if not resistencias:
        return []
    
    # Agrupar resistencias cercanas
    resistencias.sort(reverse=True)
    resistencias_agrupadas = []
    
    for r in resistencias:
        if not resistencias_agrupadas:
            resistencias_agrupadas.append({'nivel': r, 'toques': 1})
        else:
            encontrado = False
            for r_grupo in resistencias_agrupadas:
                distancia = abs(r - r_grupo['nivel']) / r_grupo['nivel'] * 100
                if distancia < tolerancia:
                    r_grupo['nivel'] = (r_grupo['nivel'] * r_grupo['toques'] + r) / (r_grupo['toques'] + 1)
                    r_grupo['toques'] += 1
                    encontrado = True
                    break
            
            if not encontrado:
                resistencias_agrupadas.append({'nivel': r, 'toques': 1})
    
    return resistencias_agrupadas[:5]


def calcular_rsi(series, periodo=14):
    """
    Calcula RSI (Relative Strength Index)
    """
    delta = series.diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    
    avg_ganancia = ganancia.rolling(window=periodo).mean()
    avg_perdida = perdida.rolling(window=periodo).mean()
    
    rs = avg_ganancia / avg_perdida
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def escanear_mercado_pullback(tickers_list):
    """
    Escanea lista de tickers buscando oportunidades PULLBACK
    
    Args:
        tickers_list: Lista de tickers
    
    Returns:
        Lista de señales ordenadas por setup_score
    """
    señales = []
    
    print(f"\n🔍 Escaneando {len(tickers_list)} valores buscando PULLBACKS...\n")
    
    for ticker in tickers_list:
        try:
            señal = detectar_pullback_swing(ticker)
            if señal and isinstance(señal, dict) and señal.get("valido"):
                señales.append(señal)

                print(f"✅ {ticker}: PULLBACK detectado (Score: {señal['setup_score']}/10, RR: {señal['rr']})")
        except Exception as e:
            print(f"❌ {ticker}: Error - {str(e)}")
    
    # Ordenar por setup_score descendente
    señales.sort(key=lambda x: x['setup_score'], reverse=True)
    
    print(f"\n📊 Total señales PULLBACK: {len(señales)}")
    
    return señales

def calcular_atr(df, periodo=14):

    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=periodo).mean()

    return atr

# ═══════════════════════════════════════════════════════════════
# TESTING - Ejemplo de uso
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    print("═" * 60)
    print("SISTEMA DE DETECCIÓN DE PULLBACKS")
    print("Estrategia: Rebotes en soportes")
    print("═" * 60)
    
    # Test con valores individuales
    tickers_test = ['TEF.MC', 'SAN.MC', 'BBVA.MC', 'IBE.MC', 'REP.MC']
    
    señales = escanear_mercado_pullback(tickers_test)
    
    if señales:
        print("\n" + "=" * 60)
        print("SEÑALES DETECTADAS:")
        print("=" * 60)
        
        for señal in señales:
            print(f"\n{señal['ticker']}:")
            print(f"  Entrada:     {señal['entrada']}€")
            print(f"  Stop:        {señal['stop']}€ (-{señal['riesgo_pct']}%)")
            print(f"  Objetivo:    {señal['objetivo']}€ (+{señal['beneficio_pct']}%)")
            print(f"  RR:          {señal['rr']}")
            print(f"  Setup Score: {señal['setup_score']}/10")
            
    else:
        print("\n⚠️  No se detectaron oportunidades PULLBACK en este momento")
