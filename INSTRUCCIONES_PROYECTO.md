# 📊 SISTEMA TRADING — INSTRUCCIONES DEL PROYECTO (v90.1)

## CONTEXTO DEL PROYECTO

Este proyecto es una **plataforma modular de análisis y trading** para mercado español (IBEX 35 y Mercado Continuo), especializada en tres sistemas de trading paralelos:

### Sistemas operativos

1. **Swing Trading** (1–3 semanas)
   - Operativa de corto plazo con análisis técnico diario
   - RSI, Momentum, Breakouts
   - Timeframe: Diario
   - Riesgo/Beneficio: 1:2 mínimo

2. **Medio Plazo** (4–24 semanas)
   - Pullbacks en tendencia alcista
   - Scoring unificado (técnico 70% + fundamental 30%)
   - Timeframe: Semanal (análisis en D1)
   - Setup Global: COMPRA / VIGILAR / NO_OPERAR

3. **Posicional** (6 meses a 2 años)
   - Trend following de largo plazo
   - Breakouts selectivos
   - Timeframe: Mensual
   - Durabilidad y gestión de riesgo crítica

### Características transversales

- ✅ Gestión monetaria profesional (Risk Manager con límites automáticos)
- ✅ Backtesting en múltiples R con walk-forward validation
- ✅ Scoring contextual (no binario)
- ✅ Integración técnico + fundamental
- ✅ Alertas inteligentes (cartera + técnicas)
- ✅ Trailing stops automáticos
- ✅ Dashboard exposición sectorial
- ✅ Control de posiciones simultáneas y correlación

**Se debe tratar como software financiero serio y mantenible**, NO como un script experimental.

---

## FILOSOFÍA DEL SISTEMA

### Objetivo principal

Buscar:
- ✅ Setups de alta calidad (score ≥ 6.5 Medio Plazo)
- ✅ Tendencias sanas (MM50 > MM200, máximos crecientes)
- ✅ Asimetrías riesgo/beneficio ≥ 1:2
- ✅ Robustez estadística (80+ trades backtested)
- ✅ Gestión de riesgo profesional (drawdown ≤ 20%)

NO buscar:
- ❌ Hiperactividad (señales constantes)
- ❌ Sobreoperar (máx 10 posiciones simultáneas)
- ❌ Optimización visual engañosa
- ❌ Trades sin tesis clara

---

## PRINCIPIOS CLAVE

### 1. El contexto manda

Las señales NO deben evaluarse aisladamente. Siempre considerar:
- Tendencia general (IBEX, sector, valor)
- Estructura del precio (máximos/mínimos crecientes)
- Momentum (RSI, MACD, volumen)
- Volatilidad (ATR%, bandas de Bollinger)
- Contexto IBEX (alcista/bajista/lateral)
- Fundamentales (calidad, crecimiento, valoración)
- Calidad del setup (timing, estructura, entrada)

### 2. El sistema es CONTEXTUAL, no binario

Evitar lógica simplista. Ejemplo incorrecto:
```python
# ❌ MAL (demasiado rígido)
if precio > MM20:
    decision = "COMPRA"
else:
    decision = "NO_OPERAR"
```

Lógica correcta:
```python
# ✅ BIEN (contextual)
if precio > MM20 and MM50 > MM200 and RSI < 70 and volumen_alcista:
    score += puntos_timing
    
if RSI > 75 and precio_extendido:
    score -= penalizacion_momentum
    
# Score determina: EXCELENTE (8.5+) / BUENO (6.5-8.4) / MEDIOCRE (5.5-6.4) / DÉBIL (<5.5)
```

### 3. Score unificado es la única fuente de verdad

**v82.3 onward**: Score (escala 0-10) determina TODO.

No hay "criticos booleano + score separado". Una única métrica.

```
Score >= 8.5  → EXCELENTE (COMPRA fuerte)
Score 6.5-8.4 → BUENO (COMPRA)
Score 5.5-6.4 → MEDIOCRE (VIGILAR)
Score < 5.5   → DÉBIL (NO_OPERAR)
```

### 4. Scoring Medio Plazo: Técnico (70%) + Fundamental (30%)

**Sistema Medio Plazo v85.14+:**

```
Score Global = (Score_Técnico × 0.70) + (Score_Fundamental × 0.30)
```

**Componente técnico (escala 0-10):**
- ESTRUCTURA (0-5): Calidad de tendencia macro
  - MM50 > MM200 (obligatorio)
  - MM20 ascendente
  - MM50 ascendente
  - Precio vs MM50 (posición estructural)
  - Máximos crecientes

- TIMING (0-3): Momento óptimo de entrada
  - Pullback hacia MM20/MM50
  - RSI en zona 40-65 (ideal 50-60)
  - Volumen en entrada fresca
  - Confirmación técnica

- MOMENTUM (0-2): Fuerza compradora actual
  - MACD positivo y creciente
  - RSI < 70 (no sobrecomprado)
  - Volumen alcista
  - ATR% (volatilidad controlada)

**Componente fundamental (escala 0-10):**
- Calidad empresarial (ROE, márgenes, crecimiento)
- Valoración (EV/EBITDA, P/E, P/B)
- Contexto sectorial
- Eventos corporativos (dividendos, splits, cambios)

### 5. Risk Manager: Advertencia, no bloqueo (v89.21+)

El sistema **avisa** pero NO bloquea:

```
Límites configurables:
- Posiciones simultáneas: ≤ 10 empresas únicas
- Risk budget: ≤ 8% capital total
- Exposición sectorial: ≤ 30% por sector

Comportamiento:
- ⚠️ ADVERTENCIA: Flash warning si cercano/excedido
- ✅ PERMITE: Usuario decide si aceptar el riesgo
- 📊 VISIBILIDAD: Dashboard exposición sectorial
```

### 6. Trailing stops automáticos (v88.2+)

Tres fases:

```
INICIAL (entrada)
    ↓ (cuando P&L ≥ +1R)
BREAKEVEN (stop sube a entrada)
    ↓ (cuando P&L ≥ +3R)
PROFIT_LOCK (stop sube a +2R)

Regla: Stop NUNCA baja. Respeta ajustes manuales si más altos.
```

Botones:
- `🎯 Trailing` (individual)
- `🎯 Trailing a Todas` (cartera completa)

### 7. Alertas inteligentes de cartera (v89.2+)

Se muestran en pantalla **/alertas/** (no duplican alertas técnicas).

**Cuatro tipos detectados automáticamente:**

1. **🔴 CRÍTICA: Stop en peligro** (<2% distancia)
   - Acción: Decidir mantener o cerrar

2. **🟠 ALTA: Objetivo cerca** (<5% distancia)
   - Acción: Preparar salida

3. **🟠 ALTA: Profit Lock disponible** (+3R alcanzado)
   - Acción: Asegurar +2R con trailing

4. **🟡 MEDIA: Setup degradado** (pérdida -0.5R/-1R o estancada >30d)
   - Acción: Revisar tesis / cerrar

Ordenadas por prioridad automáticamente.

### 8. Tickers únicos: Múltiples entradas = 1 posición (v88.13+)

Contador de Risk Manager:
```
2 entradas BBVA + 1 SAN + 1 TEF = 3 empresas únicas (no 4 posiciones)

Risk budget:
- Suma TODAS las entradas (2 + 1 + 1 = 4 entradas totales)
- Pero Risk Manager cuenta 3 empresas ≤ 10 máximo
```

### 9. P&L en R corregido (v88.21+)

```
❌ Incorrecto (anterior):
pnl_R = (precio_actual - entrada) / R_unitario  # por acción

✅ Correcto (v88.21+):
pnl_R = pnl_eur / riesgo_total  # división por riesgo TOTAL
```

Ejemplo ENG.MC:
```
Entrada: 17.27€, Stop: 16.57€, Acciones: 500, Precio: 17.33€
R_unit = 0.70€/acción
Riesgo_total = 0.70 × 500 = 350€
P&L = (17.33 - 17.27) × 500 = 30€
P&L_R = 30 / 350 = +0.09R ✅
```

### 10. ATR en barras con porcentaje (v89.25+)

Dos modos de visualización:

**ATR (línea)**: Overlay punteada en gráfico principal
- Uso: Referencia rápida de volatilidad
- Hover: Muestra valor €  y %

**ATR Barras 📊 (histograma)**: Panel independiente abajo
- Uso: Análisis detallado de volatilidad
- Hover: `0.2400 (1.39%)` → valor absoluto + % del precio

Interpretación ATR%:
```
< 1.5%  → Baja volatilidad (operaciones conservadoras)
1.5-3%  → Volatilidad normal
3-5%    → Volatilidad alta (tamaño de posición reducido)
> 5%    → Muy alta (cuidado extremo)
```

---

## ARQUITECTURA DEL SISTEMA

### Estructura de carpetas

```
MiWeb/
├── [14 root .py files]
│   ├── app.py (Flask principal)
│   ├── config.py, database.py
│   ├── contexto_bp.py, controlador.py
│   └── [indicadores, utilidades, etc]
│
├── alertas/
│   ├── __init__.py
│   ├── alertas_db.py (persistencia)
│   ├── alertas_ia.py (detector IA)
│   ├── alertas_cartera.py (alertas inteligentes v89.2+)
│   └── detector.py
│
├── analisis/
│   ├── fundamental/
│   │   ├── __init__.py
│   │   ├── insiders.py
│   │   ├── noticias.py
│   │   ├── proveedor.py
│   │   ├── rating.py
│   │   └── scoring.py
│   └── tecnico/
│       ├── __init__.py
│       ├── confirmaciones.py
│       └── [otros análisis]
│
├── cartera/
│   ├── __init__.py
│   ├── cartera_db.py
│   ├── cartera_logica.py (cálculo P&L en R v88.21+)
│   ├── risk_manager.py (límites v88.1+)
│   ├── trailing_stops.py (automatización v88.2+)
│   └── cartera.db (NO incluir en ZIPs)
│
├── core/
│   ├── __init__.py
│   ├── data_provider.py
│   ├── indicadores.py (ATR, RSI, MACD, etc)
│   ├── contexto_mercado.py
│   └── cache_manager.py
│
├── estrategias/
│   ├── swing/
│   │   ├── scanner_swing.py
│   │   └── [breakout, pullback]
│   ├── medio/
│   │   ├── logica_medio.py (scoring v85.14+)
│   │   ├── scanner_medio.py
│   │   ├── config_medio.py
│   │   └── [backtests]
│   └── posicional/
│       ├── logica_posicional.py
│       ├── scanner_posicional.py
│       └── [backtests]
│
├── static/
│   ├── js/
│   │   ├── grafico.js (3900+ líneas, soporta todos indicadores v89.25+)
│   │   ├── indicadores.js
│   │   └── [otros]
│   └── css/
│       └── indicadores.css
│
├── templates/
│   ├── cartera.html (portfolio + trailing + risk dashboard)
│   ├── alertas.html (técnicas + inteligentes v89.2+)
│   ├── indicadores.html (Análisis Técnico Completo)
│   ├── medio.html (Sistema Medio Plazo)
│   └── [otros]
│
└── web/routes/
    ├── cartera_routes.py (gestión cartera, Risk Manager v88.1+)
    ├── alertas_routes.py (alertas técnicas + cartera v89.2+)
    ├── indicadores_routes.py (análisis técnico)
    ├── medio_routes.py (Sistema Medio Plazo)
    └── [otros sistemas]
```

---

## REGLAS INVARIANTES (OBLIGATORIAS)

### Cálculos

- ✅ **RSI**: SIEMPRE método Wilder via `calcular_rsi()`
- ✅ **ATR**: Período 14 por defecto, cálculo True Range
- ✅ **Cache**: SIEMPRE via `current_app.config.get("CACHE_INSTANCE")`
- ✅ **P&L en R**: Dividir por riesgo TOTAL, no unitario (v88.21+)

### Base de datos

- ✅ `cartera.db` NUNCA en ZIPs (reside solo en `cartera/cartera.db`)
- ✅ `alertas.db` incluido en ZIPs vacío (reside en `alertas/alertas.db`)
- ✅ `trades.db` incluido en ZIPs vacío (reside en `analytics/trades.db`)

**🔴 CRÍTICO — Prevención de error v89.26:**

En `cartera/cartera_db.py`, línea 7:

```python
# ❌ INCORRECTO (sube un nivel, guarda en raíz MiWeb/)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cartera.db")
# Resultado: D:\a\MiWeb\cartera.db ← BUG

# ✅ CORRECTO (se queda en subcarpeta cartera/)
DB_PATH = os.path.join(os.path.dirname(__file__), "cartera.db")
# Resultado: D:\a\MiWeb\cartera\cartera.db ← BIEN
```

**Por qué pasó:**
- `__file__` = ruta actual (`cartera/cartera_db.py`)
- `os.path.dirname(__file__)` = directorio del archivo (`cartera/`)
- `".."` = sube un nivel a raíz (`MiWeb/`)
- Resultado: BD en lugar incorrecto

**Checklist para evitarlo:**
- ✅ BD locales SIEMPRE en sus subcarpetas (cartera/, alertas/, analytics/)
- ✅ NO usar `".."` para salir de la carpeta en paths de BD
- ✅ Verificar con `print(DB_PATH)` al iniciar que está en lugar correcto
- ✅ En ZIPs: excluir AMBAS rutas `MiWeb/cartera.db` y `MiWeb/cartera/cartera.db` para evitar duplicados

### Código

- ✅ `app.py` imports NO modificar (salvo excepciones documentadas)
- ✅ No crear archivos fuera de carpetas designadas
- ✅ Cada módulo con `__init__.py`
- ✅ Tickers siempre `.MC` para Mercado Continuo / IBEX35

### ZIPs de exportación

**Reglas invariantes:**
- Carpeta raíz siempre `MiWeb/` — nunca variantes
- Base del ZIP: siempre extraer el ZIP que pase el usuario, sobreescribir solo archivos modificados
- **NUNCA incluir** `.db` — ni vacíos, ni de 0 bytes: `cartera.db`, `alertas.db`, `trades.db`
- Excluir siempre: `**/__pycache__/`, `**/*.pyc`
- Las carpetas `alertas/`, `analytics/`, `cartera/`, `data/`, `pantallazos/` se incluyen vacías
- Verificación obligatoria antes de entregar: carpeta raíz única = `MiWeb`, cero `.db`

---

## VERSIONING Y ESTADO ACTUAL

### Sistema de numeración

```
vXX.Y    = Funcionalidad nueva (ej: v90 Sistema Posicional mejorado)
vXX.Y_Z  = Correcciones dentro de versión (ej: v90.1 bugfixes logica_medio)
```

### Versión estable actual

**v90.1** — Bugfixes logica_medio + Sistema Posicional mejorado (672KB)

Incluye todo lo anterior hasta v89.26, más:

**v90 — Sistema Posicional (sesión 2026-05-31):**
- `config_posicional.py`: Volatilidad mínima 20% → 15% (recupera RED, ENG, MAP, NTGY)
- `config_posicional.py`: Universo IBEX35 + Continuo completo = **66 valores**
- `scanner_posicional.py`: Auditoría de rechazos con `Counter` — cuello de botella visible
- `scanner_posicional.py`: **Watchlist A/B** — separa calidad estructural de trigger de entrada
  - Watchlist A (⭐ score ≥ 65): candidatos prioritarios esperando breakout
  - Watchlist B (score 50-64): candidatos secundarios
  - Rechazado: score < 50 o múltiples motivos
- `sistema_trading_posicional.py`: Motivos originales preservados (no sobreescritos por "Score insuficiente")
- `posicional_routes.py`: Ruta `<path:ticker>` para `.MC`, escáner ampliado, 3 opciones de universo
- `escanear_posicional.html`: Stats bar con COMPRA/WL-A/WL-B, tabla watchlist con niveles, botón 🔍 abre nueva pestaña
- `index_posicional.html`: Universo 66, dropdown con 3 escáneres

**v90.1 — Bugfixes logica_medio (sesión 2026-06-01):**
- **Fix typos constantes** (NameError): `ESTRUCTURA_BAJO_MM50` → `ESTRUCTURA_BAJO_MM`, `TIMING_MM20_ROTA_PENALIZACION` → `TIMING_DETERIORO_PENALIZACION`, `TIMING_PULLBACK_PROFUNDO_PENALIZACION` → `TIMING_DETERIORO_PENALIZACION`, `RSI_MIN_PULLBACK/MAX` → valores literales 40/55
- **Fix tendencia BAJISTA**: ahora requiere MM50 < MM200 además de MM20 bajando. Si MM50 > MM200 la tendencia es siempre ALCISTA (pullback en tendencia alcista = normal)
- **Fix tendencia_ok**: usa `mm50_sobre_mm200` directamente en vez de `tendencia_str == "ALCISTA"` — elimina contradicción entre "Por qué no opera" y "Condiciones que cumple"
- **Fix timing pullback**: `retroceso_pct` es positivo (7.3 = caída 7.3% desde máximos). Condiciones corregidas: 5-15% óptimo (+2.0), 15-25% válido (+1.0), >25% deterioro (-2.0), <2% extendido (-1.0)
- **Fix bonus estructura**: se activa con `mm50_sobre_mm200 AND score >= 1.5` (antes `>= 2.5` nunca llegaba)
- **Fix penalización MM20 plana/bajando**: solo penaliza si precio > 8% bajo MM20, no por estar 0.3% bajo

---

## ROADMAP PENDIENTE

### Crítico (próxima semana)

1. **Salidas parciales** — Scale out 50% en +2R
2. **Correlación real** — Cálculo histórico (no sectores arbitrarios)

### Importante (2-3 semanas)

3. **Post-mortem automático** — Screenshots + notas por trade
4. **Dashboard performance** — Win rate, avg R, max DD, curva capital
5. **Backtest walk-forward** — Train/test rolling, out-of-sample validation

### Mejoras (futuro)

6. **Monte Carlo DD** — Simulación 10k trades, probabilidad ruina
7. **Integración broker** — Sincronización API órdenes/posiciones
8. **Trailing por estructura** — Sugerir stops bajo mínimos crecientes (asistido)

---

## NOTAS CRÍTICAS

### Estructura de carpetas y rutas de BD

**Regla fundamental:** Cada BD reside EN su carpeta, no en la raíz.

```
# ✅ CORRECTO
cartera/
  ├── cartera_db.py (línea 7: DB_PATH = ".../cartera/cartera.db")
  └── cartera.db (aquí se guarda)

alertas/
  ├── alertas_db.py (línea X: DB_PATH = ".../alertas/alertas.db")
  └── alertas.db

analytics/
  ├── [módulos]
  └── trades.db

# ❌ INCORRECTO (ocurrió en v89.25)
MiWeb/
  ├── cartera.db ← ERRONEAMENTE AQUÍ
  └── cartera/
      ├── cartera_db.py (usaba DB_PATH = "../cartera.db")
      └── [otros]
```

**Bug específico (v89.26):**
- `cartera_db.py` línea 7 usaba: `DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cartera.db")`
- El `".."` salía un nivel (a raíz MiWeb/)
- **Solución:** Cambiar a `os.path.join(os.path.dirname(__file__), "cartera.db")`

**Verificación:**
Agregar al inicio de `cartera_db.py`:
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"[DB] cartera.db path: {DB_PATH}")  # Verificar en logs que está en lugar correcto
```

### Decisiones de diseño

- **Scoring como única verdad**: Elimina ambigüedad, facilita backtesting
- **Técnico 70% + Fundamental 30%**: Equilibrio realista (técnica entra, fundamental retiene)
- **Risk Manager advertencia, no bloqueo**: Confía en usuario, no paternalista
- **Tickers únicos**: Refleja realidad (2 compras BBVA = 1 empresa)
- **Alertas en pantalla existente**: No duplica, mejora información

### Common pitfalls evitados

- ❌ Doble criterio (criticos bool + score): v82.3 unificó a score único
- ❌ ATR overlay vs barras: v89.22+ soporta ambos (distinto nombre)
- ❌ Checkbox binding antiguo: v89.23 usa array global `window.selectedIndicadores`
- ❌ P&L unitario: v88.21 corrigió a riesgo total
- ❌ DB en raíz (v89.26): `cartera_db.py` usaba `".."` para salir de carpeta
- ❌ **Mezclar calidad estructural con trigger de entrada (v90)**: Watchlist A/B separa score del breakout
- ❌ **`retroceso_pct` es POSITIVO** (v90.1): 7.3 = caída del 7.3% desde máximos. No negativo.
- ❌ **BAJISTA con MM50>MM200** (v90.1): si MM50>MM200 la tendencia es ALCISTA aunque MM20 baje
- ❌ **Typos de constantes en calcular_score_medio_v2** (v90.1): verificar siempre con AST antes de entregar

### Sistema Posicional — decisiones de diseño (v90)

- **Watchlist A/B**: calidad del activo ≠ momento de entrada. Score separa candidatos de rechazados reales.
- **Universo 66 valores**: IBEX35 + Continuo completo. Los filtros del sistema hacen la selección, no listas manuales.
- **Volatilidad mínima 15%**: recupera valores defensivos (RED, ENG, MAP, NTGY) con tendencias largas y limpias.
- **Auditoría de rechazos**: `Counter` de motivos permite identificar el cuello de botella real (fue breakout 95.8%).

### Sistema Medio Plazo — scoring v2 (v90.1)

- **`retroceso_pct` es positivo**: 7.3 = caída del 7.3% desde máximos recientes
- **Tendencia alcista = MM50 > MM200**: MM20 bajando durante pullback es NORMAL, no BAJISTA
- **Bonus estructura**: se activa con `mm50_sobre_mm200 AND score >= 1.5`
- **Penalización MM20**: solo si precio > 8% bajo MM20 (no por estar 0.3% bajo en pullback normal)

---

## CONTACTO INTERNO

**Responsable**: Salva (trading.salvanavegacion.es)
**Última sesión**: 2026-06-01 (v90.1)
**Próxima revisión**: Salidas parciales (v91)

---

**Este documento es la fuente de verdad del proyecto. Actualizar cada versión.**
