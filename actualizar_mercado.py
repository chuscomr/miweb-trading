import json
import os
import time
from datetime import datetime
import yfinance as yf
import mysql.connector
from sistema_trading import sistema_trading

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
DB_CONFIG = {
    "user": "chusco",
    "password": "TU_CONTRASEÑA_DE_DATABASES", # <--- LA QUE CREASTE EN LA PESTAÑA DATABASES
    "host": "chusco.mysql.pythonanywhere-services.com",
    "database": "chusco$trading_db"
}

# ==========================================
# 2. LISTAS DE TICKERS
# ==========================================
IBEX35 = ["ACS.MC","AENA.MC","AMS.MC","ANA.MC","BBVA.MC","CABK.MC","ELE.MC","FER.MC","GRF.MC","IBE.MC","IAG.MC","IDR.MC","ITX.MC","MAP.MC","MEL.MC","MRL.MC","NTGY.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC","SAN.MC","SCYR.MC","SLR.MC","TEF.MC","UNI.MC","CLNX.MC","LOG.MC","ACX.MC","BKT.MC","COL.MC","CIE.MC","ENG.MC","FCC.MC","PUIG.MC"]
CONTINUO = ["VID.MC","TUB.MC","TRE.MC","CAF.MC","GEST.MC","APAM.MC","PHM.MC","OHLA.MC","DOM.MC","ENCE.MC","GRE.MC","AUD.MC","LRE.MC","HOME.MC","NHH.MC","LAR.MC","VIS.MC","ZOT.MC","ECR.MC","A3M.MC","ATRY.MC","R4.MC","GCO.MC","HBX.MC","TCO.MC","CASH.MC","NEA.MC","PSG.MC","AMP.MC","MTS.MC"]

# ==========================================
# 3. FUNCIÓN PARA GUARDAR EN MYSQL
# ==========================================
def guardar_en_db(ticker, info):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Esta consulta inserta el dato o lo actualiza si el ticker ya existe
        query = """
            INSERT INTO resultados (ticker, datos_json, ultima_actualizacion)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE datos_json=%s, ultima_actualizacion=%s
        """
        
        json_str = json.dumps(info, ensure_ascii=False)
        ahora = datetime.now()
        
        cursor.execute(query, (ticker, json_str, ahora, json_str, ahora))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error en DB para {ticker}: {e}")

# ==========================================
# 4. PROCESO PRINCIPAL
# ==========================================
def actualizar_mercado():
    print(f"\n[{datetime.now().strftime('%H:%M')}] --- INICIANDO ESCANEO ---")
    TODO_EL_MERCADO = list(dict.fromkeys(IBEX35 + CONTINUO))

    for ticker in TODO_EL_MERCADO:
        try:
            # Descargar datos
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 50: continue

            # Extraer precios y volúmenes
            close = df["Close"].iloc[:, 0] if hasattr(df["Close"], "columns") else df["Close"]
            volume = df["Volume"].iloc[:, 0] if hasattr(df["Volume"], "columns") else df["Volume"]

            precios = close.dropna().tolist()
            volumenes = volume.dropna().tolist()
            precio_actual = round(precios[-1], 2)

            # Tu sistema de trading (asegúrate que sistema_trading.py esté en la misma carpeta)
            res = sistema_trading(precios, volumenes, precio_actual)
            
            # Formatear datos para la DB
            datos_para_guardar = {
                "decision": res.get("decision"),
                "motivos": res.get("motivos", []),
                "precio": precio_actual,
                "entrada": res.get("entrada"),
                "stop": res.get("stop"),
                "objetivo": res.get("objetivo")
            }
            
            # Guardar directamente en MySQL
            guardar_en_db(ticker, datos_para_guardar)
            print(f" ✅ {ticker:9} | {res['decision']:10} | OK")

        except Exception as e:
            print(f" ❌ Error en {ticker}: {e}")

if __name__ == "__main__":
    actualizar_mercado()
    print("\n>>> FIN DEL PROCESO: Todos los datos están en MySQL.")