# api.py
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
    from datetime import date, timedelta
    hoy = date.today()
    fecha_inicio = hoy - timedelta(days=365)

    # ── 1. EODHD (solo timeframe diario) ────────────────────────────
    token = os.getenv("EODHD_API_TOKEN")
    if token and timeframe == "1d":
        try:
            url = f"https://eodhd.com/api/eod/{ticker}"
            params = {
                "api_token": token, "period": "d", "fmt": "json", "order": "a",
                "from": fecha_inicio.strftime("%Y-%m-%d"),
                "to":   hoy.strftime("%Y-%m-%d"),
            }
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and len(data) >= 50:
                df = pd.DataFrame(data)
                df["Date"] = pd.to_datetime(df["date"])
                df = df.set_index("Date")
                factor = df["adjusted_close"].astype(float) / df["close"].astype(float)
                df["Close"]  = df["adjusted_close"].astype(float)
                df["Open"]   = df["open"].astype(float) * factor
                df["High"]   = df["high"].astype(float) * factor
                df["Low"]    = df["low"].astype(float) * factor
                df["Volume"] = df["volume"].astype(float)

                # Vela de hoy: FMP → yfinance
                ultima = df.index[-1].date()
                if ultima < hoy:
                    vela_añadida = False
                    # 1a. FMP
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
                                    fecha_fmp = pd.to_datetime(row["date"])
                                    if fecha_fmp.date() > ultima:
                                        nueva = pd.DataFrame({
                                            "Open":   [float(row.get("open")   or row["close"])],
                                            "High":   [float(row.get("high")   or row["close"])],
                                            "Low":    [float(row.get("low")    or row["close"])],
                                            "Close":  [float(row["close"])],
                                            "Volume": [float(row.get("volume") or 0)],
                                        }, index=pd.DatetimeIndex([fecha_fmp]))
                                        df = pd.concat([df, nueva])
                                        df = df[~df.index.duplicated(keep="last")]
                                        vela_añadida = True
                                        print(f"[FMP] Vela hoy {ticker}: {row['close']}")
                        except Exception as e_fmp:
                            print(f"[FMP] Error {ticker}: {e_fmp}")
                    # 1b. Fallback yfinance para vela de hoy
                    if not vela_añadida:
                        try:
                            tick = yf.Ticker(ticker)
                            df_hoy = tick.history(period="1d", interval="1d")
                            if not df_hoy.empty:
                                if df_hoy.index.tz is not None:
                                    df_hoy.index = df_hoy.index.tz_localize(None)
                                df_hoy.index = pd.to_datetime(df_hoy.index)
                                df_hoy = df_hoy[["Open", "High", "Low", "Close", "Volume"]]
                                if df_hoy.index[-1].date() > ultima:
                                    df = pd.concat([df, df_hoy])
                                    df = df[~df.index.duplicated(keep="last")]
                                    print(f"[yfinance] Vela hoy {ticker}: {df_hoy['Close'].iloc[-1]:.2f}")
                        except Exception as e_yf:
                            print(f"[yfinance hoy] Error {ticker}: {e_yf}")

                return df[["Open", "High", "Low", "Close", "Volume"]]

        except Exception as e:
            print(f"EODHD falló para {ticker}: {e}")

    # ── 2. Fallback yfinance completo ────────────────────────────────
    try:
        tick = yf.Ticker(ticker)
        df = tick.history(
            start=fecha_inicio.strftime("%Y-%m-%d"),
            end=hoy.strftime("%Y-%m-%d"),
            interval=timeframe
        )
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index)
        print(f"[yfinance] {ticker}: {len(df)} velas")
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as e:
        print(f"[yfinance] Error {ticker}: {e}")
        return pd.DataFrame()


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
