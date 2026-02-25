import json
import os
from datetime import datetime

print(">>> alertas.py CARGADO <<<")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_ALERTAS = os.path.join(BASE_DIR, "alertas.json")


def cargar_trades():
    if not os.path.exists(RUTA_ALERTAS):
        return []

    try:
        with open(RUTA_ALERTAS, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                return []
            return json.loads(contenido)
    except json.JSONDecodeError:
        print("⚠️ alertas.json corrupto o vacío. Reiniciando.")
        return []


def guardar_trades(trades):
    with open(RUTA_ALERTAS, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


def crear_trade(ticker, entrada, stop, objetivo):
    print(">>> crear_trade EJECUTADO <<<")

    trades = cargar_trades()

    # Evitar duplicados activos
    for t in trades:
        if t["ticker"] == ticker and t["estado"] == "ACTIVO":
            print("⚠️ Trade duplicado ignorado")
            return t

    trade = {
        "trade_id": f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "ticker": ticker,
        "entrada": float(entrada),
        "stop": float(stop),
        "objetivo": float(objetivo),
        "estado": "ACTIVO",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    trades.append(trade)
    guardar_trades(trades)

    print("✅ TRADE GUARDADO EN alertas.json")
    return trade
