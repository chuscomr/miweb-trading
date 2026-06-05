"""
analisis/fundamental/clasificador_eventos.py
============================================
Clasifica noticias financieras según tipo de evento corporativo.

v87.1 — Detección por keywords + extracción de ticker
"""

import re
from typing import Optional


# ══════════════════════════════════════════════════════════════
# CLASIFICACIÓN DE EVENTOS POR KEYWORDS
# ══════════════════════════════════════════════════════════════

KEYWORDS_EVENTOS = {
    'BONOS': {
        'keywords': [
            # Emisiones - todas las variantes verbales
            'emisión de bonos', 'emite bonos', 'emitirá bonos', 'emitir bonos',
            'lanzar bonos', 'lanza bonos', 'lanzará bonos', 'lanzamiento de bonos',
            'emisión de deuda', 'emite deuda', 'emitirá deuda', 'emitir deuda',
            'colocación de deuda', 'coloca deuda', 'colocará deuda',
            'emisión obligaciones', 'emite obligaciones',
            # Tipos de bonos
            'bonos senior', 'bonos convertibles', 'bonos verdes',
            'bonos perpetuos', 'bonos híbridos', 'bonos sostenibles',
            # Operaciones relacionadas
            'refinanciación', 'refinancia', 'refinanciar',
            'recompra de bonos', 'amortización anticipada',
            'high yield', 'investment grade', 'mid-swap',
            # Patrones específicos
            'millones en bonos', 'millones de bonos', 'millones de euros en bonos',
            'reforzar la liquidez', 'reforzar liquidez',
        ],
        'impacto_default': 'NEUTRAL',
        'emoji': '💰',
        'color': '#3b82f6',  # azul
        # v87.2: Anti-falsos positivos (excluir si contiene estas frases)
        'excluir_si_contiene': [
            'mercados de bonos', 'mercado de bonos', 'mercado de deuda',
            'rentabilidad de los bonos', 'rentabilidades de los bonos',
            'cotización de bonos', 'precio de los bonos',
            'fondos de bonos', 'etf de bonos',
            'tipo de los bonos', 'tipos de los bonos',
            'curva de bonos',
        ],
    },
    'DIVIDENDO': {
        'keywords': [
            # Acciones de pago
            'paga dividendo', 'pagará dividendo', 'pagar dividendo',
            'reparte dividendo', 'repartirá dividendo', 'reparto de dividendo',
            'abona dividendo', 'abonará dividendo', 'abono de dividendo',
            'distribuye dividendo', 'distribuirá dividendo',
            # Tipos de dividendo
            'dividendo extraordinario', 'dividendo a cuenta',
            'dividendo complementario', 'dividendo ordinario',
            'scrip dividend', 'dividendo flexible', 'dividendo en acciones',
            # Conceptos relacionados
            'retribución al accionista', 'retribución a los accionistas',
            'pago a accionistas', 'remunera al accionista',
            'fecha ex-dividendo', 'ex-date', 'cupón',
            # Cambios en política
            'aumenta dividendo', 'aumenta su dividendo', 'aumentará dividendo',
            'sube el dividendo', 'sube su dividendo', 'subirá dividendo',
            'eleva dividendo', 'eleva su dividendo', 'elevará dividendo',
            'recorta dividendo', 'recorta su dividendo', 'recortará dividendo',
            'reduce dividendo', 'reduce su dividendo', 'reducirá dividendo',
            'suspende dividendo', 'suspende su dividendo', 'suspenderá dividendo',
            'recupera el dividendo', 'restablece dividendo', 'restablece su dividendo',
        ],
        'impacto_default': 'POSITIVO',
        'emoji': '💵',
        'color': '#10b981',  # verde
        'excluir_si_contiene': [
            'rentabilidad por dividendo del ibex',
            'yield por dividendo',
            'fondos de dividendo',
            'etf de dividendos',
            'estrategia de dividendos',
            'cazadividendos',
        ],
    },
    'AMPLIACION': {
        'keywords': [
            'ampliación de capital', 'ampliacion de capital', 'ampliación capital',
            'amplía capital', 'ampliará capital', 'ampliar capital',
            'derechos de suscripción', 'derechos preferentes',
            'rights issue', 'fully marketed',
            'nueva emisión de acciones', 'emite acciones',
            'colocación acelerada', 'private placement',
            'ampliación liberada', 'split de acciones', 'contrasplit',
            'reduce capital', 'reducción de capital', 'amortización de acciones',
        ],
        'impacto_default': 'NEGATIVO',
        'emoji': '📊',
        'color': '#ef4444',  # rojo
        'excluir_si_contiene': [
            'capital riesgo', 'mercado de capitales',
            'fuga de capitales', 'movimiento de capitales',
            'capital social del banco',
        ],
    },
    'EARNINGS': {
        'keywords': [
            # Publicación de resultados
            'presenta resultados', 'publica resultados', 'rendirá cuentas',
            'resultados trimestrales', 'resultados semestrales', 'resultados anuales',
            'resultados del primer trimestre', 'resultados del segundo trimestre',
            'resultados del tercer trimestre', 'resultados del cuarto trimestre',
            'resultados q1', 'resultados q2', 'resultados q3', 'resultados q4',
            'cuentas del trimestre', 'cuentas del semestre',
            # Indicadores financieros con verbos (específicos para evitar conflicto con "gana contrato")
            'gana en el trimestre', 'gana en el semestre', 'gana en el año',
            'gana en el ejercicio', 'gana hasta', 'ganó hasta',
            'gana un', 'ganará un',  # "gana un 15%" típico de earnings
            'en el primer trimestre', 'en el segundo trimestre',
            'en el tercer trimestre', 'en el cuarto trimestre',
            'en el primer semestre', 'en el segundo semestre',
            'beneficio neto de', 'beneficio neto sube', 'beneficio neto cae',
            'beneficio neto crece', 'beneficio neto baja',
            'ingresos suben', 'ingresos caen', 'ingresos crecen',
            'facturación sube', 'facturación cae', 'facturación crece',
            'ebitda sube', 'ebitda cae', 'ebitda crece',
            # Guidance
            'guidance', 'previsiones para el año', 'objetivos para',
            'profit warning', 'revisa al alza', 'revisa a la baja',
            'eleva previsiones', 'recorta previsiones',
        ],
        'impacto_default': 'NEUTRAL',
        'emoji': '📈',
        'color': '#f59e0b',  # ámbar
        'excluir_si_contiene': [
            'resultados electorales', 'resultados de la liga',
            'resultados deportivos',
        ],
    },
    'FUSION': {
        'keywords': [
            # OPAs
            'opa hostil', 'opa amistosa', 'lanza opa', 'lanzará opa',
            'oferta pública de adquisición', 'oferta de adquisición',
            'opa por', 'opa sobre', 'opa por el',
            # Fusiones
            'fusión con', 'fusiona con', 'fusionará con', 'se fusiona',
            'fusión por absorción', 'plan de fusión',
            # Adquisiciones
            'adquiere ', 'adquirirá ', 'adquirir ', 'adquisición de',
            'compra el', 'comprará el', 'compra de ', 'compra a ',
            'absorbe', 'absorberá', 'absorción de',
            'integración con', 'se integra con',
            'toma el control', 'tomará el control',
            # Inglés común en prensa
            'merger', 'takeover', 'acquires',
        ],
        'impacto_default': 'POSITIVO',
        'emoji': '🤝',
        'color': '#8b5cf6',  # violeta
        'excluir_si_contiene': [
            'fusión nuclear', 'fusión fría',
            'compra de coches', 'compra de viviendas',
            'adquisición de vivienda', 'adquirir vivienda',
        ],
    },
    'EJECUTIVO': {
        'keywords': [
            'dimite como', 'dimisión como', 'presenta su dimisión',
            'nuevo ceo', 'nuevo director general', 'nuevo presidente ejecutivo',
            'nombra ceo', 'nombrará ceo', 'nombramiento de',
            'sucesión en', 'releva como', 'sustituye como',
            'cesa como', 'cesará como', 'cese de',
            'consejero delegado',
            'nuevo presidente del consejo', 'nueva presidenta',
        ],
        'impacto_default': 'NEUTRAL',
        'emoji': '👔',
        'color': '#6b7280',  # gris
        'excluir_si_contiene': [
            'presidente del gobierno', 'presidente de españa',
            'presidente de la nación', 'presidente del país',
            'dimisión política', 'dimite ministro',
        ],
    },
    'REGULATORIO': {
        'keywords': [
            'sanción de la cnmv', 'multa de la cnmv',
            'sanción de la cnmc', 'multa de la cnmc',
            'multa de bruselas', 'multa europea',
            'sancionado con', 'sancionada con',
            'investigación cnmv', 'investigación cnmc',
            'apertura de expediente', 'expediente sancionador',
            'inspección de hacienda', 'condena por',
            'recurso al supremo', 'tribunal supremo confirma',
            'arbitraje internacional',
            'paraliza la operación', 'veta la operación',
            'autoriza la operación', 'aprueba la fusión',
        ],
        'impacto_default': 'NEGATIVO',
        'emoji': '⚖️',
        'color': '#dc2626',  # rojo oscuro
        'excluir_si_contiene': [
            'sentencia electoral', 'tribunal constitucional político',
        ],
    },
    'ESTRATEGICO': {
        'keywords': [
            'plan estratégico', 'nuevo plan estratégico',
            'capital markets day', 'investor day',
            'nueva planta', 'nueva fábrica', 'nuevo centro logístico',
            'expansión internacional', 'entra en el mercado',
            'joint venture con', 'alianza estratégica con', 'acuerdo estratégico con',
            'contrato millonario', 'mega contrato',
            'adjudicación de', 'adjudica el contrato', 'gana el contrato',
            'nuevo proyecto en', 'lanza nuevo producto',
            'desinversión en', 'desinvierte en', 'vende su filial',
            'vende su participación', 'venta de activos',
            'recompra de acciones', 'plan de recompra', 'buyback',
        ],
        'impacto_default': 'POSITIVO',
        'emoji': '🎯',
        'color': '#0891b2',  # cian
        'excluir_si_contiene': [
            'plan estratégico del gobierno',
            'plan estratégico nacional',
        ],
    },
}


# ══════════════════════════════════════════════════════════════
# MAPEO TICKER → NOMBRES EMPRESA (para detección)
# ══════════════════════════════════════════════════════════════

# Mapeo de nombres de empresa que aparecen en noticias → ticker
EMPRESAS_NOMBRES = {
    'telefónica': 'TEF.MC', 'telefonica': 'TEF.MC',
    'iberdrola': 'IBE.MC',
    'santander': 'SAN.MC', 'banco santander': 'SAN.MC',
    'bbva': 'BBVA.MC',
    'inditex': 'ITX.MC', 'zara': 'ITX.MC',
    'repsol': 'REP.MC',
    'iag': 'IAG.MC', 'iberia': 'IAG.MC', 'british airways': 'IAG.MC', 'vueling': 'IAG.MC',
    'ferrovial': 'FER.MC',
    'amadeus': 'AMS.MC',
    'caixabank': 'CABK.MC',
    'sabadell': 'SAB.MC',
    'mapfre': 'MAP.MC',
    'aena': 'AENA.MC',
    'naturgy': 'NTGY.MC',
    'enagás': 'ENG.MC', 'enagas': 'ENG.MC',
    'endesa': 'ELE.MC',
    'redeia': 'RED.MC', 'red eléctrica': 'RED.MC',
    'cellnex': 'CLNX.MC',
    'acs': 'ACS.MC',
    'acciona': 'ANA.MC',
    'acciona energía': 'ANE.MC', 'acciona energia': 'ANE.MC',
    'arcelormittal': 'MTS.MC', 'arcelor': 'MTS.MC',
    'grifols': 'GRF.MC',
    'merlin': 'MRL.MC', 'merlin properties': 'MRL.MC',
    'colonial': 'COL.MC',
    'meliá': 'MEL.MC', 'melia': 'MEL.MC',
    'unicaja': 'UNI.MC',
    'bankinter': 'BKT.MC',
    'cie automotive': 'CIE.MC',
    'fcc': 'FCC.MC',
    'puig': 'PUIG.MC',
    'indra': 'IDR.MC',
    'logista': 'LOG.MC',
    'acerinox': 'ACX.MC',
    'solaria': 'SLR.MC',
    'pharmamar': 'PHM.MC',
    'rovi': 'ROVI.MC',
    'sacyr': 'SCYR.MC',
    'atresmedia': 'A3M.MC',
    'almirall': 'ALM.MC',
    'clínica baviera': 'CBAV.MC', 'clinica baviera': 'CBAV.MC',
}


def extraer_tickers_mencionados(texto: str) -> list:
    """
    Detecta tickers mencionados en el texto de la noticia.
    
    Estrategias:
    1. Patrón TICKER.MC explícito (ej: "IAG.MC")
    2. Patrón ticker entre paréntesis (ej: "(IAG)")
    3. Nombre de empresa conocida (ej: "Iberia" → IAG.MC)
    
    Returns:
        Lista de tickers únicos detectados
    """
    if not texto:
        return []
    
    texto_lower = texto.lower()
    tickers = set()
    
    # Estrategia 1: TICKER.MC explícito
    matches = re.findall(r'\b([A-Z]{2,6})\.MC\b', texto)
    for m in matches:
        tickers.add(f"{m}.MC")
    
    # Estrategia 2: Ticker entre paréntesis (TICKER)
    matches_paren = re.findall(r'\(([A-Z]{2,6})\)', texto)
    for m in matches_paren:
        # Solo añadir si parece ser un ticker español conocido
        ticker_potencial = f"{m}.MC"
        if any(ticker_potencial == v for v in EMPRESAS_NOMBRES.values()):
            tickers.add(ticker_potencial)
    
    # Estrategia 3: Nombres de empresa conocidas
    for nombre, ticker in EMPRESAS_NOMBRES.items():
        # Búsqueda con límites de palabra para evitar falsos positivos
        if re.search(rf'\b{re.escape(nombre)}\b', texto_lower):
            tickers.add(ticker)
    
    return list(tickers)


def clasificar_noticia(titulo: str, descripcion: str = "") -> Optional[dict]:
    """
    Clasifica una noticia según tipo de evento corporativo.
    
    Args:
        titulo: Título de la noticia
        descripcion: Descripción/resumen (opcional)
    
    Returns:
        dict con:
            - tipo: 'BONOS' | 'DIVIDENDO' | ... | None
            - tipo_emoji: emoji asociado
            - tipo_color: color hex asociado
            - impacto: 'POSITIVO' | 'NEGATIVO' | 'NEUTRAL'
            - tickers: lista de tickers detectados
            - relevancia: 0-10 (basado en confidence)
        None si no se detecta evento relevante
    """
    if not titulo:
        return None
    
    texto_completo = f"{titulo} {descripcion}".lower()
    
    # Buscar tipo de evento por keywords
    tipo_detectado = None
    confidence = 0
    
    for tipo, config in KEYWORDS_EVENTOS.items():
        # v87.2 — Verificar exclusiones primero
        exclusiones = config.get('excluir_si_contiene', [])
        if any(excl in texto_completo for excl in exclusiones):
            continue  # Saltar esta categoría
        
        match_count = 0
        for keyword in config['keywords']:
            if keyword in texto_completo:
                match_count += 1
        
        if match_count > 0:
            tipo_detectado = tipo
            confidence = match_count
            break  # Primera categoría que match gana
    
    if not tipo_detectado:
        return None
    
    # Extraer tickers
    tickers = extraer_tickers_mencionados(titulo + " " + descripcion)
    
    config = KEYWORDS_EVENTOS[tipo_detectado]
    
    return {
        'tipo': tipo_detectado,
        'tipo_emoji': config['emoji'],
        'tipo_color': config['color'],
        'impacto': config['impacto_default'],
        'tickers': tickers,
        'relevancia': min(10, confidence * 3 + (5 if tickers else 0)),
    }


def enriquecer_noticias(noticias: list) -> list:
    """
    Enriquece una lista de noticias añadiendo metadatos de clasificación.
    
    Args:
        noticias: Lista de dicts con 'titulo' y opcionalmente 'descripcion'
    
    Returns:
        Misma lista con campos añadidos:
            - evento: dict de clasificación (o None)
    """
    for noticia in noticias:
        titulo = noticia.get('titulo', '') or noticia.get('title', '')
        descripcion = noticia.get('descripcion', '') or noticia.get('summary', '')
        
        clasificacion = clasificar_noticia(titulo, descripcion)
        noticia['evento'] = clasificacion
    
    return noticias
