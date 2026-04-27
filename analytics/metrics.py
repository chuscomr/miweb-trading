# -*- coding: utf-8 -*-
"""
Métricas de Trading
Cálculo de KPIs y métricas de performance
"""

def calcular_metricas(trades):
    """Calcula métricas de una lista de trades"""
    return {
        "total_trades": len(trades),
        "win_rate": 0,
        "expectancy": 0,
        "profit_factor": 0,
    }
