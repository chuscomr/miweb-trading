# ==========================================================
# SISTEMA TRADING MEDIO PLAZO - VERSIÓN OPTIMIZADA
# Integración completa: análisis + señales de entrada
# Estrategia: Pullback en tendencia alcista
# ==========================================================

from .logica_medio import *
from .config_medio import *


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 CACHE GLOBAL PARA DATOS DEL IBEX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_CACHE_IBEX = {
    "datos": None,
    "timestamp": None,
    "validez_minutos": 60  # Cache válido por 60 minutos
}


def obtener_estado_mercado_ibex(forzar_descarga=False):
    """
    Obtiene el estado del mercado IBEX (ALCISTA/BAJISTA) con caché.
    
    Args:
        forzar_descarga: Si True, ignora el caché y descarga datos frescos
    
    Returns:
        dict con estado del mercado o None si hay error
    """
    from datetime import datetime, timedelta
    import time
    
    # Verificar si el cache es válido
    ahora = datetime.now()
    cache_valido = False
    
    if not forzar_descarga and _CACHE_IBEX["timestamp"] is not None:
        tiempo_transcurrido = (ahora - _CACHE_IBEX["timestamp"]).total_seconds() / 60
        cache_valido = tiempo_transcurrido < _CACHE_IBEX["validez_minutos"]
    
    # Si el cache es válido, devolver datos cacheados
    if cache_valido and _CACHE_IBEX["datos"] is not None:
        return _CACHE_IBEX["datos"]
    
    # Descargar datos frescos del IBEX
    try:
        import yfinance as yf
        import pandas as pd
        
        # Descargar datos del IBEX
        datos_ibex = yf.download("^IBEX", period="1y", progress=False)
        
        # Aplanar MultiIndex si existe
        if isinstance(datos_ibex.columns, pd.MultiIndex):
            datos_ibex.columns = datos_ibex.columns.droplevel(1)
        
        # Verificar que tenemos datos válidos
        if not datos_ibex.empty and len(datos_ibex) >= 200:
            # Extraer serie de precios
            serie_close = datos_ibex['Close']
            
            # Calcular MM200
            mm200_serie = serie_close.rolling(200).mean()
            
            # Extraer valores escalares
            precio_ibex_valor = serie_close.iloc[-1]
            mm200_ibex_valor = mm200_serie.iloc[-1]
            
            # Convertir a float Python nativo
            precio_ibex_num = float(precio_ibex_valor)
            mm200_ibex_num = float(mm200_ibex_valor)
            
            # Determinar estado del mercado
            estado = "ALCISTA" if precio_ibex_num > mm200_ibex_num else "BAJISTA"
            
            # Guardar en caché
            resultado = {
                "estado": estado,
                "precio_ibex": round(precio_ibex_num, 2),
                "mm200_ibex": round(mm200_ibex_num, 2),
                "fecha_datos": datos_ibex.index[-1].strftime("%Y-%m-%d")
            }
            
            _CACHE_IBEX["datos"] = resultado
            _CACHE_IBEX["timestamp"] = ahora
            
            return resultado
        else:
            print(f"⚠️ Advertencia: Datos IBEX insuficientes. Continuando análisis...")
            return None
            
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo verificar mercado IBEX ({str(e)}). Continuando análisis...")
        return None


def limpiar_cache_ibex():
    """
    Limpia el caché del IBEX (útil para testing o forzar actualización).
    """
    _CACHE_IBEX["datos"] = None
    _CACHE_IBEX["timestamp"] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 EVALUADOR PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluar_entrada_medio_plazo(precios, volumenes=None, fechas=None, df=None):
    """
    Evaluador completo para entrada en medio plazo.
    
    ESTRATEGIA:
    1. Tendencia alcista (precio > MM20, pendiente +)
    2. Pullback 3-12% desde máximo reciente
    3. Giro semanal (confirmación)
    4. Stop por estructura + ATR
    5. Riesgo 1.5-4%
    
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
    # 🚨 FILTRO CRÍTICO: MERCADO ALCISTA IBEX (CON CACHÉ)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    estado_ibex = obtener_estado_mercado_ibex()
    
    if estado_ibex is not None:
        detalles["mercado_ibex"] = estado_ibex["estado"]
        detalles["precio_ibex"] = estado_ibex["precio_ibex"]
        detalles["mm200_ibex"] = estado_ibex["mm200_ibex"]
        
        if estado_ibex["estado"] == "BAJISTA":
            return {
                "decision": "NO_OPERAR",
                "motivos": ["🚫 IBEX por debajo de MM200 - Mercado bajista general"],
                "detalles": detalles
            }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 1: VOLATILIDAD MÍNIMA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if MIN_VOLATILIDAD_PCT > 0:
        vol = calcular_volatilidad(precios)
        detalles["volatilidad_pct"] = round(vol, 1) if vol else None
        
        if vol and vol < MIN_VOLATILIDAD_PCT:
            motivos_rechazo.append(f"Volatilidad baja ({vol:.1f}%)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PARÁMETROS ADAPTATIVOS SEGÚN VOLATILIDAD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    params = calcular_parametros_adaptativos(vol) if vol else None

    stop_atr_mult = params.get("stop_atr_mult", STOP_ATR_MULTIPLICADOR) if params else STOP_ATR_MULTIPLICADOR
    pullback_min = params.get("pullback_min", PULLBACK_MIN_PCT) if params else PULLBACK_MIN_PCT
    riesgo_max = params.get("riesgo_max", RIESGO_MAX_PCT) if params else RIESGO_MAX_PCT

    # Guardar para análisis / debug
    detalles["stop_atr_mult"] = stop_atr_mult
    detalles["pullback_min"] = pullback_min
    detalles["riesgo_max"] = riesgo_max

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 2: TENDENCIA ALCISTA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_tendencia = detectar_tendencia_semanal(precios)

    detalles.update({
        "tendencia": analisis_tendencia.get("tendencia"),
        "mm20": round(analisis_tendencia["mm20"], 2) if analisis_tendencia.get("mm20") else None,
        "precio_vs_mm20_pct": round(analisis_tendencia["precio_vs_mm20"], 2)
            if analisis_tendencia.get("precio_vs_mm20") is not None else None,
        "pendiente_mm20": round(analisis_tendencia.get("pendiente_mm20", 0), 4)
    })

    if analisis_tendencia["tendencia"] != "ALCISTA":
        motivos_rechazo.append(f"Tendencia {analisis_tendencia['tendencia'].lower()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 3: PULLBACK VÁLIDO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    analisis_pullback = detectar_pullback(precios)
    if analisis_pullback["es_pullback"]:
        if analisis_pullback["retroceso_pct"] < pullback_min:
            motivos_rechazo.append(
                f"Pullback insuficiente para volatilidad ({analisis_pullback['retroceso_pct']:.1f}%)"
            )

    detalles.update({
        "retroceso_pct": round(analisis_pullback.get("retroceso_pct", 0), 1),
        "maximo_reciente": round(analisis_pullback.get("maximo_reciente", 0), 2)
    })
    
    if not analisis_pullback["es_pullback"]:
        motivos_rechazo.append(analisis_pullback["motivo"])
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILTRO 4: GIRO SEMANAL (confirmación)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if REQUIERE_GIRO_SEMANAL:
        analisis_giro = detectar_giro_semanal(precios)
        detalles["giro_semanal"] = analisis_giro["hay_giro"]
        detalles["variacion_pct"] = round(analisis_giro.get("variacion_pct", 0), 2)
        if not analisis_giro["hay_giro"]:
            motivos_rechazo.append("Sin giro semanal")
    
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
    stop = calcular_stop_inicial(entrada, precios, df=df, stop_atr_mult=stop_atr_mult)
    
    # Validar riesgo
    validacion_riesgo = validar_riesgo(entrada, stop)
    detalles.update({
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2)
    })
    if validacion_riesgo["riesgo_pct"] > riesgo_max:
        return {
            "decision": "NO_OPERAR",
            "motivos": [f"Riesgo excesivo para volatilidad ({validacion_riesgo['riesgo_pct']:.2f}%)"],
            "detalles": detalles
    }

    if not validacion_riesgo["riesgo_valido"]:
        return {
            "decision": "NO_OPERAR",
            "motivos": [validacion_riesgo["motivo"]],
            "detalles": detalles
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ SEÑAL DE COMPRA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    return {
        "decision": "COMPRA",
        "entrada": round(entrada, 2),
        "stop": round(stop, 2),
        "riesgo_pct": round(validacion_riesgo["riesgo_pct"], 2),
        "detalles": detalles,
        "motivos": [
            "Tendencia alcista",
            f"Pullback {detalles['retroceso_pct']}%",
            "Giro semanal confirmado",
            "Riesgo controlado"
        ]
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 EVALUADOR CON SCORING (para escáneres)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def evaluar_con_scoring(precios, volumenes=None, fechas=None, df=None):
    """
    Evaluación completa con scoring robusto y rangos explícitos.
    """
    # 1️⃣ Evaluación base (filtros duros)
    resultado = evaluar_entrada_medio_plazo(precios, volumenes, fechas, df)
    
    # 2️⃣ Calcular score técnico
    precio_actual = precios[-1] if precios else 0
    detalles = resultado.get("detalles", {})
    
    score = calcular_score_detallado(
        precios=precios,
        volumenes=volumenes,
        df=df,
        detalles=detalles,
        decision=resultado["decision"]
    )
    
    resultado["score"] = score
    resultado["score_max"] = 10
    
    # 3️⃣ CLASIFICACIÓN CON RANGOS EXPLÍCITOS
    decision = resultado["decision"]
    
    if decision == "COMPRA" and score >= 8:
        resultado["clasificacion"] = "COMPRA_FUERTE"
        resultado["setup_calidad"] = "ALTA"
        resultado["setup_valido"] = True
    
    elif decision == "COMPRA" and score >= 6:
        resultado["clasificacion"] = "COMPRA_DEBIL"
        resultado["setup_calidad"] = "MEDIA"
        resultado["setup_valido"] = True
    
    elif decision == "COMPRA":  # Score 3-5 pero pasa filtros duros
        resultado["clasificacion"] = "COMPRA_MARGINAL"
        resultado["setup_calidad"] = "BAJA"
        resultado["setup_valido"] = True
    
    elif score >= 6:  # NO_OPERAR pero buen score
        resultado["clasificacion"] = "VIGILANCIA"
        resultado["setup_calidad"] = "MEDIA"
        resultado["setup_valido"] = False
        # Limpiar valores de entrada
        resultado["entrada"] = 0
        resultado["stop"] = 0
        resultado["riesgo_pct"] = 0
    
    else:  # NO_OPERAR y score bajo
        resultado["clasificacion"] = "DESCARTADO"
        resultado["setup_calidad"] = "BAJA"
        resultado["setup_valido"] = False
        resultado["entrada"] = 0
        resultado["stop"] = 0
        resultado["riesgo_pct"] = 0
    
    # 4️⃣ Información para UI
    resultado["precio_actual"] = round(precio_actual, 2)
    
    # 5️⃣ Mensaje descriptivo
    mensajes = {
        "COMPRA_FUERTE": "✅ Setup excelente - Alta probabilidad",
        "COMPRA_DEBIL": "🟡 Setup válido - Observaciones técnicas",
        "COMPRA_MARGINAL": "⚠️ Setup marginal - Riesgo alto",
        "VIGILANCIA": "👁️ Setup técnico bueno - Revisar filtros",
        "DESCARTADO": "❌ Setup débil - No operar"
    }
    resultado["mensaje_clasificacion"] = mensajes.get(resultado["clasificacion"], "")
    
    return resultado


def calcular_score_detallado(precios, volumenes, df, detalles, decision=None):
    """
    Score detallado 0-10 con pesos específicos y CORREGIDO.
    """
    if not detalles:
        return 0
    
    score = 0
    
    # --------------------------------------------------
    # 1. TENDENCIA (Máx: 3 puntos)
    # --------------------------------------------------
    if detalles.get("tendencia") == "ALCISTA":
        # Tendencia alcista clara (pendiente positiva)
        if detalles.get("pendiente_mm20", 0) > 0.01:  # Pendiente > 1%
            score += 3
        else:
            score += 2  # Alcista pero lateral
    
    # --------------------------------------------------
    # 2. PULLBACK (Máx: 3 puntos)
    # --------------------------------------------------
    retroceso = detalles.get("retroceso_pct", 0)
    pullback_min = detalles.get("pullback_min", PULLBACK_MIN_PCT)
    
    if 4.0 <= retroceso <= 8.0:
        score += 3  # Rango óptimo
    elif pullback_min <= retroceso < 4.0:
        score += 2  # En rango mínimo
    elif 8.0 < retroceso <= 12.0:
        score += 1  # Retroceso grande pero aceptable
    # Nota: retroceso > 12% ya es rechazado por filtro duro
    
    # --------------------------------------------------
    # 3. GIRO SEMANAL (Máx: 2 puntos)
    # --------------------------------------------------
    if detalles.get("giro_semanal"):
        variacion = detalles.get("variacion_pct", 0)
        if variacion > 1.5:  # Fuerte
            score += 2
        elif variacion > 0.5:  # Moderado
            score += 1
        else:  # Débil pero positivo
            score += 0.5  # Medio punto
    
    # --------------------------------------------------
    # 4. RIESGO CONTROLADO (Máx: 2 puntos)
    # --------------------------------------------------
    riesgo = detalles.get("riesgo_pct", 0)
    
    if 1.8 <= riesgo <= 2.5:
        score += 2  # Rango óptimo
    elif RIESGO_MIN_PCT <= riesgo < 1.8:
        score += 1  # Riesgo bajo
    elif 2.5 < riesgo <= RIESGO_MAX_PCT:
        score += 1  # Riesgo alto pero aceptable
    
    # --------------------------------------------------
    # 5. VOLATILIDAD (Máx: 1 punto)
    # --------------------------------------------------
    volatilidad = detalles.get("volatilidad_pct", 0)
    if MIN_VOLATILIDAD_PCT > 0 and volatilidad:
        if volatilidad >= MIN_VOLATILIDAD_PCT:
            score += 1  # Volatilidad suficiente
        # Nota: Si volatilidad < MIN_VOLATILIDAD_PCT, ya fue rechazada
    
    # --------------------------------------------------
    # 6. COHERENCIA SISTÉMICA (ajuste final)
    # --------------------------------------------------
    # Si pasó filtros duros (decision == "COMPRA") pero score bajo,
    # es porque es una compra marginal
    if decision == "COMPRA" and score < 3:
        score = 3  # Mínimo para compra válida
    
    # Si es ALCISTA pero score muy bajo, dar puntos base
    if detalles.get("tendencia") == "ALCISTA" and score < 2:
        score = 2
    
    # Cap a 10
    return min(round(score), 10)  # Redondear a entero


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 ANÁLISIS DETALLADO (para UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generar_reporte_completo(ticker, precios, volumenes=None, fechas=None, df=None):
    """
    Genera reporte completo para mostrar en UI.
    """
    resultado = evaluar_con_scoring(precios, volumenes, fechas, df)
    
    # Información básica
    precio_actual = precios[-1]
    
    reporte = {
        "ticker": ticker,
        "precio_actual": round(precio_actual, 2),
        "decision": resultado["decision"],
        "clasificacion": resultado.get("clasificacion", "N/A"),
        "score": f"{resultado.get('score', 0)}/{resultado.get('score_max', 10)}",
        "setup_valido": resultado.get("setup_valido", False)
    }
    
    # Solo mostrar entrada/stop si es setup válido
    if resultado.get("setup_valido"):
        reporte.update({
            "entrada": resultado.get("entrada", 0),
            "stop": resultado.get("stop", 0),
            "riesgo_pct": resultado.get("riesgo_pct", 0)
        })
    
    # Detalles técnicos
    reporte["detalles"] = resultado.get("detalles", {})
    reporte["motivos"] = resultado.get("motivos", [])
    reporte["mensaje_clasificacion"] = resultado.get("mensaje_clasificacion", "")
    
    return reporte


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧪 TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🧪 Test sistema_trading_medio.py")
    print("=" * 50)
    
    # Simular tendencia alcista con pullback
    base = [10 + i*0.3 for i in range(30)]  # Tendencia alcista
    pullback = [38, 37, 36, 35, 35.5, 36]   # Pullback 5%
    precios_test = base + pullback
    
    print(f"\n📊 Precios simulados (últimos 10):")
    print(f"   {[round(p, 1) for p in precios_test[-10:]]}")
    
    resultado = evaluar_entrada_medio_plazo(precios_test)
    
    print(f"\n🎯 RESULTADO:")
    print(f"   Decisión: {resultado['decision']}")
    
    if resultado['decision'] == 'COMPRA':
        print(f"   Entrada: {resultado['entrada']}")
        print(f"   Stop: {resultado['stop']}")
        print(f"   Riesgo: {resultado['riesgo_pct']}%")
        print(f"   Motivos: {', '.join(resultado['motivos'])}")
    else:
        print(f"   Motivos rechazo: {', '.join(resultado['motivos'])}")
    
    print(f"\n📋 Detalles:")
    for k, v in resultado.get('detalles', {}).items():
        print(f"   {k}: {v}")
