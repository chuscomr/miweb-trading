# ==========================================================
# DATOS - SISTEMA POSICIONAL / MEDIO PLAZO
#
# Este módulo ya NO implementa el pipeline de descarga.
# Delega en core/data_provider.py — punto único de verdad.
# Se mantiene la función obtener_datos_semanales() por
# compatibilidad con el resto del código que la importa.
# ==========================================================

import yfinance as yf
import pandas as pd

try:
    from .config_posicional import *
except ImportError:
    from estrategias.posicional.config_posicional import *

try:
    from core.data_provider import get_df_semanal, get_precio_rt
except ImportError:
    from MiWeb.core.data_provider import get_df_semanal, get_precio_rt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📥 DESCARGA DE DATOS SEMANALES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_datos_semanales(ticker, periodo_años=10, validar=True):
    """
    Wrapper de compatibilidad sobre core/data_provider.get_df_semanal().

    El pipeline EODHD → FMP → yfinance y la detección de entorno
    (local/produccion) están centralizados en data_provider.
    """
    df_semanal, validacion = get_df_semanal(
        ticker,
        periodo_años=periodo_años,
        min_semanas=40,
    )

    if df_semanal is None:
        return None, validacion

    # Validación adicional de calidad (legacy)
    if validar:
        errores_extra = []
        advertencias  = validacion.get("advertencias", [])

        # Gaps extremos
        ret = df_semanal["Close"].pct_change().abs()
        gaps = ret[ret > 0.30]
        if len(gaps) > 0:
            advertencias.append(f"{len(gaps)} gaps semanales >30%")

        # Volumen cero
        vol_cero = (df_semanal["Volume"] == 0).sum()
        if vol_cero > 0:
            advertencias.append(f"{vol_cero} semanas sin volumen")

        # Histórico mínimo posicional (más exigente que medio plazo)
        if len(df_semanal) < MIN_SEMANAS_HISTORICO:
            errores_extra.append(
                f"Histórico insuficiente: {len(df_semanal)} semanas "
                f"(mínimo {MIN_SEMANAS_HISTORICO})"
            )

        validacion["advertencias"] = advertencias
        if errores_extra:
            validacion["errores"] = errores_extra
            return None, validacion

    return df_semanal, validacion


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚡ PRECIO EN TIEMPO REAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def obtener_precio_tiempo_real(ticker):
    """Wrapper de compatibilidad sobre data_provider.get_precio_rt()."""
    return get_precio_rt(ticker)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔍 FILTRADO DE UNIVERSO POSICIONAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filtrar_universo_posicional(verbose=False):
    """
    Filtra IBEX 35 para obtener valores aptos para posicional.
    Criterios: volatilidad, volumen y capitalización mínimos.
    """
    valores_aptos = []

    if verbose:
        print(f"\n🔍 Filtrando universo IBEX 35...")
        print(f"   Min volatilidad:   {MIN_VOLATILIDAD_PCT}%")
        print(f"   Min volumen:       {MIN_VOLUMEN_MEDIO_DIARIO/1_000_000:.0f}M€/día")
        print(f"   Min capitalización:{MIN_CAPITALIZACION/1_000_000_000:.0f}B€")
        print(f"   Min histórico:     {MIN_SEMANAS_HISTORICO} semanas\n")

    for ticker in IBEX_35:
        if verbose:
            print(f"   Evaluando {ticker:12s} ...", end=" ")
        try:
            df, validacion = obtener_datos_semanales(ticker, validar=True)
            if df is None:
                if verbose: print("❌ Sin datos")
                continue

            if validacion.get("errores"):
                if verbose: print(f"❌ {validacion['errores'][0]}")
                continue

            stats = validacion.get("stats", {})

            # Capitalización real
            market_cap = None
            try:
                market_cap = yf.Ticker(ticker).info.get("marketCap")
            except Exception:
                pass

            # Calcular stats si no vienen de validacion
            precio_actual       = float(df["Close"].iloc[-1])
            vol_medio_semanal   = float(df["Volume"].mean())
            vol_medio_diario    = vol_medio_semanal / 5
            valor_medio_diario  = vol_medio_diario * precio_actual
            ret                 = df["Close"].pct_change()
            volatilidad_anual   = float(ret.std() * (52 ** 0.5) * 100)

            vol_ok        = valor_medio_diario >= MIN_VOLUMEN_MEDIO_DIARIO
            volatilidad_ok = volatilidad_anual >= MIN_VOLATILIDAD_PCT
            cap_ok        = (market_cap is None) or (market_cap >= MIN_CAPITALIZACION)

            if vol_ok and volatilidad_ok and cap_ok:
                valores_aptos.append(ticker)
                if verbose:
                    cap_str = f"{market_cap/1_000_000_000:.1f}B€" if market_cap else "N/A"
                    print(f"✅ APTO (Vol: {valor_medio_diario/1_000_000:.1f}M€, "
                          f"Volatilidad: {volatilidad_anual:.1f}%, Cap: {cap_str})")
            else:
                if verbose:
                    motivos = []
                    if not vol_ok:
                        motivos.append(f"vol {valor_medio_diario/1_000_000:.1f}M€")
                    if not volatilidad_ok:
                        motivos.append(f"volatilidad {volatilidad_anual:.1f}%")
                    if not cap_ok and market_cap:
                        motivos.append(f"cap {market_cap/1_000_000_000:.1f}B€")
                    print(f"⚠️  {' | '.join(motivos)}")

        except Exception as e:
            if verbose:
                print(f"❌ Error: {str(e)[:40]}")
            continue

    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ Universo filtrado: {len(valores_aptos)} valores aptos")
        print(f"{'='*60}\n")

    return valores_aptos
