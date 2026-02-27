# ==========================================================
# DATOS - SISTEMA POSICIONAL
# Descarga y preparación de datos semanales
# ==========================================================

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Imports flexibles (funciona standalone y como módulo)
try:
    from .config_posicional import *
except ImportError:
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📥 DESCARGA DE DATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_datos_semanales(ticker, periodo_años=10, validar=True):
    """
    Descarga datos semanales. Fuente principal: EODHD. Fallback: yfinance.
    """
    import os
    import requests as req
    from datetime import datetime, timedelta, date

    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=periodo_años * 365)
    token = os.getenv("EODHD_API_TOKEN")

    print(f"\n[{fecha_fin.strftime('%Y-%m-%d %H:%M:%S')}] Descargando {ticker}...")

    df_diario = None

    # ── 1. EODHD ────────────────────────────────────────────────────
    if token and not ticker.startswith("^"):
        try:
            url = f"https://eodhd.com/api/eod/{ticker}"
            params = {"api_token": token, "period": "d", "fmt": "json", "order": "a"}
            r = req.get(url, params=params, timeout=25)
            r.raise_for_status()
            data = r.json()

            if not isinstance(data, list) or len(data) == 0:
                raise ValueError("Respuesta vacía EODHD")

            data = [row for row in data
                    if datetime.strptime(row["date"], "%Y-%m-%d") >= fecha_inicio]

            if len(data) < 50:
                raise ValueError(f"Pocos datos: {len(data)}")

            df_diario = pd.DataFrame({
                "Open":   [float(row.get("open")   or row["close"]) for row in data],
                "High":   [float(row.get("high")   or row["close"]) for row in data],
                "Low":    [float(row.get("low")    or row["close"]) for row in data],
                "Close":  [float(row.get("adjusted_close") or row["close"]) for row in data],
                "Volume": [float(row.get("volume") or 0) for row in data],
            }, index=pd.DatetimeIndex(
                [datetime.strptime(row["date"], "%Y-%m-%d") for row in data]
            ))

            # Completar con vela de hoy
            try:
                hoy = date.today()
                if df_diario.index[-1].date() < hoy:
                    tick = yf.Ticker(ticker)
                    vela = tick.history(period="1d", interval="1d")
                    if not vela.empty:
                        vela.index = vela.index.tz_localize(None)
                        if vela.index[-1].date() > df_diario.index[-1].date():
                            df_diario = pd.concat([df_diario, vela[["Open","High","Low","Close","Volume"]]])
                            df_diario = df_diario[~df_diario.index.duplicated(keep="last")]
                            print(f"[yfinance hoy] Vela añadida: {vela.index[-1].date()}")
            except Exception as e:
                print(f"[yfinance hoy posicional] Error: {e}")

            print(f"✅ EODHD OK: {len(df_diario)} días para {ticker}")

        except Exception as e:
            print(f"⚠️  EODHD falló ({e}) → yfinance...")
            df_diario = None

    # ── 2. Fallback yfinance ─────────────────────────────────────────
    if df_diario is None:
        try:
            session = req.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            })
            tick = yf.Ticker(ticker, session=session)
            df_diario = tick.history(
                start=fecha_inicio.strftime("%Y-%m-%d"),
                end=fecha_fin.strftime("%Y-%m-%d"),
                interval="1d"
            )
            if df_diario is None or df_diario.empty:
                print(f"❌ No hay datos para {ticker}")
                return None, {"errores": [f"No hay datos para {ticker}"]}
            if df_diario.index.tz is not None:
                df_diario.index = df_diario.index.tz_localize(None)
            print(f"✅ yfinance OK: {len(df_diario)} días para {ticker}")
        except Exception as e:
            print(f"❌ ERROR descargando {ticker}: {e}")
            return None, {"errores": [f"Error descargando {ticker}: {e}"]}

    # ── 3. Convertir diario → semanal ────────────────────────────────
    try:
        df_semanal = pd.DataFrame({
            "Open":   df_diario["Open"].resample("W-FRI").first(),
            "High":   df_diario["High"].resample("W-FRI").max(),
            "Low":    df_diario["Low"].resample("W-FRI").min(),
            "Close":  df_diario["Close"].resample("W-FRI").last(),
            "Volume": df_diario["Volume"].resample("W-FRI").sum(),
        }).dropna()
    except Exception as e:
        return None, {"errores": [f"Error convirtiendo a semanal: {e}"]}

    ultima_fecha = df_semanal.index[-1]
    dias_antiguedad = (fecha_fin - ultima_fecha).days
    print(f"✓ {len(df_semanal)} semanas | Última: {ultima_fecha.strftime('%Y-%m-%d')} ({dias_antiguedad}d)")

    # ── 4. Validar ───────────────────────────────────────────────────
    validacion = {}
    if validar:
        validacion = validar_datos(df_semanal, ticker)
        validacion["ultima_actualizacion"] = ultima_fecha.strftime("%Y-%m-%d")
        validacion["dias_antiguedad"] = dias_antiguedad
        if validacion.get("errores"):
            return None, validacion

    return df_semanal, validacion


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚡ PRECIO EN TIEMPO REAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_precio_tiempo_real(ticker):
    """
    Precio actual. Fuente principal: EODHD intraday. Fallback: yfinance.
    """
    import os
    import requests as req
    from datetime import date

    token = os.getenv("EODHD_API_TOKEN")

    # ── 1. EODHD precio del día ──────────────────────────────────────
    if token and not ticker.startswith("^"):
        try:
            url = f"https://eodhd.com/api/real-time/{ticker}"
            params = {"api_token": token, "fmt": "json"}
            r = req.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            precio = float(data.get("close") or data.get("last") or 0)
            anterior = float(data.get("previousClose") or precio)
            if precio > 0:
                variacion_pct = ((precio - anterior) / anterior) * 100
                print(f"⚡ Precio RT {ticker}: {precio:.2f}€ ({variacion_pct:+.2f}%) [EODHD]")
                return {
                    "precio":          round(precio, 2),
                    "hora":            data.get("timestamp", ""),
                    "fecha":           str(date.today()),
                    "variacion_pct":   round(variacion_pct, 2),
                    "cierre_anterior": round(anterior, 2),
                    "fuente":          "tiempo_real"
                }
        except Exception as e:
            print(f"⚠️  EODHD RT falló ({e}) → yfinance...")

    # ── 2. Fallback yfinance ─────────────────────────────────────────
    try:
        session = req.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })
        tick = yf.Ticker(ticker, session=session)
        df_d = tick.history(period="5d", interval="1d")

        if df_d is not None and not df_d.empty:
            if df_d.index.tz is not None:
                df_d.index = df_d.index.tz_localize(None)
            precio = float(df_d["Close"].iloc[-1])
            fecha  = df_d.index[-1].strftime("%Y-%m-%d")
            anterior = float(df_d["Close"].iloc[-2]) if len(df_d) >= 2 else precio
            variacion_pct = ((precio - anterior) / anterior) * 100
            print(f"📅 Precio cierre {ticker}: {precio:.2f}€ ({variacion_pct:+.2f}%) @ {fecha}")
            return {
                "precio":          round(precio, 2),
                "hora":            "cierre",
                "fecha":           fecha,
                "variacion_pct":   round(variacion_pct, 2),
                "cierre_anterior": round(anterior, 2),
                "fuente":          "ultimo_cierre"
            }
    except Exception as e:
        print(f"⚠️  No se pudo obtener precio RT para {ticker}: {e}")

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ VALIDACIÓN DE DATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validar_datos(df, ticker):
    """
    Valida calidad y suficiencia de datos.
    
    Returns:
        dict con errores, advertencias y validaciones
    """
    errores = []
    advertencias = []
    validaciones = []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. CANTIDAD DE DATOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    n_semanas = len(df)
    
    if n_semanas < MIN_SEMANAS_HISTORICO:
        errores.append(f"Histórico insuficiente: {n_semanas} semanas (mínimo {MIN_SEMANAS_HISTORICO})")
    else:
        validaciones.append(f"✅ {n_semanas} semanas de datos")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. CALIDAD DE DATOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Gaps extremos (>30%)
    returns = df['Close'].pct_change()
    gaps_grandes = returns[abs(returns) > 0.30]
    
    if len(gaps_grandes) > 0:
        advertencias.append(f"{len(gaps_grandes)} gaps semanales >30%")
    
    # Volumen cero
    vol_cero = (df['Volume'] == 0).sum()
    if vol_cero > 0:
        advertencias.append(f"{vol_cero} semanas sin volumen")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. LIQUIDEZ (para sistema posicional)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    precio_actual = df['Close'].iloc[-1]
    vol_medio_semanal = df['Volume'].mean()
    vol_medio_diario_aprox = vol_medio_semanal / 5  # Aprox
    valor_medio_diario = vol_medio_diario_aprox * precio_actual
    
    if valor_medio_diario < MIN_VOLUMEN_MEDIO_DIARIO:
        advertencias.append(f"Liquidez baja: {valor_medio_diario:,.0f}€/día (mínimo {MIN_VOLUMEN_MEDIO_DIARIO:,.0f})")
    else:
        validaciones.append(f"✅ Liquidez: {valor_medio_diario:,.0f}€/día")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. VOLATILIDAD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    volatilidad_anual = returns.std() * (52 ** 0.5) * 100
    
    if volatilidad_anual < MIN_VOLATILIDAD_PCT:
        advertencias.append(f"Volatilidad baja: {volatilidad_anual:.1f}% (mínimo {MIN_VOLATILIDAD_PCT}%)")
    else:
        validaciones.append(f"✅ Volatilidad: {volatilidad_anual:.1f}%")
    
    return {
        "errores": errores,
        "advertencias": advertencias,
        "validaciones": validaciones,
        "stats": {
            "n_semanas": n_semanas,
            "volatilidad_anual": round(volatilidad_anual, 1),
            "volumen_medio_diario": round(valor_medio_diario, 0),
            "precio_actual": round(precio_actual, 2)
        }
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 FILTRADO DE UNIVERSO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filtrar_universo_posicional(verbose=False):
    """
    Filtra IBEX 35 para obtener solo valores aptos para posicional.
    
    Criterios EQUILIBRADOS (ajustados para más oportunidades):
    - Capitalización > 12B€ (valores grandes)
    - Volumen medio > 6M€/día (buena liquidez)
    - Volatilidad > 22% (valores dinámicos)
    - Datos completos
    
    Returns:
        list de tickers aptos
    """
    valores_aptos = []
    
    if verbose:
        print(f"\n🔍 Filtrando universo IBEX 35 (EQUILIBRADO)...")
        print(f"   Criterios:")
        print(f"   - Min volatilidad: {MIN_VOLATILIDAD_PCT}%")
        print(f"   - Min volumen: {MIN_VOLUMEN_MEDIO_DIARIO/1_000_000:.0f}M€/día")
        print(f"   - Min capitalización: {MIN_CAPITALIZACION/1_000_000_000:.0f}B€")
        print(f"   - Min histórico: {MIN_SEMANAS_HISTORICO} semanas\n")
    
    for ticker in IBEX_35:
        if verbose:
            print(f"   Evaluando {ticker:12s} ...", end=" ")
        
        try:
            # Descargar datos
            df, validacion = obtener_datos_semanales(ticker, validar=True)
            
            if df is None:
                if verbose:
                    print(f"❌ Sin datos")
                continue
            
            # Verificar criterios básicos
            errores = validacion.get("errores", [])
            stats = validacion.get("stats", {})
            
            if errores:
                if verbose:
                    print(f"❌ {errores[0]}")
                continue
            
            # Obtener capitalización real
            ticker_obj = yf.Ticker(ticker)
            market_cap = None
            try:
                info = ticker_obj.info
                market_cap = info.get('marketCap', None)
            except:
                pass
            
            # Criterios de filtrado
            vol_ok = stats.get("volumen_medio_diario", 0) >= MIN_VOLUMEN_MEDIO_DIARIO
            volatilidad_ok = stats.get("volatilidad_anual", 0) >= MIN_VOLATILIDAD_PCT
            cap_ok = True  # Por defecto aceptar si no podemos obtener cap
            
            if market_cap is not None:
                cap_ok = market_cap >= MIN_CAPITALIZACION
            
            # Verificar TODOS los criterios
            if vol_ok and volatilidad_ok and cap_ok:
                valores_aptos.append(ticker)
                if verbose:
                    vol_str = f"{stats.get('volumen_medio_diario', 0)/1_000_000:.1f}M€"
                    vol_pct = f"{stats.get('volatilidad_anual', 0):.1f}%"
                    cap_str = f"{market_cap/1_000_000_000:.1f}B€" if market_cap else "N/A"
                    print(f"✅ APTO (Vol: {vol_str}, Volatilidad: {vol_pct}, Cap: {cap_str})")
            else:
                if verbose:
                    motivos = []
                    if not vol_ok:
                        vol_actual = stats.get('volumen_medio_diario', 0)
                        motivos.append(f"vol {vol_actual/1_000_000:.1f}M€")
                    if not volatilidad_ok:
                        vol_actual = stats.get('volatilidad_anual', 0)
                        motivos.append(f"volatilidad {vol_actual:.1f}%")
                    if not cap_ok and market_cap:
                        motivos.append(f"cap {market_cap/1_000_000_000:.1f}B€")
                    print(f"⚠️  {' | '.join(motivos)}")
        
        except Exception as e:
            if verbose:
                print(f"❌ Error: {str(e)[:30]}")
            continue
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ Universo filtrado: {len(valores_aptos)} valores aptos")
        if valores_aptos:
            print(f"\n📋 Valores seleccionados:")
            for i, ticker in enumerate(valores_aptos, 1):
                print(f"   {i:2d}. {ticker}")
        print(f"\n📊 Ratio: {len(valores_aptos)}/{len(IBEX_35)} = {len(valores_aptos)/len(IBEX_35)*100:.1f}%")
        print(f"{'='*60}\n")
    
    return valores_aptos


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test datos_posicional.py")
    print("=" * 60)
    
    # Test 1: Descargar un ticker
    print("\n📥 Test 1: Descarga de datos")
    ticker = "ITX.MC"
    df, validacion = obtener_datos_semanales(ticker)
    
    if df is not None:
        print(f"✅ {ticker}: {len(df)} semanas")
        print(f"   Desde: {df.index[0].date()}")
        print(f"   Hasta: {df.index[-1].date()}")
        
        if validacion.get("validaciones"):
            for v in validacion["validaciones"]:
                print(f"   {v}")
        
        if validacion.get("advertencias"):
            for a in validacion["advertencias"]:
                print(f"   ⚠️  {a}")
    else:
        print(f"❌ Error: {validacion.get('errores')}")
    
    # Test 2: Filtrar universo
    print("\n🔍 Test 2: Filtrado de universo")
    valores_aptos = filtrar_universo_posicional(verbose=True)
    
    print(f"\n📊 Resultado:")
    print(f"   Total IBEX 35: {len(IBEX_35)}")
    print(f"   Aptos posicional: {len(valores_aptos)}")
    print(f"   Ratio: {len(valores_aptos)/len(IBEX_35)*100:.1f}%")
