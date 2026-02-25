# ==========================================================
# MÓDULO GRÁFICO AVANZADO
# Visualización con velas japonesas, S/R y patrones
# ==========================================================

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def crear_grafico_analisis_tecnico(df, soportes, resistencias, patron, precio_actual):
    """
    Crea gráfico interactivo con:
    - Velas japonesas
    - Líneas de soportes/resistencias
    - Anotación de patrón detectado
    - Volumen
    
    Args:
        df: DataFrame con OHLCV
        soportes: lista de dict con niveles de soporte
        resistencias: lista de dict con niveles de resistencia
        patron: dict con patrón de velas detectado
        precio_actual: precio de cierre actual
    
    Returns:
        HTML del gráfico plotly
    """
    
    # Crear figura con 2 subplots (precio + volumen)
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('Precio', 'Volumen')
    )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VELAS JAPONESAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Precio',
        increasing_line_color='#26a69a',  # Verde
        decreasing_line_color='#ef5350'   # Rojo
    )
    
    fig.add_trace(candlestick, row=1, col=1)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LÍNEAS DE SOPORTE (VERDES)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    for soporte in soportes:
        nivel = soporte['nivel']
        toques = soporte['toques']
        fuerza = soporte['fuerza']
        
        # Grosor según fuerza
        ancho = 3 if fuerza == "FUERTE" else 2 if fuerza == "MEDIO" else 1
        opacidad = 0.8 if fuerza == "FUERTE" else 0.6 if fuerza == "MEDIO" else 0.4
        
        fig.add_hline(
            y=nivel,
            line_dash="dash",
            line_color="#26a69a",  # Verde
            line_width=ancho,
            opacity=opacidad,
            annotation_text=f"S: {nivel}€ ({toques})",
            annotation_position="left",
            row=1, col=1
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LÍNEAS DE RESISTENCIA (ROJAS)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    for resistencia in resistencias:
        nivel = resistencia['nivel']
        toques = resistencia['toques']
        fuerza = resistencia['fuerza']
        
        ancho = 3 if fuerza == "FUERTE" else 2 if fuerza == "MEDIO" else 1
        opacidad = 0.8 if fuerza == "FUERTE" else 0.6 if fuerza == "MEDIO" else 0.4
        
        fig.add_hline(
            y=nivel,
            line_dash="dash",
            line_color="#ef5350",  # Rojo
            line_width=ancho,
            opacity=opacidad,
            annotation_text=f"R: {nivel}€ ({toques})",
            annotation_position="left",
            row=1, col=1
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANOTACIÓN PATRÓN DE VELAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    if patron['patron'] != "NINGUNO" and patron['patron'] != "INSUFICIENTE":
        # Colocar anotación en última vela
        ultima_fecha = df.index[-1]
        
        # Color según señal
        color_texto = "#26a69a" if patron['señal'] == "ALCISTA" else "#ef5350"
        
        fig.add_annotation(
            x=ultima_fecha,
            y=df['High'].iloc[-1] * 1.02,  # Arriba de la vela
            text=f"<b>{patron['patron']}</b><br>{patron['confianza']}%",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=color_texto,
            ax=0,
            ay=-40,
            bgcolor=color_texto,
            font=dict(color="white", size=11),
            bordercolor=color_texto,
            borderwidth=2,
            borderpad=4,
            row=1, col=1
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VOLUMEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    colores_volumen = ['#26a69a' if close >= open_ else '#ef5350' 
                       for close, open_ in zip(df['Close'], df['Open'])]
    
    volumen_bar = go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volumen',
        marker_color=colores_volumen,
        showlegend=False
    )
    
    fig.add_trace(volumen_bar, row=2, col=1)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONFIGURACIÓN LAYOUT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    fig.update_layout(
        title={
            'text': f'Análisis Técnico - Precio Actual: {precio_actual:.2f}€',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#333'}
        },
        xaxis_title='Fecha',
        yaxis_title='Precio (€)',
        height=700,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", size=12),
        xaxis=dict(
            gridcolor='#e0e0e0',
            showgrid=True,
            rangeslider_visible=False
        ),
        yaxis=dict(
            gridcolor='#e0e0e0',
            showgrid=True
        ),
        xaxis2=dict(
            gridcolor='#e0e0e0',
            showgrid=True
        ),
        yaxis2=dict(
            gridcolor='#e0e0e0',
            showgrid=True,
            title='Volumen'
        )
    )
    
    # Devolver HTML del gráfico
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def crear_grafico_simple_sr(df, soportes, resistencias):
    """
    Versión simplificada solo con precio y S/R (sin velas).
    Más rápido de cargar.
    """
    
    fig = go.Figure()
    
    # Línea de precio
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        mode='lines',
        name='Precio',
        line=dict(color='#1e3c72', width=2)
    ))
    
    # Soportes
    for soporte in soportes:
        fig.add_hline(
            y=soporte['nivel'],
            line_dash="dash",
            line_color="#26a69a",
            line_width=2,
            annotation_text=f"S: {soporte['nivel']}€"
        )
    
    # Resistencias
    for resistencia in resistencias:
        fig.add_hline(
            y=resistencia['nivel'],
            line_dash="dash",
            line_color="#ef5350",
            line_width=2,
            annotation_text=f"R: {resistencia['nivel']}€"
        )
    
    fig.update_layout(
        title='Soportes y Resistencias',
        xaxis_title='Fecha',
        yaxis_title='Precio (€)',
        height=500,
        plot_bgcolor='white'
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EJEMPLO DE USO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import yfinance as yf
    from soportes_resistencias import detectar_soportes_resistencias
    from patrones_velas import detectar_patrones_velas
    
    # Descargar datos
    ticker = "TEF.MC"
    df = yf.download(ticker, period="6mo", interval="1d")
    
    # Detectar S/R
    sr = detectar_soportes_resistencias(df)
    
    # Detectar patrón
    patron = detectar_patrones_velas(df)
    
    # Crear gráfico
    html = crear_grafico_analisis_tecnico(
        df=df.tail(90),  # Últimos 90 días
        soportes=sr['soportes'],
        resistencias=sr['resistencias'],
        patron=patron,
        precio_actual=sr['precio_actual']
    )
    
    # Guardar HTML
    with open('grafico_analisis.html', 'w', encoding='utf-8') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Análisis Técnico {ticker}</title></head>
        <body>
        {html}
        </body>
        </html>
        """)
    
    print(f"✅ Gráfico guardado en grafico_analisis.html")
