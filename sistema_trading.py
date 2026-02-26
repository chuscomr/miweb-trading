import pandas as pd
import numpy as np
from datetime import datetime
from utils_validacion import validar_datos_ticker

# =============================
# INDICADORES
# =============================
def media_movil(precios, n):
    return sum(precios[-n:]) / n if len(precios) >= n else None

def calcular_entrada_adaptativa(precio_actual, max_reciente, dist_max):
    """
    Calcula entrada adaptativa de forma robusta.
    - Funciona incluso si dist_max es None
    - Prioriza enfoque conservador si faltan datos
    """

    # ─────────────────────────
    # VALIDACIONES CRÍTICAS
    # ─────────────────────────
    if precio_actual is None or precio_actual <= 0:
        return None

    if max_reciente is None or max_reciente <= 0:
        return None

    # Si no sabemos la distancia al máximo, asumir escenario conservador
    if dist_max is None:
        dist_max = 999  # fuerza rama conservadora

    # ─────────────────────────
    # LÓGICA ADAPTATIVA
    # ─────────────────────────
    if dist_max <= 0.5:
        # Muy cerca del máximo → breakout controlado
        return round(max_reciente * 1.001, 2)

    elif dist_max <= 1.5:
        # Cerca del máximo → entrada por momentum
        return round(precio_actual * 1.005, 2)

    else:
        # Alejado del máximo → entrada intermedia prudente
        return round(((precio_actual + max_reciente) / 2) * 1.002, 2)


def pendiente_media(precios, n=20):
    if len(precios) < n + 5:
        return None
    mm_hoy = sum(precios[-n:]) / n
    mm_antes = sum(precios[-(n+5):-5]) / n
    return mm_hoy - mm_antes

def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganancias = delta.clip(lower=0)
    perdidas = -delta.clip(upper=0)

    media_gan = ganancias.ewm(alpha=1/periodo, adjust=False).mean()
    media_per = perdidas.ewm(alpha=1/periodo, adjust=False).mean()

    rs = media_gan / media_per
    rsi = 100 - (100 / (1 + rs))
    return rsi

def maximo_reciente(precios, periodo):
    if len(precios) < periodo:
        return None
    return max(precios[-periodo:])

def evaluar_volumen_profesional(volumenes):
    if len(volumenes) < 21:
        return {
            "nivel": "NO_VALIDADO",
            "permitir_normal": True,
            "permitir_impulso": False,
            "penalizacion_score": -1,
            "mensaje": "ℹ️ Volumen no validado"
        }

    vol_actual = volumenes[-2]
    media_vol_10 = sum(volumenes[-11:-1]) / 10
    media_vol_20 = sum(volumenes[-21:-1]) / 20

    if media_vol_20 < 50_000:
        return {
            "nivel": "ILIQUIDO",
            "permitir_normal": False,
            "permitir_impulso": False,
            "penalizacion_score": -3,
            "mensaje": f"❌ Liquidez insuficiente ({int(media_vol_20):,}/día)"
        }

    ratio = vol_actual / media_vol_10 if media_vol_10 > 0 else 0
    tendencia = media_vol_10 / media_vol_20 if media_vol_20 > 0 else 1.0

    if ratio >= 1.5:
        return {
            "nivel": "EXPLOSIVO",
            "permitir_normal": True,
            "permitir_impulso": True,
            "bonus_score": +1,
            "mensaje": f"🔥 Volumen explosivo ({ratio:.2f}x)"
        }

    elif ratio >= 1.05:
        return {
            "nivel": "FUERTE",
            "permitir_normal": True,
            "permitir_impulso": True,
            "mensaje": f"✅ Volumen fuerte ({ratio:.2f}x)"
        }

    elif ratio >= 0.85 and tendencia >= 1.1:
        return {
            "nivel": "NORMAL_CRECIENTE",
            "permitir_normal": True,
            "permitir_impulso": False,
            "mensaje": "📊 Volumen normal en crecimiento"
        }

    elif tendencia >= 1.0:
        return {
            "nivel": "SECO_SANO",
            "permitir_normal": True,
            "permitir_impulso": False,
            "mensaje": "🤫 Volumen seco saludable"
        }

    elif ratio >= 0.75:
        return {
            "nivel": "ACEPTABLE",
            "permitir_normal": True,
            "permitir_impulso": False,
            "penalizacion_score": -1,
            "mensaje": f"⚠️ Volumen aceptable ({ratio:.2f}x)"
        }

    else:
        return {
            "nivel": "INSUFICIENTE",
            "permitir_normal": False,
            "permitir_impulso": False,
            "penalizacion_score": -2,
            "mensaje": f"❌ Volumen insuficiente ({ratio:.2f}x)"
        }

# =============================
# VOLATILIDAD Y PARÁMETROS
# =============================
def volatilidad_relativa(precios, periodo=20):
    if len(precios) < periodo:
        return None

    ventana = precios[-periodo:]
    rango = max(ventana) - min(ventana)
    media = sum(ventana) / periodo
    return (rango / media) * 100 if media != 0 else None


def clasificar_volatilidad(vol):
    if vol is None:
        return "media"
    if vol < 2:
        return "baja"
    elif vol < 4:
        return "media"
    else:
        return "alta"


def obtener_parametros_adaptativos(precios):
    vol = volatilidad_relativa(precios)
    nivel = clasificar_volatilidad(vol)
    params = {"max": 30, "mm": 20, "trailing": 0.07}
    return vol, nivel, params


# =============================
# SEÑAL PRINCIPAL
# =============================
def sistema_trading(precios, volumenes, fechas=None, precio_actual=None):
    motivos = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🚨 FILTRO CRÍTICO: MERCADO ALCISTA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    try:
        import yfinance as yf
        datos_ibex = yf.download("^IBEX", period="1y", progress=False)
        
        if not mercado_alcista_general(datos_ibex):
            motivos.append({
                "ok": False,
                "texto": "❌ IBEX por debajo de MM200 - Mercado bajista"
            })
            return {
                "decision": "NO OPERAR",
                "motivos": motivos
            }
        else:
            motivos.append({
                "ok": True,
                "texto": "✅ IBEX por encima de MM200 - Mercado alcista"
            })
    except Exception as e:
        # Si falla la descarga, continuar (no bloquear por error técnico)
        print(f"⚠️ Error verificando mercado: {e}")

    # ─────────────────────────
    #  1️⃣VALIDACIÓN DE DATOS
    # ─────────────────────────
    validacion = validar_datos_ticker(
        ticker="DESCONOCIDO",   # o pásalo si lo tienes
        precios=precios,
        volumenes=volumenes,
        fechas=fechas or []
    )

    if not validacion["valido"]:
        for err in validacion["errores"]:
            motivos.append({"ok": False, "texto": f"❌ {err}"})

        return {
            "decision": "NO OPERAR",
            "motivos": motivos
        }

    # Advertencias (no bloquean)
    for adv in validacion["advertencias"]:
        motivos.append({"ok": True, "texto": f"⚠️ {adv}"})

    precio = precio_actual if precio_actual is not None else precios[-1]

    
    # ─────────────────────────
    # 2️⃣ MEDIAS Y TENDENCIA
      # ─────────────────────────
    mm20 = sum(precios[-20:]) / 20
    mm20_ant = sum(precios[-25:-5]) / 20
    pendiente = mm20 - mm20_ant

    max20 = max(precios[-20:])
    min20 = min(precios[-20:])
    volatilidad = (max20 - min20) / min20 * 100

    # 🔴 AQUÍ, SIEMPRE
    dist_mm = abs(precio - mm20) / mm20 * 100
    dist_max = (max20 - precio) / max20 * 100

    cond_mm = precio > mm20
    cond_pendiente = pendiente > 0

    motivos.append({
        "ok": cond_mm,
        "texto": "Precio por encima de MM20" if cond_mm else "Precio por debajo de MM20"
    })

    motivos.append({
        "ok": cond_pendiente,
        "texto": "MM20 con pendiente positiva" if cond_pendiente else "MM20 sin pendiente positiva"
    })

    if not (cond_mm and cond_pendiente):
        return {"decision": "NO OPERAR", "motivos": motivos}

   # ─────────────────────────────────────────────────────────────
# 3️⃣ RSI CON VALIDACIÓN PROFESIONAL
# ─────────────────────────────────────────────────────────────

def calcular_rsi_seguro(precios, periodo=14):
    """
    Calcula RSI con validaciones exhaustivas para evitar valores erróneos.
    
    Returns:
        float: RSI entre 0-100, o None si hay error
    """
    try:
        # Validar longitud mínima
        if len(precios) < periodo + 5:
            return None
        
        # Convertir a serie pandas y limpiar
        serie = pd.Series(precios, dtype=float)
        
        # Eliminar infinitos y NaN
        serie = serie.replace([np.inf, -np.inf], np.nan)
        serie = serie.dropna()
        
        if len(serie) < periodo + 5:
            return None
        
        # ──────────────────────────────────────────────────────
        # DETECCIÓN DE SPLITS/DIVIDENDOS/GAPS ANÓMALOS
        # ──────────────────────────────────────────────────────
        variaciones = serie.pct_change().abs()
        
        # Si hay cambios >50% en un día, probable split o error
        if any(variaciones > 0.50):
            print(f"⚠️ RSI: Detectado cambio extremo (>50%), datos sospechosos")
            return None
        
        # Si hay más de 3 gaps >20%, datos poco fiables
        gaps_grandes = sum(variaciones > 0.20)
        if gaps_grandes > 3:
            print(f"⚠️ RSI: {gaps_grandes} gaps >20%, volatilidad anómala")
            return None
        
        # ──────────────────────────────────────────────────────
        # DETECCIÓN DE PRECIOS ESTÁTICOS (SUSPENSIÓN COTIZACIÓN)
        # ──────────────────────────────────────────────────────
        # Si los últimos 5 días tienen el mismo precio exacto
        if len(set(serie[-5:])) == 1:
            print(f"⚠️ RSI: Precio estático últimos 5 días, posible suspensión")
            return None
        
        # ──────────────────────────────────────────────────────
        # CÁLCULO RSI
        # ──────────────────────────────────────────────────────
        delta = serie.diff()
        ganancias = delta.clip(lower=0)
        perdidas = -delta.clip(upper=0)
        
        # Media móvil exponencial (método Wilder)
        media_gan = ganancias.ewm(alpha=1/periodo, adjust=False).mean()
        media_per = perdidas.ewm(alpha=1/periodo, adjust=False).mean()
        
        # Evitar división por cero
        if media_per.iloc[-1] == 0:
            # Si no hay pérdidas, RSI = 100
            return 100.0
        
        rs = media_gan / media_per
        rsi_serie = 100 - (100 / (1 + rs))
        
        rsi_valor = rsi_serie.iloc[-1]
        
        # ──────────────────────────────────────────────────────
        # VALIDACIÓN FINAL DEL RESULTADO
        # ──────────────────────────────────────────────────────
        
        # RSI debe estar entre 0 y 100
        if not (0 <= rsi_valor <= 100):
            print(f"⚠️ RSI fuera de rango válido: {rsi_valor}")
            return None
        
        # Si es NaN
        if pd.isna(rsi_valor):
            return None
        
        return round(float(rsi_valor), 1)
        
    except Exception as e:
        print(f"❌ Error calculando RSI: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# APLICAR EN sistema_trading.py
# ─────────────────────────────────────────────────────────────

def sistema_trading(precios, volumenes, fechas=None, precio_actual=None):
    motivos = []

    # ... código anterior ...

    precio = precio_actual if precio_actual is not None else precios[-1]
    
    # ─────────────────────────────────────────────────────────
    # 2️⃣ MEDIAS Y TENDENCIA
    # ─────────────────────────────────────────────────────────
    mm20 = sum(precios[-20:]) / 20
    mm20_ant = sum(precios[-25:-5]) / 20
    pendiente = mm20 - mm20_ant

    max20 = max(precios[-20:])
    min20 = min(precios[-20:])
    volatilidad = (max20 - min20) / min20 * 100

    # 🔴 AQUÍ, SIEMPRE
    dist_mm = abs(precio - mm20) / mm20 * 100
    dist_max = (max20 - precio) / max20 * 100

    cond_mm = precio > mm20
    cond_pendiente = pendiente > 0

    motivos.append({
        "ok": cond_mm,
        "texto": "Precio por encima de MM20" if cond_mm else "Precio por debajo de MM20"
    })

    motivos.append({
        "ok": cond_pendiente,
        "texto": "MM20 con pendiente positiva" if cond_pendiente else "MM20 sin pendiente positiva"
    })

    if not (cond_mm and cond_pendiente):
        return {"decision": "NO OPERAR", "motivos": motivos}

    # ─────────────────────────────────────────────────────────
    # 3️⃣ RSI CON VALIDACIÓN SEGURA
    # ─────────────────────────────────────────────────────────
    
    rsi = calcular_rsi_seguro(precios, periodo=14)
    
    # ✅ VALIDACIÓN: Si RSI falló, no operar
    if rsi is None:
        motivos.append({
            "ok": False,
            "texto": "❌ RSI no calculable (datos insuficientes o erróneos)"
        })
        return {
            "decision": "NO OPERAR",
            "motivos": motivos,
            "setup_score": 0,
            "setup_max": 5
        }
    
    # ─────────────────────────────────────────────────────────
    # MOTIVOS INFORMATIVOS (solo si RSI es válido)
    # ─────────────────────────────────────────────────────────
    
    motivos.append({"ok": True, "texto": f"RSI actual: {rsi}"})
    motivos.append({"ok": True, "texto": f"Distancia a MM20: {dist_mm:.1f}%"})
    motivos.append({"ok": True, "texto": f"Distancia al máximo 20: {dist_max:.1f}%"})
    
    # ─────────────────────────────────────────────────────────
    # 3️⃣ BIS — VOLUMEN PROFESIONAL
    # ─────────────────────────────────────────────────────────
    eval_vol = evaluar_volumen_profesional(volumenes)

    motivos.append({
        "ok": eval_vol["permitir_normal"],
        "texto": eval_vol["mensaje"]
    })

    
    # ─────────────────────────
    # 4️⃣ VOLATILIDAD
       # ─────────────────────────
    cond_vol = volatilidad <= 10

    motivos.append({
        "ok": cond_vol,
        "texto": f"Volatilidad controlada ({volatilidad:.1f} %)"
        if cond_vol else f"Volatilidad excesiva ({volatilidad:.1f} %)"
    })

    if not cond_vol:
        return {"decision": "NO OPERAR", "motivos": motivos}

    # ─────────────────────────
    # 5️⃣ DISTANCIAS
       # ─────────────────────────
    cond_dist_max = dist_max <= 3

    motivos.append({
        "ok": cond_dist_max,
        "texto": "Precio cercano a ruptura"
        if cond_dist_max else "Precio demasiado alejado del máximo"
    })

    # ─────────────────────────
    # SETUP SCORE
    # ─────────────────────────
    setup_score = 0
    setup_max = 5

    # RSI mínimo aceptable
    if rsi >= 55:
        setup_score += 1

    # RSI óptimo
    if 60 <= rsi <= 68:
        setup_score += 1

    # Precio muy cerca del máximo
    if dist_max <= 1:
        setup_score += 1

    # Precio ordenado respecto a MM20
    if dist_mm <= 3:
        setup_score += 1

    # Tendencia fuerte
    if pendiente > 0:
        setup_score += 1
        setup_score += eval_vol.get("bonus_score", 0)
        setup_score += eval_vol.get("penalizacion_score", 0)
        setup_score = max(0, min(setup_score, setup_max))

    
    # ─────────────────────────
    # 6️⃣ COMPRA NORMAL
       # ─────────────────────────
    
    cond_rsi_fuerza = 45 < rsi < 70
    cond_mm_normal = dist_mm <= 4
    cond_max_normal = dist_max <= 3
    

    if (
        cond_rsi_fuerza
        and cond_mm_normal
        and cond_max_normal
        and setup_score >= 3
        and eval_vol["permitir_normal"]

    ):
        entrada = calcular_entrada_adaptativa(
            precio_actual=precio,
            max_reciente=max20,
            dist_max=dist_max
        )

        motivos.append({
            "ok": True,
            "texto": f"Entrada NORMAL: setup sólido ({setup_score}/5)"
        })

        return {
            "decision": "COMPRA",
            "tipo_entrada": "NORMAL",
            "entrada": entrada,
            "setup_score": setup_score,
            "setup_max": setup_max,
            "motivos": motivos
        }

    # ─────────────────────────
    # 7️⃣ COMPRA IMPULSO
     # ─────────────────────────
    
    cond_rsi_impulso = 60 <= rsi <= 73
    cond_mm_impulso = dist_mm <= 6
    cond_ruptura = dist_max <= 3
    

    if (
        cond_rsi_impulso
        and cond_mm_impulso
        and cond_ruptura
        and setup_score >= 4
        and eval_vol["permitir_impulso"]

    ):
        entrada = calcular_entrada_adaptativa(
            precio_actual=precio,
            max_reciente=max20,
            dist_max=dist_max
        )

        motivos.append({
            "ok": True,
            "texto": f"Entrada IMPULSO: setup fuerte ({setup_score}/5)"
        })

        return {
            "decision": "COMPRA",
            "tipo_entrada": "IMPULSO",
            "entrada": entrada,
            "setup_score": setup_score,
            "setup_max": setup_max,
            "motivos": motivos
        }


    # ─────────────────────────
    # 8️⃣ VIGILANCIA
       # ─────────────────────────
    motivos.append({
        "ok": False,
        "texto": "Tendencia válida pero sin setup óptimo (NORMAL / IMPULSO)"
    })
    
    return {
        "decision": "VIGILANCIA",
        "setup_score": setup_score,
        "setup_max": setup_max,
        "motivos": motivos
    }
    # ─────────────────────────
    # 9 MERCADO ALCISTA
    # ─────────────────────────
def mercado_alcista_general(datos_indice):
    """
    Recibe un DataFrame con los datos del ^IBEX y devuelve True 
    si el último cierre está por encima de la MM200.
    """
    if len(datos_indice) < 200:
        return True # Por seguridad, si no hay datos suficientes, no bloquea
    
    mm200_indice = datos_indice['Close'].rolling(window=200).mean().iloc[-1]
    ultimo_cierre_indice = datos_indice['Close'].iloc[-1]
    
    return ultimo_cierre_indice > mm200_indice  
          
    # =============================
    # BACKTESTING
    # =============================
def backtesting(precios):
    if len(precios) < 50:
        return []

    vol, nivel, p = obtener_parametros_adaptativos(precios)

    capital = 0
    en_posicion = False
    entrada = 0
    max_trade = 0

    operaciones = 0
    aciertos = 0

    for i in range(len(precios)):
        precio = precios[i]
        mm = media_movil(precios[:i+1], p["mm"])
        serie = pd.Series(precios[:i+1])
        rsi = calcular_rsi(serie).iloc[-1]

        max_rec = maximo_reciente(precios[:i], p["max"])

        if mm is None or rsi is None or max_rec is None:
            continue

        if not en_posicion and precio > max_rec and precio > mm and 45 <= rsi <= 70:
            en_posicion = True
            entrada = precio
            max_trade = precio

        if en_posicion:
            max_trade = max(max_trade, precio)
            stop = max_trade * (1 - p["trailing"])

            if precio < stop:
                resultado = precio - entrada
                capital += resultado
                operaciones += 1
                if resultado > 0:
                    aciertos += 1
                en_posicion = False

    winrate = (aciertos / operaciones * 100) if operaciones else 0

    return [
        f"Volatilidad detectada: {nivel}",
        f"Volatilidad media: {vol:.2f} %",
        f"Operaciones cerradas: {operaciones}",
        f"Aciertos: {aciertos}",
        f"Win rate: {winrate:.1f} %",
        f"Resultado total: {capital:.2f} €",
        f"Trailing stop: 7 %",
    ]


# =============================
# OPTIMIZACIÓN TRAILING
# =============================
def backtesting_trailing(precios, trailings):
    resultados = []

    for t in trailings:
        vol, nivel, p = obtener_parametros_adaptativos(precios)
        p = p.copy()
        p["trailing"] = t   # t ya es decimal (0.07 = 7%)

        capital = 0
        en_posicion = False
        entrada = 0
        max_trade = 0

        operaciones = 0
        aciertos = 0

        for i in range(len(precios)):
            precio = precios[i]
            mm = media_movil(precios[:i+1], p["mm"])
            serie = pd.Series(precios[:i+1])
            rsi = calcular_rsi(serie).iloc[-1]
            max_rec = maximo_reciente(precios[:i], p["max"])

            if mm is None or rsi is None or max_rec is None:
                continue

            if not en_posicion and precio > max_rec and precio > mm and rsi < 70:
                en_posicion = True
                entrada = precio
                max_trade = precio

            if en_posicion:
                max_trade = max(max_trade, precio)
                stop = max_trade * (1 - t)

                if precio < stop:
                    capital += precio - entrada
                    operaciones += 1
                    if precio > entrada:
                        aciertos += 1
                    en_posicion = False

        winrate = (aciertos / operaciones * 100) if operaciones else 0

        resultados.append({
            "trailing": int(t * 100),   # ahora sí: 5, 7, 10
            "operaciones": operaciones,
            "winrate": winrate,
            "resultado": capital
        })

    return resultados

# =============================
# RESUMEN Y ALERTAS
# =============================
def resumen_ejecutivo(dist_max, dist_mm, volatilidad, señal):

    if señal.startswith("COMPRA"):
        return "🟢 RUPTURA LIMPIA → COMPRA"

    if volatilidad == "alta":
        return "🔴 VOLATILIDAD ALTA → NO OPERAR"

    if dist_max > -1 and dist_mm >= 0:
        return "🟠 ACTIVO VIGILABLE → ESPERAR"

    return "⚪ SIN SETUP CLARO → ESPERAR"


def generar_alertas(dist_max, dist_mm, volatilidad, señal):
    alertas = []

    if volatilidad != "alta" and dist_max > -1 and dist_mm >= 0:
        alertas.append("🟠 VIGILANCIA: cerca de ruptura")

    if señal.startswith("COMPRA") and volatilidad != "alta":
        alertas.append("🟢 COMPRA: señal confirmada")

    return alertas
