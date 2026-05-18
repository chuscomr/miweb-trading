"""
Rutas para el Sistema de Gráficos Profesional
Gráfico limpio tipo Investing.com para análisis técnico
"""
import logging

import pandas as pd
from flask import Blueprint, jsonify, render_template, request

from analisis.tecnico.soportes_resistencias import detectar_soportes_resistencias
from core.data_provider import get_df
from core.indicadores import calcular_atr, calcular_macd, calcular_rsi


logger = logging.getLogger(__name__)

grafico_pro_bp = Blueprint(
    'grafico_pro',
    __name__,
    url_prefix='/grafico-pro'
)


def calcular_fibonacci_auto(df, ventana_swing=20, min_swing_pct=5.0):
    """
    Detecta el último swing significativo y calcula niveles de Fibonacci
    
    Args:
        df: DataFrame con OHLCV
        ventana_swing: Períodos para detectar máximos/mínimos
        min_swing_pct: Mínimo % de movimiento para considerar swing válido
    
    Returns:
        dict con niveles Fibonacci o None
    """
    if len(df) < ventana_swing * 2:
        return None

    # Detectar máximos y mínimos locales en últimas N velas
    ultimas = df.tail(100)  # Analizar últimas 100 velas

    high_values = ultimas['High'].values
    low_values = ultimas['Low'].values

    # Buscar último swing alto
    max_idx = -1
    max_val = 0
    for i in range(ventana_swing, len(high_values) - ventana_swing):
        if high_values[i] == max(high_values[i-ventana_swing:i+ventana_swing]):
            max_idx = len(df) - len(ultimas) + i
            max_val = high_values[i]

    # Buscar último swing bajo
    min_idx = -1
    min_val = 0
    for i in range(ventana_swing, len(low_values) - ventana_swing):
        if low_values[i] == min(low_values[i-ventana_swing:i+ventana_swing]):
            min_idx = len(df) - len(ultimas) + i
            min_val = low_values[i]

    if max_idx == -1 or min_idx == -1:
        return None

    # Determinar dirección del swing más reciente
    if max_idx > min_idx:
        # Último swing: bajista (de high a low)
        swing_high = max_val
        swing_low = df['Low'].iloc[-1]  # Último mínimo
        swing_start_idx = max_idx
        direccion = 'bajista'
    else:
        # Último swing: alcista (de low a high)
        swing_low = min_val
        swing_high = df['High'].iloc[-1]  # Último máximo
        swing_start_idx = min_idx
        direccion = 'alcista'

    # Validar que el swing es significativo
    swing_pct = abs((swing_high - swing_low) / swing_low * 100)
    if swing_pct < min_swing_pct:
        return None

    # Calcular niveles de Fibonacci
    diff = swing_high - swing_low

    niveles = {
        '0.0': round(swing_low, 2),
        '23.6': round(swing_low + diff * 0.236, 2),
        '38.2': round(swing_low + diff * 0.382, 2),
        '50.0': round(swing_low + diff * 0.500, 2),
        '61.8': round(swing_low + diff * 0.618, 2),
        '78.6': round(swing_low + diff * 0.786, 2),
        '100.0': round(swing_high, 2)
    }

    return {
        'niveles': niveles,
        'swing_high': round(swing_high, 2),
        'swing_low': round(swing_low, 2),
        'swing_start_idx': int(swing_start_idx),
        'direccion': direccion,
        'swing_pct': round(swing_pct, 2)
    }


def calcular_pivots(df, tipo='diario'):
    """
    Calcula Pivot Points clásicos
    
    Args:
        df: DataFrame con OHLCV
        tipo: 'diario' o 'semanal'
    
    Returns:
        dict con niveles de pivots
    """
    if len(df) < 2:
        return None

    # Obtener datos del período anterior
    if tipo == 'semanal':
        # Último viernes cerrado
        df_resample = df.resample('W-FRI').agg({
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()
        if len(df_resample) < 2:
            return None
        prev = df_resample.iloc[-2]
    else:
        # Día anterior
        if len(df) < 2:
            return None
        prev = df.iloc[-2]

    H = prev['High']
    L = prev['Low']
    C = prev['Close']

    # Cálculo estándar de Pivot Points
    PP = round((H + L + C) / 3, 2)

    R1 = round(2 * PP - L, 2)
    R2 = round(PP + (H - L), 2)
    R3 = round(H + 2 * (PP - L), 2)

    S1 = round(2 * PP - H, 2)
    S2 = round(PP - (H - L), 2)
    S3 = round(L - 2 * (H - PP), 2)

    return {
        'PP': PP,
        'R1': R1,
        'R2': R2,
        'R3': R3,
        'S1': S1,
        'S2': S2,
        'S3': S3,
        'tipo': tipo
    }


@grafico_pro_bp.route('/')
@grafico_pro_bp.route('/<ticker>')
def index(ticker='SAN.MC'):
    """Página principal del gráfico profesional"""
    from core.universos import CONTINUO, IBEX35, NOMBRES_CONTINUO, NOMBRES_IBEX

    # Ordenar lista de tickers:
    # 1. ^IBEX (índice) primero
    # 2. IBEX35 ordenado alfabéticamente con nombres
    # 3. "---CONTINUO---" como separador visual
    # 4. Mercado Continuo ordenado alfabéticamente con nombres

    # Crear lista con formato "Nombre (TICKER)"
    def formatear_ticker(t, nombres_dict):
        """Formato: 'Banco Santander (SAN)' """
        ticker_corto = t.replace('.MC', '')
        nombre = nombres_dict.get(t, ticker_corto)
        return f"{nombre} ({ticker_corto})"

    ibex_index_formato = [{'value': '^IBEX', 'label': 'IBEX 35 (^IBEX)'}]

    ibex_sin_indice = [t for t in IBEX35 if t != '^IBEX']
    ibex_formateado = [
        {'value': t, 'label': formatear_ticker(t, NOMBRES_IBEX)}
        for t in sorted(ibex_sin_indice, key=lambda x: NOMBRES_IBEX.get(x, x))
    ]

    continuo_formateado = [
        {'value': t, 'label': formatear_ticker(t, NOMBRES_CONTINUO)}
        for t in sorted(CONTINUO, key=lambda x: NOMBRES_CONTINUO.get(x, x))
    ]

    separador = [{'value': '---CONTINUO---', 'label': '━━━━━ MERCADO CONTINUO ━━━━━'}]

    todos_tickers = ibex_index_formato + ibex_formateado + separador + continuo_formateado

    return render_template(
        'grafico_pro.html',
        ticker=ticker,
        tickers=todos_tickers
    )


@grafico_pro_bp.route('/api/data/<ticker>')
def get_data(ticker):
    """
    Obtener datos OHLCV del ticker
    
    Query params:
        tf: timeframe (1d, 1wk, 1mo) - default 1d
        period: período de datos (1y, 2y, 5y, max) - default 2y
    """
    try:
        from flask import current_app

        tf = request.args.get('tf', '1d')
        period = request.args.get('period', '2y')

        # Obtener cache
        cache = current_app.config.get("CACHE_INSTANCE")

        # Obtener datos diarios
        df = get_df(ticker, periodo=period, cache=cache)

        if df is None or df.empty:
            return jsonify({'error': 'No hay datos disponibles'}), 404

        # ✅ FIX: Normalizar Volume a int64 SIEMPRE
        if 'Volume' in df.columns:
            df['Volume'] = df['Volume'].fillna(0).round().astype('int64')

        # Resamplear según timeframe
        if tf == '1wk':
            # Resamplear a semanal
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("W-FRI").first(),
                "High":   df["High"].resample("W-FRI").max(),
                "Low":    df["Low"].resample("W-FRI").min(),
                "Close":  df["Close"].resample("W-FRI").last(),
                "Volume": df["Volume"].resample("W-FRI").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        elif tf == '1mo':
            # Resamplear a mensual
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("M").first(),
                "High":   df["High"].resample("M").max(),
                "Low":    df["Low"].resample("M").min(),
                "Close":  df["Close"].resample("M").last(),
                "Volume": df["Volume"].resample("M").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        # ══════════════════════════════════════════════════════════
        # CAPPING DE OUTLIERS EN VOLUMEN
        # ══════════════════════════════════════════════════════════
        # Problema: Velas de volumen extremo (3-10x normal) comprimen
        # todas las demás, haciendo el gráfico de volumen ilegible.
        #
        # Solución: Detectar outliers y cappearlos a un máximo razonable
        # (2-2.5x la media móvil), marcándolos visualmente.
        # ══════════════════════════════════════════════════════════

        import numpy as np

        # Calcular media móvil de volumen (20 períodos)
        vol_series = df['Volume'].replace(0, np.nan)  # Ignorar ceros
        vol_ma20 = vol_series.rolling(window=20, min_periods=1).mean()

        # Detectar outliers (volumen > 3x media móvil)
        vol_threshold = vol_ma20 * 3.0
        is_outlier = vol_series > vol_threshold

        # Cappear outliers a 2.5x la media móvil
        vol_capped = vol_series.copy().astype('float64')  # ← Convertir a float para permitir decimales
        vol_capped[is_outlier] = vol_ma20[is_outlier] * 2.5

        # Marcar outliers para visualización diferente
        # Regla:
        # - Outliers (>3x media): Rojo intenso (marca anomalía)
        # - Normal alcista: Verde
        # - Normal bajista: Rojo
        vol_colors = []
        close_values = df['Close'].tolist()

        for i, outlier in enumerate(is_outlier):
            if outlier:
                # Outlier: rojo intenso independiente del movimiento
                vol_colors.append('rgba(244, 67, 54, 0.9)')
            elif i == 0:
                # Primera vela: azul neutro
                vol_colors.append('rgba(100, 181, 246, 0.6)')
            else:
                # Normal: verde si sube, rojo si baja
                if close_values[i] >= close_values[i-1]:
                    vol_colors.append('rgba(16, 185, 129, 0.6)')  # verde
                else:
                    vol_colors.append('rgba(239, 68, 68, 0.6)')   # rojo

        # Preparar datos para Plotly
        data = {
            'dates': df.index.strftime('%d.%m.%y').tolist(),  # ✅ Formato dd.mm.yy
            'open': df['Open'].round(2).tolist(),
            'high': df['High'].round(2).tolist(),
            'low': df['Low'].round(2).tolist(),
            'close': df['Close'].round(2).tolist(),
            'volume': vol_capped.fillna(0).round().astype("int64").tolist(),     # ← Volumen cappeado (para barras)
            'volume_real': vol_series.fillna(0).round().astype("int64").tolist(),  # ← Volumen real (para OBV)
            'volume_colors': vol_colors,                  # ← Colores diferenciados
            'volume_outliers': is_outlier.tolist()        # ← Flags para tooltip
        }

        # ═══════════════════════════════════════════════════════
        # FIBONACCI AUTOMÁTICO
        # ═══════════════════════════════════════════════════════
        fib_data = calcular_fibonacci_auto(df)
        if fib_data:
            data['fibonacci'] = fib_data

        # ═══════════════════════════════════════════════════════
        # PIVOT POINTS (DIARIOS Y SEMANALES)
        # ═══════════════════════════════════════════════════════
        pivot_diario = calcular_pivots(df, 'diario')
        pivot_semanal = calcular_pivots(df, 'semanal')

        data['pivots'] = {
            'diario': pivot_diario,
            'semanal': pivot_semanal
        }

        return jsonify(data)

    except Exception as e:
        logger.error(f"Error obteniendo datos de {ticker}: {e}")
        return jsonify({'error': str(e)}), 500


@grafico_pro_bp.route('/api/vela-info/<ticker>')
def get_vela_info(ticker):
    """
    Información completa de una vela específica
    
    Query params:
        date: YYYY-MM-DD
        tf: timeframe
    """
    try:
        from flask import current_app

        date_str = request.args.get('date')
        tf = request.args.get('tf', '1d')

        if not date_str:
            return jsonify({'error': 'Fecha requerida'}), 400

        # Obtener cache
        cache = current_app.config.get("CACHE_INSTANCE")

        # Obtener datos diarios
        df = get_df(ticker, periodo='2y', cache=cache)

        if df is None or df.empty:
            return jsonify({'error': 'No hay datos'}), 404

        # ✅ FIX: Normalizar Volume a int64 SIEMPRE
        if 'Volume' in df.columns:
            df['Volume'] = df['Volume'].fillna(0).round().astype('int64')

        # Resamplear si es necesario
        if tf == '1wk':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("W-FRI").first(),
                "High":   df["High"].resample("W-FRI").max(),
                "Low":    df["Low"].resample("W-FRI").min(),
                "Close":  df["Close"].resample("W-FRI").last(),
                "Volume": df["Volume"].resample("W-FRI").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        elif tf == '1mo':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("M").first(),
                "High":   df["High"].resample("M").max(),
                "Low":    df["Low"].resample("M").min(),
                "Close":  df["Close"].resample("M").last(),
                "Volume": df["Volume"].resample("M").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        # Buscar la vela por fecha
        df_date = df[df.index.strftime('%Y-%m-%d') == date_str]

        if df_date.empty:
            return jsonify({'error': 'Vela no encontrada'}), 404

        row = df_date.iloc[0]
        prev_close = df['Close'].shift(1).loc[row.name] if len(df) > 1 else None

        # Calcular variación
        if pd.notna(prev_close) and prev_close > 0:
            var_abs = row['Close'] - prev_close
            var_pct = (var_abs / prev_close) * 100
        else:
            var_abs = 0
            var_pct = 0

        # Calcular ATR (14 períodos) - siempre del diario para consistencia
        df_diario = get_df(ticker, periodo='2y', cache=cache)
        atr_series = calcular_atr(df_diario, periodo=14) if df_diario is not None else None

        # Buscar ATR de la fecha más cercana
        atr_value = None
        if atr_series is not None and not atr_series.empty:
            # Buscar la fecha en el índice diario
            fecha_buscar = pd.Timestamp(date_str)
            if fecha_buscar in atr_series.index:
                atr_value = atr_series.loc[fecha_buscar]
            else:
                # Buscar la más cercana
                idx_cercano = atr_series.index.searchsorted(fecha_buscar)
                if 0 <= idx_cercano < len(atr_series):
                    atr_value = atr_series.iloc[idx_cercano]

        # RSI - también del diario
        rsi_series = calcular_rsi(df_diario['Close'], periodo=14) if df_diario is not None else None
        rsi_value = None
        if rsi_series is not None and not rsi_series.empty:
            fecha_buscar = pd.Timestamp(date_str)
            if fecha_buscar in rsi_series.index:
                rsi_value = rsi_series.loc[fecha_buscar]
            else:
                idx_cercano = rsi_series.index.searchsorted(fecha_buscar)
                if 0 <= idx_cercano < len(rsi_series):
                    rsi_value = rsi_series.iloc[idx_cercano]

        info = {
            'fecha': row.name.strftime('%Y-%m-%d'),
            'dia_semana': row.name.strftime('%A'),
            'open': round(float(row['Open']), 2),
            'high': round(float(row['High']), 2),
            'low': round(float(row['Low']), 2),
            'close': round(float(row['Close']), 2),
            'volume': int(round(float(row['Volume']))) if pd.notna(row['Volume']) else 0,
            'variacion_abs': round(float(var_abs), 2),
            'variacion_pct': round(float(var_pct), 2),
            'atr': round(float(atr_value), 2) if pd.notna(atr_value) else None,
            'rsi': round(float(rsi_value), 1) if pd.notna(rsi_value) else None
        }

        return jsonify(info)

    except Exception as e:
        logger.error(f"Error obteniendo info de vela {ticker} {date_str}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@grafico_pro_bp.route('/api/indicadores/<ticker>')
def get_indicadores(ticker):
    """
    Calcular indicadores técnicos
    
    Query params:
        indicators: comma-separated (rsi,macd)
        tf: timeframe (1d, 1wk, 1mo)
    """
    try:
        from flask import current_app

        tf = request.args.get('tf', '1d')
        indicators_str = request.args.get('indicators', 'rsi')

        indicators_list = [ind.strip().upper() for ind in indicators_str.split(',')]

        # Obtener cache
        cache = current_app.config.get("CACHE_INSTANCE")

        # Obtener datos diarios
        df = get_df(ticker, periodo='2y', cache=cache)

        if df is None or df.empty:
            return jsonify({'error': 'No hay datos'}), 404

        # ✅ FIX: Normalizar Volume a int64 SIEMPRE
        if 'Volume' in df.columns:
            df['Volume'] = df['Volume'].fillna(0).round().astype('int64')

        # Resamplear si es necesario
        if tf == '1wk':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("W-FRI").first(),
                "High":   df["High"].resample("W-FRI").max(),
                "Low":    df["Low"].resample("W-FRI").min(),
                "Close":  df["Close"].resample("W-FRI").last(),
                "Volume": df["Volume"].resample("W-FRI").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        elif tf == '1mo':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("M").first(),
                "High":   df["High"].resample("M").max(),
                "Low":    df["Low"].resample("M").min(),
                "Close":  df["Close"].resample("M").last(),
                "Volume": df["Volume"].resample("M").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        result = {
            'dates': df.index.strftime('%d.%m.%y').tolist()  # ✅ Formato dd.mm.yy
        }

        # RSI
        if 'RSI' in indicators_list:
            rsi = calcular_rsi(df['Close'], periodo=14)
            result['rsi'] = rsi.round(2).fillna(0).tolist() if rsi is not None else []

        # MACD
        if 'MACD' in indicators_list:
            macd_result = calcular_macd(df['Close'])
            if macd_result:
                result['macd'] = {
                    'macd': macd_result['macd'].round(2).fillna(0).tolist(),
                    'signal': macd_result['señal'].round(2).fillna(0).tolist(),  # ✅ 'señal' no 'signal'
                    'histogram': macd_result['histograma'].round(2).fillna(0).tolist()  # ✅ 'histograma'
                }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error calculando indicadores de {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@grafico_pro_bp.route('/api/soportes-resistencias/<ticker>')
def get_soportes_resistencias(ticker):
    """Obtener soportes y resistencias automáticos"""
    try:
        from flask import current_app

        tf = request.args.get('tf', '1d')

        # Obtener cache
        cache = current_app.config.get("CACHE_INSTANCE")

        # Obtener datos
        df = get_df(ticker, periodo='2y', cache=cache)

        if df is None or df.empty:
            return jsonify({'error': 'No hay datos'}), 404

        # ✅ FIX: Normalizar Volume a int64 SIEMPRE
        if 'Volume' in df.columns:
            df['Volume'] = df['Volume'].fillna(0).round().astype('int64')

        # Resamplear si necesario
        if tf == '1wk':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("W-FRI").first(),
                "High":   df["High"].resample("W-FRI").max(),
                "Low":    df["Low"].resample("W-FRI").min(),
                "Close":  df["Close"].resample("W-FRI").last(),
                "Volume": df["Volume"].resample("W-FRI").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        elif tf == '1mo':
            df_resampled = pd.DataFrame({
                "Open":   df["Open"].resample("M").first(),
                "High":   df["High"].resample("M").max(),
                "Low":    df["Low"].resample("M").min(),
                "Close":  df["Close"].resample("M").last(),
                "Volume": df["Volume"].resample("M").sum().round().astype("int64"),
            }).dropna()
            df = df_resampled[df_resampled["Close"] > 0]

        # Detectar S/R
        sr_data = detectar_soportes_resistencias(
            df,
            periodo=5,  # ✅ 'periodo' no 'ventana_pivotes'
            min_toques=2,
            tolerancia_pct=1.5
        )

        soportes = []
        resistencias = []

        if sr_data:
            for nivel in sr_data.get('soportes', []):
                soportes.append({
                    'precio': round(float(nivel['nivel']), 2),  # ✅ 'nivel' no 'precio'
                    'toques': int(nivel['toques']),
                    'fuerza': nivel.get('fuerza', 'MEDIA')
                })

            for nivel in sr_data.get('resistencias', []):
                resistencias.append({
                    'precio': round(float(nivel['nivel']), 2),  # ✅ 'nivel' no 'precio'
                    'toques': int(nivel['toques']),
                    'fuerza': nivel.get('fuerza', 'MEDIA')
                })

        return jsonify({
            'soportes': soportes[:5],  # Top 5 soportes
            'resistencias': resistencias[:5]  # Top 5 resistencias
        })

    except Exception as e:
        logger.error(f"Error calculando S/R de {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

