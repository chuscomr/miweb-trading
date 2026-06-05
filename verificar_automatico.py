"""
Verificador automático de alertas para MiWeb
Ejecuta cada 5 minutos y verifica todas las alertas activas
"""
import sys
import time
from datetime import datetime

import requests


# Configuración
INTERVALO_MINUTOS = 5
URL_VERIFICACION = 'http://localhost:5001/alertas/verificar'

print("=" * 60)
print("🤖 VERIFICADOR AUTOMÁTICO DE ALERTAS - MiWeb")
print("=" * 60)
print(f"✓ Intervalo: cada {INTERVALO_MINUTOS} minutos")
print(f"✓ URL: {URL_VERIFICACION}")
print("✓ Presiona Ctrl+C para detener")
print("=" * 60)
print()

contador = 0

while True:
    try:
        contador += 1
        ahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        print(f"[{ahora}] Verificación #{contador}...", end=" ")
        sys.stdout.flush()

        # Llamar al endpoint de verificación
        r = requests.post(URL_VERIFICACION, timeout=30)

        if r.status_code != 200:
            print(f"❌ Error HTTP {r.status_code}")
            continue

        data = r.json()

        if not data.get('ok'):
            print("❌ Error en la verificación")
            continue

        verificadas = data.get('verificadas', 0)
        disparadas_count = data.get('total_disparadas', 0)

        if disparadas_count > 0:
            print(f"🔔 {disparadas_count} ALERTA(S) DISPARADA(S)!")
            disparadas = data.get('disparadas', [])
            for alerta in disparadas:
                ticker = alerta.get('ticker', 'N/A')
                tipo = alerta.get('tipo', 'N/A')
                precio = alerta.get('precio_actual', 0)
                nivel = alerta.get('nivel', 0)
                print(f"   → {ticker} {tipo}: {precio:.2f}€ (nivel: {nivel:.2f}€)")
            print("   📧 Email enviado a salva.mugica@gmail.com")
        else:
            print(f"✓ OK - {verificadas} alertas verificadas, ninguna disparada")

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor (¿está corriendo?)")
    except requests.exceptions.Timeout:
        print("❌ Timeout - el servidor no respondió a tiempo")
    except KeyboardInterrupt:
        print("\n\n🛑 Deteniendo verificador automático...")
        break
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    # Esperar hasta la próxima verificación
    try:
        time.sleep(INTERVALO_MINUTOS * 60)
    except KeyboardInterrupt:
        print("\n\n🛑 Deteniendo verificador automático...")
        break

print("✓ Verificador detenido correctamente")
