# controlador.py
from werkzeug.datastructures import ImmutableMultiDict


# ─────────────────────────────
# PASO 1 — procesar POST
# ─────────────────────────────
def procesar_post(request, session):
    datos = request.form.to_dict()

    if "escanear_ibex" in datos:
        session["modo"] = "escaner_ibex"
        session["ultima_accion"] = {"escanear_ibex": "1"}

    elif "escanear_continuo" in datos:
        session["modo"] = "escaner_continuo"
        session["ultima_accion"] = {"escanear_continuo": "1"}

    elif "backtest" in datos:
        session["modo"] = "backtest"
        session["datos_analisis"] = datos

    elif "analizar" in datos:
        session["modo"] = "analizar"
        session["datos_analisis"] = datos


# ─────────────────────────────
# PASO 2 — ejecutar contexto
# ─────────────────────────────
def ejecutar_contexto(modo, datos, cache):

    from MiWeb.logica import ejecutar_app

    fake_request = type("Req", (), {})()
    fake_request.method = "POST"

    if modo == "escaner_ibex":
        fake_request.form = ImmutableMultiDict({"escanear_ibex": "1"})

    elif modo == "escaner_continuo":
        fake_request.form = ImmutableMultiDict({"escanear_continuo": "1"})

    elif modo == "analizar" and datos:
        fake_request.form = ImmutableMultiDict(datos)

    elif modo == "backtest" and datos:
        fake_request.form = ImmutableMultiDict(datos)

    else:
        fake_request = type(
            "Req", (), {"method": "GET", "form": {}}
        )()

    return ejecutar_app("CONTEXTO", fake_request, cache)


# ─────────────────────────────
# PASO 3 — blindaje
# ─────────────────────────────
def blindar_contexto(contexto):

    defaults = {
        "dist_max": -1,
        "entrada": 0.0,
        "stop": 0.0,
        "objetivo": 0.0,
        "rr": 0.0,
    }

    for k, v in defaults.items():
        if k not in contexto or contexto[k] is None:
            contexto[k] = v

    return contexto

import base64
import os
import time

def guardar_pantallazo_controlador(data):
    imagen_base64 = data.get("imagen")
    ticker = data.get("ticker", "pantallazo")

    if not imagen_base64:
        return False, "Imagen no recibida"

    header, encoded = imagen_base64.split(",", 1)
    imagen_bytes = base64.b64decode(encoded)

    carpeta = "MiWeb\pantallazos"
    os.makedirs(carpeta, exist_ok=True)

    nombre = f"{ticker}_{int(time.time())}.png"
    ruta = os.path.join(carpeta, nombre)

    with open(ruta, "wb") as f:
        f.write(imagen_bytes)

    print(f"📸 Pantallazo guardado en {ruta}")
    return True, nombre

