# api.py
from flask import request, jsonify
import yfinance as yf
import pandas as pd
import os
import requests
import time
from datetime import datetime

from .nucleo.calculos import aplicar_indicadores
from .utilidades.serializador import preparar_para_json, formatear_niveles_sr, formatear_patrones
from .routes import indicadores_bp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCARGA DE DATOS ROBUSTA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _descargar_datos(ticker, timeframe):

    token = os.getenv("EODHD_API_TOKEN")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ Intentar EODHD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

                data = data[-260:]

                df = pd.DataFrame(data)

                df["Date"] = pd.to_datetime(df["date"])
                df = df.set_index("Date")

                factor = df["adjusted_close"].astype(float) / df["close"].astype(float)

                df["Close"] = df["adjusted_close"].astype(float)
                df["Open"] = df["open"].astype(float) * factor
                df["High"] = df["high"].astype(float) * factor
                df["Low"] = df["low"].astype(float) * factor
                df["Volume"] = df["volume"].astype(float)

                # intentar añadir vela de hoy con yahoo
                try:
                    df_hoy = yf.download(
                        ticker,
                        period="1d",
                        interval="1d",
                        auto_adjust=True,
                        progress=False,
                        threads=False
                    )

                    if isinstance(df_hoy.columns, pd.MultiIndex):
                        df_hoy.columns = df_hoy.columns.get_level_values(0)

                    if not df_hoy.empty:
                        df_hoy.index = pd.to_datetime(df_hoy.index)
                        df_hoy = df_hoy[["Open", "High", "Low", "Close", "Volume"]]

                        if df_hoy.index[-1] not in df.index:
                            df = pd.concat([df, df_hoy])

                except Exception as e:
                    print(f"No se pudo añadir vela de hoy: {e}")

                return df[["Open", "High", "Low", "Close", "Volume"]]

        except Exception as e:
            print(f"EODHD falló para {ticker}: {e}")


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ Fallback robusto yfinance
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    for intento in range(3):

        try:
            df = yf.download(
                ticker,
                period="1y",
                interval=timeframe,
                auto_adjust=True,
                progress=False,
                threads=False
            )

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if not df.empty:
                return df

        except Exception as e:
            print(f"Yahoo error intento {intento+1}: {e}")

        time.sleep(1)


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ Fallback sin ".MC"
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if ticker.endswith(".MC"):

        ticker_alt = ticker.replace(".MC", "")

        try:

            df = yf.download(
                ticker_alt,
                period="1y",
                interval=timeframe,
                auto_adjust=True,
                progress=False,
                threads=False
            )

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if not df.empty:
                return df

        except Exception as e:
            print(f"Yahoo fallback sin .MC falló: {e}")


    return pd.DataFrame()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
