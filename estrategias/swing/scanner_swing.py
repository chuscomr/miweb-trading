"""
ESCÁNER SWING TRADING
Usa las clases BreakoutSwing y PullbackSwing de la nueva arquitectura.

VERSIÓN v82.7: Integración con perfiles adaptativos por contexto de mercado
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from estrategias.swing.breakout import BreakoutSwing
from estrategias.swing.pullback import PullbackSwing
from estrategias.swing.perfiles_contexto import (
    obtener_perfil_trading,
    calcular_score_ranking,
    setup_pasa_filtro,
    clasificar_calidad_setup
)
from core.contexto_mercado import evaluar_contexto_ibex

_breakout_inst = BreakoutSwing()
_pullback_inst  = PullbackSwing()


# ══════════════════════════════════════════════════════════════
# ESCANEO INDIVIDUAL
# ══════════════════════════════════════════════════════════════

def escanear_ticker(ticker: str, tipo_scan: str = "breakout", cache=None):
    """
    Evalúa un ticker con la estrategia indicada.
    tipo_scan: 'breakout' | 'pullback'
    Devuelve dict formateado o None si no hay señal válida.
    """
    if tipo_scan == "pullback":
        r = _pullback_inst.evaluar(ticker, cache)
    else:
        r = _breakout_inst.evaluar(ticker, cache)

    if not isinstance(r, dict) or not r.get("valido", False):
        return None

    return _formatear(r)


# ══════════════════════════════════════════════════════════════
# ESCANEO MASIVO
# ══════════════════════════════════════════════════════════════

def escanear_mercado(tickers: list, tipo_scan: str = "breakout",
                     max_workers: int = 2, cache=None, usar_perfil_adaptativo=True) -> list:
    """
    Escanea una lista de tickers en paralelo con sistema de RANKING PROFESIONAL.
    
    FLUJO:
    1. Escanea todos los tickers
    2. FILTRA por score ponderado mínimo (elimina basura)
    3. RANKEA por score de ranking (prioriza según contexto)
    4. Retorna ordenados de mejor a peor
    
    tipo_scan: 'breakout' | 'pullback' | 'ambos'
    usar_perfil_adaptativo: Si True, aplica filtro+ranking según contexto
    
    NO USA CUOTAS - El mercado decide, nosotros priorizamos
    """
    # Obtener perfil según contexto de mercado
    perfil = None
    contexto_actual = "LATERAL"  # Default
    
    if usar_perfil_adaptativo:
        try:
            contexto_info = evaluar_contexto_ibex(cache=cache)
            contexto_actual = contexto_info.get("tendencia", "LATERAL")
            perfil = obtener_perfil_trading(contexto_actual)
            
            print(f"\n{'='*70}")
            print(f"🎯 SISTEMA V2.1 PROFESIONAL: {perfil['contexto']}")
            print(f"{'='*70}")
            print(f"   ✅ VALIDEZ TÉCNICA (dinámica por contexto):")
            from estrategias.swing.perfiles_contexto import UMBRALES_CONTEXTO
            umbral_ctx = UMBRALES_CONTEXTO.get(contexto_actual, 6.0)
            print(f"      • Score mínimo: {umbral_ctx}")
            print(f"\n   📊 RANKING (prioriza según contexto):")
            print(f"      • Prioridad Breakout: {perfil['prioridad_breakout']:.1f}x")
            print(f"      • Prioridad Pullback: {perfil['prioridad_pullback']:.1f}x")
            print(f"\n   💰 Gestión (ajustada por contexto):")
            print(f"      • Tamaño Breakout: {perfil['factor_tamaño_breakout']*100:.0f}%")
            print(f"      • Tamaño Pullback: {perfil['factor_tamaño_pullback']*100:.0f}%")
            print(f"      • Máx posiciones: {perfil['max_posiciones_abiertas']}")
            print(f"      • Riesgo/trade: {perfil['riesgo_por_trade_pct']}%")
            print(f"\n   🔍 Confirmaciones extra requeridas:")
            print(f"      • Breakout: {'SÍ' if perfil['requiere_confirmacion_breakout'] else 'NO'}")
            print(f"      • Pullback: {'SÍ' if perfil['requiere_confirmacion_pullback'] else 'NO'}")
            if perfil['requiere_confirmacion_breakout'] or perfil['requiere_confirmacion_pullback']:
                from estrategias.swing.perfiles_contexto import obtener_confirmaciones_requeridas
                if perfil['requiere_confirmacion_breakout']:
                    conf_b = obtener_confirmaciones_requeridas("breakout")
                    print(f"\n      Breakout debe cumplir:")
                    for c in conf_b:
                        print(f"        • {c}")
                if perfil['requiere_confirmacion_pullback']:
                    conf_p = obtener_confirmaciones_requeridas("pullback")
                    print(f"\n      Pullback debe cumplir:")
                    for c in conf_p:
                        print(f"        • {c}")
            print(f"{'='*70}\n")
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto: {e}, usando perfil estándar")
            perfil = None
    
    if tipo_scan == "ambos":
        breakouts = escanear_mercado(tickers, "breakout", max_workers, cache, usar_perfil_adaptativo)
        pullbacks = escanear_mercado(tickers, "pullback", max_workers, cache, usar_perfil_adaptativo)
        vistos = set()
        combinados = []
        for r in sorted(breakouts + pullbacks,
                        key=lambda x: x.get("score_ranking", x.get("score", 0)), reverse=True):
            if r["ticker_completo"] not in vistos:
                vistos.add(r["ticker_completo"])
                combinados.append(r)
        return combinados

    resultados = []
    vistos = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(escanear_ticker, t, tipo_scan, cache): t
            for t in tickers
        }
        for future in as_completed(futures):
            r = future.result()
            if isinstance(r, dict) and r.get("es_senal") and r["ticker_completo"] not in vistos:
                score_base = r.get("score", 0)
                
                # PASO 1: FILTRO (elimina basura)
                if perfil:
                    pasa, score_ponderado, score_minimo = setup_pasa_filtro(
                        score_base, tipo_scan, contexto_actual
                    )
                    
                    if not pasa:
                        # Rechazado por filtro
                        continue
                    
                    # PASO 2: CALCULAR SCORE DE RANKING (para ordenar)
                    score_ranking = calcular_score_ranking(
                        score_base, tipo_scan, contexto_actual
                    )
                    
                    # PASO 3: CLASIFICAR CALIDAD
                    calidad = clasificar_calidad_setup(score_base)
                    
                    # PASO 4: OBTENER FACTOR DE TAMAÑO
                    from estrategias.swing.perfiles_contexto import (
                        obtener_factor_tamaño, 
                        requiere_confirmacion_extra,
                        obtener_confirmaciones_requeridas
                    )
                    factor_tamaño = obtener_factor_tamaño(tipo_scan, contexto_actual)
                    necesita_conf = requiere_confirmacion_extra(tipo_scan, contexto_actual)
                    
                    # Agregar información al resultado
                    r["score_original"] = score_base
                    r["score_ranking"] = score_ranking  # ← USADO PARA ORDENAR
                    r["calidad"] = calidad
                    r["perfil_usado"] = perfil['contexto']
                    r["factor_tamaño"] = factor_tamaño  # ✅ NUEVO en V2
                    r["prioridad"] = perfil[f'prioridad_{tipo_scan}']  # ✅ NUEVO en V2
                    r["requiere_confirmacion"] = necesita_conf  # ✅ NUEVO en V2.1
                    if necesita_conf:
                        r["confirmaciones"] = obtener_confirmaciones_requeridas(tipo_scan)  # ✅ NUEVO en V2.1
                else:
                    # Sin perfil adaptativo
                    r["score_ranking"] = score_base
                    r["calidad"] = clasificar_calidad_setup(score_base)
                    r["factor_tamaño"] = 1.0
                
                vistos.add(r["ticker_completo"])
                resultados.append(r)

    # PASO 4: ORDENAR POR SCORE DE RANKING (NO por score original)
    resultados.sort(key=lambda x: x.get("score_ranking", 0), reverse=True)
    
    # Mostrar resumen de calidad
    if perfil and resultados:
        excelentes = sum(1 for r in resultados if r.get("calidad") == "excelente")
        buenos = sum(1 for r in resultados if r.get("calidad") == "bueno")
        mediocres = sum(1 for r in resultados if r.get("calidad") == "mediocre")
        
        print(f"\n{'─'*70}")
        print(f"📊 DISTRIBUCIÓN DE CALIDAD (NO forzada, natural):")
        print(f"   ⭐ Excelentes: {excelentes} ({excelentes/len(resultados)*100:.0f}%)")
        print(f"   🔵 Buenos:     {buenos} ({buenos/len(resultados)*100:.0f}%)")
        print(f"   🟢 Mediocres:  {mediocres} ({mediocres/len(resultados)*100:.0f}%)")
        print(f"{'─'*70}\n")
    
    return resultados


# ══════════════════════════════════════════════════════════════
# FORMATEO
# ══════════════════════════════════════════════════════════════

def _to_float(x):
    if hasattr(x, "item"):
        return float(x.item())
    return float(x) if x is not None else 0.0


def _nivel_calidad(score: float) -> dict:
    """
    Clasifica el setup en 3 niveles de calidad.
    🟢 Compra            (5.5 - 6.4): estructura + RSI
    🔵 Compra Confirmada (6.5 - 7.9): + soporte cercano
    ⭐ Alta Probabilidad (8.0+):       + patrón de vela
    """
    if score >= 8.0:
        return {"nivel": "alta_probabilidad", "label": "Alta Probabilidad", "emoji": "⭐"}
    elif score >= 6.5:
        return {"nivel": "confirmada",        "label": "Compra Confirmada", "emoji": "🔵"}
    else:
        return {"nivel": "compra",            "label": "Compra",            "emoji": "🟢"}


def _formatear(r: dict) -> dict:
    from core.universos import get_nombre
    ticker = r.get("ticker", "")
    score  = _to_float(r.get("setup_score", 0))
    nivel  = _nivel_calidad(score)

    # Mantener confianza legacy para compatibilidad
    if score >= 8:
        confianza = "muy_alto"
    elif score >= 6:
        confianza = "alto"
    elif score >= 4:
        confianza = "medio"
    else:
        confianza = "medio_bajo"

    tipo = r.get("tipo", "BREAKOUT")
    return {
        "ticker":          ticker.replace(".MC", ""),
        "ticker_completo": ticker,
        "nombre":          get_nombre(ticker),
        "precio":          _to_float(r.get("precio_actual")),
        "precio_actual":   _to_float(r.get("precio_actual")),
        "score":           score,
        "setup_score":     score,
        "setup_max":       10,
        "confianza":       confianza,
        "nivel":           nivel["nivel"],
        "nivel_label":     nivel["label"],
        "nivel_emoji":     nivel["emoji"],
        "variacion_1d":    _to_float(r.get("variacion_1d")),
        "es_senal":        True,
        "entrada":         _to_float(r.get("entrada")),
        "stop":            _to_float(r.get("stop")),
        "objetivo":        _to_float(r.get("objetivo")),
        "rr":              _to_float(r.get("rr")),
        "tipo":            tipo,
        "tipo_señal":      tipo,
    }


# ══════════════════════════════════════════════════════════════
# CLASE WRAPPER — para swing_routes.py
# ══════════════════════════════════════════════════════════════

class ScannerSwing:
    """Wrapper OOP sobre las funciones del scanner."""

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        b = _breakout_inst.evaluar(ticker, cache)
        p = _pullback_inst.evaluar(ticker, cache)
        from core.contexto_mercado import evaluar_contexto_ibex
        return {
            "breakout": b,
            "pullback": p,
            "contexto": evaluar_contexto_ibex(cache),
        }

    def escanear_todo(self, tickers=None, cache=None, top_n: int = 20) -> dict:
        from core.universos import IBEX35, CONTINUO
        if tickers is None:
            tickers = IBEX35 + CONTINUO
        señales = escanear_mercado(tickers, tipo_scan="ambos",
                                   max_workers=2, cache=cache)
        señales = señales[:top_n]
        return {
            "señales":   señales,
            "total":     len(señales),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
