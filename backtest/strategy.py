from logica import evaluar_valor
import pandas as pd


class StrategyLogic:
    """
    Adaptador del sistema REAL para backtest.
    Incluye modo_test para validar el backtester con estrategia simple.
    """
    
    def __init__(self, modo_test=False, min_volatilidad_pct=12.0, modo_backtest=True):
        self.modo_test = modo_test
        self.min_volatilidad_pct = min_volatilidad_pct
        self.modo_backtest = modo_backtest  # ✅ NUEVO: diferenciar backtest vs producción
        
        if modo_test:
            print("⚠️  MODO TEST ACTIVADO - Usando estrategia simple")
        
        if min_volatilidad_pct > 0:
            print(f"🎯 Filtro de volatilidad: mínimo {min_volatilidad_pct}%")
        
        if modo_backtest:
            print("📊 MODO BACKTEST - Evaluando todas las barras históricas")
        else:
            print("🔴 MODO PRODUCCIÓN - Solo última barra")
    
    def evaluate(self, df, contexto, posicion, ultima_barra=False):
        # ✅ CORREGIDO: Solo limitar a última barra en PRODUCCIÓN
        if not self.modo_backtest and not ultima_barra:
            return {"accion": "ESPERAR"}
        
        # No entrar si ya hay posición
        if posicion:
            return {"accion": "ESPERAR"}
        
        # 🔧 FILTRO DE VOLATILIDAD (aplicable a ambos modos)
        if self.min_volatilidad_pct > 0 and len(df) >= 20:
            volatilidad_pct = (df['Close'].std() / df['Close'].mean()) * 100
            
            if volatilidad_pct < self.min_volatilidad_pct:
                # Ticker demasiado tranquilo para nuestra estrategia
                return {"accion": "ESPERAR"}
        
        # Seleccionar estrategia según modo
        if self.modo_test:
            return self._estrategia_simple(df)
        else:
            return self._estrategia_real(df)
    
    def _estrategia_simple(self, df):
        """
        Estrategia básica para validar el sistema de backtest.
        Señal: precio > MM20 > MM50 (tendencia alcista clara)
        """
        if len(df) < 50:
            return {"accion": "ESPERAR"}
        
        precio = df["Close"].iloc[-1]
        mm20 = df["Close"].rolling(20).mean().iloc[-1]
        mm50 = df["Close"].rolling(50).mean().iloc[-1]
        
        # Señal: tendencia alcista clara
        if precio > mm20 > mm50:
            # Stop 2% por debajo del precio actual
            stop = precio * 0.98
            
            return {
                "accion": "ENTRAR",
                "entrada": precio,
                "stop": stop
            }
        
        return {"accion": "ESPERAR"}
    
    def _estrategia_real(self, df):
        """
        Estrategia original usando evaluar_valor() de logica.py
        """
        precios = df["Close"].tolist()
        volumenes = df["Volume"].tolist() if "Volume" in df.columns else []
        fechas = df.index.tolist()
        
        resultado = evaluar_valor(
            precios=precios,
            volumenes=volumenes,
            fechas=fechas
        )
        
        if not resultado:
            return {"accion": "ESPERAR"}
        
        if resultado.get("decision") != "COMPRA":
            return {"accion": "ESPERAR"}
        
        # Extraer entrada
        entrada = resultado.get("entrada_tecnica")
        
        if entrada is None:
            return {"accion": "ESPERAR"}
        
        # Extraer o calcular stop
        stop = resultado.get("stop")
        
        if stop is None:
            # 🔧 STOP HÍBRIDO: ATR con mínimo garantizado
            high = df["High"]
            low = df["Low"]
            close = df["Close"].shift(1)
            tr = (high - low).abs()
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Calcular stop basado en ATR
            if not pd.isna(atr):
                stop_atr = entrada - (2.5 * atr)
            else:
                stop_atr = None
            
            # Stop fijo 2%
            stop_fijo = entrada * 0.98
            
            # Usar el MENOR (más amplio) de los dos
            if stop_atr is not None:
                stop = min(stop_atr, stop_fijo)
            else:
                stop = stop_fijo
            
            # ✅ VALIDACIÓN: Garantizar distancia mínima del 1%
            distancia_stop = (entrada - stop) / entrada
            if distancia_stop < 0.01:  # Menos del 1%
                stop = entrada * 0.99  # Forzar stop al 1%
        
        # ✅ VALIDACIÓN FINAL: Verificar que el stop es válido
        if stop is None or stop >= entrada:
            return {"accion": "ESPERAR"}
        
        return {
            "accion": "ENTRAR",
            "entrada": float(entrada),
            "stop": float(stop)
        }
