from estrategias.medio.logica_medio import calcular_rsi 
import pandas as pd 
precios = [10, 11, 12, 11.5, 12.5, 13, 12.8, 13.2, 12.9, 13.5, 13.8, 14, 13.5, 14.2, 14.5] 
rsi_series = calcular_rsi(pd.Series(precios), periodo=14) 
print('RSI test:', round(rsi_series.iloc[-1], 1)) 
