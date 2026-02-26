# api.py
from flask import request, jsonify
import yfinance as yf
import pandas as pdimport os
import requests
from datetime import datetime
from .nucleo.calculos import aplicar_indicadores
from .utilidades.serializador import preparar_para_json, formatear_niveles_sr, formatear_patrones
from .routes import indicadores_bp

from flask import request, jsonify
import yfinance as yf
import pandas as pd
import os
import requests
from datetime import datetime
from .nucleo.calculos import aplicar_indicadores
from .utilidades.serializador import preparar_para_json, formatear_niveles_sr, formatear_patrones
from .routes import indicadores_bp


def _descargar_datos(ticker, timeframe):
    # EODHD solo para timeframe diario
    token = os.getenv("EODHD_API_TOKEN")
    if token and timeframe == "1d":
        try:
            url = f"https://eodhd.com/api/eod/{ticker}"
            params = {"api_token": token, "period": "d", "fmt": "json", "order": "a"}
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and len(data) >= 50:
                data = data[-260:]
                df = pd.DataFrame(data)
                df["Date"] = pd.to_datetime(df["date"])
                df = df.set_index("Date")
                df["Close"] = df["adjusted_close"].astype(float)
                df["Open"] = df["open"].astype(float)
                df["High"] = df["high"].astype(float)
                df["Low"] = df["low"].astype(float)
                df["Volume"] = df["volume"].astype(float)
                return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            print(f"EODHD falló para {ticker}: {e}, probando yfinance...")

    # Fallback yfinance
    df = yf.download(ticker, period="1y", interval=timeframe, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


@indicadores_bp.route("/api")
def api_indicadores():
    ticker = request.args.get("ticker")
    timeframe = request.args.get("tf", "1d")
    indicadores = request.args.get("ind", "")

    if not ticker:
        return jsonify({"error": "Ticker requerido"}), 400

    lista_indicadores = indicadores.split(",") if indicadores else []

    df = _descargar_datos(ticker, timeframe)

    if df is None or df.empty:
        return jsonify({"error": "No hay datos disponibles"}), 404

    df, soportes, resistencias, patrones, resumen_tecnico, divergencias, fibonacci, patrones_chartistas = aplicar_indicadores(df, lista_indicadores, timeframe)

    df = df.reset_index()
    datos_json = preparar_para_json(df)
    soportes_json = formatear_niveles_sr(soportes)
    resistencias_json = formatear_niveles_sr(resistencias)
    patrones_json = formatear_patrones(patrones)

    return jsonify({
        "data": datos_json,
        "soportes": soportes_json,
        "resistencias": resistencias_json,
        "patrones": patrones_json,
        "resumenTecnico": resumen_tecnico,
        "divergencias": divergencias,
        "fibonacci": fibonacci,
        "patronesChartistas": patrones_chartistas
    })
