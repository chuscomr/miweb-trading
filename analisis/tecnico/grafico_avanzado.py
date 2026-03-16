# analisis/tecnico/grafico_avanzado.py
# ══════════════════════════════════════════════════════════════
# GRÁFICO AVANZADO — Velas + S/R + Patrones
#
# Migrado desde grafico_avanzado.py del proyecto original.
# Cambios:
#   - Eliminado __main__ con yfinance directo
#   - Imports limpios
#   - Sin cambios en la lógica de visualización
# ══════════════════════════════════════════════════════════════

import pandas as pd
import logging

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False
    logger.warning("⚠️ plotly no disponible — gráficos desactivados")


def crear_grafico_analisis_tecnico(
    df:            pd.DataFrame,
    soportes:      list,
    resistencias:  list,
    patron:        dict,
    precio_actual: float,
) -> str:
    """
    Gráfico interactivo con velas japonesas, S/R, patrón detectado y volumen.

    Args:
        df:            DataFrame OHLCV (recomendado: últimos 90 días)
        soportes:      lista de dict {nivel, toques, fuerza}
        resistencias:  lista de dict {nivel, toques, fuerza}
        patron:        dict de detectar_patrones_velas()
        precio_actual: precio de cierre actual

    Returns:
        HTML del gráfico (str) o mensaje de error si plotly no está disponible.
    """
    if not PLOTLY_OK:
        return "<p>Plotly no disponible en este entorno.</p>"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=("Precio", "Volumen"),
    )

    # ── Velas japonesas ───────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        name="Precio",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ), row=1, col=1)

    # ── Soportes (verde) ──────────────────────────────
    for s in soportes:
        ancho   = 3 if s["fuerza"] == "FUERTE" else 2 if s["fuerza"] == "MEDIO" else 1
        opacidad = 0.8 if s["fuerza"] == "FUERTE" else 0.6 if s["fuerza"] == "MEDIO" else 0.4
        fig.add_hline(
            y=s["nivel"], line_dash="dash",
            line_color="#26a69a", line_width=ancho, opacity=opacidad,
            annotation_text=f"S: {s['nivel']}€ ({s['toques']})",
            annotation_position="left",
            row=1, col=1,
        )

    # ── Resistencias (rojo) ───────────────────────────
    for r in resistencias:
        ancho   = 3 if r["fuerza"] == "FUERTE" else 2 if r["fuerza"] == "MEDIO" else 1
        opacidad = 0.8 if r["fuerza"] == "FUERTE" else 0.6 if r["fuerza"] == "MEDIO" else 0.4
        fig.add_hline(
            y=r["nivel"], line_dash="dash",
            line_color="#ef5350", line_width=ancho, opacity=opacidad,
            annotation_text=f"R: {r['nivel']}€ ({r['toques']})",
            annotation_position="left",
            row=1, col=1,
        )

    # ── Anotación patrón ──────────────────────────────
    if patron.get("patron") not in ("NINGUNO", "INSUFICIENTE", None):
        color_patron = "#26a69a" if patron["señal"] == "ALCISTA" else "#ef5350"
        fig.add_annotation(
            x=df.index[-1],
            y=float(df["High"].iloc[-1]) * 1.02,
            text=f"<b>{patron['patron']}</b><br>{patron['confianza']}%",
            showarrow=True, arrowhead=2, arrowsize=1,
            arrowwidth=2, arrowcolor=color_patron,
            ax=0, ay=-40,
            bgcolor=color_patron,
            font=dict(color="white", size=11),
            bordercolor=color_patron, borderwidth=2, borderpad=4,
            row=1, col=1,
        )

    # ── Volumen ───────────────────────────────────────
    colores = [
        "#26a69a" if float(c) >= float(o) else "#ef5350"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volumen", marker_color=colores, showlegend=False,
    ), row=2, col=1)

    # ── Layout ────────────────────────────────────────
    fig.update_layout(
        title={
            "text": f"Análisis Técnico — Precio actual: {precio_actual:.2f}€",
            "x": 0.5, "xanchor": "center",
            "font": {"size": 18, "color": "#333"},
        },
        xaxis_title="Fecha",
        yaxis_title="Precio (€)",
        height=700,
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=12),
        xaxis=dict(gridcolor="#e0e0e0", showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor="#e0e0e0", showgrid=True),
        xaxis2=dict(gridcolor="#e0e0e0", showgrid=True),
        yaxis2=dict(gridcolor="#e0e0e0", showgrid=True, title="Volumen"),
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def crear_grafico_simple_sr(
    df:           pd.DataFrame,
    soportes:     list,
    resistencias: list,
) -> str:
    """
    Versión simplificada: línea de precio + S/R. Más rápida de cargar.
    """
    if not PLOTLY_OK:
        return "<p>Plotly no disponible en este entorno.</p>"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines", name="Precio",
        line=dict(color="#1e3c72", width=2),
    ))

    for s in soportes:
        fig.add_hline(
            y=s["nivel"], line_dash="dash",
            line_color="#26a69a", line_width=2,
            annotation_text=f"S: {s['nivel']}€",
        )

    for r in resistencias:
        fig.add_hline(
            y=r["nivel"], line_dash="dash",
            line_color="#ef5350", line_width=2,
            annotation_text=f"R: {r['nivel']}€",
        )

    fig.update_layout(
        title="Soportes y Resistencias",
        xaxis_title="Fecha",
        yaxis_title="Precio (€)",
        height=500,
        plot_bgcolor="white",
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")
