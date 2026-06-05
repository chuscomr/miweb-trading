from estrategias.medio.logica_medio import MedioPlazo 
from core.data_provider import get_df_semanal 
from core.indicadores import calcular_rsi 
import pandas as pd 
 
df, _ = get_df_semanal('MEL.MC') 
precios = df['Close'].tolist() 
print(f'Precios disponibles: {len(precios)}') 
 
try: 
    rsi_series = calcular_rsi(pd.Series(precios), periodo=14) 
    rsi_val = round(rsi_series.iloc[-1], 1) if not pd.isna(rsi_series.iloc[-1]) else None 
    print(f'RSI calculado: {rsi_val}') 
except Exception as e: 
    print(f'ERROR: {e}') 
