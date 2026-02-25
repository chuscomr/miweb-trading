# ==========================================================
# SISTEMA TRADING POSICIONAL
# Evaluador completo de señales de entrada
# ==========================================================

import yfinance as yf
import pandas as pd
import numpy as np

# Imports flexibles
try:
    from .logica_posicional import *
    from .config_posicional import *
except ImportError:
    from logica_posicional import *
    from config_posicional import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 EVALUADOR PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluar_entrada_posicional(precios, volumenes=None, fechas=None, df=None, usar_filtro_mercado=True):
    """
    Evaluador completo para entrada en sistema posicional.
    
    ESTRATEGIA POSICIONAL:
    1. Tendencia alcista FUERTE (precio > MM50 > MM200)
    2. Consolidación de 3-6 meses
    3. Breakout de máximos confirmado
    4. Volumen creciente
    5. Riesgo 8-15%
    
    Args:
        precios: lista de precios semanales
        volumenes: lista de volúmenes semanales (opcional)
        fechas: lista de fechas (opcional)
        df: DataFrame completo (opcional, más preciso)
    
    Returns:
        dict con decisión y detalles
    """
    motivos_rechazo = []
    detalles = {}
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VALIDACIONES PREVIAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if precios is None or len(precios) < MIN_SEMANAS_HISTORICO:
        return {
            "decision": "NO_OPERAR",
            "motivos": [f"Histórico insuficiente (<{MIN_SEMANAS_HISTORICO} semanas)"],
            "detalles": {}
        }
    
    precio_actual = precios[-1]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚨 FILTRO CRÍTICO: MERCADO ALCISTA IBEX
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if usar_filtro_mercado:
        try:
            import pandas as pd
            
            datos_ibex = yf.download("^IBEX", period="1y", progress=False)
        
            # Verificar que hay datos
            if isinstance(datos_ibex, pd.DataFrame) and len(datos_ibex) >= 200:
                # Aplanar MultiIndex si existe
                if isinstance(datos_ibex.columns, pd.MultiIndex):
                    datos_ibex.columns = datos_ibex.columns.get_level_values(0)
            
                # Extraer columna Close
                close_col = datos_ibex['Close']
            
                # Calcular MM200
                mm200_ibex = float(close_col.rolling(200).mean().iloc[-1])
                precio_ibex = float(close_col.iloc[-1])
            
                detalles["mercado_ibex"] = "ALCISTA" if precio_ibex > mm200_ibex else "BAJISTA"
                detalles["precio_ibex"] = round(precio_ibex, 2)
                detalles["mm200_ibex"] = round(mm200_ibex, 2)
            
                if precio_ibex < mm200_ibex:
                    return {
                        "decision": "NO_OPERAR",
                        "motivos": ["🚫 IBEX por debajo de MM200 - Mercado bajista general"],
                        "detalles": detalles
                }
        except Exception as e:
            print(f"⚠️ Advertencia: No se pudo verificar mercado IBEX ({e}). Continuando análisis...")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 1: TENDENCIA ALCISTA FUERTE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_tendencia = detectar_tendencia_largo_plazo(precios, df)
    detalles.update({
        "tendencia": analisis_tendencia["tendencia"],
        "mm50": round(analisis_tendencia["mm50"], 2) if analisis_tendencia.get("mm50") else None,
        "mm200": round(analisis_tendencia["mm200"], 2) if analisis_tendencia.get("mm200") else None,
        "distancia_mm50_pct": round(analisis_tendencia["distancia_mm50_pct"], 2) if analisis_tendencia.get("distancia_mm50_pct") else None,
        "pendiente_mm50": round(analisis_tendencia["pendiente_mm50"], 2) if analisis_tendencia.get("pendiente_mm50") else None
    })
    
    if not analisis_tendencia.get("cumple_criterios", False):
        if analisis_tendencia["tendencia"] != "ALCISTA":
            motivos_rechazo.append(f"Tendencia {analisis_tendencia['tendencia'].lower()}")
        else:
            # Tendencia alcista pero no cumple todos los criterios
            condiciones = analisis_tendencia.get("condiciones", {})
            if not condiciones.get("distancia_suficiente"):
                motivos_rechazo.append(f"Precio muy cerca de MM50 ({detalles['distancia_mm50_pct']}%)")
            if not condiciones.get("pendiente_positiva"):
                motivos_rechazo.append("MM50 sin pendiente alcista")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 2: CONSOLIDACIÓN PREVIA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Buscar consolidación en diferentes lookbacks
    consolidacion_encontrada = False
    mejor_consolidacion = None
    
    for lookback in range(CONSOLIDACION_MIN_SEMANAS, CONSOLIDACION_MAX_SEMANAS + 1, 4):
        if len(precios) < lookback:
            continue
        
        analisis_consol = detectar_consolidacion(precios, lookback_max=lookback)
        
        if analisis_consol["en_consolidacion"]:
            consolidacion_encontrada = True
            mejor_consolidacion = analisis_consol
            break
    
    if mejor_consolidacion:
        detalles.update({
            "consolidacion": True,
            "consolidacion_semanas": mejor_consolidacion["semanas_consolidacion"],
            "consolidacion_rango_pct": round(mejor_consolidacion["rango_pct"], 1),
            "posicion_en_rango": round(mejor_consolidacion["posicion_en_rango"], 1)
        })
    else:
        detalles["consolidacion"] = False
        # No es requisito estricto, pero resta puntos
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 3: BREAKOUT DE MÁXIMOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_breakout = detectar_breakout(precios, volumenes, lookback=26)
    detalles.update({
        "breakout": analisis_breakout["hay_breakout"],
        "breakout_distancia_pct": round(analisis_breakout.get("distancia_breakout_pct", 0), 2),
        "breakout_volumen_ratio": round(analisis_breakout.get("ratio_volumen", 1), 2)
    })
    
    if not analisis_breakout["hay_breakout"]:
        motivos_rechazo.append("Sin breakout de máximos")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 4: VOLATILIDAD SUFICIENTE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    volatilidad = calcular_volatilidad(precios, periodo=52)
    detalles["volatilidad_pct"] = round(volatilidad, 1) if volatilidad else None
    
    if volatilidad and volatilidad < MIN_VOLATILIDAD_PCT:
        motivos_rechazo.append(f"Volatilidad baja ({volatilidad:.1f}%)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SI HAY RECHAZOS → NO OPERAR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if motivos_rechazo:
        return {
            "decision": "NO_OPERAR",
            "motivos": motivos_rechazo,
            "detalles": detalles
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CALCULAR ENTRADA Y STOP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    entrada = precio_actual
    stop = calcular_stop_inicial(entrada, precios, df)
    
    # Validar riesgo
    validacion_riesgo = validar_riesgo(entrada, stop)
    detalles.update({
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2)
    })
    
    if not validacion_riesgo["riesgo_valido"]:
        return {
            "decision": "NO_OPERAR",
            "motivos": [validacion_riesgo["motivo"]],
            "detalles": detalles
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ SEÑAL DE COMPRA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    motivos_compra = [
        "Tendencia alcista fuerte",
        f"Breakout confirmado (+{detalles['breakout_distancia_pct']}%)"
    ]
    
    if mejor_consolidacion:
        motivos_compra.append(f"Consolidación previa ({mejor_consolidacion['semanas_consolidacion']} semanas)")
    
    if analisis_breakout.get("volumen_confirma"):
        motivos_compra.append(f"Volumen confirmación ({detalles['breakout_volumen_ratio']:.1f}x)")
    
    return {
        "decision": "COMPRA",
        "entrada": round(entrada, 2),
        "stop": round(stop, 2),
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2),
        "detalles": detalles,
        "motivos": motivos_compra
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 EVALUADOR CON SCORING (para escáneres)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluar_con_scoring(precios, volumenes=None, fechas=None, df=None):
    """
    Versión con scoring para clasificar valores.
    
    Scoring 0-10:
    - Tendencia alcista: +3
    - Breakout confirmado: +3
    - Consolidación previa: +2
    - Volumen confirmación: +1
    - Riesgo válido: +1
    
    Returns:
        dict con decisión + score
    """
    resultado = evaluar_entrada_posicional(precios, volumenes, fechas, df)
    
    # Calcular score (0-10)
    score = 0
    max_score = 10
    
    detalles = resultado.get("detalles", {})
    
    # Tendencia alcista: +3
    if detalles.get("tendencia") == "ALCISTA":
        score += 3
    
    # Breakout confirmado: +3
    if detalles.get("breakout"):
        score += 3
    
    # Consolidación previa: +2
    if detalles.get("consolidacion"):
        score += 2
    
    # Volumen confirmación: +1
    if detalles.get("breakout_volumen_ratio", 0) >= BREAKOUT_VOLUMEN_MIN_RATIO:
        score += 1
    
    # Riesgo válido: +1
    riesgo = detalles.get("riesgo_pct", 0)
    if RIESGO_MIN_PCT <= riesgo <= RIESGO_MAX_PCT:
        score += 1
    
    resultado["setup_score"] = score
    resultado["setup_max"] = max_score
    
    # Clasificación
    if resultado["decision"] == "COMPRA" and score >= 8:
        resultado["clasificacion"] = "COMPRA"
    elif score >= 6:
        resultado["clasificacion"] = "VIGILANCIA"
    else:
        resultado["clasificacion"] = "DESCARTADO"
    
    # Preservar entrada/stop/riesgo si existen
    if "entrada" not in resultado:
        resultado["entrada"] = 0
    if "stop" not in resultado:
        resultado["stop"] = 0
    if "riesgo_pct" not in resultado and "detalles" in resultado:
        resultado["riesgo_pct"] = resultado["detalles"].get("riesgo_pct", 0)
    
    return resultado


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 ANÁLISIS DETALLADO (para UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generar_reporte_completo(ticker, precios, volumenes=None, fechas=None, df=None):
    """
    Genera reporte completo para mostrar en UI.
    
    Returns:
        dict con toda la información formateada
    """
    resultado = evaluar_con_scoring(precios, volumenes, fechas, df)
    
    # Información básica
    precio_actual = precios[-1]
    
    reporte = {
        "ticker": ticker,
        "precio_actual": round(precio_actual, 2),
        "decision": resultado["decision"],
        "clasificacion": resultado.get("clasificacion", "N/A"),
        "score": f"{resultado.get('setup_score', 0)}/{resultado.get('setup_max', 10)}"
    }
    
    # Si hay señal de compra
    if resultado["decision"] == "COMPRA":
        reporte.update({
            "entrada": resultado["entrada"],
            "stop": resultado["stop"],
            "riesgo_pct": resultado["riesgo_pct"],
            "objetivo_r": "10-30R",  # Objetivo posicional
            "duracion_estimada": "6-24 meses"
        })
    
    # Detalles técnicos
    reporte["detalles"] = resultado.get("detalles", {})
    reporte["motivos"] = resultado.get("motivos", [])
    
    return reporte


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test sistema_trading_posicional.py")
    print("=" * 60)
    
    # Simular tendencia alcista con consolidación y breakout
    import numpy as np
    
    # 200 semanas tendencia alcista
    base = [100 + i*0.8 for i in range(200)]
    
    # 26 semanas consolidando
    consolidacion = [base[-1] + np.random.uniform(-3, 3) for _ in range(26)]
    
    # Breakout
    breakout = [consolidacion[-1] + i*2 for i in range(5)]
    
    precios_test = base + consolidacion + breakout
    volumenes_test = [1000000 + np.random.uniform(-200000, 400000) for _ in range(len(precios_test))]
    # Volumen mayor en breakout
    volumenes_test[-5:] = [v * 2 for v in volumenes_test[-5:]]
    
    print(f"\n📊 Datos simulados:")
    print(f"   Total semanas: {len(precios_test)}")
    print(f"   Precio actual: {precios_test[-1]:.2f}")
    print(f"   Precio hace 26 semanas: {precios_test[-26]:.2f}")
    print(f"   Precio hace 200 semanas: {precios_test[-200]:.2f}")
    
    print(f"\n🔍 Evaluando señal...")
    resultado = evaluar_entrada_posicional(precios_test, volumenes_test)
    
    print(f"\n🎯 RESULTADO:")
    print(f"   Decisión: {resultado['decision']}")
    
    if resultado['decision'] == 'COMPRA':
        print(f"   Entrada: {resultado['entrada']:.2f}")
        print(f"   Stop: {resultado['stop']:.2f}")
        print(f"   Riesgo: {resultado['riesgo_pct']:.1f}%")
        print(f"\n   Motivos:")
        for motivo in resultado['motivos']:
            print(f"   ✓ {motivo}")
    else:
        print(f"\n   Motivos rechazo:")
        for motivo in resultado['motivos']:
            print(f"   ✗ {motivo}")
    
    print(f"\n📋 Detalles:")
    for k, v in resultado.get('detalles', {}).items():
        print(f"   {k}: {v}")
    
    # Test scoring
    print(f"\n📊 Test con scoring:")
    resultado_scoring = evaluar_con_scoring(precios_test, volumenes_test)
    print(f"   Score: {resultado_scoring['setup_score']}/{resultado_scoring['setup_max']}")
    print(f"   Clasificación: {resultado_scoring['clasificacion']}")
    
    print("\n" + "=" * 60)
