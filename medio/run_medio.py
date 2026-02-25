from logica_medio import obtener_precios
from sistema_trading_medio import evaluar_valor_medio

TICKER = "ACS.MC"

precios, volumenes, fechas = obtener_precios(TICKER, años=10)

resultado = evaluar_valor_medio(precios, volumenes, fechas)

print("\nRESULTADO MEDIO PLAZO")
print("=====================")
print(f"Ticker: {TICKER}")
for k, v in resultado.items():
    print(f"{k}: {v}")
