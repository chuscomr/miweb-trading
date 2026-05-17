# web/routes/guardar_analisis_routes.py
from flask import Blueprint, request, jsonify
import os
from datetime import datetime

guardar_analisis_bp = Blueprint("guardar_analisis", __name__, url_prefix="/guardar_analisis")

@guardar_analisis_bp.route("/", methods=["POST"])
def guardar_analisis():
    """Guarda el análisis IA en la carpeta pantallazos"""
    try:
        data = request.get_json()
        ticker = data.get("ticker", "UNKNOWN")
        analisis = data.get("analisis", "")
        recomendaciones = data.get("recomendaciones", "")
        
        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        
        # Crear contenido
        contenido = f"""
═══════════════════════════════════════════════════════════════
 ANÁLISIS TÉCNICO CON IA - Claude Vision
═══════════════════════════════════════════════════════════════

Ticker: {ticker}
Fecha: {fecha}
Hora: {hora}

{analisis}

{f'''───────────────────────────────────────────────────────────────
💡 RECOMENDACIONES
───────────────────────────────────────────────────────────────

{recomendaciones}''' if recomendaciones else ''}

═══════════════════════════════════════════════════════════════
 Generado con MiWeb v85.4 - Análisis IA
═══════════════════════════════════════════════════════════════
""".strip()
        
        # Guardar en carpeta pantallazos
        carpeta = "pantallazos"
        os.makedirs(carpeta, exist_ok=True)
        
        nombre_archivo = f"Analisis_IA_{ticker}_{fecha}_{hora.replace(':', '-')}.txt"
        ruta_completa = os.path.join(carpeta, nombre_archivo)
        
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        return jsonify({
            "success": True,
            "mensaje": f"Análisis guardado en {nombre_archivo}",
            "ruta": ruta_completa
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
