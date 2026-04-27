# Módulo: calcular_sentimiento_empresa(ticker, cache)
# Devuelve score -100..+100 y desglose de indicadores

def calcular_sentimiento_empresa(ticker, cache=None):
    """
    Calcula el sentimiento técnico de mercado para un ticker.
    Score: -100 (muy bajista) a +100 (muy alcista)
    """
    import sys
    sys.path.insert(0, '/home/claude/MiWeb71/MiWeb')
    
    from core.data_provider import get_df
    from core.indicadores import calcular_rsi, calcular_macd, calcular_medias
    import numpy as np

    resultado = {
        'ticker': ticker,
        'score': 0,
        'veredicto': 'NEUTRO',
        'indicadores': [],
        'error': None
    }

    try:
        df = get_df(ticker, periodo='1y', cache=cache)
        if df is None or len(df) < 50:
            resultado['error'] = 'Datos insuficientes'
            return resultado

        close = df['Close']
        precio = float(close.iloc[-1])
        
        señales = []

        # ── 1. MEDIAS MÓVILES ──────────────────────────────
        df = calcular_medias(df, [20, 50, 200])
        
        mm20  = float(df['MM20'].iloc[-1])  if 'MM20'  in df.columns and not df['MM20'].isna().iloc[-1]  else None
        mm50  = float(df['MM50'].iloc[-1])  if 'MM50'  in df.columns and not df['MM50'].isna().iloc[-1]  else None
        mm200 = float(df['MM200'].iloc[-1]) if 'MM200' in df.columns and not df['MM200'].isna().iloc[-1] else None

        if mm20:
            dist20 = (precio - mm20) / mm20 * 100
            alcista = precio > mm20
            señales.append({
                'nombre': 'MM20',
                'valor': f'{mm20:.2f}€',
                'detalle': f'Precio {"por encima" if alcista else "por debajo"} ({dist20:+.1f}%)',
                'score': min(30, max(-30, dist20 * 3)),
                'señal': '🐂' if alcista else '🐻',
                'color': '#22c55e' if alcista else '#ef4444'
            })

        if mm50:
            dist50 = (precio - mm50) / mm50 * 100
            alcista = precio > mm50
            señales.append({
                'nombre': 'MM50',
                'valor': f'{mm50:.2f}€',
                'detalle': f'Precio {"por encima" if alcista else "por debajo"} ({dist50:+.1f}%)',
                'score': min(25, max(-25, dist50 * 2.5)),
                'señal': '🐂' if alcista else '🐻',
                'color': '#22c55e' if alcista else '#ef4444'
            })

        if mm200:
            dist200 = (precio - mm200) / mm200 * 100
            alcista = precio > mm200
            señales.append({
                'nombre': 'MM200',
                'valor': f'{mm200:.2f}€',
                'detalle': f'Tendencia {"alcista" if alcista else "bajista"} LP ({dist200:+.1f}%)',
                'score': min(20, max(-20, dist200 * 2)),
                'señal': '🐂' if alcista else '🐻',
                'color': '#22c55e' if alcista else '#ef4444'
            })

        # Cruce MM20/MM50
        if mm20 and mm50:
            if mm20 > mm50:
                señales.append({'nombre': 'Cruce MM', 'valor': 'Dorado', 'detalle': 'MM20 > MM50 — impulso alcista', 'score': 15, 'señal': '🐂', 'color': '#22c55e'})
            else:
                señales.append({'nombre': 'Cruce MM', 'valor': 'Muerte', 'detalle': 'MM20 < MM50 — impulso bajista', 'score': -15, 'señal': '🐻', 'color': '#ef4444'})

        # ── 2. RSI ─────────────────────────────────────────
        rsi_serie = calcular_rsi(close, 14)
        rsi = float(rsi_serie.dropna().iloc[-1]) if not rsi_serie.dropna().empty else None

        if rsi is not None:
            if rsi >= 70:
                rsi_score, rsi_txt, rsi_sig, rsi_col = -10, f'Sobrecomprado ({rsi:.0f}) — posible corrección', '⚠️', '#f59e0b'
            elif rsi >= 55:
                rsi_score, rsi_txt, rsi_sig, rsi_col = 15, f'Momentum alcista ({rsi:.0f})', '🐂', '#22c55e'
            elif rsi >= 45:
                rsi_score, rsi_txt, rsi_sig, rsi_col = 0, f'Zona neutral ({rsi:.0f})', '➡️', '#94a3b8'
            elif rsi >= 30:
                rsi_score, rsi_txt, rsi_sig, rsi_col = -15, f'Momentum bajista ({rsi:.0f})', '🐻', '#ef4444'
            else:
                rsi_score, rsi_txt, rsi_sig, rsi_col = 5, f'Sobrevendido ({rsi:.0f}) — posible rebote', '⚠️', '#f59e0b'

            señales.append({'nombre': 'RSI (14)', 'valor': f'{rsi:.1f}', 'detalle': rsi_txt, 'score': rsi_score, 'señal': rsi_sig, 'color': rsi_col})

        # ── 3. MACD ────────────────────────────────────────
        macd_data = calcular_macd(close)
        macd_line = macd_data['macd']
        signal_line = macd_data['señal']
        hist = macd_data['histograma']

        if not macd_line.dropna().empty and not signal_line.dropna().empty:
            m = float(macd_line.dropna().iloc[-1])
            s = float(signal_line.dropna().iloc[-1])
            h = float(hist.dropna().iloc[-1]) if not hist.dropna().empty else 0
            h_prev = float(hist.dropna().iloc[-2]) if len(hist.dropna()) > 1 else h

            if m > s and h > 0:
                mc_score, mc_txt, mc_sig, mc_col = 20, f'MACD sobre señal — impulso alcista (hist: {h:+.3f})', '🐂', '#22c55e'
            elif m > s and h < 0:
                mc_score, mc_txt, mc_sig, mc_col = 8, f'MACD sobre señal pero histograma negativo', '🐂', '#86efac'
            elif m < s and h < 0:
                mc_score, mc_txt, mc_sig, mc_col = -20, f'MACD bajo señal — impulso bajista (hist: {h:+.3f})', '🐻', '#ef4444'
            else:
                mc_score, mc_txt, mc_sig, mc_col = -8, f'MACD bajo señal pero histograma positivo', '🐻', '#fca5a5'

            # Divergencia (histograma creciendo o menguando)
            tendencia_hist = '↑ acelerando' if h > h_prev else '↓ frenando'
            señales.append({'nombre': 'MACD', 'valor': f'{m:+.3f}', 'detalle': f'{mc_txt} · {tendencia_hist}', 'score': mc_score, 'señal': mc_sig, 'color': mc_col})

        # ── 4. VOLUMEN ────────────────────────────────────
        if 'Volume' in df.columns:
            vol = df['Volume']
            vol_actual = float(vol.iloc[-1])
            vol_media20 = float(vol.rolling(20).mean().iloc[-1])
            ratio = vol_actual / vol_media20 if vol_media20 > 0 else 1.0
            
            precio_sube = float(close.iloc[-1]) > float(close.iloc[-2])
            
            if ratio >= 1.5 and precio_sube:
                v_score, v_txt, v_sig, v_col = 20, f'Volumen {ratio:.1f}x sobre media — compras con convicción', '🐂', '#22c55e'
            elif ratio >= 1.5 and not precio_sube:
                v_score, v_txt, v_sig, v_col = -20, f'Volumen {ratio:.1f}x sobre media — ventas con convicción', '🐻', '#ef4444'
            elif ratio >= 1.2 and precio_sube:
                v_score, v_txt, v_sig, v_col = 10, f'Volumen elevado ({ratio:.1f}x) acompaña subida', '🐂', '#86efac'
            elif ratio >= 1.2 and not precio_sube:
                v_score, v_txt, v_sig, v_col = -10, f'Volumen elevado ({ratio:.1f}x) acompaña caída', '🐻', '#fca5a5'
            else:
                v_score, v_txt, v_sig, v_col = 0, f'Volumen normal ({ratio:.1f}x sobre media 20)', '➡️', '#94a3b8'

            señales.append({'nombre': 'Volumen', 'valor': f'{ratio:.1f}x', 'detalle': v_txt, 'score': v_score, 'señal': v_sig, 'color': v_col})

        # ── 5. RANGO 52 SEMANAS ──────────────────────────
        max52 = float(close.rolling(252).max().iloc[-1])
        min52 = float(close.rolling(252).min().iloc[-1])
        rango = max52 - min52

        if rango > 0:
            posicion = (precio - min52) / rango * 100
            dist_max = (precio - max52) / max52 * 100
            dist_min = (precio - min52) / min52 * 100

            if posicion >= 80:
                r_score, r_txt, r_sig, r_col = 20, f'En zona alta del rango anual ({posicion:.0f}%) — cerca de máximos', '🐂', '#22c55e'
            elif posicion >= 55:
                r_score, r_txt, r_sig, r_col = 10, f'Por encima del punto medio del rango ({posicion:.0f}%)', '🐂', '#86efac'
            elif posicion >= 40:
                r_score, r_txt, r_sig, r_col = 0, f'En zona central del rango anual ({posicion:.0f}%)', '➡️', '#94a3b8'
            elif posicion >= 20:
                r_score, r_txt, r_sig, r_col = -10, f'Por debajo del punto medio del rango ({posicion:.0f}%)', '🐻', '#fca5a5'
            else:
                r_score, r_txt, r_sig, r_col = -20, f'En zona baja del rango anual ({posicion:.0f}%) — cerca de mínimos', '🐻', '#ef4444'

            señales.append({
                'nombre': 'Rango 52 sem.',
                'valor': f'{posicion:.0f}%',
                'detalle': f'{r_txt} · Máx: {max52:.2f}€ ({dist_max:+.1f}%) · Mín: {min52:.2f}€',
                'score': r_score, 'señal': r_sig, 'color': r_col
            })

        # ── SCORE FINAL ───────────────────────────────────
        score_total = sum(s['score'] for s in señales)
        score_norm = max(-100, min(100, score_total))

        if score_norm >= 40:
            veredicto, emoji = 'ALCISTA', '🐂'
        elif score_norm >= 15:
            veredicto, emoji = 'LIGERAMENTE ALCISTA', '🐂'
        elif score_norm >= -15:
            veredicto, emoji = 'NEUTRO', '➡️'
        elif score_norm >= -40:
            veredicto, emoji = 'LIGERAMENTE BAJISTA', '🐻'
        else:
            veredicto, emoji = 'BAJISTA', '🐻'

        resultado.update({
            'score': round(score_norm),
            'veredicto': veredicto,
            'emoji': emoji,
            'precio': round(precio, 2),
            'indicadores': señales,
        })

    except Exception as e:
        import traceback
        resultado['error'] = str(e)
        resultado['traceback'] = traceback.format_exc()

    return resultado

if __name__ == '__main__':
    r = calcular_sentimiento_empresa('BBVA.MC')
    print(f"Score: {r['score']} — {r['veredicto']}")
    for ind in r['indicadores']:
        print(f"  {ind['señal']} {ind['nombre']}: {ind['detalle']} (score: {ind['score']:+.0f})")
