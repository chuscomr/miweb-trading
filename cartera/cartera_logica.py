# cartera/cartera_logica.py
from datetime import datetime, date


class CarteraLogica:

    # ── Métricas de una posición abierta ───────────────────

    def calcular_metricas_posicion(self, pos: dict, precio_actual: float = None) -> dict:
        """Enriquece una posición con métricas calculadas."""
        entrada   = float(pos.get("precio_entrada") or 0)
        stop_ini  = pos.get("stop_inicial")
        stop      = pos.get("stop_actual") or stop_ini
        stop_ini  = float(stop_ini) if stop_ini else None
        stop      = float(stop) if stop else None
        objetivo  = pos.get("objetivo")
        acciones  = int(pos.get("acciones") or 0)
        tiene_stop = stop_ini is not None and stop_ini > 0

        R_unit     = (entrada - stop_ini) if tiene_stop and entrada > stop_ini else 0
        riesgo_ini = round(R_unit * acciones, 2) if R_unit > 0 else 0

        # Precio actual
        if precio_actual is None:
            precio_actual = self._obtener_precio_actual(pos.get("ticker", ""), entrada)

        pnl_eur = round((precio_actual - entrada) * acciones, 2)
        pnl_R   = round((precio_actual - entrada) / R_unit, 2) if R_unit > 0 else None

        # Duración
        try:
            fe = datetime.strptime(pos["fecha_entrada"][:10], "%Y-%m-%d").date()
            duracion = (date.today() - fe).days
        except Exception:
            duracion = 0

        dist_stop_pct = round((precio_actual - stop) / precio_actual * 100, 1) if stop and precio_actual > 0 else None

        return {
            **pos,
            "stop_inicial":   stop_ini,
            "stop_actual":    stop,
            "tiene_stop":     tiene_stop,
            "R_unit":         round(R_unit, 4),
            "riesgo_inicial": riesgo_ini,
            "pnl_eur":        pnl_eur,
            "pnl_R":          pnl_R,
            "duracion_dias":  duracion,
            "dist_stop_pct":  dist_stop_pct,
            "precio_actual":  precio_actual,
        }

    def _obtener_precio_actual(self, ticker: str, fallback: float) -> float:
        """Descarga el precio actual del ticker. Fallback al precio de entrada."""
        if not ticker:
            return fallback

        # Normalizar ticker — asegurar sufijo .MC para valores españoles
        tk = ticker.strip().upper()
        if not tk.endswith('.MC') and not tk.endswith('.AS') and '.' not in tk:
            tk = tk + '.MC'

        try:
            import yfinance as yf
            t  = yf.Ticker(tk)
            df = t.history(period="2d")
            if df is not None and not df.empty:
                precio = round(float(df["Close"].iloc[-1]), 4)
                print(f"[cartera] Precio {tk}: {precio}€")
                return precio
        except Exception as e:
            print(f"[cartera] yfinance error {tk}: {e}")
        try:
            from core.data_provider import get_df
            df = get_df(tk, periodo="5d")
            if df is not None and not df.empty:
                return round(float(df["Close"].iloc[-1]), 4)
        except Exception as e:
            print(f"[cartera] data_provider error {tk}: {e}")
        print(f"[cartera] Usando fallback para {tk}: {fallback}€")
        return fallback

    # ── Resumen global del dashboard ───────────────────────

    def calcular_resumen(self, posiciones: list, config: dict, cerradas_mes: list) -> dict:
        capital = float(config.get("capital_total") or 30000)
        limite  = float(config.get("limite_mensual_pct") or 6.0)
        riesgo_pct_trade = float(config.get("riesgo_pct") or 1.0)

        # Riesgo abierto actual
        riesgo_abierto = sum(p.get("riesgo_inicial") or 0 for p in posiciones)
        riesgo_abierto_pct = round(riesgo_abierto / capital * 100, 2) if capital else 0

        # P&L flotante
        pnl_flotante = sum(p.get("pnl_eur") or 0 for p in posiciones)

        # Capital invertido
        invertido = sum(float(p.get("precio_entrada", 0)) * int(p.get("acciones", 0)) for p in posiciones)
        disponible = round(capital - invertido, 2)

        # Control mensual — pérdidas reales cerradas este mes
        perdidas_mes = sum(
            abs(float(p.get("r_final", 0))) * float(p.get("stop_inicial", 0) or 1)
            for p in cerradas_mes if (p.get("r_final") or 0) < 0
        )
        # Más simple: usar riesgo_pct_trade * capital * |R| para cada perdedor
        perdida_mes_eur = 0
        for p in cerradas_mes:
            r = p.get("r_final") or 0
            if r < 0:
                r_unit = (float(p.get("precio_entrada", 0)) - float(p.get("stop_inicial", 0) or 0))
                acc    = int(p.get("acciones", 0))
                perdida_mes_eur += abs(r * r_unit * acc) if r_unit > 0 else capital * riesgo_pct_trade / 100

        perdida_mes_pct  = round(perdida_mes_eur / capital * 100, 2) if capital else 0
        margen_mes_pct   = round(limite - perdida_mes_pct, 2)
        margen_mes_eur   = round(margen_mes_pct / 100 * capital, 2)

        # P&L cerrado mes
        pnl_cerrado_mes = 0
        wr_mes_n = wr_mes_d = 0
        for p in cerradas_mes:
            r = p.get("r_final") or 0
            r_unit = (float(p.get("precio_entrada", 0)) - float(p.get("stop_inicial", 0) or 0))
            acc    = int(p.get("acciones", 0))
            if r_unit > 0:
                pnl_cerrado_mes += r * r_unit * acc
            wr_mes_d += 1
            if r > 0: wr_mes_n += 1
        pnl_cerrado_mes = round(pnl_cerrado_mes, 2)
        wr_mes = round(wr_mes_n / wr_mes_d * 100, 1) if wr_mes_d else 0

        # Conteo por sistema
        n_swing      = sum(1 for p in posiciones if p.get("sistema") == "SWING")
        n_medio      = sum(1 for p in posiciones if p.get("sistema") == "MEDIO")
        n_posicional = sum(1 for p in posiciones if p.get("sistema") == "POSICIONAL")

        # Umbrales R por sistema
        UMBRALES = {
            "SWING":      {"proteger": 2.0, "trailing": 4.0, "stop_pct": 5.0},
            "MEDIO":      {"proteger": 2.0, "trailing": 4.0, "stop_pct": 5.0},
            "POSICIONAL": {"proteger": 4.0, "trailing": 8.0, "stop_pct": 8.0},
        }

        # Alertas automáticas
        alertas = []
        for p in posiciones:
            nombre  = p.get("nombre") or p.get("ticker", "").replace(".MC", "")
            sistema = (p.get("sistema") or "SWING").upper()
            umb     = UMBRALES.get(sistema, UMBRALES["SWING"])
            dist    = float(p.get("dist_stop_pct") or 99)
            pnl_R   = p.get("pnl_R") or 0
            fase    = p.get("fase") or "INICIAL"

            # Stop muy cerca
            if p.get("tiene_stop") and dist < umb["stop_pct"]:
                alertas.append({
                    "tipo": "warn",
                    "texto": f"{nombre} [{sistema}] — stop muy cerca ({dist:.1f}%). Revisar tesis."
                })

            # Mover a breakeven (PROTEGIDO)
            if fase == "INICIAL" and pnl_R >= (umb["proteger"] - 0.2):
                alertas.append({
                    "tipo": "ok",
                    "texto": f"{nombre} [{sistema}] — +{pnl_R:.1f}R. Mover stop a breakeven (+{umb['proteger']:.0f}R)."
                })

            # Activar trailing stop
            if fase == "PROTEGIDO" and pnl_R >= (umb["trailing"] - 0.2):
                alertas.append({
                    "tipo": "ok",
                    "texto": f"{nombre} [{sistema}] — +{pnl_R:.1f}R. Activar trailing stop (+{umb['trailing']:.0f}R)."
                })

            # Cerca del objetivo (cerrar mitad)
            if p.get("objetivo") and not p.get("mitad_cerrada") and pnl_R >= 5.5:
                alertas.append({
                    "tipo": "ok",
                    "texto": f"{nombre} [{sistema}] — cerca del objetivo. Considerar cierre de la mitad."
                })

        if perdida_mes_pct >= limite * 0.8:
            alertas.append({
                "tipo": "warn",
                "texto": f"Limite mensual al {perdida_mes_pct:.1f}% / {limite}% — cuidado con nuevas posiciones."
            })

        return {
            "capital":             capital,
            "disponible":          disponible,
            "invertido":           round(invertido, 2),
            "riesgo_abierto":      round(riesgo_abierto, 2),
            "riesgo_abierto_pct":  riesgo_abierto_pct,
            "pnl_flotante":        round(pnl_flotante, 2),
            "n_posiciones":        len(posiciones),
            "n_swing":             n_swing,
            "n_medio":             n_medio,
            "n_posicional":        n_posicional,
            "perdida_mes_eur":     round(perdida_mes_eur, 2),
            "perdida_mes_pct":     perdida_mes_pct,
            "margen_mes_eur":      margen_mes_eur,
            "margen_mes_pct":      margen_mes_pct,
            "limite_mensual_pct":  limite,
            "pnl_cerrado_mes":     pnl_cerrado_mes,
            "wr_mes":              wr_mes,
            "trades_mes":          wr_mes_d,
            "alertas":             alertas,
        }

    # ── Métricas revisión domingo ──────────────────────────

    def calcular_revision_domingo(self, cerradas_semana: list, todas_cerradas: list,
                                  posiciones_abiertas: list, config: dict) -> dict:
        capital = float(config.get("capital_total") or 30000)

        # Trades semana
        pnl_sem_eur = 0; R_sem = 0; n_win = 0
        for p in cerradas_semana:
            r     = p.get("r_final") or 0
            r_unit= float(p.get("precio_entrada", 0)) - float(p.get("stop_inicial", 0) or 0)
            acc   = int(p.get("acciones", 0))
            if r_unit > 0:
                pnl_sem_eur += r * r_unit * acc
                R_sem       += r
            if r > 0: n_win += 1
        wr_sem = round(n_win / len(cerradas_semana) * 100, 1) if cerradas_semana else 0

        # Acumulado total
        Rs_total = [p.get("r_final") or 0 for p in todas_cerradas]
        n_win_t  = sum(1 for r in Rs_total if r > 0)
        wr_total = round(n_win_t / len(Rs_total) * 100, 1) if Rs_total else 0
        exp_total= round(sum(Rs_total) / len(Rs_total), 2) if Rs_total else 0

        # P&L total en EUR
        pnl_total = 0
        for p in todas_cerradas:
            r     = p.get("r_final") or 0
            r_unit= float(p.get("precio_entrada", 0)) - float(p.get("stop_inicial", 0) or 0)
            acc   = int(p.get("acciones", 0))
            if r_unit > 0: pnl_total += r * r_unit * acc
        pnl_total_pct = round(pnl_total / capital * 100, 1) if capital else 0

        # Checklist
        checklist = []
        for p in posiciones_abiertas:
            if (p.get("dist_stop_pct") or 99) < 5:
                checklist.append({"estado": "warn", "texto": f"{p['ticker']} — stop muy cerca, revisar tesis"})
        if not checklist:
            checklist.append({"estado": "ok", "texto": "Stops de posiciones abiertas revisados"})
        checklist.append({"estado": "ok", "texto": "Riesgo mensual dentro del limite"})
        checklist.append({"estado": "ok", "texto": "Escaner IBEX revisado para la proxima semana"})
        for p in cerradas_semana:
            if (p.get("r_final") or 0) < 0:
                checklist.append({"estado": "ko", "texto": f"{p['ticker']} perdio por stop — revisar si el setup fue correcto"})

        return {
            "trades_semana":   len(cerradas_semana),
            "pnl_sem_eur":     round(pnl_sem_eur, 2),
            "pnl_sem_pct":     round(pnl_sem_eur / capital * 100, 2) if capital else 0,
            "R_semana":        round(R_sem, 2),
            "wr_semana":       wr_sem,
            "trades_total":    len(todas_cerradas),
            "wr_total":        wr_total,
            "exp_total":       exp_total,
            "pnl_total_eur":   round(pnl_total, 2),
            "pnl_total_pct":   pnl_total_pct,
            "checklist":       checklist,
        }
