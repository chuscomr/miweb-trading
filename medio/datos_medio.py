# ==========================================================
# DATOS - SISTEMA MEDIO PLAZO
# Descarga, conversión a semanal y validación
# ==========================================================

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📥 DESCARGA DE DATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def descargar_datos_diarios(ticker, periodo="10y"):
    """
    Descarga datos DIARIOS de yfinance.
    Estos se convertirán a semanales después.
    
    Returns:
        DataFrame con OHLCV diarios
    """
    try:
        df = yf.download(
            ticker,
            period=periodo,
            interval="1d",
            auto_adjust=True,
            progress=False
        )
        
        if df.empty:
            return None
        
        # Normalizar columnas (yfinance puede devolver MultiIndex)
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)
        
        # Asegurar que tenemos las columnas necesarias
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required):
            return None
        
        return df
        
    except Exception as e:
        print(f"❌ Error descargando {ticker}: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 CONVERSIÓN DIARIA → SEMANAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def convertir_a_semanal(df_diario):
    """
    Convierte DataFrame DIARIO en SEMANAL.
    
    Lógica:
    - Open: primer día de la semana
    - High: máximo de la semana
    - Low: mínimo de la semana
    - Close: último día de la semana
    - Volume: suma de la semana
    
    Args:
        df_diario: DataFrame con datos diarios (index = fecha)
    
    Returns:
        DataFrame con datos semanales
    """
    if df_diario is None or df_diario.empty:
        return None
    
    # Asegurar índice datetime
    if not isinstance(df_diario.index, pd.DatetimeIndex):
        df_diario.index = pd.to_datetime(df_diario.index)
    
    # Resampleo a semanal (W-FRI = cerrar semanas en viernes)
    df_semanal = pd.DataFrame()
    
    df_semanal['Open'] = df_diario['Open'].resample('W-FRI').first()
    df_semanal['High'] = df_diario['High'].resample('W-FRI').max()
    df_semanal['Low'] = df_diario['Low'].resample('W-FRI').min()
    df_semanal['Close'] = df_diario['Close'].resample('W-FRI').last()
    df_semanal['Volume'] = df_diario['Volume'].resample('W-FRI').sum()
    
    # Eliminar filas con NaN (semanas incompletas al inicio)
    df_semanal = df_semanal.dropna()
    
    return df_semanal


def convertir_listas_a_semanal(precios, volumenes, fechas):
    """
    Versión alternativa que trabaja con listas (para compatibilidad).
    
    Returns:
        precios_sem, volumenes_sem, fechas_sem (listas)
    """
    if not precios or not volumenes or not fechas:
        return [], [], []
    
    # Crear DataFrame temporal
    df_temp = pd.DataFrame({
        'Close': precios,
        'Volume': volumenes
    }, index=pd.DatetimeIndex(fechas))
    
    # Para listas, usamos solo Close y Volume
    df_temp['Open'] = df_temp['Close']
    df_temp['High'] = df_temp['Close']
    df_temp['Low'] = df_temp['Close']
    
    # Convertir
    df_semanal = convertir_a_semanal(df_temp)
    
    if df_semanal is None or df_semanal.empty:
        return [], [], []
    
    return (
        df_semanal['Close'].tolist(),
        df_semanal['Volume'].tolist(),
        df_semanal.index.tolist()
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 VALIDACIÓN DE DATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validar_datos_semanales(df, min_semanas=52):
    """
    Valida calidad de datos semanales.
    
    Returns:
        dict con {valido: bool, errores: list, advertencias: list}
    """
    errores = []
    advertencias = []
    
    if df is None or df.empty:
        errores.append("DataFrame vacío")
        return {"valido": False, "errores": errores, "advertencias": advertencias}
    
    # 1. Histórico suficiente
    if len(df) < min_semanas:
        errores.append(f"Histórico insuficiente: {len(df)} semanas (mín: {min_semanas})")
    
    # 2. Datos recientes
    if isinstance(df.index, pd.DatetimeIndex):
        ultima_fecha = df.index[-1]
        dias_desde_ultima = (datetime.now() - ultima_fecha).days
        
        if dias_desde_ultima > 14:  # Más de 2 semanas desactualizado
            advertencias.append(f"Datos desactualizados: {dias_desde_ultima} días")
    
    # 3. Precios válidos
    if (df['Close'] <= 0).any():
        errores.append("Precios inválidos (≤0)")
    
    # 4. Volumen válido
    if (df['Volume'] == 0).any():
        advertencias.append("Semanas sin volumen detectadas")
    
    # 5. Gaps extremos (>30% semanal es sospechoso)
    returns = df['Close'].pct_change().abs()
    gaps_extremos = returns[returns > 0.30]
    
    if len(gaps_extremos) > 0:
        advertencias.append(f"{len(gaps_extremos)} gaps semanales >30%")
    
    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "advertencias": advertencias
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 CLASE MARKETDATA (para backtest)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketDataSemanal:
    """
    Wrapper para datos semanales compatible con BacktestEngine.
    Similar a la clase del sistema swing pero para datos semanales.
    """
    
    def __init__(self, df_semanal):
        """
        Args:
            df_semanal: DataFrame con datos semanales (OHLCV)
        """
        self.df = df_semanal.reset_index(drop=False)
        self._is_last = False
    
    def iter_bars(self):
        """
        Itera barra por barra (semana por semana) para backtest.
        
        Yields:
            (i, df_hasta_i) - índice y DataFrame hasta esa semana
        """
        total = len(self.df)
        
        for i in range(total):
            self._is_last = (i == total - 1)
            yield i, self.df.iloc[:i+1].copy()
    
    def is_last_bar(self):
        """Indica si estamos en la última barra."""
        return self._is_last


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 FUNCIÓN PRINCIPAL - OBTENER DATOS SEMANALES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_datos_semanales(ticker, periodo="10y", validar=True):
    """
    Pipeline completo: descarga → conversión → validación.
    
    Returns:
        tuple: (df_semanal, validacion_info)
        - df_semanal: DataFrame con datos semanales o None
        - validacion_info: dict con resultados de validación
    """
    # 1. Descargar datos diarios
    df_diario = descargar_datos_diarios(ticker, periodo)
    
    if df_diario is None:
        return None, {"valido": False, "errores": ["Descarga fallida"]}
    
    # 2. Convertir a semanal
    df_semanal = convertir_a_semanal(df_diario)
    
    if df_semanal is None:
        return None, {"valido": False, "errores": ["Conversión fallida"]}
    
    # 3. Validar (opcional)
    if validar:
        validacion = validar_datos_semanales(df_semanal)
        
        if not validacion["valido"]:
            return None, validacion
        
        # Mostrar advertencias si las hay
        if validacion["advertencias"]:
            print(f"⚠️  {ticker}: {', '.join(validacion['advertencias'])}")
        
        return df_semanal, validacion
    
    return df_semanal, {"valido": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 UTILIDADES PARA TESTING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_precios_semanales(ticker, periodo="10y"):
    """
    Versión simplificada que devuelve listas (compatibilidad).
    
    Returns:
        tuple: (precios, volumenes, fechas)
    """
    df, _ = obtener_datos_semanales(ticker, periodo, validar=False)
    
    if df is None or df.empty:
        return None, None, None
    
    return (
        df['Close'].tolist(),
        df['Volume'].tolist(),
        df.index.tolist()
    )


if __name__ == "__main__":
    # Test rápido
    print("🧪 Test datos_medio.py")
    print("=" * 50)
    
    ticker = "ACS.MC"
    print(f"Descargando {ticker}...")
    
    df, validacion = obtener_datos_semanales(ticker)
    
    if df is not None:
        print(f"✅ {len(df)} semanas de datos")
        print(f"📅 Desde: {df.index[0].date()}")
        print(f"📅 Hasta: {df.index[-1].date()}")
        print(f"\n{df.tail()}")
    else:
        print(f"❌ Error: {validacion['errores']}")
