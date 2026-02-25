# indicadores/nucleo/descargar_datos.py
import yfinance as yf
import pandas as pd

def descargar_datos(ticker, periodo="1y", intervalo="1d"):
    """
    Descarga datos de yfinance y los limpia
    """
    try:
        df = yf.download(
            ticker,
            period=periodo,
            interval=intervalo,
            auto_adjust=True,
            progress=False
        )
        
        # Limpiar MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
        
    except Exception as e:
        print(f"Error descargando {ticker}: {e}")
        return pd.DataFrame()