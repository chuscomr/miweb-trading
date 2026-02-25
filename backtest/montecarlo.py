import random
import numpy as np

def monte_carlo_R(
    Rs,
    capital_inicial,
    riesgo_pct,
    iteraciones=10_000
):
    """
    Monte Carlo sobre R-múltiplos.
    Rs: lista de R por trade (ej: [1.2, -1, 0.5, ...])
    """

    resultados = []

    for _ in range(iteraciones):
        capital = capital_inicial
        peak = capital
        max_dd = 0

        Rs_sim = random.sample(Rs, len(Rs))

        for R in Rs_sim:
            riesgo = capital * riesgo_pct
            capital += riesgo * R

            peak = max(peak, capital)
            dd = (peak - capital) / peak
            max_dd = max(max_dd, dd)

        resultados.append({
            "capital_final": capital,
            "max_dd": max_dd
        })

    return resultados

def resumen_montecarlo(resultados):

    capitals = [r["capital_final"] for r in resultados]
    dds = [r["max_dd"] for r in resultados]

    return {
        "capital_mediano": round(np.percentile(capitals, 50), 2),
        "capital_p5": round(np.percentile(capitals, 5), 2),
        "capital_p95": round(np.percentile(capitals, 95), 2),
        "dd_mediano_pct": round(np.percentile(dds, 50) * 100, 2),
        "dd_p95_pct": round(np.percentile(dds, 95) * 100, 2),
        "dd_peor_pct": round(max(dds) * 100, 2)
    }
