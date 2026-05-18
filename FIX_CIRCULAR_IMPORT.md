# 🔧 FIX CIRCULAR IMPORT - analytics/integrador.py

## ❌ PROBLEMA

Al arrancar la aplicación, crash con:
```
ImportError: cannot import name 'actualizar_trade' from partially initialized module 'analytics' 
(most likely due to a circular import)
```

## 🔍 CAUSA

**Circular import en módulo analytics:**

1. `analytics/__init__.py` línea 5:
   ```python
   from .integrador import registrar_apertura, registrar_cierre, ...
   ```

2. `analytics/integrador.py` línea 9:
   ```python
   from analytics import actualizar_trade, registrar_trade  # ❌ CIRCULAR
   ```

**Flujo del error:**
```
app.py 
  → import contexto_bp 
    → import analytics.metrics
      → import analytics.__init__
        → import analytics.integrador
          → import analytics  ⚠️ CIRCULAR - analytics aún no inicializado
            → ImportError
```

## ✅ SOLUCIÓN

Cambiar import relativo a absoluto en `analytics/integrador.py`:

```python
# ❌ ANTES (línea 9)
from analytics import actualizar_trade, registrar_trade

# ✅ DESPUÉS
from analytics.trades_log import actualizar_trade, registrar_trade
```

**Por qué funciona:**
- `trades_log.py` no importa nada de `analytics/__init__.py`
- Rompe el ciclo de dependencias
- Import directo al módulo que tiene las funciones

## 🎯 ARCHIVO MODIFICADO

- `analytics/integrador.py` línea 9

## ✅ VERIFICACIÓN

```bash
$ python app.py
✅ Blueprint contexto_bp cargado
>>> APP.PY CARGADO <<<
🚀 MiWeb — servidor Flask
* Serving Flask app 'app'
```

**Sin errores.** ✅

---

**Lección:** Siempre importar desde el módulo específico cuando hay `__init__.py` con re-exports.
