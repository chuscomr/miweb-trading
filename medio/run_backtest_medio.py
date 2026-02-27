from datos_posicional import obtener_datos_semanales
from backtest_medio import backtest_medio_plazo


TICKER = "ACS.MC"

df_semanal, validacion = obtener_datos_semanales(TICKER, periodo_años=12, validar=False)

if df_semanal is None or df_semanal.empty:
    print("❌ No se pudieron obtener datos")
    quit()

precios = df_semanal["Close"].tolist()
volumenes = df_semanal["Volume"].tolist()
fechas = df_semanal.index.to_list()

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
