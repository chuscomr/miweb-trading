import time
import subprocess
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
# Asegúrate de que este sea el nombre de tu script que baja los precios
SCRIPT_TRADING = "actualizar_ibex.py" 
INTERVALO_MINUTOS = 15

def ejecutar_actualizacion():
    # Usamos texto plano para evitar errores de caracteres
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- Iniciando actualizacion de datos ---")
    
    try:
        # Ejecutamos tu script de trading
        resultado = subprocess.run(["python", SCRIPT_TRADING], capture_output=True, text=True)
        
        if resultado.returncode == 0:
            print(f"OK: Datos procesados correctamente.")
            print(f"INFO: El archivo 'datos_trading.json' se ha actualizado en tu PC.")
        else:
            print(f"ERROR al ejecutar el script de trading:")
            print(resultado.stderr)
            
    except Exception as e:
        print(f"ERROR inesperado: {e}")

def main():
    print("SISTEMA DE ACTUALIZACION LOCAL INICIADO")
    print(f"Los datos se actualizaran cada {INTERVALO_MINUTOS} minutos.")
    print("----------------------------------------------------------")
    
    while True:
        ejecutar_actualizacion()
        
        print(f"Esperando {INTERVALO_MINUTOS} minutos para la siguiente vuelta...")
        # Espera 15 minutos (15 * 60 segundos)
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    main()