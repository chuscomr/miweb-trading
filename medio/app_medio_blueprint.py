# ==========================================================
# APP MEDIO PLAZO - CON BACKTEST SISTEMA
# ==========================================================

from flask import Blueprint, render_template, request
from .config_medio import *
from .datos_medio import obtener_datos_semanales
from .sistema_trading_medio import generar_reporte_completo, evaluar_con_scoring
from .backtest_medio import ejecutar_backtest_medio_plazo
from .backtest_sistema_medio import ejecutar_backtest_sistema_completo


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 CREAR BLUEPRINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

medio_bp = Blueprint(
    'medio',
    __name__,
    template_folder='templates',
    url_prefix='/medio'
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🏠 RUTA PRINCIPAL → /medio/
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@medio_bp.route("/", methods=["GET", "POST"])
def index():
    """Página principal: análisis de ticker individual."""
    resultado = None
    error = None
    
    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        
        if not ticker:
            error = "Debes introducir un ticker"
            return render_template("index_medio.html", error=error)
        
        # Asegurar .MC
        if not ticker.endswith(".MC"):
            ticker += ".MC"
        
        try:
            # Descargar datos
            df_semanal, validacion = obtener_datos_semanales(ticker)
            
            if df_semanal is None:
                error = f"No se pudieron obtener datos para {ticker}"
                if validacion.get("errores"):
                    error += f": {', '.join(validacion['errores'])}"
                return render_template("index_medio.html", error=error)
            
            # Generar análisis
            precios = df_semanal['Close'].tolist()
            volumenes = df_semanal['Volume'].tolist()
            fechas = df_semanal.index.tolist()
            
            reporte = generar_reporte_completo(
                ticker=ticker,
                precios=precios,
                volumenes=volumenes,
                fechas=fechas,
                df=df_semanal
            )
            
            # Añadir info adicional
            reporte["semanas_historico"] = len(df_semanal)
            reporte["fecha_desde"] = df_semanal.index[0].strftime("%Y-%m-%d")
            reporte["fecha_hasta"] = df_semanal.index[-1].strftime("%Y-%m-%d")
            
            if validacion.get("advertencias"):
                reporte["advertencias"] = validacion["advertencias"]
            
            resultado = reporte
            
        except Exception as e:
            error = f"Error al analizar {ticker}: {str(e)}"
    
    return render_template("index_medio.html", resultado=resultado, error=error)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 BACKTEST INDIVIDUAL → /medio/backtest
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@medio_bp.route("/backtest", methods=["GET", "POST"])
def backtest():
    """Página de backtest de ticker individual."""
    resultado = None
    error = None
    
    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        
        if not ticker:
            error = "Debes introducir un ticker"
            return render_template("backtest_medio.html", error=error)
        
        # Asegurar .MC
        if not ticker.endswith(".MC"):
            ticker += ".MC"
        
        try:
            # Descargar datos
            df_semanal, validacion = obtener_datos_semanales(ticker)
            
            if df_semanal is None:
                error = f"No se pudieron obtener datos para {ticker}"
                return render_template("backtest_medio.html", error=error)
            
            # Ejecutar backtest
            resultado_bt = ejecutar_backtest_medio_plazo(df_semanal, ticker, verbose=False)
            
            # Preparar resultado para template
            resultado = {
                "ticker": ticker,
                "metricas": resultado_bt["metricas"],
                "total_trades": len(resultado_bt["trades"]),
                "semanas_historico": len(df_semanal),
                "fecha_desde": df_semanal.index[0].strftime("%Y-%m-%d"),
                "fecha_hasta": df_semanal.index[-1].strftime("%Y-%m-%d")
            }
            
            # Últimos trades (hasta 10)
            if resultado_bt["trades"]:
                trades_mostrar = []
                for t in resultado_bt["trades"][-10:]:
                    fecha_entrada = t['fecha_entrada'].strftime("%Y-%m-%d") if hasattr(t['fecha_entrada'], 'strftime') else str(t['fecha_entrada'])
                    fecha_salida = t['fecha_salida'].strftime("%Y-%m-%d") if hasattr(t['fecha_salida'], 'strftime') else str(t['fecha_salida'])
                    
                    trades_mostrar.append({
                        "fecha_entrada": fecha_entrada,
                        "fecha_salida": fecha_salida,
                        "R": t["R"],
                        "semanas": t["semanas"],
                        "motivo": t["motivo"]
                    })
                
                resultado["trades"] = trades_mostrar
            
            # Evaluación
            exp = resultado["metricas"]["expectancy_R"]
            if exp >= 0.40:
                resultado["evaluacion"] = "EXCELENTE"
                resultado["color"] = "success"
            elif exp >= 0.20:
                resultado["evaluacion"] = "RENTABLE"
                resultado["color"] = "success"
            elif exp > 0:
                resultado["evaluacion"] = "MARGINAL"
                resultado["color"] = "warning"
            else:
                resultado["evaluacion"] = "NO RENTABLE"
                resultado["color"] = "danger"
            
        except Exception as e:
            error = f"Error en backtest de {ticker}: {str(e)}"
    
    return render_template("backtest_medio.html", resultado=resultado, error=error)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 BACKTEST SISTEMA COMPLETO → /medio/backtest-sistema
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@medio_bp.route("/backtest-sistema", methods=["GET", "POST"])
def backtest_sistema():
    """Backtest del sistema completo sobre todos los valores."""
    resultado = None
    
    if request.method == "POST":
        # Determinar si incluir Mercado Continuo
        usar_continuo = request.form.get("usar_continuo") == "1"
        
        try:
            print(f"\n🚀 Iniciando backtest sistema medio plazo...")
            print(f"   IBEX 35: ✅")
            print(f"   Continuo: {'✅' if usar_continuo else '❌'}")
            
            # Ejecutar backtest multi-ticker
            resultado = ejecutar_backtest_sistema_completo(
                universo=None,  # Usa IBEX_35 por defecto
                verbose=True,
                usar_continuo=usar_continuo
            )
            
            print(f"\n✅ Backtest completado exitosamente")
            
        except Exception as e:
            print(f"\n❌ Error en backtest sistema: {e}")
            import traceback
            traceback.print_exc()
            resultado = None
    
    return render_template("backtest_sistema_medio.html", resultado=resultado)



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 ESCÁNER UNIFICADO → /medio/escaner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@medio_bp.route("/escaner", methods=["GET", "POST"])
def escaner():
    """Escáner unificado: IBEX 35 o Mercado Continuo."""
    if request.method == "GET":
        return render_template("escaner_medio.html", resultado=None)
    
    # Determinar universo
    universo_seleccionado = request.form.get("universo", "ibex")
    
    if universo_seleccionado == "continuo":
        lista_tickers = MERCADO_CONTINUO
        nombre_universo = "Mercado Continuo"
    else:
        lista_tickers = IBEX_35
        nombre_universo = "IBEX 35"
    
    # POST - Ejecutar escaneo
    compras = []
    vigilancia = []
    descartados = []
    errores = []
    
    print(f"\n🔍 Escaneando {nombre_universo} ({len(lista_tickers)} valores)...")
    
    for ticker in lista_tickers:
        try:
            df_semanal, validacion = obtener_datos_semanales(ticker, validar=False)
            
            if df_semanal is None:
                errores.append(ticker)
                continue
            
            precios = df_semanal['Close'].tolist()
            volumenes = df_semanal['Volume'].tolist()
            
            resultado = evaluar_con_scoring(precios, volumenes, df=df_semanal)
            
            info = {
                "ticker": ticker,
                "nombre": ticker.replace(".MC", ""),
                "empresa": TICKER_EMPRESA.get(ticker, ticker.replace(".MC", "")),
                "precio": round(precios[-1], 2),
                "score": f"{resultado['score']}/{resultado['score_max']}",
                "setup_score": resultado['score']
            }
            
            if resultado["decision"] == "COMPRA":
                info["entrada"] = resultado.get("entrada", 0)
                info["stop"] = resultado.get("stop", 0)
                info["riesgo_pct"] = resultado.get("riesgo_pct", 0)
                compras.append(info)
            elif resultado["score"] >= 6:
                motivo = resultado.get("motivos", [""])[0] if resultado.get("motivos") else "En vigilancia"
                info["motivo"] = motivo
                vigilancia.append(info)
            else:
                descartados.append(ticker)
        
        except Exception as e:
            print(f"   ❌ Error en {ticker}: {e}")
            errores.append(ticker)
    
    resultado_escaner = {
        "universo": universo_seleccionado,
        "total_analizados": len(lista_tickers),
        "total_compras": len(compras),
        "total_vigilancia": len(vigilancia),
        "total_descartados": len(descartados),
        "total_errores": len(errores),
        "compras": sorted(compras, key=lambda x: x['setup_score'], reverse=True),
        "vigilancia": sorted(vigilancia, key=lambda x: x['setup_score'], reverse=True),
        "errores": errores
    }
    
    return render_template("escaner_medio.html", resultado=resultado_escaner)# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️ CONFIGURACIÓN → /medio/config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@medio_bp.route("/config")
def configuracion():
    """Muestra la configuración actual del sistema."""
    config = {
        "timeframe": "Semanal (1 semana por barra)",
        "estrategia": "Pullback en tendencia alcista",
        "min_semanas": MIN_SEMANAS_HISTORICO,
        "pullback_min": f"{PULLBACK_MIN_PCT}%",
        "pullback_max": f"{PULLBACK_MAX_PCT}%",
        "riesgo_min": f"{RIESGO_MIN_PCT}%",
        "riesgo_max": f"{RIESGO_MAX_PCT}%",
        "r_proteger": f"+{R_PARA_PROTEGER}R",
        "r_trailing": f"+{R_PARA_TRAILING}R",
        "volatilidad_min": f"{MIN_VOLATILIDAD_PCT}%",
        "capital_inicial": f"{CAPITAL_INICIAL:,}€",
        "riesgo_trade": f"{RIESGO_POR_TRADE_PCT}%"
    }
    
    return render_template("config_medio.html", config=config)