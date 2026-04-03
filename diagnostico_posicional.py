"""
=============================================================================
DIAGNÓSTICO SISTEMA POSICIONAL — Por qué se rechazan los valores
=============================================================================
Ejecutar desde D:\\a\\MiWeb\\:
    python diagnostico_posicional.py

Muestra para cada valor del IBEX35:
  - Cuántas semanas de histórico hay
  - Qué filtro lo rechaza en la última vela disponible
  - Los valores de cada indicador
=============================================================================
"""

import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")

# ── Path para imports ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
import pandas as pd
import numpy as np

from estrategias.posicional.datos_posicional import obtener_datos_semanales
from estrategias.posicional.logica_posicional import (
    detectar_tendencia_largo_plazo,
    detectar_consolidacion,
    detectar_breakout,
    calcular_volatilidad,
)
from estrategias.posicional.config_posicional import (
    MIN_SEMANAS_HISTORICO,
    CONSOLIDACION_MIN_SEMANAS,
    CONSOLIDACION_MAX_SEMANAS,
    MIN_VOLATILIDAD_PCT,
    R_PARA_PROTEGER,
    R_PARA_TRAILING,
)

# ── Universo ───────────────────────────────────────────────────────────────
IBEX_35 = [
    "ACX.MC","ACS.MC","AENA.MC","AMS.MC","ANA.MC","ANE.MC",
    "BBVA.MC","BKT.MC","CABK.MC","CLNX.MC","COL.MC","ELE.MC",
    "ENG.MC","FCC.MC","FER.MC","GRF.MC","IAG.MC","IBE.MC",
    "IDR.MC","ITX.MC","LOG.MC","MAP.MC","MRL.MC","MTS.MC",
    "NTGY.MC","PUIG.MC","RED.MC","REP.MC","ROVI.MC","SAB.MC",
    "SAN.MC","SCYR.MC","SLR.MC","TEF.MC","UNI.MC",
]

# ── Contadores globales ────────────────────────────────────────────────────
CONTADORES = {
    "historico_insuficiente": [],
    "ibex_bajista":           [],
    "tendencia_rechazada":    [],
    "breakout_rechazado":     [],
    "volatilidad_baja":       [],
    "aprobados":              [],
    "error":                  [],
}


def separador(char="─", n=70):
    print(char * n)


def diagnosticar_ticker(ticker, df_ibex):
    """
    Evalúa el valor con los mismos filtros que el sistema posicional
    pero en la última vela disponible, con detalle de cada filtro.
    """
    try:
        time.sleep(1.2)
        df, _ = obtener_datos_semanales(ticker, periodo_años=10, validar=False)

        if df is None or df.empty:
            print(f"  ❌ Sin datos")
            CONTADORES["error"].append(ticker)
            return

        n_sem = len(df)
        print(f"  📊 {n_sem} semanas")

        if n_sem < MIN_SEMANAS_HISTORICO:
            print(f"  ⛔ RECHAZADO — Histórico insuficiente ({n_sem} < {MIN_SEMANAS_HISTORICO} sem)")
            CONTADORES["historico_insuficiente"].append(ticker)
            return

        precios   = df["Close"].values
        volumenes = df["Volume"].values if "Volume" in df.columns else None
        precio_actual = precios[-1]

        # ── FILTRO 0: IBEX ─────────────────────────────────────────────
        if df_ibex is not None and not df_ibex.empty:
            close_ibex = df_ibex["Close"]
            if len(close_ibex) >= 200:
                mm200 = float(close_ibex.rolling(200).mean().iloc[-1])
                precio_ibex = float(close_ibex.iloc[-1])
                estado_ibex = "ALCISTA" if precio_ibex > mm200 else "BAJISTA"
                print(f"  {'🟢' if estado_ibex == 'ALCISTA' else '🔴'} IBEX: {estado_ibex}  "
                      f"(precio {precio_ibex:.0f} | MM200 {mm200:.0f})")
                if estado_ibex == "BAJISTA":
                    print(f"  ⛔ RECHAZADO — IBEX bajista")
                    CONTADORES["ibex_bajista"].append(ticker)
                    return
        else:
            print(f"  ⚠️  IBEX no disponible — filtro omitido")

        # ── FILTRO 1: TENDENCIA ────────────────────────────────────────
        tend = detectar_tendencia_largo_plazo(precios, df)
        mm50  = round(tend.get("mm50", 0), 2)
        mm200 = round(tend.get("mm200", 0), 2)
        dist  = round(tend.get("distancia_mm50_pct", 0), 1)
        pend  = round(tend.get("pendiente_mm50", 0), 2)
        cumple_tend = tend.get("cumple_criterios", False)
        estado_tend = tend.get("tendencia", "?")

        icon_t = "✅" if cumple_tend else "❌"
        cond_t = tend.get("condiciones", {})
        aviso_ext = ""
        if cumple_tend and not cond_t.get("no_sobreextendido", True):
            aviso_ext = f"  ⚠️  SOBREEXTENDIDO ({dist}% sobre MM50)"
        print(f"  {icon_t} TENDENCIA: {estado_tend}  "
              f"(precio {precio_actual:.2f} | MM50 {mm50} | MM200 {mm200} | "
              f"dist {dist}% | pend {pend}){aviso_ext}")

        if not cumple_tend:
            cond = tend.get("condiciones", {})
            razones = []
            if estado_tend != "ALCISTA":
                razones.append(f"tendencia {estado_tend.lower()}")
            if not cond.get("distancia_suficiente"):
                razones.append(f"precio muy cerca de MM50 ({dist}%)")
            if not cond.get("pendiente_positiva"):
                razones.append("MM50 sin pendiente alcista")
            print(f"  ⛔ RECHAZADO — {' | '.join(razones)}")
            CONTADORES["tendencia_rechazada"].append(
                (ticker, estado_tend, dist, pend)
            )
            return

        # ── FILTRO 2: CONSOLIDACIÓN (informativo, no bloquea) ──────────
        consol_ok = False
        for lb in range(CONSOLIDACION_MIN_SEMANAS, CONSOLIDACION_MAX_SEMANAS + 1, 4):
            if len(precios) < lb:
                continue
            c = detectar_consolidacion(precios, lookback_max=lb)
            if c["en_consolidacion"]:
                consol_ok = True
                rango = round(c.get("rango_pct", 0), 1)
                sem_c = c.get("semanas_consolidacion", 0)
                print(f"  ✅ CONSOLIDACIÓN: {sem_c} sem | rango {rango}%")
                break
        if not consol_ok:
            print(f"  ⚠️  Sin consolidación reciente (no bloquea pero resta puntos)")

        # ── FILTRO 3: BREAKOUT ─────────────────────────────────────────
        bk = detectar_breakout(precios, volumenes, lookback=26)
        hay_bk   = bk["hay_breakout"]
        dist_bk  = round(bk.get("distancia_breakout_pct", 0), 2)
        vol_rat  = round(bk.get("ratio_volumen", 1), 2)

        icon_bk = "✅" if hay_bk else "❌"
        print(f"  {icon_bk} BREAKOUT: {'SÍ' if hay_bk else 'NO'}  "
              f"(dist máximos {dist_bk}% | vol ratio {vol_rat}x)")

        if not hay_bk:
            print(f"  ⛔ RECHAZADO — Sin breakout de máximos de 26 semanas")
            CONTADORES["breakout_rechazado"].append((ticker, dist_bk, vol_rat))
            return

        # ── FILTRO 4: VOLATILIDAD ──────────────────────────────────────
        vol = calcular_volatilidad(precios, periodo=52)
        vol_r = round(vol, 1) if vol else 0
        icon_v = "✅" if (not vol or vol >= MIN_VOLATILIDAD_PCT) else "❌"
        print(f"  {icon_v} VOLATILIDAD: {vol_r}%  (mínimo {MIN_VOLATILIDAD_PCT}%)")

        if vol and vol < MIN_VOLATILIDAD_PCT:
            print(f"  ⛔ RECHAZADO — Volatilidad baja")
            CONTADORES["volatilidad_baja"].append((ticker, vol_r))
            return

        # ── APROBADO ───────────────────────────────────────────────────
        print(f"  🎯 APROBADO — Señal de compra en la última vela")
        CONTADORES["aprobados"].append(ticker)

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        CONTADORES["error"].append(ticker)


def main():
    separador("=")
    print("🔍 DIAGNÓSTICO SISTEMA POSICIONAL — Filtros por valor")
    separador("=")
    print(f"Universo: {len(IBEX_35)} valores del IBEX 35")
    print(f"Fecha de análisis: última vela disponible\n")

    # ── Descargar IBEX una sola vez ───────────────────────────────────
    df_ibex = None
    print("📥 Descargando IBEX (^IBEX)...")
    try:
        time.sleep(2)
        ibex_obj = yf.Ticker("^IBEX")
        datos_ibex = ibex_obj.history(period="10y", interval="1d")
        if not datos_ibex.empty:
            if datos_ibex.index.tz is not None:
                datos_ibex.index = datos_ibex.index.tz_localize(None)
            if isinstance(datos_ibex.columns, pd.MultiIndex):
                datos_ibex.columns = datos_ibex.columns.get_level_values(0)
            df_ibex = datos_ibex
            precio_hoy = float(df_ibex["Close"].iloc[-1])
            mm200_hoy  = float(df_ibex["Close"].rolling(200).mean().iloc[-1])
            estado     = "🟢 ALCISTA" if precio_hoy > mm200_hoy else "🔴 BAJISTA"
            print(f"✅ IBEX descargado — Precio: {precio_hoy:.0f} | MM200: {mm200_hoy:.0f} | {estado}")
        else:
            print("⚠️  Sin datos de IBEX — filtro de mercado se omitirá")
    except Exception as e:
        print(f"⚠️  Error descargando IBEX ({e}) — filtro de mercado se omitirá")

    separador()
    print(f"\nAnalizando {len(IBEX_35)} valores...\n")

    # ── Analizar cada ticker ──────────────────────────────────────────
    for i, ticker in enumerate(IBEX_35):
        separador("─", 50)
        print(f"[{i+1:02d}/{len(IBEX_35)}] {ticker}")
        diagnosticar_ticker(ticker, df_ibex)
        # Pausa extra cada 8 tickers
        if (i + 1) % 8 == 0:
            print(f"\n  ⏸️  Pausa ({i+1}/{len(IBEX_35)})...\n")
            time.sleep(5)

    # ── RESUMEN FINAL ─────────────────────────────────────────────────
    separador("=")
    print("\n📊 RESUMEN — ¿Por qué se rechaza cada valor?\n")

    total = len(IBEX_35)

    print(f"  🎯 APROBADOS ({len(CONTADORES['aprobados'])}/{total}):")
    if CONTADORES["aprobados"]:
        for t in CONTADORES["aprobados"]:
            print(f"      → {t}")
    else:
        print("      (ninguno en este momento)")

    print(f"\n  🔴 IBEX BAJISTA ({len(CONTADORES['ibex_bajista'])}/{total}):")
    for t in CONTADORES["ibex_bajista"]:
        print(f"      → {t}")

    print(f"\n  📉 TENDENCIA RECHAZADA ({len(CONTADORES['tendencia_rechazada'])}/{total}):")
    for t, estado, dist, pend in CONTADORES["tendencia_rechazada"]:
        print(f"      → {t:10s}  tendencia: {estado:8s}  dist MM50: {dist:+.1f}%  pend: {pend:+.2f}")

    print(f"\n  📊 SIN BREAKOUT ({len(CONTADORES['breakout_rechazado'])}/{total}):")
    for t, dist_bk, vol_rat in CONTADORES["breakout_rechazado"]:
        print(f"      → {t:10s}  dist máximos: {dist_bk:+.1f}%  vol ratio: {vol_rat:.1f}x")

    print(f"\n  📏 VOLATILIDAD BAJA ({len(CONTADORES['volatilidad_baja'])}/{total}):")
    for t, v in CONTADORES["volatilidad_baja"]:
        print(f"      → {t:10s}  volatilidad: {v:.1f}%")

    print(f"\n  ⛔ HISTÓRICO INSUFICIENTE ({len(CONTADORES['historico_insuficiente'])}/{total}):")
    for t in CONTADORES["historico_insuficiente"]:
        print(f"      → {t}")

    print(f"\n  ❌ ERROR DESCARGA ({len(CONTADORES['error'])}/{total}):")
    for t in CONTADORES["error"]:
        print(f"      → {t}")

    # ── TABLA DE EMBUDO ───────────────────────────────────────────────
    separador("─")
    print("\n  EMBUDO DE FILTROS (cuello de botella):\n")
    filtros = [
        ("Histórico insuficiente", len(CONTADORES["historico_insuficiente"])),
        ("IBEX bajista",           len(CONTADORES["ibex_bajista"])),
        ("Tendencia rechazada",    len(CONTADORES["tendencia_rechazada"])),
        ("Sin breakout",           len(CONTADORES["breakout_rechazado"])),
        ("Volatilidad baja",       len(CONTADORES["volatilidad_baja"])),
        ("Aprobados",              len(CONTADORES["aprobados"])),
    ]
    for nombre, n in filtros:
        barra = "█" * n + "░" * (total - n)
        print(f"  {nombre:28s} {n:2d}/{total}  |{barra}|")

    separador("=")
    print(f"\nEste diagnóstico analiza la ÚLTIMA VELA disponible.")
    print(f"Para ver por qué fallaron en el backtest histórico,")
    print(f"ejecuta el backtest completo.\n")


if __name__ == "__main__":
    main()
