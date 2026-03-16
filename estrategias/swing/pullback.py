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
  5. Estructura alcista  (precio > MM20 > MM50)
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

from estrategias.base import EstrategiaBase
from core.indicadores import calcular_rsi, calcular_atr
from core.riesgo import calcular_rr, calcular_objetivo
from core.utilidades import respuesta_invalida, respuesta_valida, f

logger = logging.getLogger(__name__)

TIPO = "PULLBACK"


class PullbackSwing(EstrategiaBase):

    nombre        = "Pullback Swing"
    periodo_datos = "1y"
    min_velas     = 100     # necesita MM200 → mínimo ~200, pero con 100 ya filtra basura

    # ── Implementación obligatoria ─────────────────────────

    def _evaluar_df(self, df: pd.DataFrame, ticker: str) -> dict:
        motivos = []

        # ── Indicadores base ──────────────────────────────
        df = df.copy()
        df["MM20"]  = df["Close"].rolling(20).mean()
        df["MM50"]  = df["Close"].rolling(50).mean()
        df["MM200"] = df["Close"].rolling(200).mean()
        df["ATR"]   = calcular_atr(df, 14)
        df["RSI"]   = calcular_rsi(df["Close"], 14)

        precio_actual = f(df["Close"].iloc[-1])
        rsi_val       = f(df["RSI"].iloc[-1])
        atr_val       = f(df["ATR"].iloc[-1])
        mm20_val      = f(df["MM20"].iloc[-1])
        mm50_val      = f(df["MM50"].iloc[-1])
        mm200_raw     = df["MM200"].iloc[-1]
        mm200_val     = f(mm200_raw) if not pd.isna(mm200_raw) else None

        variacion_1d = self._variacion_1d(df)

        # ══════════════════════════════════════════════════
        # 1️⃣  TENDENCIA ALCISTA MACRO  (precio > MM200 × 0.95)
        # ══════════════════════════════════════════════════
        if mm200_val:
            tendencia_ok = precio_actual > mm200_val * 0.95
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"Precio vs MM200 ({precio_actual:.2f}€ vs {mm200_val:.2f}€)"
            })
        else:
            # Sin MM200 (< 200 velas): criterio suavizado con MM50
            tendencia_ok = precio_actual > mm50_val * 0.95
            motivos.append({
                "ok":    tendencia_ok,
                "texto": f"MM200 no disponible — Precio vs MM50 ({precio_actual:.2f}€ vs {mm50_val:.2f}€)"
            })

        # ══════════════════════════════════════════════════
        # 2️⃣  RETROCESO DESDE MÁXIMO  (5% – 20%)
        # ══════════════════════════════════════════════════
        maximo_60    = f(df["Close"].tail(60).max())
        retroceso_pct = ((maximo_60 - precio_actual) / maximo_60) * 100
        retroceso_ok  = 5.0 <= retroceso_pct <= 20.0

        motivos.append({
            "ok":    retroceso_ok,
            "texto": f"Retroceso {retroceso_pct:.2f}% desde máximo"
        })

        # ══════════════════════════════════════════════════
        # 3️⃣  RSI SOBREVENTA MODERADA  (≤ 50)
        # ══════════════════════════════════════════════════
        rsi_ok = rsi_val <= 50

        motivos.append({
            "ok":    rsi_ok,
            "texto": f"RSI {rsi_val:.1f} (≤ 50)"
        })

        # ══════════════════════════════════════════════════
        # 4️⃣  SOPORTE CERCANO  (2% – 8%)
        # ══════════════════════════════════════════════════
        minimo_30          = f(df["Low"].tail(30).min())
        dist_soporte_pct   = ((precio_actual - minimo_30) / precio_actual) * 100
        soporte_ok         = 2.0 <= dist_soporte_pct <= 8.0

        motivos.append({
            "ok":    soporte_ok,
            "texto": f"Distancia a soporte {dist_soporte_pct:.2f}%"
        })

        # ══════════════════════════════════════════════════
        # 5️⃣  ESTRUCTURA ALCISTA  (precio > MM20 > MM50)
        # ══════════════════════════════════════════════════
        estructura_ok = precio_actual > mm20_val > mm50_val

        motivos.append({
            "ok":    estructura_ok,
            "texto": f"Estructura: Precio > MM20 > MM50 "
                     f"({precio_actual:.2f} > {mm20_val:.2f} > {mm50_val:.2f})"
        })

        # ══════════════════════════════════════════════════
        # VEREDICTO FINAL
        # ══════════════════════════════════════════════════
        valido = all(m["ok"] for m in motivos)

        if not valido:
            return respuesta_invalida(
                ticker, TIPO,
                "Criterios técnicos no cumplidos",
                motivos, variacion_1d, precio_actual
            )

        # ══════════════════════════════════════════════════
        # PLAN DE TRADING
        # ══════════════════════════════════════════════════
        stop    = round(minimo_30 * 0.98, 2)
        entrada = precio_actual

        riesgo_unitario = entrada - stop
        riesgo_pct_op   = (riesgo_unitario / entrada) * 100 if entrada > 0 else 0

        objetivo = calcular_objetivo(
            entrada=entrada,
            stop=stop,
            atr=atr_val,
            setup_score=sum(m["ok"] for m in motivos),
        )
        rr = calcular_rr(entrada, stop, objetivo)

        return respuesta_valida(
            ticker=ticker,
            tipo=TIPO,
            entrada=entrada,
            stop=stop,
            objetivo=objetivo,
            rr=rr,
            setup_score=sum(m["ok"] for m in motivos),
            motivos=motivos,
            variacion_1d=variacion_1d,
            precio_actual=precio_actual,
            # Campos extra específicos de PULLBACK
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
        )
