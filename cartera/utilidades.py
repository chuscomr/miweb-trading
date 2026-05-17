# core/utilidades.py
# ══════════════════════════════════════════════════════════════
# UTILIDADES COMPARTIDAS
#
# Funciones auxiliares sin dependencias internas al proyecto.
# Ningún módulo de core/ importa desde utilidades.py para
# evitar dependencias circulares.
# ══════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
from typing import Optional, Union


# ─────────────────────────────────────────────────────────────
# CONVERSIÓN SEGURA DE TIPOS
# ─────────────────────────────────────────────────────────────

def f(x) -> float:
    """
    Extrae float de cualquier tipo (numpy scalar, Series, float, int).
    Úsalo en lugar de float(x.item()) disperso por el código.
    """
    if hasattr(x, "item"):
        return x.item()
    return float(x)


def safe_float(x, default: float = 0.0) -> float:
    """Como f() pero con fallback si falla la conversión."""
    try:
        return f(x)
    except Exception:
        return default


def safe_round(x, decimales: int = 2, default: float = 0.0) -> float:
    """Redondeo seguro con fallback."""
    try:
        return round(f(x), decimales)
    except Exception:
        return default


# ─────────────────────────────────────────────────────────────
# VALIDACIÓN DE DATOS
# ─────────────────────────────────────────────────────────────

def validar_datos(
    precios: list,
    volumenes: list = None,
    fechas: list = None,
    min_velas: int = 50,
) -> dict:
    """
    Valida que los datos sean suficientes y coherentes.

    Returns:
        dict con 'valido' (bool), 'errores' (list), 'advertencias' (list)
    """
    errores = []
    advertencias = []

    if not precios:
        errores.append("No hay datos de precio")
        return {"valido": False, "errores": errores, "advertencias": advertencias}

    if len(precios) < min_velas:
        errores.append(f"Datos insuficientes: {len(precios)} velas (mínimo {min_velas})")

    if volumenes is not None and len(volumenes) != len(precios):
        advertencias.append(f"Longitudes no coinciden: precios={len(precios)}, volúmenes={len(volumenes)}")

    if fechas is not None and len(fechas) != len(precios):
        advertencias.append(f"Longitudes no coinciden: precios={len(precios)}, fechas={len(fechas)}")

    # Detectar precios anómalos
    serie = pd.Series(precios, dtype=float)
    if serie.isna().any():
        advertencias.append(f"{serie.isna().sum()} valores NaN detectados")

    variacion = serie.pct_change().abs()
    if (variacion > 0.30).any():
        advertencias.append("Detectada variación diaria >30% (posible split o dato erróneo)")

    return {
        "valido":       len(errores) == 0,
        "errores":      errores,
        "advertencias": advertencias,
    }


# ─────────────────────────────────────────────────────────────
# ALINEACIÓN DE SERIES
# ─────────────────────────────────────────────────────────────

def alinear_series(
    precios: list,
    volumenes: list,
    fechas: list,
) -> tuple:
    """
    Alinea precios, volúmenes y fechas descartando registros inválidos.

    Returns:
        (precios, volumenes, fechas) alineados, o ([], [], []) si falla.
    """
    try:
        if not precios or not volumenes or not fechas:
            return [], [], []

        df = pd.DataFrame(
            {"precio": precios, "volumen": volumenes},
            index=pd.DatetimeIndex(fechas)
        )
        df = df[~df.index.duplicated(keep="last")]
        df = df.dropna()
        df = df[(df["precio"] > 0) & (df["volumen"] > 0)]

        # Filtrar gaps extremos
        df = df[df["precio"].pct_change().abs().lt(0.30) | df["precio"].pct_change().isna()]
        df = df.sort_index()

        return (
            df["precio"].tolist(),
            df["volumen"].tolist(),
            df.index.to_pydatetime().tolist(),
        )
    except Exception as e:
        return [], [], []


# ─────────────────────────────────────────────────────────────
# RESPUESTAS ESTÁNDAR DE SEÑAL
# ─────────────────────────────────────────────────────────────

def respuesta_invalida(
    ticker: str,
    tipo: str,
    motivo: str,
    motivos_extra: list = None,
    variacion_1d: float = 0,
    precio_actual: float = 0,
    score_parcial: float = 0,
) -> dict:
    """
    Construye respuesta de señal inválida con estructura estándar.
    Utilidad compartida para construir respuestas estándar de estrategia.

    Args:
        ticker:       Ticker del valor
        tipo:         "BREAKOUT" | "PULLBACK" | "SWING" | etc.
        motivo:       Texto del motivo de invalidación
        motivos_extra: Lista de motivos previos (se añade el motivo final)
        variacion_1d: Variación del día en %
        precio_actual: Último precio
        score_parcial: Score acumulado hasta el punto de fallo (para contexto)

    Returns:
        dict estándar de señal.
    """
    motivos = list(motivos_extra or [])
    motivos.append({"ok": False, "texto": f"❌ {motivo}"})

    return {
        "valido":         False,
        "ticker":         ticker,
        "tipo":           tipo,
        "variacion_1d":   round(variacion_1d, 2),
        "precio_actual":  round(precio_actual, 2),
        "entrada":        0,
        "stop":           0,
        "objetivo":       0,
        "rr":             0,
        "setup_score":    round(score_parcial, 1),
        "motivo_bloqueo": motivo,   # motivo del filtro obligatorio que falló
        "motivos":        motivos,
    }


def respuesta_valida(
    ticker: str,
    tipo: str,
    entrada: float,
    stop: float,
    objetivo: float,
    rr: float,
    setup_score: int,
    motivos: list,
    variacion_1d: float = 0,
    precio_actual: float = 0,
    **extra,
) -> dict:
    """
    Construye respuesta de señal válida con estructura estándar.

    Returns:
        dict estándar de señal.
    """
    base = {
        "valido":       True,
        "ticker":       ticker,
        "tipo":         tipo,
        "variacion_1d": round(variacion_1d, 2),
        "precio_actual": round(precio_actual, 2),
        "entrada":      round(entrada, 2),
        "stop":         round(stop, 2),
        "objetivo":     round(objetivo, 2),
        "rr":           rr,
        "setup_score":  setup_score,
        "motivos":      motivos,
    }
    base.update(extra)
    return base


# ─────────────────────────────────────────────────────────────
# FORMATEO
# ─────────────────────────────────────────────────────────────

def formatear_precio(precio: Optional[float], decimales: int = 2) -> str:
    """Formatea un precio como string con símbolo €."""
    if precio is None:
        return "—"
    return f"{precio:,.{decimales}f} €"


def formatear_pct(valor: Optional[float], decimales: int = 2) -> str:
    """Formatea un porcentaje."""
    if valor is None:
        return "—"
    signo = "+" if valor >= 0 else ""
    return f"{signo}{valor:.{decimales}f}%"


# ─────────────────────────────────────────────────────────────
# FECHAS
# ─────────────────────────────────────────────────────────────

def formatear_fechas_para_json(fechas):
    """Convierte fechas a string ISO para JSON."""
    import pandas as pd
    if isinstance(fechas, pd.DatetimeIndex):
        return [f.strftime('%Y-%m-%dT%H:%M:%S') for f in fechas]
    elif isinstance(fechas, list):
        return [
            f.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(f, (datetime, pd.Timestamp)) else f
            for f in fechas
        ]
    return fechas


def obtener_rango_fechas(periodo: str):
    """Devuelve (inicio, fin) según el período solicitado."""
    from datetime import timedelta
    fin = datetime.now()
    mapa = {"1y": 365, "6m": 180, "3m": 90, "1m": 30}
    dias = mapa.get(periodo, 365)
    return fin - timedelta(days=dias), fin


# ─────────────────────────────────────────────────────────────
# SERIALIZADOR JSON
# ─────────────────────────────────────────────────────────────

def preparar_para_json(df) -> list:
    """Convierte DataFrame OHLCV+indicadores a lista de dicts JSON-safe."""
    import pandas as pd
    import numpy as np
    if df is None or df.empty:
        return []
    registros = []
    for idx, fila in df.iterrows():
        reg = {}
        for col, val in fila.items():
            if pd.isna(val) or val is None:
                reg[col] = None
            elif isinstance(val, (datetime, pd.Timestamp)):
                reg[col] = val.strftime('%Y-%m-%dT%H:%M:%S')
            elif isinstance(val, (np.integer, np.floating)):
                reg[col] = float(round(val, 4))
            elif isinstance(val, float) and (np.isinf(val) or np.isnan(val)):
                reg[col] = None
            else:
                reg[col] = val
        registros.append(reg)
    return registros


def formatear_niveles_sr(niveles: list) -> list:
    """Serializa niveles de S/R para JSON."""
    import pandas as pd
    if not niveles:
        return []
    resultado = []
    for n in niveles:
        item = {
            'precio': round(float(n['precio']), 4),
            'fuerza': float(n.get('fuerza', 1)),
            'toques': int(n.get('toques', 1)),
        }
        if 'distancia_pct' in n:
            item['distancia_pct'] = float(n['distancia_pct'])
        fecha = n.get('fecha') or n.get('fecha_mas_reciente')
        if fecha is not None:
            item['fecha'] = fecha.strftime('%Y-%m-%d') if isinstance(fecha, (datetime, pd.Timestamp)) else str(fecha)
        resultado.append(item)
    return resultado
