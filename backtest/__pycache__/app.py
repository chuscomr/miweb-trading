import yfinance as yf
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_caching import Cache
from MiWeb.controlador import ejecutar_contexto, procesar_post, blindar_contexto
import base64
from datetime import datetime
from MiWeb import cartera_db
from MiWeb import cartera_logica
import os
import sys
import pandas as pd

from MiWeb.analisis_tecnico.soportes_resistencias import (
    detectar_soportes_resistencias,
    obtener_sr_mas_cercanos
)
from MiWeb.analisis_tecnico.patrones_velas import (
    detectar_patrones_velas,
    analizar_confluencia_velas_sr
)
from MiWeb.analisis_tecnico.grafico_avanzado import crear_grafico_analisis_tecnico
from MiWeb.analisis_tecnico.confirmaciones_pullback import calcular_confirmaciones_pullback
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
print(">>> APP.PY CARGANDO... <<<")

# ════════════════════════════════════════════════════════════════
# 1️⃣ CREAR LA APLICACIÓN FLASK PRIMERO
# ════════════════════════════════════════════════════════════════
application = Flask(__name__)
application.secret_key = "chusco"

# ════════════════════════════════════════════════════════════════
# 2️⃣ CONFIGURAR CACHE
# ════════════════════════════════════════════════════════════════
cache = Cache(application, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 600
})

# ════════════════════════════════════════════════════════════════
# 3️⃣ REGISTRAR BLUEPRINT DEL BACKTEST
# ════════════════════════════════════════════════════════════════
from MiWeb.backtest.backtest_api import backtest_bp
application.register_blueprint(backtest_bp)
from MiWeb.medio.app_medio_blueprint import medio_bp
application.register_blueprint(medio_bp)
from MiWeb.posicional.posicional_bp import posicional_bp
application.register_blueprint(posicional_bp) 

print(">>> APP.PY CARGADO CON RUTAS POPUP Y BACKTEST <<<")

# ════════════════════════════════════════════════════════════════
# RUTAS PRINCIPALES
# ════════════════════════════════════════════════════════════════

@application.route("/popup/ibex")
def popup_ibex():
    contexto = ejecutar_contexto("escaner_ibex", None, cache)
    return render_template("ibex.html", **contexto)


@application.route("/popup/continuo")
def popup_continuo():
    contexto = ejecutar_contexto("escaner_continuo", None, cache)
    return render_template("continuo.html", **contexto)


@application.route("/", methods=["GET"])
def inicio():
    """Hub principal - selector de sistemas"""
    return render_template("hub.html")


# ════════════════════════════════════════════════════════════════
# RUTA SWING (Sistema completo)
# ════════════════════════════════════════════════════════════════

@application.route("/swing/", methods=["GET", "POST"])
def swing_sistema():
    """Sistema Swing completo"""
    if request.method == "POST":
        procesar_post(request, session)
        return redirect(url_for("swing_sistema"))
    
    modo = session.get("modo")
    datos = session.get("datos_analisis")
    contexto = ejecutar_contexto(modo, datos, cache)
    
    session.pop("modo", None)
    session.pop("datos_analisis", None)
    
    return render_template("index_swing.html", **contexto)
# ════════════════════════════════════════════════════════════════
# RESTO DE RUTAS
# ════════════════════════════════════════════════════════════════

from MiWeb.controlador import guardar_pantallazo_controlador


@application.route("/guardar_pantallazo", methods=["POST"])
def guardar_pantallazo():
    ok, resultado = guardar_pantallazo_controlador(request.get_json())
    if not ok:
        return resultado, 400
    return jsonify({"ok": True, "archivo": resultado})


# ════════════════════════════════════════════════════════════════
# RUTAS DE CARTERA
# ════════════════════════════════════════════════════════════════

@application.route("/cartera")
def ver_cartera():
    """
    Muestra el panel de cartera con todas las posiciones abiertas
    """
    try:
        # Obtener posiciones abiertas
        posiciones = cartera_db.obtener_posiciones_abiertas()
        
        # Calcular métricas para cada posición
        posiciones_con_metricas = []
        for pos in posiciones:
            metricas = cartera_logica.calcular_metricas_posicion(pos)
            if metricas:
                posiciones_con_metricas.append(metricas)
        
        # Calcular resumen global
        resumen = cartera_logica.calcular_resumen_cartera(posiciones_con_metricas)
        
        return render_template("cartera.html", 
                             posiciones=posiciones_con_metricas,
                             resumen=resumen)
    
    except Exception as e:
        print(f"❌ Error en ver_cartera: {e}")
        return render_template("cartera.html", 
                             posiciones=[],
                             resumen=None,
                             mensaje_error=f"Error al cargar cartera: {str(e)}")


@application.route("/cartera/nueva", methods=["GET"])
def nueva_posicion_form():
    """
    Muestra el formulario para añadir una nueva posición
    """
    return render_template("cartera_nueva.html")


@application.route("/cartera/nueva", methods=["POST"])
def nueva_posicion_guardar():
    """
    Procesa y guarda una nueva posición
    """
    try:
        # Obtener datos del formulario
        ticker = request.form.get("ticker", "").strip().upper()
        nombre = request.form.get("nombre", "").strip()
        fecha_entrada = request.form.get("fecha_entrada")
        precio_entrada = float(request.form.get("precio_entrada", 0))
        stop_loss = float(request.form.get("stop_loss", 0))
        objetivo = float(request.form.get("objetivo", 0))
        acciones = int(request.form.get("acciones", 0))
        setup_score = request.form.get("setup_score")
        contexto_ibex = request.form.get("contexto_ibex")
        notas = request.form.get("notas", "").strip()
        
        # Convertir setup_score a int si existe
        if setup_score:
            setup_score = int(setup_score)
        else:
            setup_score = None
        
        # Validar datos
        errores = cartera_logica.validar_nueva_posicion(
            ticker, precio_entrada, stop_loss, objetivo, acciones
        )
        
        if errores:
            # Devolver formulario con errores
            return render_template("cartera_nueva.html", 
                                 errores=errores,
                                 datos=request.form)
        
        # Guardar en base de datos
        posicion_id = cartera_db.agregar_posicion(
            ticker=ticker,
            nombre=nombre or ticker,
            fecha_entrada=fecha_entrada,
            precio_entrada=precio_entrada,
            stop_loss=stop_loss,
            objetivo=objetivo,
            acciones=acciones,
            setup_score=setup_score,
            contexto_ibex=contexto_ibex,
            notas=notas
        )
        
        print(f"✅ Nueva posición creada: {ticker} (ID: {posicion_id})")
        
        # Redirigir a cartera con mensaje de éxito
        return redirect(url_for("ver_cartera"))
    
    except ValueError as e:
        return render_template("cartera_nueva.html", 
                             errores=[f"Error en los datos: {str(e)}"],
                             datos=request.form)
    except Exception as e:
        print(f"❌ Error guardando posición: {e}")
        return render_template("cartera_nueva.html", 
                             errores=[f"Error inesperado: {str(e)}"],
                             datos=request.form)


@application.route("/cartera/cerrar/<int:posicion_id>", methods=["POST"])
def cerrar_posicion(posicion_id):
    """
    Cierra una posición abierta al precio actual
    """
    try:
        # Obtener posición
        posicion = cartera_db.obtener_posicion_por_id(posicion_id)
        
        if not posicion:
            print(f"❌ Posición {posicion_id} no encontrada")
            return redirect(url_for("ver_cartera"))
        
        # Obtener precio actual
        precio_actual = cartera_logica.obtener_precio_actual(posicion['ticker'])
        
        if not precio_actual:
            print(f"❌ No se pudo obtener precio actual de {posicion['ticker']}")
            return redirect(url_for("ver_cartera"))
        
        # Cerrar posición
        fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        exito = cartera_db.cerrar_posicion(
            posicion_id=posicion_id,
            fecha_cierre=fecha_cierre,
            precio_cierre=precio_actual,
            motivo_cierre="Cierre manual"
        )
        
        if exito:
            print(f"✅ Posición {posicion_id} cerrada exitosamente")
        
        return redirect(url_for("ver_cartera"))
    
    except Exception as e:
        print(f"❌ Error cerrando posición {posicion_id}: {e}")
        return redirect(url_for("ver_cartera"))


@application.route("/cartera/editar/<int:posicion_id>", methods=["GET"])
def editar_posicion_form(posicion_id):
    """
    Muestra el formulario para editar una posición existente
    """
    try:
        posicion = cartera_db.obtener_posicion_por_id(posicion_id)
        
        if not posicion:
            return redirect(url_for("ver_cartera"))
        
        return render_template("cartera_editar.html", posicion=posicion)
    
    except Exception as e:
        print(f"❌ Error mostrando formulario de edición: {e}")
        return redirect(url_for("ver_cartera"))


@application.route("/cartera/editar/<int:posicion_id>", methods=["POST"])
def editar_posicion_guardar(posicion_id):
    """
    Procesa y guarda los cambios en una posición
    """
    try:
        # Obtener posición actual
        posicion_actual = cartera_db.obtener_posicion_por_id(posicion_id)
        
        if not posicion_actual:
            return redirect(url_for("ver_cartera"))
        
        # Obtener datos del formulario
        ticker = request.form.get("ticker", "").strip().upper()
        nombre = request.form.get("nombre", "").strip()
        fecha_entrada = request.form.get("fecha_entrada")
        precio_entrada = float(request.form.get("precio_entrada", 0))
        stop_loss = float(request.form.get("stop_loss", 0))
        objetivo = float(request.form.get("objetivo", 0))
        acciones = int(request.form.get("acciones", 0))
        setup_score = request.form.get("setup_score")
        contexto_ibex = request.form.get("contexto_ibex")
        notas = request.form.get("notas", "").strip()
        
        # Convertir setup_score a int si existe
        if setup_score:
            setup_score = int(setup_score)
        else:
            setup_score = None
        
        # Validar datos (usando validación específica para edición)
        errores = cartera_logica.validar_edicion_posicion(
            ticker, precio_entrada, stop_loss, objetivo, acciones
        )
        
        if errores:
            # Devolver formulario con errores
            posicion_actual.update(request.form)
            return render_template("cartera_editar.html", 
                                 posicion=posicion_actual,
                                 errores=errores)
        
        # Actualizar en base de datos
        exito = cartera_db.actualizar_posicion(
            posicion_id=posicion_id,
            ticker=ticker,
            nombre=nombre or ticker,
            precio_entrada=precio_entrada,
            stop_loss=stop_loss,
            objetivo=objetivo,
            acciones=acciones,
            setup_score=setup_score,
            contexto_ibex=contexto_ibex,
            notas=notas
        )
        
        if exito:
            print(f"✅ Posición {posicion_id} actualizada: {ticker}")
        
        # Redirigir a cartera
        return redirect(url_for("ver_cartera"))
    
    except ValueError as e:
        posicion = cartera_db.obtener_posicion_por_id(posicion_id)
        return render_template("cartera_editar.html", 
                             posicion=posicion,
                             errores=[f"Error en los datos: {str(e)}"])
    except Exception as e:
        print(f"❌ Error actualizando posición: {e}")
        posicion = cartera_db.obtener_posicion_por_id(posicion_id)
        return render_template("cartera_editar.html", 
                             posicion=posicion,
                             errores=[f"Error inesperado: {str(e)}"])


@application.route("/cartera/eliminar/<int:posicion_id>", methods=["POST"])
def eliminar_posicion(posicion_id):
    """
    Elimina permanentemente una posición
    """
    try:
        exito = cartera_db.eliminar_posicion(posicion_id)
        
        if exito:
            print(f"✅ Posición {posicion_id} eliminada")
        
        return redirect(url_for("ver_cartera"))
    
    except Exception as e:
        print(f"❌ Error eliminando posición {posicion_id}: {e}")
        return redirect(url_for("ver_cartera"))

# ==========================================================
# ANÁLISIS TÉCNICO COMPLEMENTARIO
# ==========================================================

@application.route("/analisis-tecnico", methods=["GET", "POST"])
def analisis_tecnico():
    """
    Dashboard de análisis técnico complementario.
    Muestra S/R, patrones velas, gráfico interactivo.
    """
    
    if request.method == "GET":
        # Mostrar formulario selector de ticker
        return render_template('selector_analisis.html')
    
    # POST - Analizar ticker
    ticker = request.form.get('ticker', '').strip().upper()
    
    if not ticker:
        return render_template('selector_analisis.html', 
                             error="Introduce un ticker válido")
    
    # Añadir .MC si no lo tiene
    if not ticker.endswith('.MC'):
        ticker += '.MC'
    
    try:
        # PASO 1: Descargar datos (6 meses, diario)
        print(f"\n🔍 Analizando {ticker}...")
        
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        
        if df is None or len(df) < 50:
            return render_template('selector_analisis.html',
                                 error=f"No se pudieron obtener datos de {ticker}")
        
        # Aplanar MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # PASO 2: Detectar Soportes/Resistencias
        resultado_sr = detectar_soportes_resistencias(
            df=df,
            periodo=10,           # Más sensible a máx/mín locales
            tolerancia_pct=3.0,   # Agrupa niveles dentro 3%
            min_toques=2          # 2 toques = confirmación real
        )
        
        soportes = resultado_sr['soportes']
        resistencias = resultado_sr['resistencias']
        precio_actual = resultado_sr['precio_actual']
        analisis_posicion = resultado_sr['analisis']
        
        # PASO 3: Detectar Patrón de Velas
        patron = detectar_patrones_velas(df, ultimas_n=2)
        
        # PASO 4: Obtener soporte/resistencia más cercanos
        sr_cercanos = obtener_sr_mas_cercanos(precio_actual, soportes, resistencias)
        distancia_soporte_pct = sr_cercanos['distancia_soporte_pct']
        soporte_cercano = sr_cercanos.get('soporte_cercano')
        
        # Obtener fuerza del soporte más cercano
        fuerza_soporte = None
        if soporte_cercano:
            for s in soportes:
                if abs(s['nivel'] - soporte_cercano) < 0.01:
                    fuerza_soporte = s['fuerza']
                    break
        
        # PASO 5: SISTEMA PROFESIONAL DE CONFIRMACIONES (10 factores)
        confirmaciones = calcular_confirmaciones_pullback(
            df=df,
            patron=patron,
            distancia_soporte_pct=distancia_soporte_pct,
            fuerza_soporte=fuerza_soporte
        )
        
        # Mantener compatibilidad con confluencia básica (para fallback)
        confluencia_basica = analizar_confluencia_velas_sr(patron, distancia_soporte_pct)
        
        # PASO 6: Generar Gráfico Interactivo
        grafico_html = crear_grafico_analisis_tecnico(
            df=df.tail(90),  # Últimos 90 días
            soportes=soportes,
            resistencias=resistencias,
            patron=patron,
            precio_actual=precio_actual
        )
        
        # PASO 7: Renderizar Template con sistema profesional
        return render_template('analisis_tecnico.html',
                             ticker=ticker,
                             precio_actual=f"{precio_actual:.2f}",
                             soportes=soportes,
                             resistencias=resistencias,
                             analisis_posicion=analisis_posicion,
                             patron=patron,
                             confirmaciones=confirmaciones,  # Sistema profesional
                             confluencia=confluencia_basica if 'mensaje' in confluencia_basica else None,  # Fallback
                             grafico_html=grafico_html)
    
    except Exception as e:
        print(f"❌ Error en análisis técnico: {e}")
        import traceback
        traceback.print_exc()
        
        return render_template('selector_analisis.html',
                             error=f"Error al analizar {ticker}: {str(e)}")

@application.route("/swing/breakout", methods=["POST"])
def swing_breakout():
    """Estrategia BREAKOUT - Independiente del sistema principal"""
    ticker = request.form.get("ticker", "").upper()
    
    if not ticker:
        return redirect(url_for("swing_sistema"))
    
    # Obtener parámetros (igual que en el análisis normal)
    capital_total = float(request.form.get("capital_total", 10000))
    riesgo_pct = float(request.form.get("riesgo_pct", 1))
    
    try:
        from MiWeb.swing_trading.logica_breakout import detectar_breakout_swing
        señal = detectar_breakout_swing(ticker)
        
        if señal:
            # Calcular tamaño posición
            riesgo_por_accion = señal['entrada'] - señal['stop']
            riesgo_permitido = capital_total * riesgo_pct / 100
            acciones = int(riesgo_permitido / riesgo_por_accion)
            
            contexto = {
                'ticker': ticker,
                'señal': 'COMPRA',
                'entrada': señal['entrada'],
                'stop': señal['stop'],
                'objetivo': señal['objetivo'],
                'rr': señal['rr'],
                'setup_score': señal['setup_score'],
                'tipo_estrategia': 'BREAKOUT',
                'acciones': acciones,
                'capital_total': capital_total,
                'riesgo_pct': riesgo_pct,
                'motivos': [{'ok': True, 'texto': f'🚀 Señal BREAKOUT - Resistencia rota: {señal["resistencia_rota"]}€'}]
            }
        else:
            contexto = {
                'ticker': ticker,
                'señal': 'NO OPERAR',
                'tipo_estrategia': 'BREAKOUT',
                'motivos': [{'ok': False, 'texto': '❌ No se detectó señal BREAKOUT'}]
            }
        
        # Cargar el resto del contexto del sistema principal
        from logica import ejecutar_app
        contexto_base = ejecutar_app(None, None, cache)
        contexto.update(contexto_base)
        
        return render_template("index_swing.html", **contexto)
        
    except Exception as e:
        print(f"❌ Error BREAKOUT: {e}")
        return redirect(url_for("swing_sistema"))


@application.route("/swing/pullback", methods=["POST"])
def swing_pullback():
    """Estrategia PULLBACK - Independiente del sistema principal"""
    ticker = request.form.get("ticker", "").upper()
    
    if not ticker:
        return redirect(url_for("swing_sistema"))
    
    capital_total = float(request.form.get("capital_total", 10000))
    riesgo_pct = float(request.form.get("riesgo_pct", 1))
    
    try:
        from MiWeb.swing_trading.logica_pullback import detectar_pullback_swing
        señal = detectar_pullback_swing(ticker)
        
        if señal:
            riesgo_por_accion = señal['entrada'] - señal['stop']
            riesgo_permitido = capital_total * riesgo_pct / 100
            acciones = int(riesgo_permitido / riesgo_por_accion)
            
            contexto = {
                'ticker': ticker,
                'señal': 'COMPRA',
                'entrada': señal['entrada'],
                'stop': señal['stop'],
                'objetivo': señal['objetivo'],
                'rr': señal['rr'],
                'setup_score': señal['setup_score'],
                'tipo_estrategia': 'PULLBACK',
                'acciones': acciones,
                'capital_total': capital_total,
                'riesgo_pct': riesgo_pct,
                'motivos': [{'ok': True, 'texto': f'📊 Señal PULLBACK - Soporte: {señal["soporte_cercano"]}€ ({señal["distancia_soporte_pct"]}% abajo)'}]
            }
        else:
            contexto = {
                'ticker': ticker,
                'señal': 'NO OPERAR',
                'tipo_estrategia': 'PULLBACK',
                'motivos': [{'ok': False, 'texto': '❌ No se detectó señal PULLBACK'}]
            }
        
        contexto_base = ejecutar_app(None, None, cache)
        contexto.update(contexto_base)
        
        return render_template("index_swing.html", **contexto)
        
    except Exception as e:
        print(f"❌ Error PULLBACK: {e}")
        return redirect(url_for("swing_sistema"))
# ════════════════════════════════════════════════════════════════
# EJECUTAR SERVIDOR
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 SERVIDOR FLASK INICIADO")
    print("="*70)
    print("\n📍 Rutas disponibles:")
    print("   • http://localhost:5000/                  ← HUB PRINCIPAL")
    print("   • http://localhost:5000/swing/            ← SWING")
    print("   • http://localhost:5000/medio/            ← MEDIO PLAZO")
    print("   • http://localhost:5000/posicional/       ← POSICIONAL")
    print("   • http://localhost:5000/cartera           ← CARTERA")
    print("   • http://localhost:5000/popup/ibex")
    print("   • http://localhost:5000/popup/continuo")
    print("   • http://localhost:5000/api/backtest/ejecutar")
    print("\n" + "="*70 + "\n")
    
    application.run(debug=True)