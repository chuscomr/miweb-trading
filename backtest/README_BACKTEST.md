# Sistema de Backtesting - Versión Final

## 📂 Estructura de Archivos

### Archivos ESENCIALES (mantener):

```
backtest/
├── __init__.py              # Inicialización del módulo
├── datos.py                 # Gestión de datos de mercado
├── engine.py                # Motor del backtest (VERSIÓN CORREGIDA)
├── execution.py             # Modelo de ejecución (slippage, comisiones)
├── metrics.py               # Cálculo de métricas
├── montecarlo.py            # Simulación Monte Carlo
├── portfolio.py             # Gestión del portfolio
├── position.py              # Gestión de posiciones (VERSIÓN CORREGIDA)
├── risk.py                  # Gestión de riesgo
├── strategy.py              # Lógica de estrategia (CON FILTRO VOLATILIDAD)
├── trade.py                 # Clase Trade
└── run_backtest.py          # Script principal (VERSIÓN FINAL)
```

### Archivos a ELIMINAR:

```
❌ backtest_completo.py
❌ backtest_costes_reducidos.py
❌ backtest_filtro_volatilidad.py
❌ backtest_top_tickers.py
❌ analizar_filtros.py
❌ analizar_y_filtrar_tickers.py
❌ analizar_compra.py
❌ diagnostico_ITX.py
❌ __pycache__/*.pyc (todos los archivos compilados)
```

---

## 🚀 Uso del Sistema

### Ejecución básica:

```bash
cd C:\Users\chusc\Desktop\MiWeb\backtest
python run_backtest.py
```

### Configuración (editar en run_backtest.py):

```python
CAPITAL_INICIAL = 10_000       # Capital inicial
RIESGO_POR_TRADE = 0.01        # 1% por trade
MIN_VOLATILIDAD = 12.0         # Filtro de volatilidad
MODO_TEST = False              # False = estrategia real
```

---

## ✨ Características del Sistema

### 1. Filtro de Volatilidad Automático
- Excluye tickers con volatilidad <12%
- ITX, TEF, IBE automáticamente filtrados
- Solo opera valores compatibles

### 2. Gestión de Riesgo
- Target: +3R
- Break-even: +1R
- Stop inicial: 2% o basado en ATR

### 3. Costes Realistas
- Comisión: 0.05% por operación
- Slippage: 1% del ATR
- Representa condiciones reales de mercado

### 4. Métricas Completas
- Win Rate
- Expectancy (R)
- Max Drawdown
- Simulación Monte Carlo

---

## 📊 Resultados Esperados

Con configuración por defecto:
- **Expectancy:** +0.50R
- **Win Rate:** ~35%
- **Max Drawdown:** ~8%
- **Tickers operados:** 10/20

---

## 🔧 Personalización

### Cambiar volatilidad mínima:

```python
MIN_VOLATILIDAD = 15.0  # Más restrictivo (menos tickers, mejor calidad)
MIN_VOLATILIDAD = 10.0  # Menos restrictivo (más tickers)
```

### Cambiar target:

En `position.py` línea 20 y `engine.py` línea 102:
```python
# Para target +4R en lugar de +3R:
if high >= self.trade.entrada + 4 * self.riesgo:  # position.py
salida_precio = pos.trade.entrada + (4 * pos.riesgo)  # engine.py
```

### Modo test (estrategia simple):

```python
MODO_TEST = True  # Usar estrategia de medias móviles simple
```

---

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'logica'"
**Solución:** Ejecutar desde la carpeta `backtest/`

### Error: Todos los trades pierden
**Verificar:** 
1. `position.py` tiene indentación correcta
2. `engine.py` usa precio correcto en TARGET

### Sin señales
**Verificar:**
1. Volatilidad no demasiado alta
2. `evaluar_valor()` está generando señales
3. Datos suficientes (>60 barras)

---

## 📝 Notas Importantes

1. **ITX es buena empresa**, pero volatilidad baja (9.5%) incompatible
2. **No todos los tickers funcionan** - es normal y profesional
3. **10-12 tickers aprobados** es excelente diversificación
4. **Expectancy >0.30R** indica sistema rentable

---

## 🎯 Próximos Pasos (Opcional)

1. **Paper trading** - Probar 1-2 meses en simulado
2. **Alertas** - Crear sistema de notificaciones
3. **Portfolio management** - Gestionar múltiples posiciones simultáneas
4. **Optimización** - Ajustar parámetros por ticker

---

Creado: 2026-01-28
Versión: 1.0 Final
