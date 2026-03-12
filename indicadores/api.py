# api.py

from flask import request, jsonify
import yfinance as yf
import pandas as pd
import os
import requests
import time

from .nucleo.calculos import aplicar_indicadores
from .utilidades.serializador import preparar_para_json, formatear_niveles_sr, formatear_patrones
from .routes import indicadores_bp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCARGA DE DATOS MULTI-PROVEEDOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _descargar_datos(ticker, timeframe):

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ FMP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    fmp_key = os.getenv("FMP_API_KEY")

    if fmp_key and timeframe == "1d":

        try:

            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"

            r = requests.get(url, params={"apikey": fmp_key}, timeout=15)

            if r.status_code == 200:

                data = r.json()

                hist = data.get("historical")

                if hist:

                    df = pd.DataFrame(hist)

                    df["date"] = pd.to_datetime(df["date"])

                    df = df.set_index("date")

                    df = df.rename(columns={
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume"
                    })

                    df = df.sort_index()

                    print("📊 Datos desde FMP")

                    return df[["Open","High","Low","Close","Volume"]]

        except Exception as e:

            print("FMP falló:", e)


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ EODHD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    token = os.getenv("EODHD_API_TOKEN")

    if token and timeframe == "1d":

        try:

            url = f"https://eodhd.com/api/eod/{ticker}"

            params = {
                "api_token": token,
                "period": "d",
                "fmt": "json",
                "order": "a"
            }

            r = requests.get(url, params=params, timeout=20)

            r.raise_for_status()

            data = r.json()

            if isinstance(data, list) and len(data) >= 50:

                df = pd.DataFrame(data)

                df["Date"] = pd.to_datetime(df["date"])

                df = df.set_index("Date")

                factor = df["adjusted_close"].astype(float) / df["close"].astype(float)

                df["Close"] = df["adjusted_close"].astype(float)

                df["Open"] = df["open"].astype(float) * factor

                df["High"] = df["high"].astype(float) * factor

                df["Low"] = df["low"].astype(float) * factor

                df["Volume"] = df["volume"].astype(float)

                print("📊 Datos desde EODHD")

                return df[["Open","High","Low","Close","Volume"]]

        except Exception as e:

            print("EODHD falló:", e)


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ Yahoo Finance (.MC)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    for intento in range(2):

        try:

            ticker_obj = yf.Ticker(ticker)

            df = ticker_obj.history(
                period="1y",
                interval=timeframe,
                auto_adjust=True
            )

            if not df.empty:

                print("📊 Datos desde Yahoo (.MC)")

                return df

        except Exception as e:

            print(f"Yahoo intento {intento+1} falló:", e)

        time.sleep(1)


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4️⃣ Yahoo fallback sin ".MC"
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if ticker.endswith(".MC"):

        ticker_alt = ticker.replace(".MC","")

        try:

            ticker_obj = yf.Ticker(ticker_alt)

            df = ticker_obj.history(
                period="1y",
                interval=timeframe,
                auto_adjust=True
            )

            if not df.empty:

                print("📊 Datos desde Yahoo (sin .MC)")

                return df

        except Exception as e:

            print("Yahoo fallback falló:", e)


    print("❌ Ningún proveedor devolvió datos")

    return pd.DataFrame()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@indicadores_bp.route("/api")

def api_indicadores():

    ticker = request.args.get("ticker")

    timeframe = request.args.get("tf", "1d")

    indicadores = request.args.get("ind", "")

    if not ticker:

        return jsonify({"ok": False, "error": "Ticker requerido"})


    lista_indicadores = indicadores.split(",") if indicadores else []


    df = _descargar_datos(ticker, timeframe)


    if df is None or df.empty:

        return jsonify({
            "ok": False,
            "data": [],
            "error": "No hay datos disponibles"
        })


    df, soportes, resistencias, patrones, resumen_tecnico, divergencias, fibonacci, patrones_chartistas = aplicar_indicadores(
        df,
        lista_indicadores,
        timeframe
    )


    df = df.reset_index()


    datos_json = preparar_para_json(df)


    soportes_json = formatear_niveles_sr(soportes)

    resistencias_json = formatear_niveles_sr(resistencias)

    patrones_json = formatear_patrones(patrones)


    return jsonify({
        "ok": True,
        "data": datos_json,
        "soportes": soportes_json,
        "resistencias": resistencias_json,
        "patrones": patrones_json,
        "resumenTecnico": resumen_tecnico,
        "divergencias": divergencias,
        "fibonacci": fibonacci,
        "patronesChartistas": patrones_chartistas
    })
