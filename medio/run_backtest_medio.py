import yfinance as yf
from backtest_medio import backtest_medio_plazo
from logica_medio import convertir_a_semanal

TICKER = "ACS.MC"

df = yf.download(TICKER, period="12y", interval="1d", auto_adjust=True)

precios = df["Close"].values.reshape(-1).tolist()
volumenes = df["Volume"].values.reshape(-1).tolist()
fechas = df.index.to_list()

precios, volumenes, fechas = convertir_a_semanal(
    precios=precios,
    volumenes=volumenes,
    fechas=fechas
)

trades, equity = backtest_medio_plazo(precios, volumenes, fechas)

print("\n📊 BACKTEST MEDIO PLAZO")
print("=" * 40)
print(f"Trades totales: {len(trades)}")

if trades:
    R_tot = sum(t["R"] for t in trades)
    avg_R = R_tot / len(trades)
    winners = [t for t in trades if t["R"] > 0]

    print(f"Expectancy (R): {avg_R:.2f}")
    print(f"% Trades positivos: {len(winners)/len(trades)*100:.1f}%")
    print(f"Mejor trade: {max(t['R'] for t in trades):.2f}R")
    print(f"Peor trade: {min(t['R'] for t in trades):.2f}R")
