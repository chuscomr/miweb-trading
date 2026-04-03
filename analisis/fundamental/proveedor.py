# analisis/fundamental/proveedor.py
# ══════════════════════════════════════════════════════════════
# PROVEEDOR DE DATOS FUNDAMENTALES
#
# Fuente principal: yfinance (gratuito, sin API key)
# Fuente secundaria: FMP API (para datos que yfinance no tiene)
#
# La función pública obtener_datos_fundamentales() devuelve
# siempre el mismo dict estándar independientemente de la fuente.
# ══════════════════════════════════════════════════════════════

import yfinance as yf
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")


def obtener_datos_fundamentales(ticker: str, cache=None) -> dict:
    """
    Obtiene datos fundamentales de un ticker.

    Intenta yfinance primero. Si faltan campos clave,
    complementa con FMP si hay API key disponible.

    Returns:
        dict estándar con todos los campos fundamentales.
        Los campos no disponibles son None.
    """
    cache_key = f"fundamentales_{ticker}"

    # Intentar desde cache
    if cache:
        try:
            cached = cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    datos = _desde_yfinance(ticker)

    # Enriquecer con FCF, CAGR, Momentum (solo si no hubo error)
    if not datos.get("error"):
        datos = _enriquecer_con_financials(ticker, datos)

    # Complementar con FMP si hay key y faltan datos clave
    if FMP_API_KEY and _necesita_complemento(datos):
        datos = _complementar_con_fmp(ticker, datos)

    # Guardar en cache (10 minutos)
    if cache:
        try:
            cache.set(cache_key, datos, timeout=600)
        except Exception:
            pass

    return datos


# ─────────────────────────────────────────────────────────────
# YFINANCE
# ─────────────────────────────────────────────────────────────

def _desde_yfinance(ticker: str) -> dict:
    """Extrae datos fundamentales usando yfinance.Ticker.info."""
    try:
        info = yf.Ticker(ticker).info
        if not info or info.get("regularMarketPrice") is None:
            logger.warning(f"⚠️ yfinance sin datos para {ticker}")
            return _datos_vacios(ticker)

        return {
            "ticker":              ticker,
            "nombre":              info.get("longName") or info.get("shortName"),
            "sector":              info.get("sector"),
            "industria":           info.get("industry"),
            "descripcion":         info.get("longBusinessSummary"),

            # Precio
            "precio_actual":       _safe(info.get("regularMarketPrice")),
            "precio_52s_max":      _safe(info.get("fiftyTwoWeekHigh")),
            "precio_52s_min":      _safe(info.get("fiftyTwoWeekLow")),

            # Valoración
            "per":                 _safe(info.get("trailingPE")),
            "per_forward":         _safe(info.get("forwardPE")),
            "peg":                 _safe(info.get("pegRatio")),
            "precio_ventas":       _safe(info.get("priceToSalesTrailing12Months")),
            "precio_valor_libro":  _safe(info.get("priceToBook")),
            "ev_ebitda":           _safe(info.get("enterpriseToEbitda")),

            # Rentabilidad
            "roe":                 _safe_pct(info.get("returnOnEquity")),
            "roa":                 _safe_pct(info.get("returnOnAssets")),
            "margen_bruto":        _safe_pct(info.get("grossMargins")),
            "margen_operativo":    _safe_pct(info.get("operatingMargins")),
            "margen_neto":         _safe_pct(info.get("profitMargins")),

            # Crecimiento
            "crecimiento_ingresos": _safe_pct(info.get("revenueGrowth")),
            "crecimiento_bpa":      _safe_pct(info.get("earningsGrowth")),
            "bpa":                  _safe(info.get("trailingEps")),
            "bpa_forward":          _safe(info.get("forwardEps")),

            # Balance
            "deuda_equity":        _safe(info.get("debtToEquity")),
            "ratio_corriente":     _safe(info.get("currentRatio")),
            "cash_por_accion":     _safe(info.get("totalCashPerShare")),

            # Dividendo
            "dividendo_yield":     _safe_pct(info.get("dividendYield")),
            "payout_ratio":        _safe_pct(info.get("payoutRatio")),

            # Mercado
            "market_cap":          info.get("marketCap"),
            "volumen_medio":       info.get("averageVolume"),
            "beta":                _safe(info.get("beta")),

            # Analistas
            "recomendacion":       info.get("recommendationKey"),
            "precio_objetivo":     _safe(info.get("targetMeanPrice")),
            "num_analistas":       info.get("numberOfAnalystOpinions"),

            # Datos extra balance
            "deuda_total":         _safe(info.get("totalDebt")),
            "cash_total":          _safe(info.get("totalCash")),

            "fuente": "yfinance",
            "error":  None,
        }

    except Exception as e:
        logger.error(f"❌ Error yfinance fundamentales {ticker}: {e}")
        datos = _datos_vacios(ticker)
        datos["error"] = str(e)
        return datos





# ─────────────────────────────────────────────────────────────
# ENRIQUECIMIENTO CON FINANCIALS (FCF, CAGR, Momentum, Deuda Neta)
# ─────────────────────────────────────────────────────────────

def _enriquecer_con_financials(ticker: str, datos: dict) -> dict:
    """
    Calcula FCF, CAGR 3Y ingresos/beneficios, momentum fundamental
    y deuda neta a partir de los estados financieros de yfinance.
    """
    try:
        import yfinance as yf
        import numpy as np
        t = yf.Ticker(ticker)

        # ── Deuda Neta ─────────────────────────────────────────
        deuda   = datos.get("deuda_total") or 0
        efectivo = datos.get("cash_total") or 0
        if deuda or efectivo:
            datos["deuda_neta"] = round((deuda - efectivo) / 1e6, 1)  # en millones
        else:
            datos["deuda_neta"] = None

        # ── Deuda / EBITDA ─────────────────────────────────────
        try:
            income = t.financials
            if income is not None and not income.empty:
                ebitda_row = income.loc["EBITDA"] if "EBITDA" in income.index else None
                if ebitda_row is None and "Operating Income" in income.index:
                    ebitda_row = income.loc["Operating Income"]
                if ebitda_row is not None:
                    ebitda_val = float(ebitda_row.iloc[0])
                    if ebitda_val and ebitda_val != 0:
                        datos["deuda_ebitda"] = round(deuda / abs(ebitda_val), 2)
        except Exception:
            datos["deuda_ebitda"] = None

        # ── FCF (Free Cash Flow) ────────────────────────────────
        try:
            cf = t.cashflow
            if cf is not None and not cf.empty:
                # Operaciones - CapEx
                op_key  = next((k for k in cf.index if "Operating" in k and "Cash" in k), None)
                cap_key = next((k for k in cf.index if "Capital" in k and "Expenditure" in k), None)
                if op_key and cap_key:
                    ops  = cf.loc[op_key].values[:4]   # últimos 4 años
                    caps = cf.loc[cap_key].values[:4]
                    fcfs = [float(o) + float(c) for o, c in zip(ops, caps)
                            if o is not None and c is not None and
                            not (isinstance(o, float) and np.isnan(o))]
                    if fcfs:
                        positivos = sum(1 for f in fcfs if f > 0)
                        datos["fcf_positivo_anos"] = f"{positivos}/{len(fcfs)} años"
                        datos["fcf_ultimo_ano"]    = round(fcfs[0] / 1e6, 1)  # M€
        except Exception:
            datos["fcf_positivo_anos"] = None
            datos["fcf_ultimo_ano"]    = None

        # ── CAGR 3Y Ingresos y Beneficios ──────────────────────
        try:
            fin = t.financials
            if fin is not None and not fin.empty and fin.shape[1] >= 3:
                # Ingresos CAGR
                rev_key = next((k for k in fin.index if "Total Revenue" in k or "Revenue" in k), None)
                if rev_key:
                    rev = [v for v in fin.loc[rev_key].values[:4]
                           if v is not None and not (isinstance(v, float) and np.isnan(v))]
                    if len(rev) >= 3 and rev[-1] and rev[-1] != 0:
                        n = len(rev) - 1
                        cagr_ing = ((rev[0] / rev[-1]) ** (1/n) - 1) * 100
                        datos["cagr_ingresos_3y"] = round(cagr_ing, 1)
                        # Aceleración: último año vs año anterior
                        if len(rev) >= 2 and rev[1] and rev[1] != 0:
                            crec_1 = (rev[0] - rev[1]) / abs(rev[1]) * 100
                            datos["aceleracion_ingresos"] = round(crec_1, 1)

                # Beneficios CAGR
                net_key = next((k for k in fin.index if "Net Income" in k), None)
                if net_key:
                    net = [v for v in fin.loc[net_key].values[:4]
                           if v is not None and not (isinstance(v, float) and np.isnan(v))]
                    if len(net) >= 3 and net[-1] and net[-1] != 0:
                        n = len(net) - 1
                        cagr_ben = ((net[0] / net[-1]) ** (1/n) - 1) * 100
                        datos["cagr_beneficios_3y"] = round(cagr_ben, 1)
                        if len(net) >= 2 and net[1] and net[1] != 0:
                            crec_1 = (net[0] - net[1]) / abs(net[1]) * 100
                            datos["aceleracion_beneficios"] = round(crec_1, 1)
        except Exception:
            pass

        # ── Momentum Fundamental (score 0-4) ───────────────────
        mom_score = 0
        mom_detalles = []

        ac_ing = datos.get("aceleracion_ingresos")
        ac_ben = datos.get("aceleracion_beneficios")
        cagr_i = datos.get("cagr_ingresos_3y")
        cagr_b = datos.get("cagr_beneficios_3y")
        margen = datos.get("margen_neto")
        fcf    = datos.get("fcf_positivo_anos", "")

        if ac_ing is not None:
            if ac_ing > 5:  mom_score += 1; mom_detalles.append(f"Aceleración ingresos +{ac_ing:.1f}%")
            else:           mom_detalles.append(f"Ingresos {'creciendo' if ac_ing > 0 else 'cayendo'} {ac_ing:+.1f}%")
        if ac_ben is not None:
            if ac_ben > 5:  mom_score += 1; mom_detalles.append(f"Aceleración beneficios +{ac_ben:.1f}%")
            else:           mom_detalles.append(f"BPA cayendo {ac_ben:+.1f}%")
        if margen is not None:
            if margen >= 10: mom_score += 1; mom_detalles.append(f"Margen neto sólido {margen:.1f}%")
            else:            mom_detalles.append(f"Margen {'bajo' if margen < 5 else 'ajustado'} {margen:.1f}%")
        if fcf:
            partes = fcf.split("/")
            pos = int(partes[0]) if partes else 0
            tot = int(partes[1].split()[0]) if len(partes) > 1 else 1
            if pos >= tot * 0.75: mom_score += 1; mom_detalles.append(f"FCF consistente {fcf}")
            else:                 mom_detalles.append(f"FCF débil")

        nivel_mom = "FUERTE" if mom_score >= 3 else ("MODERADO" if mom_score >= 2 else "DÉBIL")
        datos["momentum_score"]     = mom_score
        datos["momentum_nivel"]     = nivel_mom
        datos["momentum_detalles"]  = mom_detalles

    except Exception as e:
        logger.warning(f"⚠️ _enriquecer_con_financials error {ticker}: {e}")

    return datos


# ─────────────────────────────────────────────────────────────
# FMP (complemento)
# ─────────────────────────────────────────────────────────────

def _complementar_con_fmp(ticker: str, datos: dict) -> dict:
    """
    Complementa campos None usando FMP API.
    Solo se llama si hay FMP_API_KEY en el entorno.
    """
    try:
        import requests
        url = (
            f"https://financialmodelingprep.com/api/v3/profile/{ticker}"
            f"?apikey={FMP_API_KEY}"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return datos

        fmp = resp.json()
        if not fmp:
            return datos

        perfil = fmp[0]

        # Solo rellenar campos que faltan
        if not datos.get("per"):
            datos["per"] = _safe(perfil.get("pe"))
        if not datos.get("sector"):
            datos["sector"] = perfil.get("sector")
        if not datos.get("beta"):
            datos["beta"] = _safe(perfil.get("beta"))

        datos["fuente"] = "yfinance+fmp"

    except Exception as e:
        logger.warning(f"⚠️ FMP complemento fallido para {ticker}: {e}")

    return datos


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _safe(val) -> Optional[float]:
    """Convierte a float o devuelve None."""
    try:
        return round(float(val), 2) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_pct(val) -> Optional[float]:
    """Convierte ratio decimal a porcentaje (0.15 → 15.0).
    Si el valor ya parece estar en % (>1.5 para yields), lo devuelve tal cual."""
    try:
        if val is None:
            return None
        v = float(val)
        # yfinance a veces devuelve dividendYield/payoutRatio ya en %
        # Si el valor es > 1.5, asumimos que ya está en porcentaje
        if abs(v) > 1.5:
            return round(v, 2)
        return round(v * 100, 2)
    except (TypeError, ValueError):
        return None


def _necesita_complemento(datos: dict) -> bool:
    """True si faltan campos clave que FMP puede proveer."""
    return any(datos.get(k) is None for k in ["per", "sector", "beta"])


def _datos_vacios(ticker: str) -> dict:
    """Dict estándar con todos los campos a None."""
    campos = [
        "nombre", "sector", "industria", "descripcion",
        "precio_actual", "precio_52s_max", "precio_52s_min",
        "per", "per_forward", "peg", "precio_ventas", "precio_valor_libro", "ev_ebitda",
        "roe", "roa", "margen_bruto", "margen_operativo", "margen_neto",
        "crecimiento_ingresos", "crecimiento_bpa", "bpa", "bpa_forward",
        "deuda_equity", "ratio_corriente", "cash_por_accion",
        "dividendo_yield", "payout_ratio",
        "market_cap", "volumen_medio", "beta",
        "recomendacion", "precio_objetivo", "num_analistas",
        "deuda_neta", "deuda_ebitda", "deuda_total", "cash_total",
        "fcf_positivo_anos", "fcf_ultimo_ano",
        "cagr_ingresos_3y", "cagr_beneficios_3y",
        "aceleracion_ingresos", "aceleracion_beneficios",
        "momentum_score", "momentum_nivel", "momentum_detalles",
    ]
    return {
        "ticker": ticker,
        **{c: None for c in campos},
        "fuente": None,
        "error":  "Sin datos",
    }
