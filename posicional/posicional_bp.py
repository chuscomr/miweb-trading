# ==========================================================
# BLUEPRINT - SISTEMA POSICIONAL
# Interfaz web para sistema de trading posicional
# ==========================================================

from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime
import json
import os

# Imports del sistema posicional
try:
    from .config_posicional import *
    from .datos_posicional import obtener_datos_semanales, filtrar_universo_posicional
    from .sistema_trading_posicional import evaluar_entrada_posicional
    from .backtest_sistema_posicional import ejecutar_backtest_sistema_completo
    from .backtest_posicional import ejecutar_backtest_posicional
except ImportError:
    from config_posicional import *
    from datos_posicional import obtener_datos_semanales, filtrar_universo_posicional
    from sistema_trading_posicional import evaluar_entrada_posicional
    from backtest_sistema_posicional import ejecutar_backtest_sistema_completo
    from backtest_posicional import ejecutar_backtest_posicional

# Definir RESULTADOS_DIR si no existe
if 'RESULTADOS_DIR' not in globals():
    RESULTADOS_DIR = os.path.join(os.path.dirname(__file__), "resultados")
    os.makedirs(RESULTADOS_DIR, exist_ok=True)

# ==========================================================
# CREAR BLUEPRINT
# ==========================================================

posicional_bp = Blueprint(
    'posicional',
    __name__,
    url_prefix='/posicional'
)

# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

@posicional_bp.route('/')
def index():
    """Dashboard principal del sistema posicional"""
    try:
        # NO filtrar universo aquí (muy lento) - solo info estática
        contexto = {
            "sistema": "posicional",
            "titulo": "Sistema Posicional",
            "subtitulo": "Trading 6M-2Y · IBEX 35",
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "universo": {
                "total": len(IBEX_35),
                "aptos": len(IBEX_35),  # Mostrar 35 sin filtrar
                "ratio": "100%"
            },
            "parametros": {
                "volatilidad_min": MIN_VOLATILIDAD_PCT,
                "volumen_min": f"{MIN_VOLUMEN_MEDIO_DIARIO/1_000_000:.1f}M€",
                "capitalizacion_min": f"{MIN_CAPITALIZACION/1_000_000_000:.1f}B€" if MIN_CAPITALIZACION > 0 else "Sin filtro",
                "duracion": "6 meses - 2 años",
                "riesgo_por_trade": f"{RIESGO_POR_TRADE_PCT}%"
            }
        }
        
        return render_template('index_posicional.html', **contexto)
    
    except Exception as e:
        print(f"❌ Error en index posicional: {e}")
        return render_template('index_posicional.html',
                             sistema="posicional",
                             error=str(e))

# ==========================================================
# ANALIZAR VALOR INDIVIDUAL
# ==========================================================

@posicional_bp.route('/analizar')
def analizar():
    """Página de análisis individual con IBEX 35 + Mercado Continuo"""
    return render_template('analizar_posicional.html',
                         titulo="Analizar Valor Posicional",
                         valores_ibex=IBEX_35,
                         valores_continuo=MERCADO_CONTINUO,
                         sistema="posicional")

@posicional_bp.route('/api/analizar/<ticker>')
def api_analizar(ticker):
    """API: Analizar un valor específico (IBEX 35 o Mercado Continuo)"""
    try:
        # Validar ticker en ambos universos
        if ticker not in IBEX_35 and ticker not in MERCADO_CONTINUO:
            return jsonify({
                "success": False,
                "error": f"{ticker} no está en IBEX 35 ni Mercado Continuo"
            })
        
        # Obtener datos semanales
        df, validacion = obtener_datos_semanales(ticker, validar=True)
        
        if df is None:
            return jsonify({
                "success": False,
                "error": "No se pudieron obtener datos",
                "validacion": validacion
            })
        
        # Extraer datos para análisis
        precios = df['Close'].tolist()
        volumenes = df['Volume'].tolist() if 'Volume' in df.columns else None
        
        # Analizar valor
        resultado = evaluar_entrada_posicional(precios, volumenes, df=df)
        
        # Formatear respuesta según decisión
        analisis = {
            "decision": resultado["decision"],
            "motivo": ", ".join(resultado.get("motivos", [])),
            "entrada": resultado.get("entrada", 0),
            "stop": resultado.get("stop", 0),
            "riesgo_pct": resultado.get("riesgo_pct", 0)
        }
        
        # Formatear respuesta
        return jsonify({
            "success": True,
            "ticker": ticker,
            "fecha_analisis": datetime.now().isoformat(),
            "datos": {
                "semanas": len(df),
                "desde": df.index[0].strftime("%Y-%m-%d"),
                "hasta": df.index[-1].strftime("%Y-%m-%d"),
                "precio_actual": float(df['Close'].iloc[-1])
            },
            "validacion": validacion.get("stats", {}),
            "analisis": analisis
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ==========================================================
# BACKTEST INDIVIDUAL
# ==========================================================

@posicional_bp.route('/backtest-valor')
def backtest_valor():
    """Página de backtest individual"""
    return render_template('backtest_valor_posicional.html',
                         titulo="Backtest Valor Individual",
                         valores=IBEX_35,
                         sistema="posicional")

@posicional_bp.route('/api/backtest-valor/<ticker>')
def api_backtest_valor(ticker):
    """API: Ejecutar backtest de un valor específico"""
    try:
        if ticker not in IBEX_35:
            return jsonify({"success": False, "error": f"{ticker} no está en IBEX 35"})
        
        print(f"\n🔍 Ejecutando backtest de {ticker}...")
        
        df, _ = obtener_datos_semanales(ticker, periodo_años=AÑOS_BACKTEST)
        
        if df is None or df.empty:
            return jsonify({"success": False, "error": "No se pudieron obtener datos"})
        
        resultado = ejecutar_backtest_posicional(df, ticker, verbose=False)
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "resultado": {
                "total_trades": resultado.get("total_trades", 0),
                "expectancy": round(resultado.get("expectancy", 0), 2),
                "winrate": round(resultado.get("winrate", 0), 1),
                "profit_factor": round(resultado.get("profit_factor", 0), 2),
                "equity_final": round(resultado.get("equity_final", 0), 2),
                "mejor_trade": round(resultado.get("mejor_trade", 0), 2),
                "peor_trade": round(resultado.get("peor_trade", 0), 2),
                "duracion_media": round(resultado.get("duracion_media", 0), 0)
            }
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

# ==========================================================
# GESTIÓN DE CARTERA
# ==========================================================

@posicional_bp.route('/cartera')
def cartera():
    """Página de gestión de cartera posicional"""
    try:
        from .config_posicional import IBEX_35, MERCADO_CONTINUO
        
        # Cargar cartera desde archivo
        cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
        
        if os.path.exists(cartera_path):
            with open(cartera_path, 'r') as f:
                data = json.load(f)
        else:
            data = {"posiciones": []}
        
        return render_template('cartera_posicional.html',
                             titulo="Cartera Posicional",
                             sistema="posicional",
                             cartera=data,
                             valores_ibex=IBEX_35,
                             valores_continuo=MERCADO_CONTINUO)
    
    except Exception as e:
        print(f"❌ Error en cartera posicional: {e}")
        return render_template('cartera_posicional.html',
                             sistema="posicional",
                             error=str(e))

@posicional_bp.route('/api/cartera/agregar', methods=['POST'])
def api_agregar_posicion():
    """API: Agregar posición manual a cartera"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        campos_requeridos = ['ticker', 'precio_entrada', 'stop', 'acciones']
        for campo in campos_requeridos:
            if campo not in data:
                return jsonify({"success": False, "error": f"Campo {campo} requerido"})
        
        ticker = data['ticker']
        precio_entrada = float(data['precio_entrada'])
        stop = float(data['stop'])
        acciones = int(data['acciones'])
        
        # Validaciones
        if precio_entrada <= 0 or stop <= 0 or acciones <= 0:
            return jsonify({"success": False, "error": "Valores deben ser positivos"})
        
        if stop >= precio_entrada:
            return jsonify({"success": False, "error": "Stop debe ser menor que entrada"})
        
        # Calcular métricas
        riesgo_pct = ((precio_entrada - stop) / precio_entrada) * 100
        
        # Cargar cartera
        cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
        
        if os.path.exists(cartera_path):
            with open(cartera_path, 'r') as f:
                cartera = json.load(f)
        else:
            cartera = {"posiciones": []}
        
        # Verificar si ya existe
        if any(p['ticker'] == ticker for p in cartera['posiciones']):
            return jsonify({"success": False, "error": f"{ticker} ya está en cartera"})
        
        # Agregar posición
        nueva_posicion = {
            "ticker": ticker,
            "fecha_entrada": datetime.now().strftime("%Y-%m-%d"),
            "precio_entrada": precio_entrada,
            "stop": stop,
            "acciones": acciones,
            "riesgo_pct": round(riesgo_pct, 2),
            "R_actual": 0,
            "estado": "INICIAL",
            "notas": data.get('notas', '')
        }
        
        cartera['posiciones'].append(nueva_posicion)
        
        # Guardar
        with open(cartera_path, 'w') as f:
            json.dump(cartera, f, indent=2)
        
        return jsonify({
            "success": True,
            "mensaje": f"{ticker} agregado a cartera",
            "posicion": nueva_posicion
        })
        
    except Exception as e:
        print(f"❌ Error agregando posición: {e}")
        return jsonify({"success": False, "error": str(e)})

@posicional_bp.route('/api/cartera/eliminar/<ticker>', methods=['POST'])
def api_eliminar_posicion(ticker):
    """API: Eliminar posición de cartera"""
    try:
        cartera_path = os.path.join(RESULTADOS_DIR, "cartera_posicional.json")
        
        if not os.path.exists(cartera_path):
            return jsonify({"success": False, "error": "Cartera vacía"})
        
        with open(cartera_path, 'r') as f:
            cartera = json.load(f)
        
        posiciones_antes = len(cartera['posiciones'])
        cartera['posiciones'] = [p for p in cartera['posiciones'] if p['ticker'] != ticker]
        
        if len(cartera['posiciones']) == posiciones_antes:
            return jsonify({"success": False, "error": f"{ticker} no está en cartera"})
        
        # Guardar
        with open(cartera_path, 'w') as f:
            json.dump(cartera, f, indent=2)
        
        return jsonify({
            "success": True,
            "mensaje": f"{ticker} eliminado de cartera"
        })
        
    except Exception as e:
        print(f"❌ Error eliminando posición: {e}")
        return jsonify({"success": False, "error": str(e)})

# ==========================================================
# HISTORIAL DE TRADES
# ==========================================================

@posicional_bp.route('/historial')
def historial():
    """Página de historial de trades cerrados"""
    try:
        historial_path = os.path.join(RESULTADOS_DIR, "historial_posicional.json")
        
        if os.path.exists(historial_path):
            with open(historial_path, 'r') as f:
                data = json.load(f)
        else:
            data = {"trades": []}
        
        return render_template('historial_posicional.html',
                             titulo="Historial Posicional",
                             sistema="posicional",
                             historial=data)
    
    except Exception as e:
        print(f"❌ Error en historial posicional: {e}")
        return render_template('historial_posicional.html',
                             sistema="posicional",
                             error=str(e))

# ==========================================================
# BACKTEST SISTEMA
# ==========================================================

@posicional_bp.route('/backtest')
def backtest():
    """Página de resultados backtest"""
    return render_template('backtest_posicional.html',
                         titulo="Backtest Sistema Posicional",
                         sistema="posicional")

@posicional_bp.route('/api/backtest/ejecutar')
def api_ejecutar_backtest():
    """API: Ejecutar backtest completo"""
    try:
        print("\n🔄 Ejecutando backtest sistema posicional...")
        
        # Ejecutar backtest
        resultado_raw = ejecutar_backtest_sistema_completo(verbose=True)
        
        # Adaptar estructura para el frontend
        resultado = adaptar_resultado_backtest(resultado_raw)
        
        # Guardar resultado
        resultado_path = os.path.join(RESULTADOS_DIR, "ultimo_backtest_posicional.json")
        with open(resultado_path, 'w') as f:
            json.dump(resultado, f, indent=2, default=str)
        
        print(f"✅ Backtest completado: {resultado['metricas_globales']['total_trades']} trades")
        
        return jsonify({
            "success": True,
            "resultado": resultado,
            "mensaje": "Backtest ejecutado exitosamente"
        })
        
    except Exception as e:
        print(f"❌ Error ejecutando backtest: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        })

@posicional_bp.route('/api/backtest/ultimo')
def api_ultimo_backtest():
    """API: Obtener último backtest guardado"""
    try:
        resultado_path = os.path.join(RESULTADOS_DIR, "ultimo_backtest_posicional.json")
        
        if os.path.exists(resultado_path):
            with open(resultado_path, 'r') as f:
                resultado = json.load(f)
            
            return jsonify({
                "success": True,
                "resultado": resultado
            })
        else:
            return jsonify({
                "success": False,
                "error": "No hay backtest previo"
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

@posicional_bp.route('/config')
def config():
    """Página de configuración"""
    return render_template('config_posicional.html',
                         titulo="Configuración Sistema Posicional",
                         sistema="posicional",
                         parametros={
                             "volatilidad_min": MIN_VOLATILIDAD_PCT,
                             "volumen_min": MIN_VOLUMEN_MEDIO_DIARIO,
                             "capitalizacion_min": MIN_CAPITALIZACION,
                             "riesgo_trade": RIESGO_POR_TRADE_PCT,
                             "consolidacion_min": CONSOLIDACION_MIN_SEMANAS,
                             "consolidacion_max": CONSOLIDACION_MAX_SEMANAS
                         })

# ==========================================================
# ADAPTADOR DE RESULTADOS
# ==========================================================

def adaptar_resultado_backtest(resultado_raw):
    """Adapta resultado del backtest al formato esperado por el frontend"""
    
    # Extraer top performers
    resultados_detallados = resultado_raw.get("resultados_detallados", [])
    resultados_con_trades = [r for r in resultados_detallados if r.get("total_trades", 0) > 0]
    
    top_mejores = sorted(
        resultados_con_trades,
        key=lambda x: x.get("expectancy", 0),
        reverse=True
    )[:5]
    
    top_peores = sorted(
        resultados_con_trades,
        key=lambda x: x.get("expectancy", 0)
    )[:5]
    
    # Formatear para frontend
    return {
        "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "universo": {
            "total_tickers": resultado_raw.get("total_tickers", 0),
            "analizados": resultado_raw.get("tickers_analizados", 0),
            "sin_datos": 0,
            "con_error": resultado_raw.get("tickers_con_error", 0)
        },
        "metricas_globales": {
            "total_trades": resultado_raw.get("total_trades", 0),
            "expectancy_R": resultado_raw.get("expectancy_global", 0),
            "winrate": resultado_raw.get("winrate_global", 0),
            "profit_factor": resultado_raw.get("profit_factor_global", 0),
            "equity_final_R": resultado_raw.get("equity_total", 0),
            "mejor_trade": max((r.get("mejor_trade", 0) for r in resultados_con_trades), default=0),
            "peor_trade": min((r.get("peor_trade", 0) for r in resultados_con_trades), default=0),
            "max_drawdown_R": 0,
            "tickers_rentables": resultado_raw.get("tickers_rentables", 0),
            "tickers_no_rentables": resultado_raw.get("tickers_no_rentables", 0)
        },
        "top_performers": {
            "mejores": [
                {
                    "ticker": r.get("ticker", ""),
                    "empresa": r.get("ticker", "").replace(".MC", ""),
                    "total_trades": r.get("total_trades", 0),
                    "expectancy_R": r.get("expectancy", 0),
                    "winrate": r.get("winrate", 0),
                    "equity_final_R": r.get("equity_final", 0)
                }
                for r in top_mejores
            ],
            "peores": [
                {
                    "ticker": r.get("ticker", ""),
                    "empresa": r.get("ticker", "").replace(".MC", ""),
                    "total_trades": r.get("total_trades", 0),
                    "expectancy_R": r.get("expectancy", 0),
                    "winrate": r.get("winrate", 0),
                    "equity_final_R": r.get("equity_final", 0)
                }
                for r in top_peores
            ]
        }
    }
# ==========================================================
# ESCÁNERES
# ==========================================================

@posicional_bp.route('/escanear/ibex')
def escanear_ibex():
    """Escáner IBEX 35 - Señales de compra posicionales"""
    try:
        print("\n🔍 Ejecutando escáner IBEX 35...")
        
        resultados = []
        
        for ticker in IBEX_35:
            try:
                # Obtener datos semanales
                df, validacion = obtener_datos_semanales(ticker, validar=False)
                
                if df is None or len(df) < 50:
                    continue
                
                # Analizar
                precios = df['Close'].tolist()
                volumenes = df['Volume'].tolist() if 'Volume' in df.columns else None
                analisis = evaluar_entrada_posicional(precios, volumenes, df=df)
                
                # Guardar resultado
                resultados.append({
                    "ticker": ticker,
                    "nombre": ticker.replace(".MC", ""),
                    "precio": float(df['Close'].iloc[-1]),
                    "decision": analisis.get("decision", "ESPERAR"),
                    "motivo": ", ".join(analisis.get("motivos", [])),
                    "entrada": analisis.get("entrada", 0),
                    "stop": analisis.get("stop", 0),
                    "riesgo_pct": analisis.get("riesgo_pct", 0)
                })
                
            except Exception as e:
                print(f"⚠️ Error en {ticker}: {e}")
                continue
        
        # Separar por decisión
        compras = [r for r in resultados if r['decision'] == 'COMPRA']
        esperas = [r for r in resultados if r['decision'] != 'COMPRA']
        
        print(f"✅ Escáner completado: {len(compras)} señales de compra")
        
        return render_template('escanear_posicional.html',
                             titulo="Escáner IBEX 35",
                             universo="IBEX 35",
                             total=len(IBEX_35),
                             analizados=len(resultados),
                             compras=compras,
                             esperas=esperas,
                             sistema="posicional")
    
    except Exception as e:
        print(f"❌ Error en escáner IBEX: {e}")
        import traceback
        traceback.print_exc()
        return render_template('escanear_posicional.html',
                             error=str(e),
                             sistema="posicional")

@posicional_bp.route('/escanear/continuo')
def escanear_continuo():
    """Escáner Mercado Continuo - Señales de compra posicionales"""
    try:
        print("\n🔍 Ejecutando escáner Mercado Continuo...")
        
        resultados = []
        
        for ticker in MERCADO_CONTINUO:
            try:
                # Obtener datos semanales
                df, validacion = obtener_datos_semanales(ticker, validar=False)
                
                if df is None or len(df) < 50:
                    continue
                
                # Analizar
                precios = df['Close'].tolist()
                volumenes = df['Volume'].tolist() if 'Volume' in df.columns else None
                analisis = evaluar_entrada_posicional(precios, volumenes, df=df)
                
                # Guardar resultado
                resultados.append({
                    "ticker": ticker,
                    "nombre": ticker.replace(".MC", ""),
                    "precio": float(df['Close'].iloc[-1]),
                    "decision": analisis.get("decision", "ESPERAR"),
                    "motivo": ", ".join(analisis.get("motivos", [])),
                    "entrada": analisis.get("entrada", 0),
                    "stop": analisis.get("stop", 0),
                    "riesgo_pct": analisis.get("riesgo_pct", 0)
                })
                
            except Exception as e:
                print(f"⚠️ Error en {ticker}: {e}")
                continue
        
        # Separar por decisión
        compras = [r for r in resultados if r['decision'] == 'COMPRA']
        esperas = [r for r in resultados if r['decision'] != 'COMPRA']
        
        print(f"✅ Escáner completado: {len(compras)} señales de compra")
        
        return render_template('escanear_posicional.html',
                             titulo="Escáner Mercado Continuo",
                             universo="Mercado Continuo",
                             total=len(MERCADO_CONTINUO),
                             analizados=len(resultados),
                             compras=compras,
                             esperas=esperas,
                             sistema="posicional")
    
    except Exception as e:
        print(f"❌ Error en escáner Continuo: {e}")
        import traceback
        traceback.print_exc()
        return render_template('escanear_posicional.html',
                             error=str(e),
                             sistema="posicional")

print("✅ Blueprint posicional_bp cargado")
