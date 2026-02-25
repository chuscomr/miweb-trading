import numpy as np

def calcular_metricas(trades, equity):

    Rs = [t.R for t in trades]
    resultados = [t.resultado for t in trades]

    winrate = sum(1 for r in Rs if r > 0) / len(Rs) if Rs else 0
    expectancy = np.mean(Rs) if Rs else 0

    max_dd = 0
    peak = equity[0]

    for e in equity:
        peak = max(peak, e)
        dd = (peak - e) / peak
        max_dd = max(max_dd, dd)

    return {
        "trades": len(trades),
        "winrate": round(winrate * 100, 2),
        "expectancy_R": round(expectancy, 2),
        "max_drawdown_pct": round(max_dd * 100, 2)
    }
