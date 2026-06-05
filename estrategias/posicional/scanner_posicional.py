"""
═══════════════════════════════════════════════════════════════
SCANNER POSICIONAL — IBEX 35 + CONTINUO LÍQUIDO
═══════════════════════════════════════════════════════════════

Uso:
    scanner = ScannerPosicional()

    # Escaneo completo (IBEX + Continuo líquido)
    resultado = scanner.escanear_todo(cache)

    # Solo IBEX
    señales = scanner.escanear(IBEX35, cache)

    # Con auditoría de rechazos
    resultado = scanner.escanear_todo(cache, auditoria=True)
    print(resultado["auditoria"])
"""

import logging
from collections import Counter
from core.universos import IBEX35, CONTINUO, TODOS
from core.contexto_mercado import evaluar_contexto_ibex, mercado_operable
from .datos_posicional import obtener_datos_semanales
from .sistema_trading_posicional import evaluar_con_scoring
from .config_posicional import CONTINUO_LIQUIDO, UNIVERSO_POSICIONAL_AMPLIADO

logger = logging.getLogger(__name__)


class ScannerPosicional:

    def __init__(self):
        pass

    def escanear(
        self,
        tickers: list = None,
        cache=None,
        top_n: int = None,
        auditoria: bool = False,
    ) -> list | dict:
        """
        Escanea posicional usando evaluar_con_scoring.
        Por defecto usa UNIVERSO_POSICIONAL_AMPLIADO (IBEX35 + Continuo líquido).

        Args:
            tickers:   lista de tickers a escanear (por defecto UNIVERSO_POSICIONAL_AMPLIADO)
            cache:     objeto Cache de Flask
            top_n:     limitar resultados COMPRA a los N mejores scores
            auditoria: si True, devuelve dict con señales + estadísticas de rechazos

        Returns:
            list de señales COMPRA, o dict {señales, rechazos, auditoria} si auditoria=True
        """
        import time

        universo     = tickers or UNIVERSO_POSICIONAL_AMPLIADO
        resultados   = []
        watchlist    = []              # tendencia OK, solo falta breakout
        rechazos_raw = []              # lista de dicts {ticker, motivos}
        contador_motivos = Counter()   # breakout: N, volatilidad: N, ...

        for ticker in universo:
            try:
                time.sleep(0.3)
                df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)
                if df is None or df.empty or len(df) < 200:
                    contador_motivos["historico_insuficiente"] += 1
                    if auditoria:
                        rechazos_raw.append({
                            "ticker":  ticker,
                            "motivos": ["Histórico insuficiente (<200 semanas)"]
                        })
                    continue

                precios   = df["Close"].values
                volumenes = df["Volume"].values if "Volume" in df.columns else None
                res       = evaluar_con_scoring(precios, volumenes)

                if res.get("decision") == "COMPRA":
                    resultados.append({
                        "ticker":          ticker,
                        "nombre":          ticker.replace(".MC", ""),
                        "mercado":         "IBEX35" if ticker in IBEX35 else "CONTINUO",
                        "precio":          float(precios[-1]),
                        "entrada":         res.get("entrada", 0),
                        "stop":            res.get("stop", 0),
                        "riesgo_pct":      res.get("riesgo_pct", 0),
                        "score":           res.get("setup_score", 0),
                        "clasificacion":   res.get("clasificacion", ""),
                        "motivo":          " · ".join(res.get("motivos", [])),
                        "fuerza_relativa": res.get("detalles", {}).get("fr_cat", ""),
                        "fr_diferencial":  res.get("detalles", {}).get("fr_diff", 0),
                    })
                else:
                    # Registrar motivos de rechazo para auditoría
                    motivos = res.get("motivos", ["Sin señal"])
                    score   = res.get("setup_score", 0)

                    for motivo in motivos:
                        cat = _categorizar_motivo(motivo)
                        contador_motivos[cat] += 1

                    detalles  = res.get("detalles", {})
                    tendencia = detalles.get("tendencia", "")

                    # ── CLASIFICACIÓN EN 4 ESTADOS ───────────────────
                    # Solo entra en watchlist si:
                    #   - El único motivo de rechazo es falta de breakout
                    #   - Tendencia ALCISTA confirmada
                    # Dentro de watchlist, score separa A (≥65) de B (50-64)
                    # Por debajo de 50 → RECHAZADO independientemente

                    solo_sin_breakout = (
                        len(motivos) == 1
                        and _categorizar_motivo(motivos[0]) == "sin_breakout"
                        and tendencia == "ALCISTA"
                    )

                    if solo_sin_breakout and score >= 50:
                        dist_bk  = detalles.get("breakout_distancia_pct", 0) or 0
                        maximo_26= detalles.get("maximo_26") or 0
                        nivel_wl = "A" if score >= 65 else "B"

                        watchlist.append({
                            "ticker":           ticker,
                            "nombre":           ticker.replace(".MC", ""),
                            "mercado":          "IBEX35" if ticker in IBEX35 else "CONTINUO",
                            "precio":           float(precios[-1]),
                            "score":            score,
                            "clasificacion":    res.get("clasificacion", ""),
                            "nivel_watchlist":  nivel_wl,      # "A" ≥65 | "B" 50-64
                            "distancia_bk_pct": round(abs(dist_bk), 2),
                            "maximo_26":        round(maximo_26, 2),
                            "tendencia":        tendencia,
                            "distancia_mm50":   round(detalles.get("distancia_mm50_pct", 0) or 0, 1),
                            "fuerza_relativa":  detalles.get("fr_cat", ""),
                            "fr_diferencial":   detalles.get("fr_diff", 0),
                        })
                    # score < 50 o múltiples motivos → RECHAZADO (no aparece en watchlist)

                    if auditoria:
                        rechazos_raw.append({
                            "ticker":  ticker,
                            "motivos": motivos,
                            "score":   score,
                        })

            except Exception as e:
                logger.warning(f"Scanner posicional error {ticker}: {e}")
                contador_motivos["error"] += 1

        resultados.sort(key=lambda x: x["score"], reverse=True)
        watchlist.sort(key=lambda x: x["score"], reverse=True)
        señales = resultados[:top_n] if top_n else resultados

        if not auditoria:
            return {"señales": señales, "watchlist": watchlist}

        # Ordenar rechazos por score desc antes de construir auditoría
        rechazos_raw.sort(key=lambda x: x.get("score", 0), reverse=True)

        # ── Construir resumen auditoría ──────────────────────────
        total_analizados = len(universo)
        total_rechazados = total_analizados - len(señales)
        auditoria_data   = _construir_auditoria(
            contador_motivos, total_analizados, total_rechazados,
            len(señales), rechazos_raw
        )

        return {
            "señales":   señales,
            "watchlist": watchlist,
            "auditoria": auditoria_data,
        }

    def escanear_todo(self, cache=None, top_n: int = 15, auditoria: bool = False) -> dict:
        """
        Escaneo completo con contexto de mercado incluido.
        Usa UNIVERSO_POSICIONAL_AMPLIADO (IBEX35 + Continuo líquido).

        Returns:
            dict con 'señales', 'contexto', 'total', 'cancelado', 'auditoria' (si auditoria=True)
        """
        contexto = evaluar_contexto_ibex(cache)

        if not mercado_operable(cache):
            logger.warning("⚠️ ScannerPosicional: mercado bajista — scan cancelado")
            return {
                "señales":   [],
                "contexto":  contexto,
                "total":     0,
                "cancelado": True,
                "motivo":    "Mercado en estado BAJISTA — posicional cancelado",
                "auditoria": None,
            }

        resultado = self.escanear(cache=cache, top_n=top_n, auditoria=auditoria)

        # resultado siempre es dict ahora
        señales      = resultado.get("señales", [])
        watchlist    = resultado.get("watchlist", [])
        auditoria_dt = resultado.get("auditoria") if auditoria else None

        logger.info(
            f"📊 ScannerPosicional: {len(señales)} señales · "
            f"{len(watchlist)} watchlist · "
            f"contexto={contexto['estado']} · "
            f"universo={len(UNIVERSO_POSICIONAL_AMPLIADO)} valores"
        )

        return {
            "señales":   señales,
            "watchlist": watchlist,
            "contexto":  contexto,
            "total":     len(señales),
            "cancelado": False,
            "auditoria": auditoria_dt,
        }

    def evaluar_ticker(self, ticker: str, cache=None) -> dict:
        """Evalúa un ticker individual."""
        df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)
        if df is None or df.empty:
            return {"error": f"Sin datos para {ticker}"}
        precios   = df["Close"].values
        volumenes = df["Volume"].values if "Volume" in df.columns else None
        res       = evaluar_con_scoring(precios, volumenes)
        return {
            "señal":    res,
            "contexto": evaluar_contexto_ibex(cache),
        }


# ──────────────────────────────────────────────────────────────
# HELPERS PRIVADOS
# ──────────────────────────────────────────────────────────────

def _categorizar_motivo(motivo: str) -> str:
    """Normaliza un motivo de rechazo a una categoría de auditoría."""
    m = motivo.lower()
    if "breakout" in m or "máximos" in m or "ruptura" in m:
        return "sin_breakout"
    if "consolidac" in m:
        return "sin_consolidacion"
    if "tendencia" in m or "mm50" in m or "mm200" in m or "pendiente" in m or "lateral" in m or "bajista" in m and "mercado" not in m:
        return "tendencia_no_alcista"
    if "volatilidad" in m:
        return "volatilidad"
    if "histórico" in m or "historico" in m or "insuficiente" in m and "score" not in m:
        return "historico_insuficiente"
    if "score" in m or "criterios" in m:
        return "score_bajo"
    if "ibex" in m or "mercado" in m:
        return "mercado_bajista"
    if "riesgo" in m:
        return "riesgo_invalido"
    return "otros"


def _construir_auditoria(
    contador: Counter,
    total: int,
    rechazados: int,
    señales: int,
    rechazos_raw: list,
) -> dict:
    """Construye el resumen de auditoría de rechazos."""

    LABELS = {
        "sin_breakout":          "Sin breakout de máximos",
        "tendencia_no_alcista":  "Tendencia no alcista",
        "sin_consolidacion":     "Sin consolidación previa",
        "volatilidad":           "Volatilidad fuera de rango",
        "historico_insuficiente":"Histórico insuficiente",
        "score_bajo":            "Score insuficiente",
        "mercado_bajista":       "Mercado bajista (filtro global)",
        "riesgo_invalido":       "Riesgo inválido",
        "error":                 "Error técnico",
        "otros":                 "Otros",
    }

    total_rechazos_contados = sum(contador.values())

    motivos_ordenados = []
    for cat, n in contador.most_common():
        pct = round(n / total * 100, 1) if total > 0 else 0
        motivos_ordenados.append({
            "categoria": cat,
            "label":     LABELS.get(cat, cat),
            "n":         n,
            "pct":       pct,
        })

    # Cuello de botella = motivo más frecuente
    cuello = motivos_ordenados[0] if motivos_ordenados else None

    return {
        "total_analizados":  total,
        "total_señales":     señales,
        "total_rechazados":  rechazados,
        "tasa_conversion":   round(señales / total * 100, 1) if total > 0 else 0,
        "motivos":           motivos_ordenados,
        "cuello_botella":    cuello,
        "detalle_rechazos":  rechazos_raw[:20],  # primeros 20 para no saturar
    }
