# alertas/alertas_ia.py
# ══════════════════════════════════════════════════════════════
# INTERPRETACIÓN IA DE ALERTAS — Claude Haiku
#
# Migrado desde alertas_ia.py del proyecto original.
# Sin cambios en la lógica — solo imports limpios.
# Solo se llama cuando hay alertas activas (economiza tokens).
# ══════════════════════════════════════════════════════════════

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MODELO = "claude-haiku-4-5-20251001"

_CONTEXTO_SISTEMA = {
    "swing":      "Swing trading (1-3 semanas). Stop basado en ATR 1.5x-2x. RR mínimo 2.5:1.",
    "medio":      "Trading medio plazo (4-24 semanas). Stops amplios. RR mínimo 3:1.",
    "posicional": "Trading posicional (6 meses-2 años). Stops muy amplios 8-15%. RR mínimo 3:1.",
}

_RESPUESTA_FALLBACK = {
    "interpretacion": "Análisis IA no disponible.",
    "recomendacion":  "ESPERAR",
    "razon":          "Error de conexión con la IA.",
    "confianza":      "BAJA",
    "sesgo":          "NEUTRO",
}


def interpretar_alertas(
    alertas:        list,
    ticker:         str,
    sistema:        str  = "swing",
    filtro_mercado: bool = True,
) -> Optional[dict]:
    """
    Interpreta un conjunto de alertas ya detectadas para un ticker.
    Solo llamar cuando len(alertas) > 0.

    Returns:
        dict con interpretacion, recomendacion, confianza, sesgo
        o None si no hay alertas.
    """
    if not alertas:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except Exception as e:
        logger.warning(f"⚠️ No se pudo inicializar cliente Anthropic: {e}")
        return {**_RESPUESTA_FALLBACK, "razon": str(e)}

    alertas_top = alertas[:4]
    alertas_str = "\n".join([
        f"• [{a['severidad']}] {a['titulo']}: {a['detalle']}"
        for a in alertas_top
    ])

    contexto    = _CONTEXTO_SISTEMA.get(sistema, _CONTEXTO_SISTEMA["swing"])
    filtro_str  = ("Filtro de mercado ACTIVO: solo entradas largas si IBEX > MA200."
                   if filtro_mercado else "Filtro de mercado DESACTIVADO.")

    prompt = f"""Eres un asistente de trading para mercado español (IBEX 35 / Mercado Continuo).
Sistema: {contexto}
{filtro_str}
Mercado: España (Bankinter como bróker).

Ticker: {ticker}
Alertas técnicas detectadas hoy:
{alertas_str}

Analiza si estas alertas son coherentes entre sí. Responde SOLO con este JSON (sin markdown):
{{
  "interpretacion": "análisis conjunto en 2-3 frases en español",
  "recomendacion": "ENTRAR_LARGO | ENTRAR_CORTO | ESPERAR | REDUCIR_POSICION | CERRAR_POSICION | AJUSTAR_STOP",
  "razon": "1 frase justificando la recomendación",
  "confianza": "ALTA | MEDIA | BAJA",
  "sesgo": "ALCISTA | BAJISTA | NEUTRO"
}}"""

    try:
        response = client.messages.create(
            model=MODELO,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = response.content[0].text.strip()
        texto = texto.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)

    except Exception as e:
        logger.warning(f"⚠️ Error IA interpretar_alertas {ticker}: {e}")
        return {**_RESPUESTA_FALLBACK, "razon": str(e)}


def interpretar_cartera(
    posiciones:         list,
    alertas_por_ticker: dict,
) -> Optional[str]:
    """
    Análisis global de la cartera con alertas activas.

    Args:
        posiciones:         [{"ticker": "SAN", "lado": "largo", "entrada": 4.20, "stop": 3.90}]
        alertas_por_ticker: dict {ticker: [alertas]}

    Returns:
        Texto libre con sugerencias de gestión, o None si no hay posiciones.
    """
    if not posiciones:
        return None

    tickers_con_alertas = {
        t: [a['titulo'] for a in al]
        for t, al in alertas_por_ticker.items()
        if al
    }

    if not tickers_con_alertas:
        return "Cartera sin alertas activas. Mantener posiciones según plan."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except Exception as e:
        return f"Análisis de cartera no disponible: {e}"

    pos_str = "\n".join([
        f"• {p['ticker']} {p.get('lado','largo').upper()} | "
        f"Entrada: {p.get('entrada','?')} | Stop: {p.get('stop','?')}"
        for p in posiciones
    ])
    alertas_str = "\n".join([
        f"• {t}: {', '.join(al)}"
        for t, al in tickers_con_alertas.items()
    ])

    prompt = f"""Eres un gestor de riesgo para swing trading en mercado español.
Sistema: stops basados en ATR, RR mínimo 2.5:1, horizonte 1-3 semanas.

Posiciones abiertas:
{pos_str}

Alertas activas en cartera:
{alertas_str}

Dame en 3-4 frases en español:
1. Qué posiciones requieren atención inmediata
2. Ajustes de stops recomendados
3. Si hay señales de reducir exposición global"""

    try:
        response = client.messages.create(
            model=MODELO,
            max_tokens=350,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"⚠️ Error IA interpretar_cartera: {e}")
        return f"Análisis de cartera no disponible: {e}"
