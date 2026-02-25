import time
from database import guardar_trade

class PaperTrader:
    def __init__(self, capital_inicial=10_000, riesgo_pct=0.01):
        self.capital = capital_inicial
        self.riesgo_pct = riesgo_pct
        self.en_posicion = False
        self.trade = None

    def abrir_trade(self, señal, ticker, precio_actual):
        if self.en_posicion:
            return

        entrada = señal["entrada"]
        riesgo = self.capital * self.riesgo_pct

        stop = entrada * 0.95
        size = int(riesgo / (entrada - stop))

        self.trade = {
            "ticker": ticker,
            "fecha_entrada": time.time(),
            "entrada": entrada,
            "stop": stop,
            "size": size,
            "riesgo": riesgo,
            "max": entrada,
            "setup_score": señal["setup_score"],
            "tipo_entrada": señal["tipo_entrada"],
            "estrategia": "paper_trading"
        }

        self.en_posicion = True
        print(f"🟢 PAPER TRADE ABIERTO {ticker} @ {entrada}")

    def gestionar_trade(self, precio_actual):
        if not self.en_posicion:
            return

        self.trade["max"] = max(self.trade["max"], precio_actual)
        trailing_stop = self.trade["max"] * 0.93

        if precio_actual <= trailing_stop:
            self.cerrar_trade(precio_actual, motivo="TRAILING")

    def obtener_operaciones_abiertas(self, precio_actual):
        if not self.en_posicion or not self.trade:
            return []

        entrada = self.trade["entrada"]
        size = self.trade["size"]

        bp_flotante = (precio_actual - entrada) * size

        return [{
            "ticker": self.trade["ticker"],
            "entrada": round(entrada, 2),
            "precio_actual": round(precio_actual, 2),
            "bp_flotante": round(bp_flotante, 2),
            "estado": "ABIERTA"
        }]

    def cerrar_trade(self, precio_salida, motivo="SALIDA"):
        entrada = self.trade["entrada"]
        size = self.trade["size"]

        beneficio = (precio_salida - entrada) * size
        self.capital += beneficio

        guardar_trade({
            "fecha_entrada": self.trade["fecha_entrada"],
            "fecha_salida": time.time(),
            "ticker": self.trade["ticker"],
            "entrada": entrada,
            "salida": precio_salida,
            "acciones": size,
            "beneficio": beneficio,
            "R_alcanzado": beneficio / self.trade["riesgo"] if self.trade["riesgo"] else 0,
            "setup_score": self.trade["setup_score"],
            "gestion": motivo,
            "tipo_entrada": self.trade["tipo_entrada"],
            "estrategia": self.trade["estrategia"],
            "notas": "Trading simulado"
        })

        print(f"🔴 PAPER TRADE CERRADO {self.trade['ticker']} | PnL: {beneficio:.2f} €")

        self.en_posicion = False
        self.trade = None
