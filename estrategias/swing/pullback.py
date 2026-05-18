"""
═══════════════════════════════════════════════════════════════
ESTRATEGIA: PULLBACK (Retrocesos)
Sistema Swing Trading — Estrategia de Rebotes en Soporte
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio retrocede a un soporte
en una tendencia alcista establecida.

Filosofía: "Comprar barato en soporte"

Criterios:
  1. Tendencia alcista macro  (precio > MM200 × 0.95)
  2. Retroceso desde máximo reciente  (5% – 20%)
  3. RSI sobreventa moderada  (≤ 50)
  4. Soporte cercano  (2% – 8% por debajo)
  5. Estructura alcista  (precio > MM50 + MM20 pendiente positiva)
"""

import logging
from datetime import datetime

import pandas as pd

from analisis.tecnico.patrones_velas import detectar_patrones_velas
from core.indicadores import calcular_atr, calcular_rsi
from core.riesgo import calcular_objetivo, calcular_rr
from core.utilidades import f, respuesta_invalida, respuesta_valida
from estrategias.base import EstrategiaBase


logger = logging.getLogger(__name__)

TIPO = "PULLBACK"


def _evaluar_contexto_patron(soporte_ok: bool, rsi_ok: bool, estructura_ok: bool) -> dict:
    """Evalúa la calidad del contexto donde aparece un patrón de vela."""
    condiciones = sum([soporte_ok, rsi_ok, estructura_ok])
    detalles = []
    if soporte_ok:  detalles.append("soporte cercano")
    if rsi_ok:      detalles.append("RSI en zona")
    if estructura_ok: detalles.append("estructura alcista")

    if condiciones >= 3:
        calidad = "fuerte"
    elif condiciones == 2:
        calidad = "moderado"
    elif condiciones == 1:
        calidad = "débil"
    else:
        calidad = "muy débil"

    return {
        "calidad": calidad,
        "condiciones": condiciones,
        "detalle": " + ".join(detalles) if detalles else "sin confirmación",
    }


class PullbackSwing(EstrategiaBase):

    nombre        = "Pullback Swing"
    periodo_datos = "1y"
    min_velas     = 100     # necesita MM200 → mínimo ~200, pero con 100 ya filtra basura

    # ── Implementación obligatoria ─────────────────────────

    def _evaluar_df(self, df: pd.DataFrame, ticker: str) -> dict:
        motivos = []

        # ── Indicadores base ──────────────────────────────
        # Si el df ya tiene las columnas calculadas (backtest vectorizado),
        # las reutilizamos en lugar de recalcular desde cero
        df = df.copy()
        if "MM20" not in df.columns:
            df["MM20"]  = df["Close"].rolling(20).mean()
        if "MM50" not in df.columns:
            df["MM50"]  = df["Close"].rolling(50).mean()
        if "MM200" not in df.columns:
            df["MM200"] = df["Close"].rolling(200).mean()
        if "ATR" not in df.columns:
            df["ATR"]   = calcular_atr(df, 14)
        if "RSI" not in df.columns:
            df["RSI"]   = calcular_rsi(df["Close"], 14)

        precio_actual = f(df["Close"].iloc[-1])
        rsi_val = f(df["RSI"].iloc[-1])
        import math
        if math.isnan(rsi_val):
            rsi_serie = df["RSI"].dropna()
            if len(rsi_serie) < 14:
                return respuesta_invalida(
                    ticker, TIPO, "Histórico insuficiente para calcular RSI",
                    [], variacion_1d, precio_actual
                )
            rsi_val = float(rsi_serie.iloc[-1])
        atr_val       = f(df["ATR"].iloc[-1])
        mm20_val      = f(df["MM20"].iloc[-1])
        mm50_val      = f(df["MM50"].iloc[-1])
        mm200_raw     = df["MM200"].iloc[-1]
        mm200_val     = f(mm200_raw) if not pd.isna(mm200_raw) else None

        variacion_1d = self._variacion_1d(df)

        # ══════════════════════════════════════════════════
        # 1️⃣  TENDENCIA ALCISTA MACRO  (precio > MM200 × 0.95 + MM50 > MM200)
        # ══════════════════════════════════════════════════
        if mm200_val:
            precio_ok   = precio_actual > mm200_val * 0.95
            mm50_ok     = mm50_val > mm200_val
            tendencia_ok = precio_ok and mm50_ok
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Tendencia macro: precio {precio_actual:.2f}€ vs MM200 {mm200_val:.2f}€ | MM50 {mm50_val:.2f}€ {'>' if mm50_ok else '<'} MM200"
            })
        else:
            # Sin MM200 (< 200 velas): criterio suavizado con MM50
            tendencia_ok = precio_actual > mm50_val * 0.95
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"MM200 no disponible — Precio vs MM50 ({precio_actual:.2f}€ vs {mm50_val:.2f}€)"
            })

        # ══════════════════════════════════════════════════
        # 2️⃣  RETROCESO DESDE MÁXIMO — SISTEMA DUAL
        #
        # PROFUNDO (5-15%): Válido siempre (setup clásico)
        # SUPERFICIAL (3-5%): Válido SOLO con estructura fuerte
        #
        # Razón: Pullbacks poco profundos necesitan confirmación
        # extra de fuerza. Sin estructura son micro-caídas sin edge.
        # ══════════════════════════════════════════════════
        # CORRECCIÓN LOOKAHEAD: Excluye el precio actual (no usamos información futura)
        maximo_60    = f(df["Close"].iloc[:-1].tail(60).max())
        retroceso_pct = ((maximo_60 - precio_actual) / maximo_60) * 100

        # Evaluar tipo de pullback
        es_pullback_profundo = 5.0 <= retroceso_pct <= 15.0
        es_pullback_superficial = 3.0 <= retroceso_pct < 5.0

        # Pre-evaluar estructura para pullbacks superficiales
        # (necesitamos saber si es válido antes del scoring)
        estructura_base_ok = precio_actual > mm50_val
        mm20_serie = df["MM20"].dropna()
        mm20_pendiente = (float(mm20_serie.iloc[-1]) >= float(mm20_serie.iloc[-4])
                         if len(mm20_serie) >= 4 else True)
        estructura_fuerte = estructura_base_ok and mm20_pendiente

        # Determinar validez según tipo
        if es_pullback_profundo:
            retroceso_ok = True
            tipo_pullback = "profundo"
            motivos.append({
                "ok": True,
                "texto": f"Pullback profundo {retroceso_pct:.2f}% (5-15%) — válido siempre"
            })
        elif es_pullback_superficial:
            # Superficial necesita estructura fuerte
            retroceso_ok = estructura_fuerte
            tipo_pullback = "superficial"
            if estructura_fuerte:
                motivos.append({
                    "ok": True,
                    "texto": f"Pullback superficial {retroceso_pct:.2f}% (3-5%) — válido con estructura fuerte ✓"
                })
            else:
                motivos.append({
                    "ok": False,
                    "texto": f"Pullback superficial {retroceso_pct:.2f}% (3-5%) — requiere estructura fuerte (precio>MM50 + MM20↗)"
                })
        else:
            # Fuera de rango
            retroceso_ok = False
            tipo_pullback = "invalido"
            if retroceso_pct < 3.0:
                motivos.append({
                    "ok": False,
                    "texto": f"Retroceso {retroceso_pct:.2f}% insuficiente (mínimo 3%)"
                })
            else:
                motivos.append({
                    "ok": False,
                    "texto": f"Retroceso {retroceso_pct:.2f}% demasiado profundo (máximo 15%)"
                })

        # ══════════════════════════════════════════════════
        # 3️⃣  RSI PULLBACK SANO  (38–57)
        # No queremos sobreventa sino retroceso ordenado.
        # Zona ideal: 38–57. Mejor si el RSI está rebotando.
        # ══════════════════════════════════════════════════
        rsi_zona_ok = 38 <= rsi_val <= 57

        # Detectar si el RSI lleva 3 días subiendo (rebote activo)
        rsi_serie   = df["RSI"].dropna()
        rsi_rebotando = False
        if len(rsi_serie) >= 4:
            rsi_rebotando = (
                float(rsi_serie.iloc[-1]) > float(rsi_serie.iloc[-2]) > float(rsi_serie.iloc[-4])
            )

        rsi_ok = rsi_zona_ok
        if rsi_zona_ok and rsi_rebotando:
            rsi_texto = f"RSI {rsi_val:.1f} ↗ rebotando (zona óptima)"
        elif rsi_zona_ok:
            rsi_texto = f"RSI {rsi_val:.1f} (zona pullback 38–57)"
        elif rsi_val < 38:
            rsi_texto = f"RSI {rsi_val:.1f} (sobreventa — evitar entrada)"
        else:
            rsi_texto = f"RSI {rsi_val:.1f} (momentum alto — no es pullback)"

        motivos.append({
            "ok":           rsi_ok,
            "texto":        rsi_texto,
            "rsi_rebotando": rsi_rebotando,
        })

        # ══════════════════════════════════════════════════
        # 4️⃣  SOPORTE CERCANO  (2% – 8%)
        # ══════════════════════════════════════════════════
        # CORRECCIÓN LOOKAHEAD: Excluye el precio actual
        minimo_30          = f(df["Low"].iloc[:-1].tail(30).min())
        dist_soporte_pct   = ((precio_actual - minimo_30) / precio_actual) * 100
        soporte_ok         = 2.0 <= dist_soporte_pct <= 8.0

        motivos.append({
            "ok":    soporte_ok,
            "texto": f"Soporte cercano {dist_soporte_pct:.2f}% (2–8%)"
        })

        # ══════════════════════════════════════════════════
        # 5️⃣  PATRÓN DE VELAS DE GIRO ALCISTA
        #     Martillo, Envolvente alcista, Estrella mañana,
        #     Piercing Line, Harami alcista → confirma que
        #     los compradores están entrando en la zona de soporte
        # ══════════════════════════════════════════════════
        # Patrones alta fiabilidad (1.5 pts): señal fuerte de reversión
        PATRONES_ALTA = {"Martillo", "Envolvente Alcista", "Estrella de Mañana", "Piercing Line", "Tweezer Bottom"}
        # Patrones media fiabilidad (1.0 pts): señal moderada
        PATRONES_MEDIA = {"Harami Alcista", "Doji", "Harami"}

        vela_ok       = False
        vela_nombre   = ""
        vela_peso     = 0.0
        try:
            patrones_recientes = detectar_patrones_velas(df, ultimas_n=5)
            for pat in patrones_recientes:
                if pat.get("tipo") == "alcista":
                    nombre = pat.get("nombre", "")
                    if nombre in PATRONES_ALTA:
                        vela_ok     = True
                        vela_nombre = nombre
                        vela_peso   = 1.5
                        break
                    if nombre in PATRONES_MEDIA and not vela_ok:
                        vela_ok     = True
                        vela_nombre = nombre
                        vela_peso   = 1.0
        except Exception as _e:
            logger.debug(f'cálculo ignorado: {_e}')  # no penaliza si falla la detección

        motivos.append({
            "ok":        vela_ok,
            "texto":     f"Vela de giro: {vela_nombre} ({'alta' if vela_peso==1.5 else 'media'} fiabilidad)" if vela_ok else "Sin patrón de giro alcista",
            "vela_peso": vela_peso,
        })

        # ══════════════════════════════════════════════════
        # 6️⃣  ESTRUCTURA ALCISTA
        #     Antes: precio > MM20 > MM50  (demasiado estricto:
        #            el precio normalmente rompe MM20 en el retroceso)
        #     Ahora: precio > MM50  +  MM20 con pendiente positiva
        #            Permite capturar pullbacks buenos sin exigir
        #            que el precio ya haya recuperado MM20.
        # ══════════════════════════════════════════════════
        estructura_base_ok = precio_actual > mm50_val

        # Pendiente MM20: la media de hoy debe ser >= media de hace 3 velas
        mm20_serie      = df["MM20"].dropna()
        mm20_pendiente  = (float(mm20_serie.iloc[-1]) >= float(mm20_serie.iloc[-4])
                           if len(mm20_serie) >= 4 else True)

        estructura_ok = estructura_base_ok and mm20_pendiente

        motivos.append({
            "ok":    estructura_ok,
            "texto": (
                f"Precio > MM50 ({precio_actual:.2f} > {mm50_val:.2f}) "
                f"+ MM20 {'↗' if mm20_pendiente else '↘'} pendiente"
            )
        })

        # ══════════════════════════════════════════════════
        # SCORE PONDERADO — OBLIGATORIOS + OPCIONALES
        #
        # OBLIGATORIOS: si falla uno → descartado inmediatamente
        #   · Tendencia macro (MM200)   (sin tendencia no hay pullback)
        #   · Retroceso 3–15% (dual)    (define el setup)
        #
        # OPCIONALES: suman puntos al score (máx 10.5)
        #   Criterio          Peso
        #   Tendencia fuerte  2.0   ← MM50>MM200 + pendiente fuerte
        #   RSI pullback sano 1.5   (+0.5 bonus si rebotando)
        #   Soporte cercano   2.5   ← zona de entrada concreta
        #   Estructura>MM50   3.5   ← reducido para menos dependencia
        #   Vela giro         1.0-1.5 ← confirmación
        #   ──────────────── ─────
        #   TOTAL MÁX        10.5-11.0
        #   UMBRAL OPERAR     6.0 (LATERAL), 6.5 (ALCISTA)
        #
        # MEJORA V2.2: Menos dependencia de estructura única
        # Ahora puedes llegar a 6.0 con múltiples caminos:
        # - Tendencia (2.0) + Soporte (2.5) + RSI (2.0) = 6.5 ✓
        # - Estructura (3.5) + Soporte (2.5) = 6.0 ✓
        # - Estructura (3.5) + RSI (2.0) + Vela (1.5) = 7.0 ✓
        # ══════════════════════════════════════════════════

        # Evaluar tendencia fuerte (bonus adicional)
        tendencia_fuerte = False
        if mm50_val > mm200_val:
            pendiente_mm50 = (float(mm50_val) - float(df["MM50"].iloc[-10])) / float(df["MM50"].iloc[-10]) if len(df) >= 10 else 0
            tendencia_fuerte = pendiente_mm50 > 0.02  # >2% pendiente en 10 días

        # — Score parcial (para contexto en NO OPERAR aunque fallen obligatorios)
        bonus_rsi    = 0.5 if any(m.get("rsi_rebotando") for m in motivos) else 0.0
        vela_peso_real = next((m.get("vela_peso", 0.0) for m in motivos if "vela_peso" in m), 0.0)
        PESOS_OPC = [
            ("tendencia_fuerte", tendencia_fuerte, 2.0),
            ("rsi",        rsi_ok,        1.5),
            ("soporte",    soporte_ok,    2.5),
            ("vela",       vela_ok,       vela_peso_real),
            ("estructura", estructura_ok, 3.5),
        ]
        score_parcial_raw = sum(peso for _, ok, peso in PESOS_OPC if ok) + bonus_rsi

        # Normalizar a escala 0-10 (máximo posible ~11.5)
        SCORE_MAX = 11.5
        score_parcial = min(10.0, (score_parcial_raw / SCORE_MAX) * 10.0)

        # — Obligatorios
        if not tendencia_ok:
            return respuesta_invalida(
                ticker, TIPO, "Sin tendencia alcista macro",
                motivos, variacion_1d, precio_actual, score_parcial
            )
        if not retroceso_ok:
            if tipo_pullback == "superficial":
                motivo = f"Pullback superficial {retroceso_pct:.1f}% sin estructura fuerte — requiere precio>MM50 + MM20↗"
            else:
                motivo = f"Retroceso fuera de rango ({retroceso_pct:.1f}%) — esperado 3–15%"
            return respuesta_invalida(
                ticker, TIPO, motivo,
                motivos, variacion_1d, precio_actual, score_parcial
            )

        SCORE_MINIMO = 5.5
        setup_score  = score_parcial
        valido       = setup_score >= SCORE_MINIMO

        if not valido:
            return respuesta_invalida(
                ticker, TIPO,
                f"Score insuficiente ({setup_score:.1f}/10 — mínimo {SCORE_MINIMO})",
                motivos, variacion_1d, precio_actual, score_parcial
            )

        # ══════════════════════════════════════════════════
        # PLAN DE TRADING
        # ══════════════════════════════════════════════════
        #
        # STOP: mínimo de las últimas 5 velas del pullback
        #   (más preciso que mínimo 30d — captura el suelo real del retroceso)
        #   Buffer: × 0.98 (-2%) para evitar stop-hunts
        #   Validación ATR: si stop queda a más de 1.5× ATR del precio
        #   el setup está sobreextendido y se descarta
        #
        # TRIGGER DE ENTRADA (orden en broker):
        #   Principal  → Buy Stop al máximo de la vela de giro + 0.2%
        #   Alternativa → si no hay vela de giro clara: cierre > MM20
        #   Ambas evitan entrar antes de confirmación real
        #
        # CORRECCIÓN LOOKAHEAD: Excluye el precio actual
        minimo_5v   = f(df["Low"].iloc[:-1].tail(5).min())
        minimo_stop = min(minimo_5v, minimo_30)   # el más bajo entre 5 velas y soporte 30d
        stop        = round(minimo_stop * 0.98, 2)

        # Entrada: precio actual de cierre
        # (el trigger Buy Stop al máximo de la vela de giro + 0.2% es para
        #  operativa real en broker; en backtest y análisis usamos precio actual)
        entrada = precio_actual

        riesgo_unitario = entrada - stop
        riesgo_pct_op   = (riesgo_unitario / entrada) * 100 if entrada > 0 else 0

        # Validación ATR: stop no puede estar a más de 3× ATR del precio
        # (umbral ampliado para no filtrar setups válidos con ATR variable)
        if atr_val > 0 and (entrada - stop) > 3.0 * atr_val:
            motivos.append({
                "ok":    False,
                "texto": f"Stop sobreextendido ({entrada - stop:.2f}€ > 3× ATR {atr_val:.2f}€)"
            })
            return respuesta_invalida(
                ticker, TIPO,
                f"Stop a {entrada - stop:.2f}€ supera 3× ATR ({atr_val:.2f}€) — setup sobreextendido",
                motivos, variacion_1d, precio_actual
            )

        # Stop máximo 10% — por encima el tamaño de posición no es operable
        STOP_MAX_PCT = 10.0
        if riesgo_pct_op > STOP_MAX_PCT:
            motivos.append({
                "ok":    False,
                "texto": f"Stop demasiado amplio ({riesgo_pct_op:.1f}% > {STOP_MAX_PCT}%)"
            })
            return respuesta_invalida(
                ticker, TIPO,
                f"Stop {riesgo_pct_op:.1f}% supera el máximo permitido ({STOP_MAX_PCT}%)",
                motivos, variacion_1d, precio_actual
            )

        objetivo = calcular_objetivo(
            entrada=entrada,
            stop=stop,
            atr=atr_val,
            setup_score=setup_score,
        )
        rr = calcular_rr(entrada, stop, objetivo)

        return respuesta_valida(
            ticker=ticker,
            tipo=TIPO,
            entrada=entrada,
            stop=stop,
            objetivo=objetivo,
            rr=rr,
            setup_score=round(setup_score, 1),
            motivos=motivos,
            variacion_1d=variacion_1d,
            precio_actual=precio_actual,
            riesgo_pct=round(riesgo_pct_op, 2),
            beneficio_pct=round(((objetivo - entrada) / entrada) * 100, 2) if objetivo else 0,
            retroceso_pct=round(retroceso_pct, 2),
            dist_soporte_pct=round(dist_soporte_pct, 2),
            soporte_nivel=round(minimo_30, 2),
            rsi=round(rsi_val, 1),
            atr=round(atr_val, 2),
            mm20=round(mm20_val, 2),
            mm50=round(mm50_val, 2),
            mm200=round(mm200_val, 2) if mm200_val else None,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
            vela_ok=vela_ok,
            vela_nombre=vela_nombre,
            contexto_patron=_evaluar_contexto_patron(soporte_ok, rsi_zona_ok, estructura_ok),
        )
