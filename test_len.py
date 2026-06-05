from estrategias.medio.logica_medio import MedioPlazo 
from core.data_provider import get_df_semanal 
 
scanner = MedioPlazo() 
df, _ = get_df_semanal('MEL.MC') 
precios_manual = df['Close'].tolist() 
print(f'Precios manual: {len(precios_manual)}') 
 
# Ahora via evaluar 
import estrategias.medio.logica_medio 
original_evaluar = estrategias.medio.logica_medio.MedioPlazo.evaluar 
def debug_evaluar(self, ticker, cache): 
    print(f'DENTRO DE EVALUAR para {ticker}') 
    return original_evaluar(self, ticker, cache) 
estrategias.medio.logica_medio.MedioPlazo.evaluar = debug_evaluar 
 
resultado = scanner.evaluar('MEL.MC', None) 
