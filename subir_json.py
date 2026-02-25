import requests
import os

def subir_a_pythonanywhere():
    username = 'chusco'
    token = '42ebab5cfbff45323865624bd2e85549dfc51a7a'
    file_name = 'datos_trading.json'
    
    # RUTA LOCAL
    ruta_local = os.path.join(os.path.dirname(__file__), file_name)
    
    # RUTA REMOTA: Sin barra inicial para la construcción de la URL
    remote_path = f'home/{username}/mi_trading_app/{file_name}'
    
    # URL: Fíjate que hay una barra DESPUÉS de path y una antes de home
    url = f'https://www.pythonanywhere.com/api/v1/user/{username}/files/path/{remote_path}'

    print(f"🚀 Intento final a: {url}")

    try:
        with open(ruta_local, 'rb') as f:
            # Importante: Usamos POST y el nombre del campo debe ser 'content'
            response = requests.post(
                url,
                headers={'Authorization': f'Token {token}'},
                files={'content': f}
            )

        if response.status_code in [200, 201]:
            print('✅ ¡POR FIN! Archivo subido con éxito.')
        else:
            print(f'❌ Error {response.status_code}')
            # Si vuelve a dar 404, intentaremos el método PUT que a veces es necesario para sobreescribir
            print("Reintentando con método de actualización (PUT)...")
            with open(ruta_local, 'rb') as f:
                response_put = requests.put(
                    url,
                    headers={'Authorization': f'Token {token}'},
                    files={'content': f}
                )
            if response_put.status_code in [200, 201]:
                print('✅ ¡LOGRADO CON PUT!')
            else:
                print(f'❌ Fallo definitivo. Código: {response_put.status_code}')

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    subir_a_pythonanywhere()