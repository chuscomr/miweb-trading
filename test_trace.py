from estrategias.medio.logica_medio import MedioPlazo
import pandas as pd
from core.data_provider import get_df_semanal
from core.indicadores import calcular_rsi

df, _ = get_df_semanal('MEL.MC')
precios = df['Close'].tolist()

print('Test 1 - RSI directo:')
rsi_series = calcular_rsi(pd.Series(precios), periodo=14)
print(f'  RSI: {round(rsi_series.iloc[-1], 1)}')

print('\nTest 2 - Via MedioPlazo:')
scanner = MedioPlazo()
resultado = scanner.evaluar('MEL.MC', None)
print(f'  RSI detalles: {resultado.get("detalles", {}).get("rsi")}')
print(f'  Score: {resultado.get("setup_score")}')
print(f'  Todos los detalles: {resultado.get("detalles", {})}')
