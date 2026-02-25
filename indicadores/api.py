# api.py
from flask import request, jsonify
import yfinance as yf
import pandas as pd
from .nucleo.calculos import aplicar_indicadores
from .utilidades.serializador import preparar_para_json, formatear_niveles_sr, formatear_patrones
from .routes import indicadores_bp

@indicadores_bp.route("/api")
def api_indicadores():
    ticker = request.args.get("ticker")
    timeframe = request.args.get("tf", "1d")
    indicadores = request.args.get("ind", "")

    if not ticker:
        return jsonify({"error": "Ticker requerido"}), 400

    lista_indicadores = indicadores.split(",") if indicadores else []

    # Descargar datos
    df = yf.download(
        ticker,
        period="1y",
        interval=timeframe,
        auto_adjust=True,
        progress=False
    )

    # Limpiar columnas si es MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return jsonify({"error": "No hay datos disponibles"}), 404

    # Aplicar indicadores (devuelve 8 valores: añadido patrones chartistas)
    # IMPORTANTE: Pasar timeframe para pivot points adaptativos
    df, soportes, resistencias, patrones, resumen_tecnico, divergencias, fibonacci, patrones_chartistas = aplicar_indicadores(df, lista_indicadores, timeframe)

    # Resetear índice y preparar datos
    df = df.reset_index()
    datos_json = preparar_para_json(df)
    
    # Formatear soportes y resistencias
    soportes_json = formatear_niveles_sr(soportes)
    resistencias_json = formatear_niveles_sr(resistencias)
    
    # Formatear patrones
    patrones_json = formatear_patrones(patrones)
    
    return jsonify({
        "data": datos_json,
        "soportes": soportes_json,
        "resistencias": resistencias_json,
        "patrones": patrones_json,
        "resumen_tecnico": resumen_tecnico,
        "divergencias": divergencias,
        "fibonacci": fibonacci,
        "patrones_chartistas": patrones_chartistas
    })
    