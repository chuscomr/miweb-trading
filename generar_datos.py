from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import json

# ⚠️ IMPORTAMOS TU SISTEMA LOCAL TAL CUAL
from sistema_trading import sistema_trading


# ======================================================
# UNIVERSOS
# ======================================================

IBEX35 = [
    "ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC",
    "GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MEL.MC","MRL.MC",
    "NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC",
    "TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","CIE.MC",
    "ENG.MC","FCC.MC","PUIG.MC"
]

CONTINUO = [
    "ACX.MC","CIE.MC","VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC",
    "PHM.MC","SCYR.MC","OHLA.MC","DOM.MC","ENC.MC","GRE.MC","AUD.MC","ANE.MC",
    "COL.MC","MRL.MC","LRE.MC","HOME.MC","NHH.MC","LAR.MC",
    "MEL.MC","VIS.MC","ZOT.MC","ECR.MC",
    "A3M.MC","ATRY.MC","R4.MC","GCO.MC",
    "HBX.MC","TCO.MC","CASH.MC",
    "NEA.MC","PSG.MC","AMP.MC","MTS.MC"
]


# ======================================================
# OBTENER PRECIOS
# ======================================================

def obtener_precios(ticker):
    hora_precio = (datetime.now() - timedelta(minutes=15)).strftime("%H:%M")

    df = yf.download(
        ticker,
        period="3y",
        interval="1d",
        progress=False
    )

    if df is None or df.empty:
        return None, None, None

    close = df["Close"]
    volume = df["Volume"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
        volume = volume.iloc[:, 0]

    precios = close.dropna().tolist()
    volumenes = volume.dropna().tolist()

    return precios, volumenes, hora_precio


# ======================================================
# INDICADORES SOLO PARA WEB (DESCRIPTIVOS)
# ======================================================

def calcular_indicadores_web(precios):
    if len(precios) < 20:
        return {
            "mm20": None,
            "max_reciente": None,
            "volatilidad": None
        }

    ventana = precios[-20:]
    mm20 = sum(ventana) / 20
    max20 = max(ventana)
    min20 = min(ventana)

    volatilidad = (
        (max20 - min20) / min20 * 100
        if min20 != 0 else None
    )

    return {
        "mm20": round(mm20, 2),
        "max_reciente": round(max20, 2),
        "volatilidad": round(volatilidad, 2) if volatilidad else None
    }


# ======================================================
# ADAPTADOR → JSON WEB (CLAVE)
# ======================================================

def adaptar_a_web(resultado_local, precios, hora_precio):

    indicadores = calcular_indicadores_web(precios)

    return {
        # Resultado del sistema LOCAL
        "decision": resultado_local.get("decision", "NO OPERAR"),
        "motivos": resultado_local.get("motivos", []),

        # Precio actual
        "precio": round(precios[-1], 2),
        "hora": hora_precio,

        # Indicadores VISUALES (siempre presentes)
        "mm20": indicadores["mm20"],
        "max_reciente": indicadores["max_reciente"],
        "volatilidad": indicadores["volatilidad"]
    }


# ======================================================
# PROCESAR UNIVERSO
# ======================================================

def procesar_universo(lista_tickers, resultado):
    for ticker in lista_tickers:
        try:
            precios, volumenes, hora_precio = obtener_precios(ticker)

            if precios is None or volumenes is None or len(precios) < 50:
                print(f"❌ Sin datos válidos para {ticker}")
                continue

            # ⚠️ AQUÍ USAMOS TU SISTEMA LOCAL SIN TOCARLO
            resultado_local = sistema_trading(precios, volumenes)

            # Adaptamos SOLO para la web
            resultado[ticker] = adaptar_a_web(
                resultado_local,
                precios,
                hora_precio
            )

            print(f"✔ {ticker} → {resultado[ticker]['decision']}")

        except Exception as e:
            print(f"⚠️ Error en {ticker}: {e}")


# ======================================================
# GENERAR JSON FINAL
# ======================================================

resultado = {}

procesar_universo(IBEX35, resultado)
procesar_universo(CONTINUO, resultado)

# ------------------------------------------------------
# METADATOS
# ------------------------------------------------------

ahora = datetime.now()

resultado["__meta__"] = {
    "fecha": ahora.strftime("%d/%m/%Y"),
    "hora": ahora.strftime("%H:%M"),
    "timezone": "local",
    "mercado_abierto": True,
    "fuente": "generar_datos.py"
}

# ------------------------------------------------------
# GUARDAR ARCHIVO
# ------------------------------------------------------

with open("datos_trading.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, indent=4, ensure_ascii=False)

print("\n✔ datos_trading.json generado correctamente")
print(f"✔ Total valores: {len(resultado) - 1}")
print(f"✔ Hora: {ahora.strftime('%H:%M:%S')}")
