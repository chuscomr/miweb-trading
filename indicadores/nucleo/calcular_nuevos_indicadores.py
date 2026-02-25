# ═══════════════════════════════════════════════════════════════
# CÓDIGO PYTHON - CÁLCULO DE LOS 10 NUEVOS INDICADORES
# Para añadir en tu backend (logica.py o donde calcules indicadores)
# ═══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np

def calcular_nuevos_indicadores(df):
    """
    Calcula los 10 nuevos indicadores técnicos
    
    Args:
        df: DataFrame con columnas ['Open', 'High', 'Low', 'Close', 'Volume']
    
    Returns:
        df con nuevas columnas de indicadores
    """
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. EMAs (Medias Móviles Exponenciales)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. ADX (Average Directional Index)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    periodo = 14
    
    # Calcular +DM y -DM
    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    # True Range
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift())
    tr3 = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Suavizado
    atr = tr.rolling(periodo).mean()
    plus_di = 100 * (plus_dm.rolling(periodo).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(periodo).mean() / atr)
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(periodo).mean()
    df['DI_PLUS'] = plus_di
    df['DI_MINUS'] = minus_di
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. Parabolic SAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def calcular_psar(high, low, close, af_start=0.02, af_increment=0.02, af_max=0.2):
        psar = close.copy()
        bull = True
        af = af_start
        ep = low[0]
        hp = high[0]
        lp = low[0]
        
        for i in range(2, len(close)):
            if bull:
                psar[i] = psar[i - 1] + af * (hp - psar[i - 1])
            else:
                psar[i] = psar[i - 1] + af * (lp - psar[i - 1])
            
            reverse = False
            
            if bull:
                if low[i] < psar[i]:
                    bull = False
                    reverse = True
                    psar[i] = hp
                    lp = low[i]
                    af = af_start
            else:
                if high[i] > psar[i]:
                    bull = True
                    reverse = True
                    psar[i] = lp
                    hp = high[i]
                    af = af_start
            
            if not reverse:
                if bull:
                    if high[i] > hp:
                        hp = high[i]
                        af = min(af + af_increment, af_max)
                    if low[i - 1] < psar[i]:
                        psar[i] = low[i - 1]
                    if low[i - 2] < psar[i]:
                        psar[i] = low[i - 2]
                else:
                    if low[i] < lp:
                        lp = low[i]
                        af = min(af + af_increment, af_max)
                    if high[i - 1] > psar[i]:
                        psar[i] = high[i - 1]
                    if high[i - 2] > psar[i]:
                        psar[i] = high[i - 2]
        
        return psar
    
    df['PSAR'] = calcular_psar(df['High'], df['Low'], df['Close'])
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. Ichimoku Cloud
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tenkan-sen (línea de conversión)
    periodo_tenkan = 9
    high_tenkan = df['High'].rolling(periodo_tenkan).max()
    low_tenkan = df['Low'].rolling(periodo_tenkan).min()
    df['TENKAN'] = (high_tenkan + low_tenkan) / 2
    
    # Kijun-sen (línea base)
    periodo_kijun = 26
    high_kijun = df['High'].rolling(periodo_kijun).max()
    low_kijun = df['Low'].rolling(periodo_kijun).min()
    df['KIJUN'] = (high_kijun + low_kijun) / 2
    
    # Senkou Span A (adelantada 26 períodos)
    df['SENKOU_A'] = ((df['TENKAN'] + df['KIJUN']) / 2).shift(26)
    
    # Senkou Span B (adelantada 26 períodos)
    periodo_senkou = 52
    high_senkou = df['High'].rolling(periodo_senkou).max()
    low_senkou = df['Low'].rolling(periodo_senkou).min()
    df['SENKOU_B'] = ((high_senkou + low_senkou) / 2).shift(26)
    
    # Chikou Span (retrasada 26 períodos)
    df['CHIKOU'] = df['Close'].shift(-26)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. Stochastic
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    periodo_k = 14
    periodo_d = 3
    
    low_min = df['Low'].rolling(periodo_k).min()
    high_max = df['High'].rolling(periodo_k).max()
    
    df['STOCH_K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    df['STOCH_D'] = df['STOCH_K'].rolling(periodo_d).mean()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. MFI (Money Flow Index)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    periodo_mfi = 14
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    positive_mf = positive_flow.rolling(periodo_mfi).sum()
    negative_mf = negative_flow.rolling(periodo_mfi).sum()
    
    mfi_ratio = positive_mf / negative_mf
    df['MFI'] = 100 - (100 / (1 + mfi_ratio))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. VWAP (Volume Weighted Average Price)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    df['VWAP'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 8. Volume Profile (simplificado - POC)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def calcular_volume_profile(df_segment, num_bins=20):
        """Calcula el Point of Control (POC) - nivel con más volumen"""
        if len(df_segment) < 2:
            return None
        
        price_min = df_segment['Low'].min()
        price_max = df_segment['High'].max()
        
        bins = np.linspace(price_min, price_max, num_bins)
        volume_at_price = np.zeros(len(bins) - 1)
        
        for i in range(len(bins) - 1):
            mask = (df_segment['Close'] >= bins[i]) & (df_segment['Close'] < bins[i + 1])
            volume_at_price[i] = df_segment.loc[mask, 'Volume'].sum()
        
        # POC es el precio con más volumen
        max_volume_idx = volume_at_price.argmax()
        poc = (bins[max_volume_idx] + bins[max_volume_idx + 1]) / 2
        
        return poc
    
    # Calcular POC para los últimos 60 días
    if len(df) >= 60:
        df['POC'] = calcular_volume_profile(df.tail(60))
    else:
        df['POC'] = None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 9. Keltner Channels
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    periodo_keltner = 20
    multiplicador = 2
    
    # ATR ya calculado anteriormente (asumimos que existe)
    if 'ATR' not in df.columns:
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
    
    ema_keltner = df['Close'].ewm(span=periodo_keltner, adjust=False).mean()
    df['KELTNER_UPPER'] = ema_keltner + (multiplicador * df['ATR'])
    df['KELTNER_LOWER'] = ema_keltner - (multiplicador * df['ATR'])
    df['KELTNER_MIDDLE'] = ema_keltner
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10. Pivot Points (Clásicos)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Usar datos del día anterior
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)
    prev_close = df['Close'].shift(1)
    
    # Pivot Point
    df['PIVOT_PP'] = (prev_high + prev_low + prev_close) / 3
    
    # Resistencias
    df['PIVOT_R1'] = (2 * df['PIVOT_PP']) - prev_low
    df['PIVOT_R2'] = df['PIVOT_PP'] + (prev_high - prev_low)
    df['PIVOT_R3'] = prev_high + 2 * (df['PIVOT_PP'] - prev_low)
    
    # Soportes
    df['PIVOT_S1'] = (2 * df['PIVOT_PP']) - prev_high
    df['PIVOT_S2'] = df['PIVOT_PP'] - (prev_high - prev_low)
    df['PIVOT_S3'] = prev_low - 2 * (prev_high - df['PIVOT_PP'])
    
    return df


# ═══════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import yfinance as yf
    
    # Descargar datos
    ticker = "AAPL"
    df = yf.download(ticker, period="6mo")
    
    # Calcular nuevos indicadores
    df = calcular_nuevos_indicadores(df)
    
    # Ver resultados
    print(f"\n{'='*60}")
    print(f"INDICADORES CALCULADOS PARA {ticker}")
    print(f"{'='*60}\n")
    
    print("📈 TENDENCIA:")
    print(f"  EMA9:  {df['EMA9'].iloc[-1]:.2f}")
    print(f"  EMA21: {df['EMA21'].iloc[-1]:.2f}")
    print(f"  EMA50: {df['EMA50'].iloc[-1]:.2f}")
    print(f"  ADX:   {df['ADX'].iloc[-1]:.2f} {'✅ Tendencia fuerte' if df['ADX'].iloc[-1] > 25 else '⚠️ Lateral'}")
    print(f"  PSAR:  {df['PSAR'].iloc[-1]:.2f}")
    
    print("\n⚡ MOMENTUM:")
    print(f"  Stochastic K: {df['STOCH_K'].iloc[-1]:.2f}")
    print(f"  Stochastic D: {df['STOCH_D'].iloc[-1]:.2f}")
    print(f"  MFI: {df['MFI'].iloc[-1]:.2f} {'🔴 Sobrecompra' if df['MFI'].iloc[-1] > 80 else '🟢 Sobreventa' if df['MFI'].iloc[-1] < 20 else '⚪ Neutral'}")
    
    print("\n📊 VOLUMEN:")
    print(f"  VWAP: {df['VWAP'].iloc[-1]:.2f}")
    if df['POC'].iloc[-1]:
        print(f"  POC (Volume Profile): {df['POC'].iloc[-1]:.2f}")
    
    print("\n📉 VOLATILIDAD:")
    print(f"  Keltner Superior: {df['KELTNER_UPPER'].iloc[-1]:.2f}")
    print(f"  Keltner Medio:    {df['KELTNER_MIDDLE'].iloc[-1]:.2f}")
    print(f"  Keltner Inferior: {df['KELTNER_LOWER'].iloc[-1]:.2f}")
    
    print("\n🎯 NIVELES:")
    print(f"  Pivot R1: {df['PIVOT_R1'].iloc[-1]:.2f}")
    print(f"  Pivot PP: {df['PIVOT_PP'].iloc[-1]:.2f}")
    print(f"  Pivot S1: {df['PIVOT_S1'].iloc[-1]:.2f}")
    
    print(f"\n{'='*60}\n")
