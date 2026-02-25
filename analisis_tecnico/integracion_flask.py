# ==========================================================
# INTEGRACIÓN ANÁLISIS TÉCNICO EN FLASK
# Añadir esta ruta a app.py
# ==========================================================

from flask import render_template, request, jsonify
import yfinance as yf
import pandas as pd

# Imports del módulo análisis técnico
from analisis_tecnico.soportes_resistencias import (
    detectar_soportes_resistencias,
    obtener_sr_mas_cercanos
)
from analisis_tecnico.patrones_velas import (
    detectar_patrones_velas,
    analizar_confluencia_velas_sr
)
from analisis_tecnico.grafico_avanzado import crear_grafico_analisis_tecnico


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RUTA PRINCIPAL - ANÁLISIS TÉCNICO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 1: Descargar datos (6 meses, diario)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        print(f"\n🔍 Analizando {ticker}...")
        
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        
        if df is None or len(df) < 50:
            return render_template('selector_analisis.html',
                                 error=f"No se pudieron obtener datos de {ticker}")
        
        # Aplanar MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 2: Detectar Soportes/Resistencias
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        resultado_sr = detectar_soportes_resistencias(
            df=df,
            periodo=20,
            tolerancia_pct=2.0,
            min_toques=2
        )
        
        soportes = resultado_sr['soportes']
        resistencias = resultado_sr['resistencias']
        precio_actual = resultado_sr['precio_actual']
        analisis_posicion = resultado_sr['analisis']
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 3: Detectar Patrón de Velas
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        patron = detectar_patrones_velas(df, ultimas_n=2)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 4: Analizar Confluencia (Velas + S/R)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        sr_cercanos = obtener_sr_mas_cercanos(precio_actual, soportes, resistencias)
        distancia_soporte_pct = sr_cercanos['distancia_soporte_pct']
        
        confluencia = analizar_confluencia_velas_sr(patron, distancia_soporte_pct)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 5: Generar Gráfico Interactivo
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        grafico_html = crear_grafico_analisis_tecnico(
            df=df.tail(90),  # Últimos 90 días para mejor visualización
            soportes=soportes,
            resistencias=resistencias,
            patron=patron,
            precio_actual=precio_actual
        )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PASO 6: Renderizar Template
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        return render_template('analisis_tecnico.html',
                             ticker=ticker,
                             precio_actual=f"{precio_actual:.2f}",
                             soportes=soportes,
                             resistencias=resistencias,
                             analisis_posicion=analisis_posicion,
                             patron=patron,
                             confluencia=confluencia if 'mensaje' in confluencia else None,
                             grafico_html=grafico_html)
    
    except Exception as e:
        print(f"❌ Error en análisis técnico: {e}")
        import traceback
        traceback.print_exc()
        
        return render_template('selector_analisis.html',
                             error=f"Error al analizar {ticker}: {str(e)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEMPLATE SELECTOR (OPCIONAL - Página de entrada)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
Crear: MiWeb/templates/selector_analisis.html

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Análisis Técnico</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 500px;
            width: 100%;
        }
        h1 {
            color: #667eea;
            margin-bottom: 20px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 16px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            background: #764ba2;
        }
        .error {
            background: #fee;
            border-left: 4px solid #c33;
            padding: 12px;
            margin-bottom: 20px;
            color: #c33;
            border-radius: 4px;
        }
        .back {
            display: block;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Análisis Técnico</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post">
            <div class="form-group">
                <label>Ticker (Ejemplo: TEF, SAN, BBVA)</label>
                <input type="text" name="ticker" placeholder="TEF" required autofocus>
            </div>
            <button type="submit">Analizar</button>
        </form>
        <a href="/swing/" class="back">← Volver al Sistema Swing</a>
    </div>
</body>
</html>
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRACIÓN EN INDEX SWING (BOTÓN ACCESO)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
Añadir botón en index_swing.html (en la sección de botones):

<a href="/analisis-tecnico" class="btn-analisis-tecnico" style="
    padding: 10px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-size: 14px;
    display: inline-block;
    margin-top: 10px;">
    📊 Análisis Técnico
</a>
"""
