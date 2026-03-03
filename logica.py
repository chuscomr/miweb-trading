print(">>> logica.py CARGADO <<<")


import time
import random
from datetime import datetime, timedelta
import yfinance as yf
import os
import requests
import pandas as pd
import numpy as np  # ✅ AÑADIDO
MODO_SCAN = "SCAN"
MODO_TRADE = "TRADE"
from sistema_trading import sistema_trading, calcular_rsi_seguro

def _data_provider():
    return (os.getenv("DATA_PROVIDER", "yfinance") or "yfinance").strip().lower()


def obtener_precios_yfinance(ticker, cache, periodo="1y"):
    try:
        cache_key = f"precios_{ticker}_{periodo}"

        @cache.cached(timeout=600, key_prefix=cache_key)
        def descargar():
            print(f"Descargando datos (yfinance) de {ticker}...")
            # FIX RENDER: User-Agent para evitar bloqueo en IPs cloud
            _session = requests.Session()
            _session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            })
            _tick = yf.Ticker(ticker, session=_session)
            datos = _tick.history(period=periodo, interval="1d")
            if not datos.empty and datos.index.tz is not None:
                datos.index = datos.index.tz_localize(None)
            return datos

        datos = descargar()
        if datos is None or datos.empty:
            return None, None, None, None

        # Completar con cierre de hoy: FMP → yfinance
        try:
            from datetime import date as _date
            hoy = _date.today()
            ultima = datos.index[-1].date() if not datos.empty else None
            if ultima and ultima < hoy:
                vela_añadida = False
                fmp_key = os.getenv("FMP_API_KEY")
                if fmp_key:
                    try:
                        r_fmp = requests.get(
                            f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}",
                            params={"apikey": fmp_key, "from": hoy.strftime("%Y-%m-%d"), "to": hoy.strftime("%Y-%m-%d")},
                            timeout=10
                        )
                        if r_fmp.status_code == 200:
                            hist = r_fmp.json().get("historical", [])
                            if hist:
                                row = hist[0]
                                fecha_fmp = pd.Timestamp(row["date"])
                                if fecha_fmp.date() > ultima:
                                    nueva = pd.DataFrame({
                                        "Open": [float(row.get("open") or row["close"])],
                                        "High": [float(row.get("high") or row["close"])],
                                        "Low":  [float(row.get("low")  or row["close"])],
                                        "Close":[float(row["close"])],
                                        "Volume":[float(row.get("volume") or 0)]
                                    }, index=pd.DatetimeIndex([fecha_fmp]))
                                    datos = pd.concat([datos, nueva])
                                    datos = datos[~datos.index.duplicated(keep="last")]
                                    vela_añadida = True
                                    print(f"[FMP hoy] {ticker}: {row['close']} ({fecha_fmp.date()})")
                    except Exception as e_fmp:
                        print(f"[FMP hoy] Error: {e_fmp}")
                if not vela_añadida:
                    try:
                        _s2 = requests.Session()
                        _s2.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
                        _t2 = yf.Ticker(ticker, session=_s2)
                        vela_hoy = _t2.history(period="1d", interval="1d")
                        if not vela_hoy.empty:
                            if vela_hoy.index.tz is not None:
                                vela_hoy.index = vela_hoy.index.tz_localize(None)
                            if vela_hoy.index[-1].date() > ultima:
                                datos = pd.concat([datos, vela_hoy[["Open","High","Low","Close","Volume"]]])
                                datos = datos[~datos.index.duplicated(keep="last")]
                                print(f"[yfinance hoy] Vela añadida para {ticker}")
                    except Exception as e_yf:
                        print(f"[yfinance hoy] Error: {e_yf}")
        except Exception as e:
            print(f"[vela hoy] Error: {e}")

        close = datos["Close"]
        volume = datos["Volume"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        precios = close.dropna().tolist()
        volumenes = volume.dropna().tolist()
        fechas = close.index.to_pydatetime().tolist()
        precio_actual = precios[-1] if precios else None

        if len(precios) < 50:
            return None, None, None, None

        return precios, volumenes, fechas, precio_actual

    except Exception as e:
        print("Error descargando (yfinance):", ticker, e)
        return None, None, None, None


def obtener_precios_eodhd(ticker, cache, periodo="1y"):
    dias_map = {"6mo": 160, "1y": 260, "2y": 520, "5y": 1300}
    dias = dias_map.get(periodo, 260)
    try:
        token = os.getenv("EODHD_API_TOKEN")
        if not token:
            print("Falta EODHD_API_TOKEN")
            return None, None, None, None

        symbol = ticker
        
        # Blindaje: ^IBEX no es válido en EODHD (es formato Yahoo)
        if symbol.startswith("^"):
            print(f"Ticker {symbol} no compatible con EODHD, ignorando")
            return None, None, None, None

        cache_key = f"eod_{symbol}_{periodo}"

        @cache.cached(timeout=6 * 3600, key_prefix=cache_key)  # 6h
        def descargar():
            print(f"Descargando datos (EODHD) de {symbol}...")
            # FIX: fechas explícitas → EODHD devuelve histórico completo
            dias_map2 = {"6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
            _dias = dias_map2.get(periodo, 365)
            _fecha_fin = datetime.now()
            _fecha_ini = _fecha_fin - timedelta(days=_dias)
            url = f"https://eodhd.com/api/eod/{symbol}"
            params = {
                "api_token": token,
                "period": "d",
                "fmt": "json",
                "order": "a",
                "from": _fecha_ini.strftime("%Y-%m-%d"),
                "to":   _fecha_fin.strftime("%Y-%m-%d"),
            }
            r = requests.get(url, params=params, timeout=25)
            r.raise_for_status()
            return r.json()

        data = descargar()
        if not isinstance(data, list) or len(data) == 0:
            return None, None, None, None

        fechas = [datetime.strptime(row["date"], "%Y-%m-%d") for row in data]
        precios = [float(row.get("adjusted_close") or row["close"]) for row in data]
        volumenes = [float(row.get("volume") or 0) for row in data]

        # Completar con cierre de hoy: FMP → yfinance
        try:
            from datetime import date as _date
            hoy = _date.today()
            ultima_fecha = fechas[-1].date() if fechas else None
            if ultima_fecha and ultima_fecha < hoy:
                vela_añadida = False
                fmp_key = os.getenv("FMP_API_KEY")
                if fmp_key:
                    try:
                        r_fmp = requests.get(
                            f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}",
                            params={"apikey": fmp_key, "from": hoy.strftime("%Y-%m-%d"), "to": hoy.strftime("%Y-%m-%d")},
                            timeout=10
                        )
                        if r_fmp.status_code == 200:
                            hist = r_fmp.json().get("historical", [])
                            if hist:
                                row = hist[0]
                                fecha_fmp = datetime.strptime(row["date"], "%Y-%m-%d")
                                if fecha_fmp.date() > ultima_fecha:
                                    fechas.append(fecha_fmp)
                                    precios.append(float(row["close"]))
                                    volumenes.append(float(row.get("volume") or 0))
                                    vela_añadida = True
                                    print(f"[FMP hoy] {symbol}: {row['close']} ({fecha_fmp.date()})")
                    except Exception as e_fmp:
                        print(f"[FMP hoy] Error {symbol}: {e_fmp}")
                if not vela_añadida:
                    try:
                        _syf = requests.Session()
                        _syf.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
                        _tyf = yf.Ticker(ticker, session=_syf)
                        vela_hoy = _tyf.history(period="1d", interval="1d")
                        if not vela_hoy.empty:
                            if vela_hoy.index.tz is not None:
                                vela_hoy.index = vela_hoy.index.tz_localize(None)
                            f = vela_hoy.index[-1].to_pydatetime()
                            if f.date() > ultima_fecha:
                                fechas.append(f)
                                precios.append(float(vela_hoy["Close"].iloc[-1]))
                                volumenes.append(float(vela_hoy["Volume"].iloc[-1]))
                                print(f"[yfinance hoy] {symbol}: {precios[-1]} ({f.date()})")
                    except Exception as e_yf:
                        print(f"[yfinance hoy EODHD] Error: {e_yf}")
        except Exception as e:
            print(f"[vela hoy EODHD] Error: {e}")

        if len(precios) < 50:
            return None, None, None, None

        return precios, volumenes, fechas, precios[-1]

    except Exception as e:
        print("Error descargando (EODHD):", ticker, e)
        return None, None, None, None


def obtener_precios(ticker, cache, periodo="1y"):
    provider = _data_provider()
    print("USANDO PROVIDER =", provider, "ticker=", ticker, "periodo=", periodo)

    # ^IBEX siempre con yfinance, EODHD no lo soporta
    if ticker == "^IBEX":
        return obtener_precios_yfinance(ticker, cache, periodo)

    if provider == "eodhd":
        return obtener_precios_eodhd(ticker, cache, periodo)

    return obtener_precios_yfinance(ticker, cache, periodo)

# =============================
# 📊 UNIVERSOS
# =============================

IBEX35 = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","ANE.MC",
    "ENG.MC","FCC.MC","PUIG.MC","MTS.MC"
]

NOMBRES_IBEX = {
    "ACS.MC":"ACS","AENA.MC":"AENA","AMS.MC":"Amadeus","ANA.MC":"Acciona",
    "BBVA.MC":"BBVA","CABK.MC":"CaixaBank","ELE.MC":"Endesa","FER.MC":"Ferrovial",
    "GRF.MC":"Grifols","IBE.MC":"Iberdrola","IAG.MC":"IAG","IDR.MC":"Indra",
    "ITX.MC":"Inditex","MAP.MC":"Mapfre","MRL.MC":"Merlin",
    "NTGY.MC":"Naturgy","RED.MC":"Redeia","REP.MC":"Repsol","ROVI.MC":"Rovi",
    "SAB.MC":"Sabadell","SAN.MC":"Santander","SCYR.MC":"Sacyr","SLR.MC":"Solaria",
    "TEF.MC":"Telefónica","UNI.MC":"Unicaja","CLNX.MC":"Cellnex","LOG.MC":"Logista",
    "ACX.MC":"Acerinox","BKT.MC":"Bankinter","COL.MC":"Colonial","ANE.MC":"Acciona Energía",
    "ENG.MC":"Enagás","FCC.MC":"FCC","PUIG.MC":"PUIG","MTS.MC":"ARCELOR"
}

CONTINUO = [
    "CIE.MC","VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC",
    "PHM.MC","OHLA.MC","DOM.MC","ENC.MC","GRE.MC","ADX.MC","AUDAX",
    "HOME.MC","CIRSA.MC","FAE.MC","NEA.MC","PSG.MC","LDA.MC",
    "MEL.MC","VIS.MC","ECR.MC","ENO.MC","DIA.MC","IMC.MC","LIB.MC",
    "A3M.MC","ATRY.MC","R4.MC","RLIA.MC","MVC.MC","EBROM.MC","AMP.MC",
    "HBX.MC","CASH.MC","ADX.MC","AMP.MC","IZER.MC","AEDAS.MC"
    
]

NOMBRES_CONTINUO = {
    "CIE.MC":"CIE Automotive","VID.MC":"Vidrala",
    "TUB.MC":"Tubacex","TRE.MC":"Técnicas Reunidas","CAF.MC":"CAF",
    "GEST.MC":"Gestamp","APAM.MC":"Applus","PHM.MC":"PharmaMar",
    "OHLA.MC":"OHLA","DOM.MC":"Global Dominion",
    "ENC.MC":"ENCE","GRE.MC":"Grenergy","ADX.MC":"Audax Renovables",
    "HOME.MC":"Neinor Homes","NHH.MC":"NH Hotel Group","AMP.MC":"AMPER",
    "MEL.MC":"Meliá","VIS.MC":"Viscofan","ENO.MC":"Elecnor",
    "ECR.MC":"Ercros","A3M.MC":"Atresmedia","ATRY.MC":"Atrys Health",
    "R4.MC":"Renta 4","HBX.MC":"HBX Group","LIB.MC":"Libertas",
    "CASH.MC":"Cash Converters","NEA.MC":"Naturhouse",
    "PSG.MC":"Prosegur","AMP.MC":"Amper","MVC.MC":"Metrovacesa",
    "CIRSA.MC":"CIRSA","DIA.MC":"DIA","LDA.MC":"Linea Directa",
    "IMC.MC":"Inmocentro","FAE.MC":"Faes Farma","RLIA.MC":"Realia Business",
    "EBROM.MC":"Ebro Motor","IZER.MC":"Izertis","AEDAS.MC":"AEDAS Inmb."
}

# =============================
# FUNCIONES AUXILIARES
# =============================

def generar_grafico(precios, fechas, ticker, señal=None, entrada=None, stop=None):
    print(f"\n{'='*60}")
    print(f"[GENERAR_GRAFICO] INICIANDO con Plotly")
    print(f"Ticker: {ticker}")
    print(f"{'='*60}\n")

    if not precios or not fechas or len(precios) != len(fechas):
        return None

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        serie = pd.Series(precios, index=pd.DatetimeIndex(fechas))
        mm20 = serie.rolling(20).mean()

        # RSI
        rsi_valores = [np.nan] * len(precios)
        for i in range(14, len(precios)):
            rsi_calc = calcular_rsi_seguro(precios[:i+1])
            if rsi_calc is not None:
                rsi_valores[i] = rsi_calc
        rsi = pd.Series(rsi_valores, index=serie.index)

        # Color del título según señal
        color_titulo = "green" if señal == "COMPRA" else "orange" if señal == "VIGILANCIA" else "red"
        titulo = f"{ticker} – {señal or 'NO OPERAR'}"

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.05
        )

        # Precio
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values,
            name="Precio", line=dict(color="black", width=1.5)
        ), row=1, col=1)

        # MM20
        fig.add_trace(go.Scatter(
            x=mm20.index, y=mm20.values,
            name="MM20", line=dict(color="blue", width=1, dash="dash")
        ), row=1, col=1)

        # Entrada
        if entrada is not None:
            fig.add_hline(y=entrada, line_color="green", line_dash="dash",
                          line_width=1.5, annotation_text="Entrada",
                          annotation_position="right", row=1, col=1)

        # Stop
        if stop is not None:
            fig.add_hline(y=stop, line_color="red", line_dash="dash",
                          line_width=1.5, annotation_text="Stop",
                          annotation_position="right", row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(
            x=rsi.index, y=rsi.values,
            name="RSI", line=dict(color="orange", width=1.5)
        ), row=2, col=1)

        fig.add_hline(y=70, line_color="red", line_dash="dash", row=2, col=1)
        fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)

        fig.update_layout(
            title=dict(text=titulo, font=dict(color=color_titulo, size=14)),
            height=450,
            margin=dict(l=40, r=40, t=50, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        fig.update_yaxes(range=[0, 100], row=2, col=1)
        fig.update_xaxes(showgrid=True, gridcolor="lightgrey")
        fig.update_yaxes(showgrid=True, gridcolor="lightgrey")

        print(f"✅ [GENERAR_GRAFICO] Plotly OK")
        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    except Exception as e:
        print(f"❌ [GENERAR_GRAFICO] ERROR Plotly: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================
# 🧪 EVALUACIÓN TÉCNICA
# =============================

def alinear_series_por_fecha(precios, volumenes, fechas):
    """
    Alineación segura usando pandas para garantizar correspondencia temporal.
    Devuelve listas alineadas o ([], [], []) si no es posible.
    """
    try:
        # ─────────────────────────────
        # VALIDACIÓN DE CONTRATO
        # ─────────────────────────────
        if not precios or not volumenes or not fechas:
            return [], [], []

        if not (len(precios) == len(volumenes) == len(fechas)):
            print("⚠️ Alineamiento: longitudes no coinciden")
            return [], [], []

        # ─────────────────────────────
        # CONSTRUCCIÓN DATAFRAME
        # ─────────────────────────────
        df = pd.DataFrame(
            {
                "precio": precios,
                "volumen": volumenes
            },
            index=pd.DatetimeIndex(fechas)
        )

        # ─────────────────────────────
        # LIMPIEZA BÁSICA
        # ─────────────────────────────
        df = df[~df.index.duplicated(keep="last")]
        df = df.dropna(subset=["precio", "volumen"])
        df = df[df["precio"] > 0]
        df = df[df["volumen"] >= 0]

        # ─────────────────────────────
        # FILTRO DE GAPS EXTREMOS
        # ─────────────────────────────
        df["variacion"] = df["precio"].pct_change().abs()
        df = df[df["variacion"].isna() | (df["variacion"] < 0.30)]
        df = df.drop(columns=["variacion"])

        # ─────────────────────────────
        # ORDEN TEMPORAL
        # ─────────────────────────────
        df = df.sort_index()

        return (
            df["precio"].tolist(),
            df["volumen"].tolist(),
            df.index.to_pydatetime().tolist()
        )

    except Exception as e:
        print(f"⚠️ Error en alineamiento: {e}")
        return [], [], []


def evaluar_valor(precios, volumenes, fechas=None):
    """
    Evalúa un valor aplicando alineamiento seguro y el sistema de trading.
    """

    # ─────────────────────────────
    # ALINEAMIENTO SEGURO
    # ─────────────────────────────
    if fechas is not None and fechas:
        precios, volumenes, fechas = alinear_series_por_fecha(precios, volumenes, fechas)
    else:
        n = min(len(precios), len(volumenes))
        precios = precios[-n:]
        volumenes = volumenes[-n:]
        fechas = None

    # ─────────────────────────────
    # VALIDACIÓN MÍNIMA
    # ─────────────────────────────
    if not precios or len(precios) < 50:
        return {
            "decision": "NO OPERAR",
            "motivos": [{"ok": False, "texto": "Datos insuficientes"}],
            "tipo_entrada": None,
            "setup_score": 0,
            "setup_max": 5,
            "entrada_tecnica": None,
            "ultimo_cierre": None,
        }

    # ─────────────────────────────
    # SISTEMA DE TRADING
    # ─────────────────────────────
    if fechas:
        resultado = sistema_trading(precios, volumenes, fechas=fechas)
    else:
        resultado = sistema_trading(precios, volumenes)

    return {
        "decision": resultado.get("decision", "NO OPERAR"),
        "motivos": resultado.get("motivos", []),
        "tipo_entrada": resultado.get("tipo_entrada"),
        "setup_score": resultado.get("setup_score", 0),
        "setup_max": resultado.get("setup_max", 5),
        "entrada_tecnica": resultado.get("entrada"),
        "ultimo_cierre": precios[-1],
    }


# =============================
# 🛠️ HELPERS DE RIESGO
# =============================

def decision_final(resultado, precios, precios_ibex, contexto_mercado, modo=MODO_TRADE):
    señal = resultado.get("decision", "NO OPERAR")
    setup_score = resultado.get("setup_score", 0)
    motivos = list(resultado.get("motivos", []))

    # ─────────────────────────────
    # 🔍 MODO SCAN (EXPLORATORIO)
    # ─────────────────────────────
    if modo == MODO_SCAN:

        if señal == "COMPRA":
            # COMPRA clara → se muestra
            return "COMPRA", motivos

        # Setup en formación → vigilancia
        if setup_score >= 3:
            motivos.append({
                "ok": False,
                "texto": f"Setup en formación ({setup_score}/5)"
            })
            return "VIGILANCIA", motivos

        return "NO OPERAR", motivos

    # ─────────────────────────────
    # 💣 MODO TRADE (EJECUCIÓN)
    # ─────────────────────────────
    if señal != "COMPRA":
        return "NO OPERAR", motivos

    estado = contexto_mercado.get("estado", "RIESGO MEDIO")

    if estado == "RIESGO ALTO":
        if setup_score < 5:
            motivos.append({
                "ok": False,
                "texto": "🔴 RIESGO ALTO: requiere setup 5/5"
            })
            return "NO OPERAR", motivos

    if estado == "RIESGO MEDIO":
        if setup_score < 4:
            motivos.append({
                "ok": False,
                "texto": "🟠 RIESGO MEDIO: setup insuficiente"
            })
            return "VIGILANCIA", motivos

    return "COMPRA", motivos


def calcular_atr(precios, periodo=14):
    """
    Calcula ATR con validaciones robustas.
    """
    try:
        if not precios or len(precios) < periodo + 1:
            return None

        serie = pd.Series(precios, dtype=float)
        serie = serie.replace([np.inf, -np.inf], np.nan).dropna()

        if len(serie) < periodo + 1:
            return None

        variaciones = serie.pct_change().abs().dropna()

        if not variaciones.empty and (variaciones > 0.40).any():
            print("⚠️ ATR: Detectado gap >40%, datos anómalos")
            return None

        rangos = serie.diff().abs().dropna()

        if rangos.tail(periodo).eq(0).all():
            print("⚠️ ATR: Precio estático (sin movimiento)")
            return None

        atr_valor = rangos.tail(periodo).mean()
        precio_actual = serie.iloc[-1]

        if atr_valor <= 0 or precio_actual <= 0:
            return None

        atr_pct = (atr_valor / precio_actual) * 100

        if atr_pct > 15:
            print(f"⚠️ ATR anormalmente alto ({atr_pct:.1f}% del precio)")
            return None

        return round(float(atr_valor), 2)

    except Exception as e:
        print(f"❌ Error calculando ATR: {e}")
        return None


def calcular_stop_adaptativo(precios, entrada, setup_score, atr, min_reciente=None):
    """
    Calcula stop loss profesional con múltiples fallbacks.
    """
    if entrada is None or entrada <= 0:
        print(f"❌ Stop: Entrada inválida ({entrada})")
        return None

    setup_score = setup_score or 0
    stops_validos = []

    # ── MÉTODO 1: ATR
    stop_atr = None
    if atr and atr > 0:
        mult = 2.5 if setup_score >= 5 else 2.0 if setup_score >= 4 else 1.8
        stop_atr = entrada - (atr * mult)
        if stop_atr > 0:
            stops_validos.append(("ATR", stop_atr))

    # ── MÉTODO 2: VOLATILIDAD
    if precios and len(precios) >= 20:
        try:
            vol = np.std(precios[-20:])
            mult_vol = 2.0 if setup_score >= 4 else 1.5
            stop_vol = entrada - (vol * mult_vol)
            if stop_vol > 0:
                stops_validos.append(("Volatilidad", stop_vol))
        except:
            pass

    # ── MÉTODO 3: ESTRUCTURA
    if min_reciente and min_reciente > 0:
        stop_estructura = min_reciente * 0.995
        stops_validos.append(("Estructura", stop_estructura))

    # ── MÉTODO 4: FIJO (siempre existe)
    pct_fijo = 0.04 if setup_score >= 4 else 0.03
    stop_fijo = entrada * (1 - pct_fijo)
    stops_validos.append(("Fijo", stop_fijo))

    # ── SELECCIÓN INICIAL
    metodo_usado, stop_final = max(stops_validos, key=lambda x: x[1])

    riesgo_final = ((entrada - stop_final) / entrada) * 100

    # ── AJUSTES FINALES
    if riesgo_final > 5.0:
        stop_final = entrada * 0.95
        metodo_usado = "Limitado 5%"
        riesgo_final = 5.0

    if riesgo_final < 1.0:
        stop_final = entrada * 0.99
        metodo_usado = "Mínimo 1%"
        riesgo_final = 1.0

    if stop_final >= entrada:
        stop_final = entrada * 0.97
        metodo_usado = "Corrección 3%"

    print(f"✅ Stop FINAL: {stop_final:.2f}€ ({metodo_usado}, riesgo {riesgo_final:.1f}%)")

    return round(stop_final, 2)


def calcular_objetivo_adaptativo(entrada, riesgo_por_accion, atr, setup_score):
    """
    Calcula objetivo técnico con múltiples métodos.
    """
    if not entrada or entrada <= 0:
        return None

    if not riesgo_por_accion or riesgo_por_accion <= 0:
        return None

    setup_score = setup_score or 0

    rr_objetivo = 3.0 if setup_score >= 5 else 2.5 if setup_score >= 4 else 2.0
    objetivo_rr = entrada + (riesgo_por_accion * rr_objetivo)

    objetivo_atr = None
    if atr and atr > 0:
        mult_atr = 4.0 if setup_score >= 5 else 3.0 if setup_score >= 4 else 2.0
        objetivo_atr = entrada + (atr * mult_atr)

    if objetivo_atr:
        objetivo_final = min(objetivo_rr, objetivo_atr)
    else:
        objetivo_final = objetivo_rr

    minimo_aceptable = entrada + (riesgo_por_accion * 2.0)
    if objetivo_final < minimo_aceptable:
        objetivo_final = minimo_aceptable

    print(f"🎯 Objetivo: {objetivo_final:.2f}€")

    return round(objetivo_final, 2)


# =============================
# 🌍 CONTEXTO DE MERCADO
# =============================

def contexto_ibex(cache):
    # FIX RENDER: ^IBEX siempre con yfinance + User-Agent (EODHD no soporta ^IBEX)
    try:
        session_ibex = requests.Session()
        session_ibex.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })
        ibex_obj = yf.Ticker("^IBEX", session=session_ibex)
        datos_ibex = ibex_obj.history(period="1y", interval="1d")
        if not datos_ibex.empty and datos_ibex.index.tz is not None:
            datos_ibex.index = datos_ibex.index.tz_localize(None)
        precios = datos_ibex["Close"].dropna().tolist() if not datos_ibex.empty else []
        precio_actual = precios[-1] if precios else None
    except Exception as e:
        print(f"contexto_ibex error: {e}")
        precios = []
        precio_actual = None
    if not precios or len(precios) < 210 or precio_actual is None:
        return {"estado": "RIESGO MEDIO", "color": "grey", "texto": "IBEX sin datos suficientes"}
    if not precios or len(precios) < 210 or precio_actual is None:
        return {"estado": "RIESGO MEDIO", "color": "grey", "texto": "IBEX sin datos suficientes"}
    serie = pd.Series(precios, dtype=float).dropna()

    if len(serie) < 210:
        return {
            "estado": "RIESGO MEDIO",
            "color": "grey",
            "texto": "IBEX sin datos suficientes"
        }

    mm50 = serie.rolling(50).mean().iloc[-1]
    mm200 = serie.rolling(200).mean().iloc[-1]

    # Pendiente MM200 segura
    mm200_prev = serie.rolling(200).mean().iloc[-2]
    pendiente_mm200 = mm200 - mm200_prev if pd.notna(mm200_prev) else 0

    # ─────────────────────────────
    # CONTEXTO DE RIESGO
    # ─────────────────────────────
    if precio_actual < mm200 and pendiente_mm200 < 0:
        return {
            "estado": "RIESGO ALTO",
            "color": "red",
            "texto": "IBEX bajo MM200 y tendencia bajista"
        }

    if precio_actual > mm200 and pendiente_mm200 > 0 and precio_actual > mm50:
        return {
            "estado": "RIESGO BAJO",
            "color": "green",
            "texto": "IBEX alcista y con momentum"
        }

    return {
        "estado": "RIESGO MEDIO",
        "color": "orange",
        "texto": "IBEX en transición"
    }


def fuerza_relativa_ok(precios_valor, precios_ibex):
    """
    Comprueba si el valor tiene mejor comportamiento relativo que el IBEX.
    """
    if not precios_valor or not precios_ibex:
        return False

    if len(precios_valor) < 50 or len(precios_ibex) < 50:
        return False

    base_valor = precios_valor[-50]
    base_ibex = precios_ibex[-50]

    if base_valor <= 0 or base_ibex <= 0:
        return False

    rv = (precios_valor[-1] - base_valor) / base_valor
    ri = (precios_ibex[-1] - base_ibex) / base_ibex

    return rv > ri


# =============================
# 🔍 ESCÁNERES
# =============================

def escanear_ibex35(cache):
    print(">>> ESCANEAR IBEX EJECUTADO <<<")

    compras = []
    vigilancia = []

    # ─────────────────────────────
    # CONTEXTO IBEX (UNA SOLA VEZ)
    # ─────────────────────────────
    contexto = contexto_ibex(cache)
    precios_ibex, _, _, _ = obtener_precios("^IBEX", cache)

    if not precios_ibex or len(precios_ibex) < 50:
        print("⚠️ IBEX sin datos, usando contexto RIESGO MEDIO por defecto")
        precios_ibex = []
        contexto = {"estado": "RIESGO MEDIO", "color": "orange", "texto": "Sin datos IBEX"}

    # ─────────────────────────────
    # ESCÁNER VALORES
    # ─────────────────────────────
    for ticker in IBEX35:
        precios, volumenes, fechas, _ = obtener_precios(ticker, cache)

        if not precios or len(precios) < 50:
            continue

        resultado = evaluar_valor(precios, volumenes, fechas)
        decision, motivos = decision_final(resultado, precios, precios_ibex, contexto, modo=MODO_SCAN)

        nombre = NOMBRES_IBEX.get(ticker, ticker)

        if decision == "COMPRA":
            compras.append({
                "nombre": nombre,
                "ticker": ticker,
                "tipo": resultado.get("tipo_entrada"),
                "motivos": list(motivos),
                "setup_score": resultado.get("setup_score", 0),
                "setup_max": resultado.get("setup_max", 5),
            })

        elif decision == "VIGILANCIA":
            motivo_fallo = next(
                (m.get("texto") for m in motivos if not m.get("ok")),
                "Sin motivo claro"
            )

            vigilancia.append({
                "nombre": nombre,
                "ticker": ticker,
                "motivo": motivo_fallo,
                "setup_score": resultado.get("setup_score", 0),
                "setup_max": resultado.get("setup_max", 5),
            })

    compras.sort(key=lambda x: x["setup_score"], reverse=True)
    vigilancia.sort(key=lambda x: x["setup_score"], reverse=True)

    return {
        "compras": compras,
        "vigilancia": vigilancia,
        "total_compras": len(compras),
        "total_vigilancia": len(vigilancia),
    }


def escanear_continuo(cache):
    print(">>> ESCANEAR CONTINUO EJECUTADO <<<")

    compras = []
    vigilancia = []

    # ─────────────────────────────
    # CONTEXTO IBEX (UNA SOLA VEZ)
    # ─────────────────────────────
    contexto = contexto_ibex(cache)
    precios_ibex, _, _, _ = obtener_precios("^IBEX", cache)

    if not precios_ibex or len(precios_ibex) < 50:
        print("⚠️ IBEX sin datos, usando contexto RIESGO MEDIO por defecto")
        precios_ibex = []
    contexto = {"estado": "RIESGO MEDIO", "color": "orange", "texto": "Sin datos IBEX"}

    # ─────────────────────────────
    # ESCÁNER VALORES
    # ─────────────────────────────
    for ticker in CONTINUO:
        precios, volumenes, fechas, _ = obtener_precios(ticker, cache)

        if not precios or len(precios) < 50:
            continue

        resultado = evaluar_valor(precios, volumenes, fechas)
        decision, motivos = decision_final(resultado, precios, precios_ibex, contexto, modo=MODO_SCAN)

        nombre = NOMBRES_CONTINUO.get(ticker, ticker)

        if decision == "COMPRA":
            compras.append({
                "nombre": nombre,
                "ticker": ticker,
                "tipo": resultado.get("tipo_entrada"),
                "motivos": list(motivos),
                "setup_score": resultado.get("setup_score", 0),
                "setup_max": resultado.get("setup_max", 5),
            })

        elif decision == "VIGILANCIA":
            motivo_fallo = next(
                (m.get("texto") for m in motivos if not m.get("ok")),
                "Sin motivo claro"
            )

            vigilancia.append({
                "nombre": nombre,
                "ticker": ticker,
                "motivo": motivo_fallo,
                "setup_score": resultado.get("setup_score", 0),
                "setup_max": resultado.get("setup_max", 5),
            })

    compras.sort(key=lambda x: x["setup_score"], reverse=True)
    vigilancia.sort(key=lambda x: x["setup_score"], reverse=True)

    return {
        "compras": compras,
        "vigilancia": vigilancia,
        "total_compras": len(compras),
        "total_vigilancia": len(vigilancia),
    }


# =============================
# 🧪 BACKTESTING
# =============================

def backtesting_fase1(precios, volumenes, fechas,
                      capital_inicial=10_000,
                      riesgo_pct_trade=0.01):
    """
    Backtest Fase 1 PRO con alineamiento seguro
    """

    print(f"\n>>> ALINEANDO SERIES <<<")
    print(f"    Datos recibidos: {len(precios)} precios, {len(volumenes)} volumenes, {len(fechas)} fechas")

    precios, volumenes, fechas = alinear_series_por_fecha(precios, volumenes, fechas)

    # ─────────────────────────
    # VALIDACIÓN CRÍTICA
    # ─────────────────────────
    if not precios or not fechas or len(precios) < 50:
        print(f"❌ Datos insuficientes tras alineamiento")
        return {
            "capital_final": capital_inicial,
            "trades": [],
            "equity_curve": [],
            "metricas": {
                "total_trades": 0,
                "win_rate_pct": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "expectancy_R": 0,
                "max_drawdown_pct": 0,
                "retorno_pct": 0
            }
        }

    print(f"    ✅ Datos alineados: {len(precios)} velas válidas")
    print(f"    Rango: {fechas[0].strftime('%Y-%m-%d')} a {fechas[-1].strftime('%Y-%m-%d')}")

    # Aviso informativo (alineamiento ya corrige)
    if fechas != sorted(fechas):
        print("⚠️ ADVERTENCIA: Fechas no estaban ordenadas")

    gaps_dias = [(fechas[i + 1] - fechas[i]).days for i in range(len(fechas) - 1)]
    max_gap = max(gaps_dias) if gaps_dias else 0

    if max_gap > 10:
        print(f"⚠️ ADVERTENCIA: Gap temporal máximo detectado: {max_gap} días")

    capital = capital_inicial
    max_capital = capital_inicial
    max_drawdown = 0

    equity_curve = []
    trades = []

    en_posicion = False
    pos_actual = None
    ultimo_max_bloqueo = None
    trades_debuggeados = 0

    for i in range(50, len(precios)):
        precio_hoy = precios[i]
        fecha_hoy = fechas[i]

        # ─────────────────────────
        # GESTIÓN DE POSICIÓN ABIERTA
        # ─────────────────────────
        if en_posicion and pos_actual:
            pos_actual["max_precio"] = max(pos_actual["max_precio"], precio_hoy)

            R = pos_actual["entrada"] - pos_actual["stop_inicial"]  # riesgo por acción
            ganancia = precio_hoy - pos_actual["entrada"]
            R_actual = ganancia / R if R > 0 else 0

            atr = pos_actual.get("atr")

            # 🔍 DEBUG primeros trades
            if trades_debuggeados < 3 and pos_actual.get("debug_activo"):
                print(f"\n  📊 Gestión Trade #{len(trades) + 1} en {fecha_hoy.strftime('%Y-%m-%d')}")
                print(f"     Precio hoy: {precio_hoy:.2f}€")
                print(f"     Entrada: {pos_actual['entrada']:.2f}€")
                print(f"     Stop actual: {pos_actual['stop_actual']:.2f}€")
                print(f"     Max alcanzado: {pos_actual['max_precio']:.2f}€")
                print(f"     R actual: {R_actual:.2f}R")
                print(f"     Gestión: {pos_actual['gestion']}")

            # +1R → BE
            if R_actual >= 1.0 and pos_actual["stop_actual"] < pos_actual["entrada"]:
                pos_actual["stop_actual"] = pos_actual["entrada"]
                pos_actual["gestion"] = "Stop en BE (+1R)"

            # +2R → asegurar +1R
            elif R_actual >= 2.0 and pos_actual["stop_actual"] < pos_actual["entrada"] + R:
                pos_actual["stop_actual"] = pos_actual["entrada"] + R
                pos_actual["gestion"] = "Asegurado +1R (+2R)"

            # +3R → trailing ATR
            elif R_actual >= 3.0 and atr is not None and atr > 0:
                trailing_atr = pos_actual["max_precio"] - (atr * 2)
                pos_actual["stop_actual"] = max(pos_actual["stop_actual"], trailing_atr)
                pos_actual["gestion"] = "Trailing ATR (+3R)"

            # ❌ SALIDA POR STOP
            if precio_hoy <= pos_actual["stop_actual"]:
                beneficio = (precio_hoy - pos_actual["entrada"]) * pos_actual["acciones"]
                capital += beneficio
                max_capital = max(max_capital, capital)

                drawdown_actual = (max_capital - capital) / max_capital
                max_drawdown = max(max_drawdown, drawdown_actual)

                if pos_actual.get("debug_activo"):
                    print(f"\n  ❌ SALIDA POR STOP")
                    print(f"     Entrada: {pos_actual['entrada']:.2f}€")
                    print(f"     Salida: {precio_hoy:.2f}€")
                    print(f"     Beneficio: {beneficio:.2f}€")
                    print(f"     R alcanzado: {R_actual:.2f}R")
                    print(f"     Capital restante: {capital:.2f}€")
                    trades_debuggeados += 1

                trades.append({
                    "fecha_entrada": pos_actual["fecha_entrada"],
                    "fecha_salida": fecha_hoy,
                    "entrada": pos_actual["entrada"],
                    "salida": precio_hoy,
                    "beneficio": beneficio,
                    "R_alcanzado": round(R_actual, 2),
                    "gestion": pos_actual["gestion"],
                    "setup_score": pos_actual["setup_score"]
                })

                ultimo_max_bloqueo = pos_actual["max_precio"]
                en_posicion = False
                pos_actual = None

        # =========================
        # 🔍 BUSCAR NUEVA ENTRADA
        # =========================
        if not en_posicion:
            p = precios[:i+1]
            v = volumenes[:i+1]
            f = fechas[:i+1]

            señal = evaluar_valor(p, v, f)

            # ───────────────────────────────────────
            # 1️⃣ VALIDAR SEÑAL DE COMPRA
            # ───────────────────────────────────────
            if señal.get("decision") != "COMPRA":
                continue

            entrada = señal.get("entrada_tecnica")
            setup_score = señal.get("setup_score", 3) or 3

            # ───────────────────────────────────────
            # 2️⃣ VALIDAR ENTRADA TÉCNICA
            # ───────────────────────────────────────
            if entrada is None:
                if trades_debuggeados < 3:
                    print("\n⚠️ ENTRADA RECHAZADA: Sin entrada técnica definida")
                continue

            if entrada <= 0:
                if trades_debuggeados < 3:
                    print(f"\n⚠️ ENTRADA RECHAZADA: Entrada inválida ({entrada})")
                continue

            # ───────────────────────────────────────
            # 3️⃣ BLOQUEO DE REENTRADA
                  # ───────────────────────────────────────
            if ultimo_max_bloqueo and entrada <= ultimo_max_bloqueo:
                if trades_debuggeados < 3:
                    print(f"\n🔒 ENTRADA BLOQUEADA: Reentrada por debajo de máximo anterior")
                    print(f"   Entrada: {entrada:.2f}€ ≤ Último máx: {ultimo_max_bloqueo:.2f}€")
                continue

            # ───────────────────────────────────────
            # 4️⃣ CALCULAR ATR Y STOP
                  # ───────────────────────────────────────
            atr = calcular_atr(p)

            if atr is not None and atr > 0:
                mult_atr = 2.5 if setup_score >= 4 else 1.8
                stop = entrada - (atr * mult_atr)
            else:
                stop = entrada * 0.96

            # ───────────────────────────────────────
            # 5️⃣ VALIDAR STOP
                  # ───────────────────────────────────────
            if stop is None or stop <= 0:
                if trades_debuggeados < 3:
                    print(f"\n⚠️ ENTRADA RECHAZADA: Stop inválido ({stop})")
                continue

            if stop >= entrada:
                if trades_debuggeados < 3:
                    print(f"\n⚠️ ENTRADA RECHAZADA: Stop por encima de entrada")
                    print(f"   Entrada: {entrada:.2f}€, Stop: {stop:.2f}€")
                continue

            # ───────────────────────────────────────
            # 6️⃣ CALCULAR RIESGO
                  # ───────────────────────────────────────
            riesgo_por_accion = entrada - stop
            riesgo_pct = (riesgo_por_accion / entrada) * 100

            # ───────────────────────────────────────
            # 7️⃣ RIESGO MÍNIMO
            # ───────────────────────────────────────
            if riesgo_pct < 1.0:
                if trades_debuggeados < 3:
                    print(f"\n⚠️ ENTRADA RECHAZADA: Riesgo demasiado bajo ({riesgo_pct:.2f}%)")
                continue

            # ───────────────────────────────────────
            # 8️⃣ RIESGO MÁXIMO
            # ───────────────────────────────────────
            riesgo_max_permitido = 3.0 if setup_score >= 5 else 2.5

            if riesgo_pct > riesgo_max_permitido:
                if trades_debuggeados < 3:
                    print(f"\n⚠️ ENTRADA RECHAZADA: Riesgo excesivo ({riesgo_pct:.2f}%)")
                continue

            # ───────────────────────────────────────
            # 9️⃣ RIESGO VS ATR
                  # ───────────────────────────────────────
            if atr is not None and atr > 0:
                if riesgo_por_accion > atr * 3.5:
                    continue
                if riesgo_por_accion < atr * 0.8:
                    continue

            # ───────────────────────────────────────
            # 🔟 TAMAÑO DE POSICIÓN
            # ───────────────────────────────────────
            riesgo_monetario = capital * riesgo_pct_trade
            acciones = int(riesgo_monetario / riesgo_por_accion)

            if acciones <= 0:
                continue

            # ───────────────────────────────────────
            # 1️⃣1️⃣ EXPOSICIÓN DE CAPITAL
            # ───────────────────────────────────────
            if capital <= 0:
                continue

            capital_necesario = acciones * entrada
            exposicion_pct = (capital_necesario / capital) * 100

            exposicion_max = 35.0 if setup_score >= 5 else 25.0

            if exposicion_pct > exposicion_max:
                acciones_ajustadas = int((capital * (exposicion_max / 100)) / entrada)
                if acciones_ajustadas <= 0:
                    continue

                acciones = acciones_ajustadas
                capital_necesario = acciones * entrada

            # ───────────────────────────────────────
            # 1️⃣2️⃣ CAPITAL SUFICIENTE
                  # ───────────────────────────────────────
            if capital_necesario > capital:
                continue

            # ═══════════════════════════════════════
            # ✅ TODAS LAS VALIDACIONES PASADAS
            # ═══════════════════════════════════════

            # Logging detallado para primeros 3 trades
            if trades_debuggeados < 3:
                print(f"\n{'='*60}")
                print(f"🟢 NUEVA ENTRADA #{len(trades)+1}")
                print(f"{'='*60}")
                print(f"   📅 Fecha: {fecha_hoy.strftime('%Y-%m-%d')}")
                print(f"   💰 Precio actual: {precio_hoy:.2f}€")
                print(f"   📈 Entrada: {entrada:.2f}€")
                print(f"   🛑 Stop: {stop:.2f}€")
                print(f"   📊 ATR: {atr:.2f}€" if atr else "   📊 ATR: No disponible")
                print(f"   ⚠️  Riesgo/acción: {riesgo_por_accion:.2f}€ ({riesgo_pct:.2f}%)")
                print(f"   🎯 Setup: {setup_score}/5")
                print(f"   🔢 Acciones: {acciones}")
                print(f"   💵 Capital invertido: {capital_necesario:.2f}€ ({exposicion_pct:.1f}%)")
                print(f"   🎲 Riesgo total: {acciones * riesgo_por_accion:.2f}€")
                print(f"   💼 Capital disponible: {capital:.2f}€")
                print(f"{'='*60}\n")

            # ───────────────────────────────────────
            # ABRIR POSICIÓN
            # ───────────────────────────────────────
            en_posicion = True
            pos_actual = {
                "fecha_entrada": fecha_hoy,
                "entrada": entrada,
                "stop_inicial": stop,
                "stop_actual": stop,
                "acciones": acciones,
                "max_precio": entrada,
                "setup_score": setup_score,
                "gestion": "Inicial",
                "atr": atr,
                "riesgo_por_accion": riesgo_por_accion,
                "capital_invertido": capital_necesario,
                "debug_activo": trades_debuggeados < 3
            }

        # =========================
        # 📈 EQUITY CURVE
        # =========================
        drawdown_actual = (max_capital - capital) / max_capital if max_capital > 0 else 0

        equity_curve.append({
            "fecha": fecha_hoy,
            "capital": capital,
            "drawdown": drawdown_actual,
            "en_posicion": en_posicion
        })

    # =========================
    # CIERRE FINAL
    # =========================
    if en_posicion and pos_actual:
        precio_final = precios[-1]
        beneficio = (precio_final - pos_actual["entrada"]) * pos_actual["acciones"]
        capital += beneficio
        max_capital = max(max_capital, capital)

        riesgo_inicial = pos_actual["entrada"] - pos_actual["stop_inicial"]
        R_final = (precio_final - pos_actual["entrada"]) / riesgo_inicial if riesgo_inicial > 0 else 0

        trades.append({
            "fecha_entrada": pos_actual["fecha_entrada"],
            "fecha_salida": fechas[-1],
            "entrada": pos_actual["entrada"],
            "salida": precio_final,
            "beneficio": beneficio,
            "R_alcanzado": round(R_final, 2),
            "gestion": "Cierre final",
            "setup_score": pos_actual["setup_score"]
        })

    print(f"\n>>> BACKTEST FINALIZADO <<<")
    print(f"    Trades ejecutados: {len(trades)}")
    print(f"    Capital final: {capital:.2f}€")
    print(f"    Retorno: {((capital-capital_inicial)/capital_inicial*100):.2f}%\n")

    metricas = calcular_metricas_fase1(trades, equity_curve, capital_inicial, capital)

    return {
        "capital_final": capital,
        "trades": trades,
        "equity_curve": equity_curve,
        "metricas": metricas
    }


def calcular_metricas_fase1(trades, equity_curve, capital_inicial, capital_final):
    """
    Métricas profesionales del backtest (nivel institucional)
    """

    if not trades:
        return {
            "total_trades": 0,
            "win_rate_pct": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "expectancy_R": 0,
            "max_drawdown_pct": 0,
            "retorno_pct": 0
        }

    beneficios = [t["beneficio"] for t in trades]
    R_trades = [t.get("R_alcanzado", 0) for t in trades]

    ganadores = [b for b in beneficios if b > 0]
    perdedores = [b for b in beneficios if b < 0]

    total_trades = len(trades)

    # ─────────────────────────
    # Win rate
    # ─────────────────────────
    win_rate = len(ganadores) / total_trades * 100 if total_trades > 0 else 0

    # ─────────────────────────
    # Profit Factor
    # ─────────────────────────
    suma_ganancias = sum(ganadores)
    suma_perdidas = abs(sum(perdedores))

    if suma_perdidas > 0:
        profit_factor = suma_ganancias / suma_perdidas
    else:
        profit_factor = 99 if suma_ganancias > 0 else 0

    # ─────────────────────────
    # Expectancy
    # ─────────────────────────
    expectancy = sum(beneficios) / total_trades if total_trades > 0 else 0

    # Expectancy en R (CLAVE)
    expectancy_R = sum(R_trades) / total_trades if total_trades > 0 else 0

    # ─────────────────────────
    # Drawdown
    # ─────────────────────────
    max_dd = max((e.get("drawdown", 0) for e in equity_curve), default=0)

    # ─────────────────────────
    # Retorno total
    # ─────────────────────────
    retorno_pct = ((capital_final - capital_inicial) / capital_inicial) * 100 if capital_inicial > 0 else 0

    # ─────────────────────────
    # Métricas adicionales
    # ─────────────────────────
    avg_win = sum(ganadores) / len(ganadores) if ganadores else 0
    avg_loss = abs(sum(perdedores) / len(perdedores)) if perdedores else 0

    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0

    # Distribución por R
    trades_mayor_1R = len([r for r in R_trades if r >= 1])
    trades_menor_m1R = len([r for r in R_trades if r <= -1])

    pct_mayor_1R = trades_mayor_1R / total_trades * 100 if total_trades > 0 else 0
    pct_menor_m1R = trades_menor_m1R / total_trades * 100 if total_trades > 0 else 0

    return {
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
        "expectancy_R": round(expectancy_R, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "retorno_pct": round(retorno_pct, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "payoff_ratio": round(payoff_ratio, 2),
        "r_promedio": round(expectancy_R, 2),
        "pct_trades_>1R": round(pct_mayor_1R, 2),
        "pct_trades_<-1R": round(pct_menor_m1R, 2),
        "mejor_trade": round(max(beneficios), 2),
        "peor_trade": round(min(beneficios), 2),
    }


# =============================
# 🚀 FUNCIÓN PRINCIPAL
# =============================

def ejecutar_app(MODO, request, cache):
    # 🔍 DEBUG
    print(f">>> EJECUTAR_APP LLAMADO <<<")
    print(f"    Método: {request.method}")
    print(f"    Form keys: {list(request.form.keys())}")
    contexto_mercado = contexto_ibex(cache)

    # ────────────────────────────
    # VALORES POR DEFECTO
    # ────────────────────────────
    ticker = nombre_valor = None
    precios = volumenes = fechas = []
    precio_actual = precio_real = None
    precio_actual_mostrado = None  # ✅ AGREGADO

    señal = None
    motivos = []

    # Niveles técnicos (SIEMPRE definidos)
    max_reciente = None
    min_reciente = None
    mm_actual = None
    dist_max = None

    tipo_entrada = setup_score = setup_max = None

    entrada = stop = objetivo = None
    entrada_tecnica = None
    riesgo_por_accion = riesgo_pct = None
    beneficio_potencial = beneficio_pct = rr = None

    acciones = capital_invertido = riesgo_operacion = None
    gestion_R = None

    grafico_file = None

    capital_total = 10000
    riesgo_pct_trade = 1

    # ────────────────────────────
    # PROCESAMIENTO POST
    # ────────────────────────────
    if request.method == "POST":
         
        # ═══════════════════════════
        # BOTÓN BREAKOUT
        # ═══════════════════════════
        if "breakout" in request.form:
            print("🔥🔥🔥 ENTRÓ EN BREAKOUT 🔥🔥🔥")

            ticker = request.form.get("ticker", "").upper()
            if not ticker:
                return locals()

            from MiWeb.swing_trading.logica_breakout import detectar_breakout_swing

            resultado_dual = detectar_breakout_swing(ticker, periodo="6mo")

            # 🔐 Blindaje total
            if not isinstance(resultado_dual, dict):
                resultado_dual = {
                    "valido": False,
                    "motivos": [{
                        "ok": False,
                        "texto": "❌ Error analizando BREAKOUT"
                    }]
                }

            señal = "COMPRA" if resultado_dual.get("valido") else "NO OPERAR"

            # ✅ USAR SIEMPRE LOS MOTIVOS REALES
            motivos = resultado_dual.get("motivos", [])

            tipo_estrategia = "BREAKOUT"
            precios, volumenes, fechas, _ = obtener_precios(ticker, cache)
            grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)

            return locals()


        # ═══════════════════════════
        # BOTÓN PULLBACK
        # ═══════════════════════════
        if "pullback" in request.form:

            ticker = request.form.get("ticker", "").upper()
            if not ticker:
                return locals()

            from MiWeb.swing_trading.logica_pullback import detectar_pullback_swing

            resultado_dual = detectar_pullback_swing(ticker, periodo="2y")

            # 🔐 Blindaje total
            if not isinstance(resultado_dual, dict):
                resultado_dual = {
                    "valido": False,
                    "motivos": [{
                        "ok": False,
                        "texto": "❌ Error analizando PULLBACK"
                    }]
                }

            señal = "COMPRA" if resultado_dual.get("valido") else "NO OPERAR"

            # ✅ USAR SIEMPRE LOS MOTIVOS REALES
            motivos = resultado_dual.get("motivos", [])

            precios, volumenes, fechas, _ = obtener_precios(ticker, cache)
            grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)

            return locals()

        # ═══════════════════════════
        # ESCÁNER IBEX
        # ═══════════════════════════
        if "escanear_ibex" in request.form:
            escaneo_ibex = escanear_ibex35(cache)
            return locals()

        # ═══════════════════════════
        # ESCÁNER CONTINUO
        # ═══════════════════════════
        if "escanear_continuo" in request.form:
            escaneo_continuo = escanear_continuo(cache)
            return locals()

        # ═══════════════════════════
        # BACKTEST FASE 1
        # ═══════════════════════════
        if "backtest" in request.form:

            ticker = request.form.get("ticker", "").strip().upper()

            if not ticker:
                backtest_error = "❌ Introduce un ticker para ejecutar el backtest"
                backtest_metricas = None
                backtest_trades = None
                return locals()

            precios, volumenes, fechas, _ = obtener_precios(ticker, cache, periodo="5y")

            if not precios or len(precios) < 50:
                backtest_error = "❌ Datos insuficientes para backtesting"
                backtest_metricas = None
                backtest_trades = None
                return locals()

            print(f">>> EJECUTANDO BACKTEST PARA {ticker} <<<")
            print(f"    Precios: {len(precios)}, Volumenes: {len(volumenes)}, Fechas: {len(fechas)}")

            resultado_bt = backtesting_fase1(
                precios,
                volumenes,
                fechas,
                capital_inicial=10_000,
                riesgo_pct_trade=0.01
            )

            # ✅ ASIGNAR A VARIABLES QUE EL TEMPLATE PUEDE LEER
            backtest_metricas = resultado_bt["metricas"]
            backtest_trades = resultado_bt["trades"]
            backtest_equity = resultado_bt["equity_curve"]
            backtest_capital_final = resultado_bt["capital_final"]

            # ✅ MENSAJE DE DEBUG
            print(f">>> BACKTEST COMPLETADO <<<")
            print(f"    Trades: {backtest_metricas.get('total_trades', 0)}")
            print(f"    Win Rate: {backtest_metricas.get('win_rate_pct', 0)}%")
            print(f"    Capital Final: {backtest_capital_final}")

            # Nombre del valor
            nombre_valor = NOMBRES_IBEX.get(ticker, ticker)

            return locals()

        # ═══════════════════════════
        # ANALIZAR VALOR
        # ═══════════════════════════
        if "analizar" in request.form:

            ticker = request.form.get("ticker", "").upper()
            if not ticker:
                return locals()

            # Descargar datos
            precios, volumenes, fechas, precio_actual = obtener_precios(ticker, cache)

            if precios is None or len(precios) < 50:
                señal = "NO OPERAR"
                motivos = [{"ok": False, "texto": "Datos insuficientes"}]
                return locals()

            # Parámetros del formulario
            try:
                capital_total = float(request.form.get("capital_total", 10000))
                if capital_total <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                capital_total = 10000
                motivos.append({"ok": False, "texto": "⚠️ Capital inválido, usando 10,000€"})
            riesgo_pct_trade = float(request.form.get("riesgo_pct", 1))

            acciones_manual = request.form.get("acciones_manual")
            acciones_manual = int(acciones_manual) if acciones_manual else None

            precio_broker = request.form.get("precio_broker")
            precio_broker = float(precio_broker) if precio_broker else None

            precio_real = precio_broker if precio_broker else precio_actual

            precio_actual_mostrado = precio_real
            fuente_precio = "broker" if precio_broker else "yfinance"

            resultado = evaluar_valor(precios, volumenes, fechas)

            # Nombre del valor
            nombre_valor = NOMBRES_IBEX.get(ticker, ticker)

            # ───────────────────────────
            # EVALUACIÓN TÉCNICA (HISTÓRICO LIMPIO)
            # ───────────────────────────

            señal = resultado["decision"]
            motivos = resultado["motivos"]
            tipo_entrada = resultado.get("tipo_entrada")
            setup_score = resultado.get("setup_score", 0)
            setup_max = resultado.get("setup_max", 5)
            entrada_tecnica = resultado.get("entrada_tecnica")
            ultimo_cierre = resultado.get("ultimo_cierre")

            # ───────────────────────────
            # FILTRO CONTEXTO IBEX
            # ───────────────────────────
            if señal == "COMPRA":
                precios_ibex, _, _, _ = obtener_precios("^IBEX", cache)
                estado = contexto_mercado["estado"]

                if estado == "RIESGO ALTO" and precios_ibex and len(precios_ibex) >= 20:
                    rv = (precios[-1] - precios[-20]) / precios[-20] * 100
                    ri = (precios_ibex[-1] - precios_ibex[-20]) / precios_ibex[-20] * 100
                    ventaja = rv - ri

                    if setup_score < 5 or ventaja < 3:
                        señal = "NO OPERAR"
                        motivos.append({
                            "ok": False,
                            "texto": "🔴 RIESGO ALTO: setup o ventaja insuficiente"
                        })

                elif estado == "RIESGO MEDIO":
                    if setup_score < 4 or not fuerza_relativa_ok(precios, precios_ibex):
                        señal = "VIGILANCIA"
                        motivos.append({
                            "ok": False,
                            "texto": "⚠️ RIESGO MEDIO: requiere setup ≥4 y fuerza relativa"
                        })

                elif estado == "RIESGO BAJO" and setup_score < 3:
                    señal = "VIGILANCIA"
                    motivos.append({
                        "ok": False,
                        "texto": "ℹ️ RIESGO BAJO: setup inferior a 3"
                    })

            # ───────────────────────────
            # MÉTRICAS ADICIONALES
            # ───────────────────────────
            max_reciente = max(precios[-20:])
            min_reciente = min(precios[-20:])
            mm_actual = sum(precios[-20:]) / 20

            dist_max = (precio_real - max_reciente) / max_reciente * 100

            dist_min = (precio_real - min_reciente) / min_reciente * 100
            dist_mm  = (precio_real - mm_actual) / mm_actual * 100

            if señal != "COMPRA":
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            # ════════════
            # PLAN DE TRADING
            # ════════════
            
            # ───────────────────────────
            # CÁLCULO DISTANCIA AL MÁXIMO
            # ───────────────────────────
            if dist_max is None and max_reciente and max_reciente > 0 and precio_real:
                dist_max = (precio_real - max_reciente) / max_reciente * 100

            # ───────────────────────────
            # 1️⃣ ENTRADA – RECALCULAR si hay precio_broker
            # ───────────────────────────
            if precio_broker:
                # 🔄 RECALCULAR entrada usando precio_broker
                entrada = calcular_entrada_adaptativa(
                    precio_actual=precio_broker,
                    max_reciente=max_reciente,
                    dist_max=abs(dist_max) if dist_max is not None else None
                )
                
                # Informar que se está usando precio broker
                motivos.append({
                    "ok": True,
                    "texto": f"ℹ️ Usando precio broker ({precio_broker:.2f}€) para cálculo del plan"
                })
                
                # Si había entrada técnica diferente, informar
                if entrada_tecnica and abs(precio_broker - entrada_tecnica) > 0.01:
                    diff = ((precio_broker - entrada_tecnica) / entrada_tecnica) * 100
                    motivos.append({
                        "ok": True,
                        "texto": f"📊 Entrada técnica original: {entrada_tecnica:.2f}€ (dif: {diff:+.1f}%)"
                    })
            else:
                # No hay precio broker, usar lógica original
                if entrada_tecnica is not None and entrada_tecnica > 0:
                    entrada = entrada_tecnica
                else:
                    entrada = calcular_entrada_adaptativa(
                        precio_actual=precio_real,
                        max_reciente=max_reciente,
                        dist_max=abs(dist_max) if dist_max is not None else None
                    )

            # ✅ Validación crítica: entrada debe ser válida
            if entrada is None or entrada <= 0:
                señal = "NO OPERAR"
                motivos.append({
                    "ok": False,
                    "texto": "❌ No se pudo calcular entrada técnica válida"
                })
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            # ───────────────────────────
            # 2️⃣ CALCULAR ATR
                     # ───────────────────────────
            print(f"\n📊 Calculando ATR para {ticker}...")
            atr = calcular_atr(precios)

            if atr:
                print(f"✅ ATR calculado: {atr:.2f}€")
            else:
                print(f"⚠️ ATR no disponible, se usarán métodos alternativos")

            # ───────────────────────────
            # 3️⃣ CALCULAR STOP
                     # ───────────────────────────
            stop = calcular_stop_adaptativo(
                precios=precios,
                entrada=entrada,
                setup_score=setup_score,
                atr=atr,
                min_reciente=min_reciente
            )

            # Validación stop
            if stop is None or stop <= 0 or stop >= entrada:
                señal = "NO OPERAR"
                motivos.append({
                    "ok": False,
                    "texto": f"❌ Error calculando stop (entrada={entrada:.2f}, stop={stop})"
                })
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            # ───────────────────────────
            # 4️⃣ RIESGO Y TAMAÑO DE POSICIÓN
            # ───────────────────────────
            riesgo_por_accion = round(entrada - stop, 2)
            riesgo_pct = round((riesgo_por_accion / entrada) * 100, 2)

            if not (0.6 <= riesgo_pct <= 5.0):
                señal = "NO OPERAR"
                motivos.append({
                    "ok": False,
                    "texto": f"❌ Riesgo {riesgo_pct}% fuera de rango (0.6–5%)"
                })
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            riesgo_permitido = capital_total * riesgo_pct_trade / 100
            acciones = acciones_manual if acciones_manual else int(riesgo_permitido / riesgo_por_accion)

            if acciones <= 0:
                señal = "NO OPERAR"
                motivos.append({
                    "ok": False,
                    "texto": "❌ Tamaño de posición = 0"
                })
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            capital_invertido = round(acciones * entrada, 2)
            riesgo_operacion = round(acciones * riesgo_por_accion, 2)

            # ───────────────────────────
            # 5️⃣ GESTIÓN POR R
            # ───────────────────────────
            R = riesgo_por_accion
            gestion_R = {
                "R": R,
                "niveles": [
                    {"nivel": "+1R", "precio": round(entrada + R, 2), "accion": "mover stop a BE"},
                    {"nivel": "+2R", "precio": round(entrada + 2 * R, 2), "accion": "asegurar +1R"},
                    {"nivel": "+3R", "precio": round(entrada + 3 * R, 2), "accion": "trailing agresivo"}
                ]
            }

            # ───────────────────────────
            # 6️⃣ OBJETIVO
                     # ───────────────────────────
            objetivo = calcular_objetivo_adaptativo(
                entrada=entrada,
                riesgo_por_accion=riesgo_por_accion,
                atr=atr,
                setup_score=setup_score
            )

            if objetivo is None or objetivo <= entrada:
                objetivo = round(entrada + (riesgo_por_accion * 2.0), 2)

            beneficio_potencial = round(objetivo - entrada, 2)
            rr = round(beneficio_potencial / riesgo_por_accion, 2)

            if rr < 2.0:
                señal = "NO OPERAR"
                motivos.append({
                    "ok": False,
                    "texto": f"❌ R/R insuficiente ({rr:.1f})"
                })
                grafico_file = generar_grafico(precios, fechas, ticker, señal=señal)
                return locals()

            # ───────────────────────────
            # 7️⃣ GRÁFICO FINAL
            # ───────────────────────────
            grafico_file = generar_grafico(
                precios, fechas, ticker,
                señal=señal,
                entrada=entrada,
                stop=stop
            )

            print(f"\n✅ PLAN DE TRADING COMPLETADO")
            print(f"   Entrada: {entrada:.2f}€")
            print(f"   Stop: {stop:.2f}€")
            print(f"   Objetivo: {objetivo:.2f}€")
            print(f"   R/R: {rr:.1f}")
            print(f"   Acciones: {acciones}\n")

   # ✅ Asignar precio_actual_mostrado solo si fue definido
    if precio_actual_mostrado is not None:
        precio_actual = precio_actual_mostrado
    
    print(f"\n{'='*60}")
    print(f"[DEBUG FINAL]")
    print(f"ticker: {locals().get('ticker', 'NO DEFINIDO')}")
    print(f"grafico_file: {locals().get('grafico_file', 'NO DEFINIDO')}")
    print(f"señal: {locals().get('señal', 'NO DEFINIDO')}")
    if 'grafico_file' in locals():
        import os
        print(f"Archivo existe: {os.path.exists(locals()['grafico_file']) if locals()['grafico_file'] else False}")
    print(f"{'='*60}\n")
    
    return locals()
