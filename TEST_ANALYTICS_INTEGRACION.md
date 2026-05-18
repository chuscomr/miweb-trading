# 🧪 TEST: Integración Analytics + Cartera

## ✅ CAMBIOS APLICADOS

### 1. **cartera_db.py**
- ✅ Añadida columna `analytics_id INTEGER` (migración automática)
- ✅ Modificado `agregar_posicion()` para aceptar `analytics_id`
- ✅ Logging mejorado con analytics_id

### 2. **cartera_routes.py**
- ✅ Import `registrar_apertura, registrar_cierre` de analytics
- ✅ `nueva_guardar()`: llama `registrar_apertura()` antes de crear posición
- ✅ `cerrar_guardar()`: llama `registrar_cierre()` al cerrar posición
- ✅ Manejo de errores: continúa si Analytics falla
- ✅ Logging detallado de operaciones

---

## 🔄 FLUJO COMPLETO

### **Apertura de posición:**
```
1. Usuario rellena formulario /cartera/nueva
2. Route nueva_guardar():
   a. Validar datos
   b. Evaluar contexto IBEX
   c. → registrar_apertura() → analytics.trades_log
   d. ← trade_id (analytics_id)
   e. → agregar_posicion(analytics_id=trade_id) → cartera.posiciones
   f. ← pid
3. Redirect a /cartera
```

### **Cierre de posición:**
```
1. Usuario rellena formulario /cartera/cerrar/<pid>
2. Route cerrar_guardar(pid):
   a. Obtener posición
   b. Calcular R final
   c. → cerrar_posicion() → cartera.posiciones
   d. Si analytics_id existe:
      → registrar_cierre() → analytics.trades_log
   e. Redirect a /cartera
```

---

## 🧪 PLAN DE TESTING

### **Test 1: Apertura con Analytics OK**
```bash
# Abrir posición nueva
http://localhost:5001/cartera/nueva

Datos:
- Ticker: SAN.MC
- Sistema: SWING
- Precio entrada: 4.50
- Stop: 4.30
- Objetivo: 5.00
- Acciones: 100

Verificar:
1. ✅ Posición creada en cartera
2. ✅ Trade creado en analytics
3. ✅ posiciones.analytics_id = trades_log.id
4. ✅ Logs: "Analytics registrado: trade_id=X"
```

### **Test 2: Cierre con Analytics OK**
```bash
# Cerrar posición
http://localhost:5001/cartera/cerrar/<pid>

Datos:
- Precio cierre: 4.80
- Motivo: OBJETIVO

Verificar:
1. ✅ Posición cerrada en cartera
2. ✅ Trade actualizado en analytics
3. ✅ R calculado correctamente
4. ✅ Logs: "Analytics actualizado: trade_id=X, R=1.5"
```

### **Test 3: Apertura sin Analytics (fallo)**
```python
# Simular fallo en registrar_apertura()
# Verificar que la posición se crea igual
# analytics_id = None

Verificar:
1. ✅ Posición creada
2. ✅ analytics_id = NULL
3. ✅ Warning log: "Error registrando en Analytics"
```

### **Test 4: Cierre sin analytics_id**
```bash
# Posición antigua sin analytics_id
# Cerrar normalmente

Verificar:
1. ✅ Posición cerrada
2. ✅ No llama registrar_cierre()
3. ✅ Warning log: "sin analytics_id, no se registra cierre"
```

---

## 🔍 VERIFICACIÓN EN BD

### **Verificar columna analytics_id:**
```sql
-- Desde Python
from cartera.cartera_db import CarteraDB
db = CarteraDB()
with db._conexion() as con:
    cols = [r[1] for r in con.execute("PRAGMA table_info(posiciones)")]
    print('analytics_id' in cols)  # Debe ser True
```

### **Verificar vinculos:**
```sql
SELECT 
    p.id as posicion_id,
    p.ticker,
    p.analytics_id,
    t.id as trade_id,
    t.ticker
FROM posiciones p
LEFT JOIN analytics.trades_log t ON p.analytics_id = t.id
WHERE p.estado = 'ABIERTA';
```

---

## 📊 VERIFICACIÓN EN UI

### **/contexto (Analytics Dashboard)**
Después de abrir/cerrar trades:

1. **KPIs Globales:**
   - Total Trades: debería incrementar
   - Win Rate: actualizado
   - Profit Factor: actualizado

2. **Resultados por Sistema:**
   - Swing/Medio/Posicional: desglosado

3. **Resultados por Setup:**
   - Por score_nivel/tipo_setup

4. **Resultados por Contexto:**
   - ALCISTA/TRANSICION/BAJISTA

---

## ⚠️ CASOS EDGE

### 1. **Posición abierta antes de v85.21**
- Sin analytics_id
- Al cerrar: warning log, NO falla

### 2. **Analytics DB no disponible**
- Error al abrir: posición se crea igual
- Error al cerrar: posición se cierra igual

### 3. **Múltiples cierres parciales**
- Por ahora: solo registra cierre final
- TODO futuro: registrar mitad cerrada

---

## 🎯 ÉXITO CONFIRMADO SI:

✅ Posición nueva → trade nuevo en analytics
✅ Posición cerrada → trade actualizado
✅ Fallo en Analytics → no bloquea operación cartera
✅ Posición sin analytics_id → warning, no error
✅ Dashboard /contexto muestra datos correctos
✅ KPIs se calculan con trades reales

---

**Siguiente paso:** Ejecutar tests manuales o crear script automatizado.
