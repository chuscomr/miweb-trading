# cartera/cartera_logica.py
# ══════════════════════════════════════════════════════════════
# LÓGICA DE CARTERA
#
# Cálculos sobre posiciones: P&L, RR actual, distancia al stop,
# métricas de cartera completa y validaciones de formulario.
# ══════════════════════════════════════════════════════════════

import logging
from typing import Optional
from core.data_provider import get_precios
from core.universos import get_nombre

logger = logging.getLogger(__name__)


class CarteraLogica:
    """
    Lógica de negocio de la cartera.
    No accede a la BD directamente — trabaja sobre dicts de posición.
    """

    # ── Precio actual ──────────────────────────────────────

    def obtener_precio_actual(self, ticker: str, cache=None) -> Optional[float]:
        """Obtiene el último precio de cierre del ticker."""
        try:
            from core.data_provider import get_df
            # Normalizar ticker: añadir .MC si es español sin sufijo
            t = ticker.strip().upper()
            if "." not in t:
                t = t + ".MC"
            # min_velas=1: solo necesitamos el último precio, no 50 velas
            df = get_df(t, periodo="5d", cache=cache, min_velas=1)
            if df is None or df.empty:
                df = get_df(t, periodo="1mo", cache=cache, min_velas=1)
            if df is None or df.empty:
                return None
            return round(float(df["Close"].iloc[-1]), 2)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener precio de {ticker}: {e}")
            return None

    # ── Métricas de posición individual ───────────────────

    def calcular_metricas_posicion(self, pos: dict, cache=None) -> Optional[dict]:
        """
        Enriquece una posición con métricas calculadas en tiempo real.

        Args:
            pos:   dict de posición (de CarteraDB)
            cache: Cache Flask (opcional)

        Returns:
            dict con la posición + métricas, o None si falla.
        """
        try:
            ticker         = pos["ticker"]
            precio_entrada = float(pos["precio_entrada"])
            stop_loss      = float(pos["stop_loss"])
            objetivo       = float(pos["objetivo"])
            acciones       = int(pos["acciones"])

            precio_actual = self.obtener_precio_actual(ticker, cache)

            if precio_actual is None:
                return {
                    **pos,
                    "nombre":            get_nombre(ticker),
                    "precio_actual":     None,
                    "error":             "Sin datos de precio",
                    "pnl_por_accion":    0.0,
                    "pnl_total":         0.0,
                    "pnl_pct":           0.0,
                    "rr_inicial":        0.0,
                    "r_actual":          0.0,
                    "dist_stop_pct":     0.0,
                    "dist_objetivo_pct": 0.0,
                    "estado_precio":     "SIN_DATOS",
                    "capital_en_riesgo": 0.0,
                    "valor_posicion":    0.0,
                    "capital_invertido": 0.0,
                    "pnl_euros":         0.0,
                    "pnl_porcentaje":    0.0,
                    "r_alcanzado":       0.0,
                    "progreso":          0.0,
                    "direccion":         "largo",
                }

            # ── P&L ───────────────────────────────────────
            pnl_por_accion = precio_actual - precio_entrada
            pnl_total      = pnl_por_accion * acciones
            pnl_pct        = (pnl_por_accion / precio_entrada) * 100

            # ── Riesgo/Recompensa actual ───────────────────
            riesgo_inicial   = precio_entrada - stop_loss
            beneficio_potencial = objetivo - precio_entrada
            rr_inicial       = (beneficio_potencial / riesgo_inicial
                                if riesgo_inicial > 0 else 0)

            # ── Distancias ────────────────────────────────
            dist_stop_pct    = ((precio_actual - stop_loss) / precio_actual) * 100
            dist_objetivo_pct = ((objetivo - precio_actual) / precio_actual) * 100

            # ── R actual ──────────────────────────────────
            r_actual = (pnl_por_accion / riesgo_inicial
                        if riesgo_inicial > 0 else 0)

            # ── Estado ────────────────────────────────────
            if precio_actual <= stop_loss:
                estado_precio = "STOP_TOCADO"
            elif precio_actual >= objetivo:
                estado_precio = "OBJETIVO_ALCANZADO"
            elif pnl_pct > 0:
                estado_precio = "EN_GANANCIA"
            else:
                estado_precio = "EN_PERDIDA"

            # Progreso hacia objetivo (0-100%)
            rango = objetivo - precio_entrada
            progreso = round((precio_actual - precio_entrada) / rango * 100, 1) if rango > 0 else 0
            progreso = max(0, min(100, progreso))

            return {
                **pos,
                "nombre":              get_nombre(ticker),
                "precio_actual":       round(precio_actual, 2),
                "pnl_por_accion":      round(pnl_por_accion, 2),
                "pnl_total":           round(pnl_total, 2),
                "pnl_pct":             round(pnl_pct, 2),
                "rr_inicial":          round(rr_inicial, 2),
                "r_actual":            round(r_actual, 2),
                "dist_stop_pct":       round(dist_stop_pct, 2),
                "dist_objetivo_pct":   round(dist_objetivo_pct, 2),
                "estado_precio":       estado_precio,
                "capital_en_riesgo":   round(riesgo_inicial * acciones, 2),
                "valor_posicion":      round(precio_actual * acciones, 2),
                # Aliases que usa el template
                "capital_invertido":   round(precio_actual * acciones, 2),
                "pnl_euros":           round(pnl_total, 2),
                "pnl_porcentaje":      round(pnl_pct, 2),
                "r_alcanzado":         round(r_actual, 2),
                "progreso":            progreso,
                "direccion":           "largo",
            }

        except Exception as e:
            logger.error(f"❌ Error calculando métricas para {pos.get('ticker')}: {e}")
            return {**pos, "error": str(e)}

    # ── Resumen de cartera ─────────────────────────────────

    def calcular_resumen_cartera(self, posiciones_con_metricas: list) -> dict:
        """
        Agrega las métricas de todas las posiciones en un resumen global.

        Args:
            posiciones_con_metricas: lista de dicts enriquecidos

        Returns:
            dict con totales y promedios de la cartera
        """
        if not posiciones_con_metricas:
            return {
                "num_posiciones":    0,
                "pnl_total":         0,
                "pnl_porcentaje":    0,
                "riesgo_total_pct":  0,
                "capital_invertido": 0,
                "mejor_posicion":    None,
                "peor_posicion":     None,
                "total_posiciones":  0,
                "pnl_pct_medio":     0,
                "capital_en_riesgo": 0,
                "valor_total":       0,
                "en_ganancia":       0,
                "en_perdida":        0,
            }

        validas = [p for p in posiciones_con_metricas if p.get("precio_actual")]

        pnl_total        = sum(p.get("pnl_total", 0) for p in validas)
        capital_en_riesgo = sum(p.get("capital_en_riesgo", 0) for p in validas)
        valor_total      = sum(p.get("valor_posicion", 0) for p in validas)
        pnl_pcts         = [p.get("pnl_pct", 0) for p in validas]
        pnl_pct_medio    = sum(pnl_pcts) / len(pnl_pcts) if pnl_pcts else 0
        en_ganancia      = sum(1 for p in validas if p.get("pnl_total", 0) > 0)
        en_perdida       = sum(1 for p in validas if p.get("pnl_total", 0) <= 0)

        # Mejor y peor posición
        mejor = max(validas, key=lambda p: p.get("pnl_pct", 0), default=None)
        peor  = min(validas, key=lambda p: p.get("pnl_pct", 0), default=None)

        # Riesgo total como % del valor total
        riesgo_total_pct = (capital_en_riesgo / valor_total * 100) if valor_total > 0 else 0

        return {
            # Nombres que usa el template
            "num_posiciones":    len(posiciones_con_metricas),
            "pnl_total":         round(pnl_total, 2),
            "pnl_porcentaje":    round(pnl_pct_medio, 2),
            "riesgo_total_pct":  round(riesgo_total_pct, 2),
            "capital_invertido": round(valor_total, 2),
            "mejor_posicion":    mejor["ticker"] if mejor else None,
            "peor_posicion":     peor["ticker"] if peor else None,
            # Campos extra útiles
            "total_posiciones":  len(posiciones_con_metricas),
            "pnl_pct_medio":     round(pnl_pct_medio, 2),
            "capital_en_riesgo": round(capital_en_riesgo, 2),
            "valor_total":       round(valor_total, 2),
            "en_ganancia":       en_ganancia,
            "en_perdida":        en_perdida,
        }

    # ── Validaciones ──────────────────────────────────────

    def validar_nueva_posicion(
        self,
        ticker:         str,
        precio_entrada: float,
        stop_loss:      float,
        objetivo:       float,
        acciones:       int,
    ) -> list:
        """
        Valida los datos de una nueva posición.

        Returns:
            Lista de strings con errores. Lista vacía = datos válidos.
        """
        errores = []

        if not ticker:
            errores.append("El ticker es obligatorio")

        if precio_entrada <= 0:
            errores.append("El precio de entrada debe ser mayor que 0")

        if stop_loss <= 0:
            errores.append("El stop loss debe ser mayor que 0")

        if objetivo <= 0:
            errores.append("El objetivo debe ser mayor que 0")

        if acciones <= 0:
            errores.append("El número de acciones debe ser mayor que 0")

        if precio_entrada > 0 and stop_loss >= precio_entrada:
            errores.append("El stop loss debe ser menor que el precio de entrada")

        if precio_entrada > 0 and objetivo <= precio_entrada:
            errores.append("El objetivo debe ser mayor que el precio de entrada")

        if precio_entrada > 0 and stop_loss > 0:
            riesgo_pct = ((precio_entrada - stop_loss) / precio_entrada) * 100
            if riesgo_pct > 15:
                errores.append(f"Stop loss demasiado alejado ({riesgo_pct:.1f}% de riesgo, máximo 15%)")

        return errores

    def validar_edicion_posicion(
        self,
        ticker:         str,
        precio_entrada: float,
        stop_loss:      float,
        objetivo:       float,
        acciones:       int,
    ) -> list:
        """Mismas validaciones que nueva posición."""
        return self.validar_nueva_posicion(
            ticker, precio_entrada, stop_loss, objetivo, acciones
        )
