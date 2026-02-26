import yfinance as yf
import pandas as pd
import os
import requests


def descargar_datos(ticker, periodo="1y", intervalo="1d"):
    """Descarga datos con EODHD (si disponible) o yfinance como fallback"""

    # EODHD solo para datos diarios
    token = os.getenv("EODHD_API_TOKEN")
    if token and intervalo == "1d":
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
            print(f"⚠️ EODHD falló para {ticker}: {e}, usando yfinance...")

    # Fallback yfinance
    try:
        df = yf.download(ticker, period=periodo, interval=intervalo,
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Error descargando {ticker}: {e}")
        return pd.DataFrame()
