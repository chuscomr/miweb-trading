"""
═══════════════════════════════════════════════════════════════
ESTRATEGIA: BREAKOUT (Rupturas)
Sistema Swing Trading — Estrategia de Impulsos
═══════════════════════════════════════════════════════════════

Detecta oportunidades cuando el precio rompe resistencias
y entra en nueva fase de tendencia alcista.

Filosofía: "Comprar caro para vender más caro"

Criterios (ajustados por Salva):
  1. Precio cerca del máximo 52d  (≥ -3%)
  2. Resistencia clara identificada y precio en zona  (-3% / +6%)
  3. Consolidación previa  (≥ 8 días, rango ≤ 10%)
  4. Volumen en ruptura  (1.2x IBEX · 1.1x Continuo)
  5. RSI momentum fuerte  (55 – 70)
  6. Estructura alcista  (precio ≥ MM20 · MM20 ≥ MM50)
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

from estrategias.base import EstrategiaBase
from core.indicadores import calcular_rsi, calcular_atr, atr_actual
from core.riesgo import calcular_rr, calcular_objetivo
from core.universos import es_ibex
from core.utilidades import respuesta_invalida, respuesta_valida, f

logger = logging.getLogger(__name__)

TIPO = "BREAKOUT"


class BreakoutSwing(EstrategiaBase):

    nombre        = "Breakout Swing"
    periodo_datos = "1y"
    min_velas     = 60

    # ── Implementación obligatoria ─────────────────────────

    def _evaluar_df(self, df: pd.DataFrame, ticker: str) -> dict:
        motivos = []

        # ── Indicadores base ──────────────────────────────
        # Si el df ya tiene las columnas calculadas (backtest vectorizado),
        # las reutilizamos en lugar de recalcular desde cero
        df = df.copy()
        if "MM20" not in df.columns:
            df["MM20"] = df["Close"].rolling(20).mean()
        if "MM50" not in df.columns:
            df["MM50"] = df["Close"].rolling(50).mean()
        if "ATR" not in df.columns:
            df["ATR"]  = calcular_atr(df, 14)
        if "RSI" not in df.columns:
            df["RSI"]  = calcular_rsi(df["Close"], 14)

        precio_actual = f(df["Close"].iloc[-1])
        rsi_val       = f(df["RSI"].iloc[-1])
        atr_val       = f(df["ATR"].iloc[-1])
        mm20_val      = f(df["MM20"].iloc[-1])
        mm50_raw      = df["MM50"].iloc[-1]
        mm50_val      = f(mm50_raw) if not pd.isna(mm50_raw) else None

        variacion_1d  = self._variacion_1d(df)

        import math
        if math.isnan(rsi_val):
            # La vela de hoy puede estar incompleta (mercado abierto)
            # Usar la última vela cerrada con RSI válido
            rsi_serie = df["RSI"].dropna()
            if len(rsi_serie) < 14:
                return respuesta_invalida(
                    ticker, TIPO, "Histórico insuficiente para calcular RSI",
                    [], variacion_1d, precio_actual
                )
            rsi_val = float(rsi_serie.iloc[-1])
        if math.isnan(atr_val):
            atr_val = float(df["ATR"].dropna().iloc[-1]) if not df["ATR"].dropna().empty else 0.0
        if math.isnan(mm20_val):
            mm20_val = float(df["MM20"].dropna().iloc[-1]) if not df["MM20"].dropna().empty else precio_actual

        # ══════════════════════════════════════════════════
        # 1️⃣  PRECIO CERCA DEL MÁXIMO 52d  (≥ -3%)
        #     52 días ≈ máximo trimestral institucional.
        #     Filtra micro-breakouts de 20d que tienen bajo winrate.
        # ══════════════════════════════════════════════════
        maximo_52         = f(df["Close"].tail(52).max())
        dist_maximo_pct   = ((precio_actual - maximo_52) / maximo_52) * 100
        precio_max_ok     = dist_maximo_pct >= -3.0

        motivos.append({
            "ok":    precio_max_ok,
            "texto": f"Precio cerca máximo 52d ({dist_maximo_pct:.2f}%)"
        })

        # ══════════════════════════════════════════════════
        # 2️⃣  RESISTENCIA PRINCIPAL  (-3% / +6%)
        # ══════════════════════════════════════════════════
        resistencias = _identificar_resistencias(df.tail(120))

        if not resistencias:
            return respuesta_invalida(
                ticker, TIPO,
                "No se detectaron resistencias claras",
                motivos, variacion_1d, precio_actual
            )

        resistencia_principal = resistencias[0]
        dist_resistencia_pct  = ((precio_actual - resistencia_principal)
                                  / resistencia_principal) * 100
        resistencia_ok = -2.0 <= dist_resistencia_pct <= 2.0

        motivos.append({
            "ok":    resistencia_ok,
            "texto": f"Distancia a resistencia ({dist_resistencia_pct:.2f}%)"
        })

        # ══════════════════════════════════════════════════
        # 3️⃣  CONSOLIDACIÓN  (≥ 8 días, rango ≤ 10%)
        # ══════════════════════════════════════════════════
        consolidacion_dias = _detectar_consolidacion(df.tail(40))
        consolidacion_ok   = consolidacion_dias >= 8

        motivos.append({
            "ok":    consolidacion_ok,
            "texto": f"Consolidación {consolidacion_dias} días"
        })

        # ── VCP: volumen decreciente durante la consolidación ──────────
        # Patrón Minervini/O'Neil: compresión de volumen → acumulación
        # → la explosión de volumen en la ruptura es más fiable
        vcp_ok = False
        if consolidacion_ok and consolidacion_dias >= 5:
            vol_consol = df["Volume"].iloc[-(consolidacion_dias + 1):-1]
            if len(vol_consol) >= 5:
                # Tendencia bajista del volumen durante la consolidación
                vol_primera_mitad = vol_consol.iloc[:len(vol_consol)//2].mean()
                vol_segunda_mitad = vol_consol.iloc[len(vol_consol)//2:].mean()
                vcp_ok = vol_segunda_mitad < vol_primera_mitad * 0.85  # al menos 15% menor
        motivos.append({
            "ok":    vcp_ok,
            "texto": f"VCP: volumen {'decreciente ✓' if vcp_ok else 'sin compresión'} en consolidación"
        })

        # ══════════════════════════════════════════════════
        # 4️⃣  VOLUMEN EN RUPTURA
        # ══════════════════════════════════════════════════
        vol_promedio_20 = f(df["Volume"].rolling(20).mean().iloc[-1])
        vol_3_velas     = f(df["Volume"].tail(3).mean())
        ratio_vol       = vol_3_velas / vol_promedio_20 if vol_promedio_20 > 0 else 0

        # Umbral diferenciado: Continuo (ticker > 4 chars) es menos líquido
        umbral_vol = 1.1 if len(ticker.replace(".MC", "")) > 4 else 1.2
        volumen_ok = ratio_vol >= umbral_vol

        motivos.append({
            "ok":    volumen_ok,
            "texto": f"Volumen ruptura {ratio_vol:.2f}x (umbral {umbral_vol}x)"
        })

        # ══════════════════════════════════════════════════
        # 5️⃣  RSI MOMENTUM  (55 – 70) — zona óptima sin sobrecompra
        # ══════════════════════════════════════════════════
        rsi_ok = 55 <= rsi_val <= 70

        motivos.append({
            "ok":    rsi_ok,
            "texto": f"RSI momentum ({rsi_val:.1f})"
        })

        # ══════════════════════════════════════════════════
        # 6️⃣  ESTRUCTURA ALCISTA
        # ══════════════════════════════════════════════════
        estructura_ok = precio_actual >= mm20_val * 0.98
        motivos.append({
            "ok":    estructura_ok,
            "texto": f"Precio ≥ MM20 ({precio_actual:.2f} vs {mm20_val:.2f})"
        })

        if mm50_val:
            estructura2_ok = mm20_val >= mm50_val * 0.98
            motivos.append({
                "ok":    estructura2_ok,
                "texto": f"MM20 ≥ MM50 ({mm20_val:.2f} vs {mm50_val:.2f})"
            })
        else:
            estructura2_ok = True

        # ══════════════════════════════════════════════════
        # SCORE PONDERADO — OBLIGATORIOS + OPCIONALES
        #
        # OBLIGATORIOS: si falla uno → descartado inmediatamente
        #   · Resistencia identificada  (sin ella no hay breakout)
        #   · RSI momentum 55–70        (zona óptima sin sobrecompra)
        #
        # OPCIONALES: suman puntos al score (máx 10)
        #   Criterio          Peso
        #   Máximo 52d        1.5
        #   Consolidación     2.0
        #   Volumen ruptura   3.5   ← el más predictivo
        #   Precio ≥ MM20     1.5
        #   MM20 ≥ MM50       1.5
        #   ──────────────── ─────
        #   TOTAL MÁX        10.0
        #   UMBRAL OPERAR     6.0
        #
        # Esto permite operar setups sin volumen perfecto si
        # el resto del setup es sólido, y rechaza setups que
        # solo cumplen 1-2 criterios opcionales aunque sean
        # perfectos en ellos.
        # ══════════════════════════════════════════════════

        # — Obligatorios
        if not resistencia_ok:
            return respuesta_invalida(
                ticker, TIPO, "Sin resistencia clara identificada",
                motivos, variacion_1d, precio_actual
            )
        if not rsi_ok:
            return respuesta_invalida(
                ticker, TIPO, f"RSI fuera de rango óptimo ({rsi_val:.1f}) — esperado 55–70",
                motivos, variacion_1d, precio_actual
            )
        if not volumen_ok:
            return respuesta_invalida(
                ticker, TIPO, f"Volumen insuficiente ({ratio_vol:.2f}x — mínimo {umbral_vol}x)",
                motivos, variacion_1d, precio_actual
            )

        # — Score sobre criterios opcionales (volumen ya validado arriba)
        # VCP añade 1.5 pts — pesos reajustados para mantener máx ~10
        PESOS_OPC = [
            ("maximo 52d",    precio_max_ok,    1.5),
            ("consolidacion", consolidacion_ok, 2.0),
            ("vcp",           vcp_ok,           1.5),  # Minervini VCP
            ("estructura",    estructura_ok,    2.5),
            ("estructura2",   estructura2_ok,   2.5),
        ]
        SCORE_MINIMO = 5.0
        setup_score  = sum(peso for _, ok, peso in PESOS_OPC if ok)
        valido       = setup_score >= SCORE_MINIMO

        if not valido:
            return respuesta_invalida(
                ticker, TIPO,
                f"Score insuficiente ({setup_score:.1f}/10 — mínimo {SCORE_MINIMO})",
                motivos, variacion_1d, precio_actual
            )

        # ══════════════════════════════════════════════════
        # PLAN DE TRADING
        # ══════════════════════════════════════════════════
        lookback_consol   = max(consolidacion_dias, 5)  # mínimo 5 velas
        min_consolidacion = f(df["Low"].tail(lookback_consol).min())
        stop    = round(min_consolidacion * 0.98, 2)
        entrada = precio_actual

        # Precio de activación (buy stop): máximo de la consolidación + 0.2%
        # El usuario coloca esta orden en su broker — solo compra si rompe de verdad
        import math
        max_consolidacion = f(df["High"].iloc[-(lookback_consol + 1):-1].max())
        if math.isnan(max_consolidacion) or max_consolidacion <= 0:
            max_consolidacion = f(df["High"].tail(5).max())
        precio_activacion = round(max_consolidacion * 1.002, 2)

        riesgo_unitario = entrada - stop
        riesgo_pct_op   = (riesgo_unitario / entrada) * 100 if entrada > 0 else 0

        # Stop inválido — usar ATR como fallback
        import math
        if stop <= 0 or stop >= entrada or math.isnan(stop):
            stop          = round(entrada - atr_val * 2, 2)
            riesgo_unitario = entrada - stop
            riesgo_pct_op   = (riesgo_unitario / entrada) * 100 if entrada > 0 else 0

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
            resistencia_rota=round(resistencia_principal, 2),
            consolidacion_dias=consolidacion_dias,
            precio_activacion=precio_activacion,
            vcp=vcp_ok,
            volumen_ruptura=round(ratio_vol, 2),
            rsi=round(rsi_val, 1),
            atr=round(atr_val, 2),
            mm20=round(mm20_val, 2),
            mm50=round(mm50_val, 2) if mm50_val else None,
            dist_maximo_pct=round(dist_maximo_pct, 2),
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )


# ─────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES PRIVADAS
# (específicas de breakout — no pertenecen a core/)
# ─────────────────────────────────────────────────────────────

def _identificar_resistencias(df: pd.DataFrame, ventana: int = 5, tolerancia: float = 2.5) -> list:
    """
    Detecta máximos locales y los agrupa en niveles de resistencia.

    Returns:
        Lista de floats (niveles) ordenada de mayor a menor.
    """
    resistencias = []

    for i in range(ventana, len(df) - ventana):
        ventana_high = df["High"].iloc[i - ventana: i + ventana + 1]
        valor = float(df["High"].iloc[i])
        if valor == float(ventana_high.max()):
            resistencias.append(valor)

    if not resistencias:
        return []

    resistencias.sort(reverse=True)
    agrupadas = []

    for r in resistencias:
        if not agrupadas:
            agrupadas.append(r)
        else:
            if all(abs(r - ex) / ex * 100 >= tolerancia for ex in agrupadas):
                agrupadas.append(r)

    return agrupadas[:5]


def _detectar_consolidacion(df: pd.DataFrame) -> int:
    """
    Devuelve el número de días de consolidación (rango ≤ 10%).
    Busca hacia atrás desde el presente.
    """
    if len(df) < 10:
        return 0

    for ventana in range(min(30, len(df)), 9, -1):
        datos  = df.tail(ventana)
        maximo = float(datos["High"].max())
        minimo = float(datos["Low"].min())
        if minimo == 0:
            continue
        if ((maximo - minimo) / minimo) * 100 <= 10:
            return ventana

    return 0
