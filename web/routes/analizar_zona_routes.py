"""
Ruta para analizar zona seleccionada del gráfico con Claude IA
"""
import os

import anthropic
from flask import Blueprint, jsonify, request


analizar_zona_bp = Blueprint('analizar_zona', __name__)

@analizar_zona_bp.route('/api/analizar_zona_ia', methods=['POST'])
def analizar_zona_ia():
    """
    Analiza una zona con Claude Vision API
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        zona = data.get('zona')
        screenshot = data.get('screenshot')  # base64 string

        # Extraer datos de la imagen base64
        if screenshot.startswith('data:image'):
            screenshot = screenshot.split(',')[1]

        # Inicializar cliente de Anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                'error': 'ANTHROPIC_API_KEY no configurada. Por favor, configura la API key en las variables de entorno.'
            }), 500

        client = anthropic.Anthropic(api_key=api_key)

        # Crear prompt mejorado para Claude
        prompt = f"""Eres un analista técnico profesional senior con 15 años de experiencia en mercados bursátiles españoles.

TICKER: {ticker}
ZONA ANALIZADA:
- Período: {zona.get('fecha_inicio')} hasta {zona.get('fecha_fin')}
- Rango de precio: {zona.get('precio_min', 'N/A')}€ - {zona.get('precio_max', 'N/A')}€

OBJETIVO: Proporciona un análisis técnico completo y accionable de esta zona del gráfico.

---

## 1. **Patrones Chartistas Detectados**

Identifica TODOS los patrones técnicos visibles con el máximo detalle:
- **Patrones de continuación**: canales, banderas, pennants, cuñas
- **Patrones de reversión**: HCH, doble/triple techo/suelo, martillos, envolventes
- Para CADA patrón detectado indica:
  * Tipo exacto y calidad (perfecto/claro/débil)
  * Coordenadas precisas (precios y fechas de formación)
  * Estado actual (en formación/completado/activado/fallido)
  * Implicaciones direccionales

---

## 2. **Análisis de Contexto**

**Tendencia Global:**
- Dirección (alcista/bajista/lateral) y fuerza (débil/moderada/fuerte)
- Estructura de máximos y mínimos
- Fase del ciclo (acumulación/markup/distribución/markdown)

**Momentum y Fuerza:**
- RSI: valor actual aproximado, zonas (sobreventa <30, neutral 30-70, sobrecompra >70)
- IMPORTANTE: detecta divergencias alcistas/bajistas entre precio y RSI
- Velocidad del movimiento (acelerando/desacelerando/constante)

**Zonas Críticas:**
- Soportes: lista ordenada de menor a mayor con precios exactos
- Resistencias: lista ordenada de menor a mayor con precios exactos
- Indica CALIDAD de cada nivel (débil/medio/fuerte) según:
  * Número de toques previos
  * Tiempo de formación
  * Volumen en esas zonas

**Volumen:**
- Comportamiento reciente (creciente/decreciente/estable)
- Picos significativos: dónde ocurrieron y qué señalan (acumulación/distribución)
- Divergencias precio/volumen (precio sube con volumen bajo = debilidad)

---

## 3. **Señales Técnicas Avanzadas**

**Medias Móviles:**
- Identificar MM20 (naranja), MM50 (violeta), MM200 (azul) si visibles
- Relación del precio con cada MM (encima/debajo/tocando)
- Cruces recientes o inminentes
- MM actuando como soporte/resistencia dinámica

**Confluencias Críticas:**
Identifica zonas donde coinciden 2+ factores técnicos:
- Ejemplo: "18.50€ = MM50 + Fibo 50% + soporte horizontal anterior → zona MUY fuerte"
- Lista TODAS las confluencias importantes con sus componentes

**Indicadores Complementarios:**
- MACD: ¿cruce alcista/bajista visible? ¿histograma creciendo/decreciendo?
- Bollinger Bands: ¿precio en banda superior/inferior? ¿compresión/expansión?
- ADX: ¿tendencia fuerte (>25) o mercado en rango (<20)?

**Divergencias:**
- RSI vs Precio: ¿precio hace nuevos máximos pero RSI no? (bajista)
- RSI vs Precio: ¿precio hace nuevos mínimos pero RSI no? (alcista)
- MACD vs Precio: ¿divergencias visibles?
- Volumen vs Precio: ¿subida sin volumen? (debilidad)

---

## 4. **Escenarios Probables**

**Escenario Bajista (Probabilidad: X%):**
- Desarrollo paso a paso esperado
- Objetivos: precio objetivo 1, precio objetivo 2, precio objetivo 3
- Activación: qué nivel debe perder para confirmar
- Invalidación: qué nivel confirmaría que este escenario falló

**Escenario Alcista (Probabilidad: Y%):**
- Desarrollo paso a paso esperado
- Objetivos: precio objetivo 1, precio objetivo 2, precio objetivo 3
- Activación: qué nivel debe superar para confirmar
- Invalidación: qué nivel confirmaría que este escenario falló

**Niveles Decisivos:**
Lista los 3-5 niveles MÁS importantes a vigilar con sus implicaciones

---

## 5. **Recomendaciones

**Setup Bajista (Preferido):**
- **Entrada**: [precio exacto] + [condición técnica para entrar]
- **Stop Loss**: [precio] (justificación: por encima de [nivel])
- **Take Profit 1**: [precio] (R:R X:1) - [razón técnica]
- **Take Profit 2**: [precio] (R:R Y:1) - [razón técnica]
- **Tamaño posición**: 2% del capital máximo
- **Confirmaciones necesarias**: [volumen/patrón/cierre/etc.]

**Setup Alcista (Contrarian):**
- **Entrada**: [precio exacto] + [condición técnica para entrar]
- **Stop Loss**: [precio] (justificación)
- **Take Profit**: [precio] (R:R X:1) - [razón técnica]
- **Condición CRÍTICA**: Solo entrar con [señal específica de reversión]
- **Confirmaciones necesarias**: [listar]

**Gestión de Riesgo:**
- Tamaño de posición máximo recomendado (% capital)
- Tipo de stop (fijo/trailing/por tiempo)
- Gestión multi-nivel (escalar entrada/salida)
- Qué hacer si el mercado se mueve contra ti

---

**INSTRUCCIONES CRÍTICAS:**
1. SIEMPRE indica valores NUMÉRICOS específicos (precios, porcentajes, ratios)
2. NO uses lenguaje vago ("podría", "tal vez") - sé decisivo y específico
3. Justifica CADA nivel técnico con razones concretas
4. Las probabilidades deben sumar 100% entre escenarios
5. Calcula R/R real de cada setup
6. Señala claramente cuál setup prefieres y POR QUÉ
7. Si detectas una trampa (bull trap, bear trap), AVISAR explícitamente

**FORMATO DE SALIDA:**
- Usa formato Markdown con ## para secciones principales
- Usa negrita (**) para niveles de precio importantes
- Usa listas con guiones para claridad
- Separa visualmente cada sección
- Escribe de forma profesional pero accesible"""

        # Llamar a Claude Vision API
        print(f"🤖 Llamando a Claude Vision API para analizar {ticker}...")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,  # Aumentado para análisis más detallado
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # Extraer respuesta
        analisis_completo = message.content[0].text

        print(f"✅ Análisis completado ({len(analisis_completo)} caracteres)")

        # Separar análisis y recomendaciones si es posible
        partes = analisis_completo.split('**Recomendaciones', 1)
        if len(partes) == 2:
            analisis = partes[0].strip()
            recomendaciones = '**Recomendaciones' + partes[1].strip()
        else:
            analisis = analisis_completo
            recomendaciones = None

        return jsonify({
            'analisis': analisis,
            'recomendaciones': recomendaciones,
            'ticker': ticker,
            'zona': zona
        })

    except Exception as e:
        print(f"❌ Error en analizar_zona_ia: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
