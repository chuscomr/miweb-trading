from estrategias.medio.logica_medio import MedioPlazo 
scanner = MedioPlazo() 
resultado = scanner.evaluar('MEL.MC', None) 
print('RSI:', resultado.get('detalles', {}).get('rsi')) 
print('Score:', resultado.get('setup_score')) 
