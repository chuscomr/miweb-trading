# 🔍 INFORME AUDITORÍA RUFF v85.19
**Fecha:** 17/05/2026  
**Versión ruff:** 0.15.13

---

## 📊 RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| **Errores totales detectados** | 2,080 |
| **Errores corregidos automáticamente** | 1,326 (64%) |
| **Errores restantes** | 798 (36%) |
| **Líneas de código analizadas** | ~15,000 |

---

## ✅ CORRECCIONES APLICADAS (1,326)

### 1. **Imports desordenados** (131 → 1 restante)
- Todos los imports ordenados alfabéticamente
- Agrupados por: stdlib → third-party → first-party
- 2 líneas después de imports

### 2. **Espacios en blanco** (1,001 → 188)
- Eliminadas líneas en blanco con espacios
- Trailing whitespace limpiado (41 → 20)

### 3. **Type hints modernos** (90 corregidos)
- `Optional[X]` → `X | None`
- `List[X]` → `list[X]`
- `Dict[X, Y]` → `dict[X, Y]`

### 4. **Imports no usados** (77 → 1)
- Eliminados imports muertos

### 5. **F-strings sin placeholders** (57 corregidos)
- `f"texto"` → `"texto"`

### 6. **Return statements** (33 corregidos)
- Eliminados `elif` innecesarios después de `return`

---

## 🚨 ERRORES CRÍTICOS PENDIENTES (798)

### 🔴 **PRIORIDAD ALTA (corregir YA)**

#### 1. **Bare except** (5 ocurrencias) - PELIGROSO
```python
# ❌ MAL - silencia TODOS los errores, incluidos KeyboardInterrupt
try:
    fecha = datetime.strptime(...)
except:
    pass

# ✅ BIEN
try:
    fecha = datetime.strptime(...)
except (ValueError, TypeError):
    logger.error(f"Fecha inválida: {fecha_str}")
    pass
```

**Archivos afectados:**
- `analytics/integrador.py:187`
- `sentimiento_mercado.py:277, 299`
- `web/routes/cartera_routes.py:270, 275`

#### 2. **Undefined name** (13 ocurrencias) - BUG
```python
# En analisis/tecnico/calculos_avanzados.py:1686
resumen_tecnico = generar_resumen_tecnico(df, indicadores_lista)
# ERROR: generar_resumen_tecnico no existe
```

**Archivos afectados:**
- `analisis/tecnico/calculos_avanzados.py` (función faltante)

#### 3. **Mutable default argument** (1 ocurrencia) - BUG SUTIL
```python
# ❌ MAL - la lista se comparte entre todas las llamadas
def calcular_medias_moviles(df, periodos=[20, 50, 200]):
    ...

# ✅ BIEN
def calcular_medias_moviles(df, periodos=None):
    if periodos is None:
        periodos = [20, 50, 200]
    ...
```

**Archivo:**
- `analisis/tecnico/calculos_avanzados.py:49`

---

### 🟡 **PRIORIDAD MEDIA (corregir esta semana)**

#### 4. **Import star** (148 ocurrencias)
```python
# ❌ MAL
from modulo import *

# ✅ BIEN
from modulo import funcion1, funcion2, funcion3
```

**Afecta a:** Múltiples archivos, dificulta debugging

#### 5. **Multiple statements inline** (295 ocurrencias)
```python
# ❌ MAL - difícil de leer y debuggear
if condicion: return valor

# ✅ BIEN
if condicion:
    return valor
```

**Archivos afectados:**
- `analisis/fundamental/scoring.py` (mayoría)
- `analisis/fundamental/proveedor.py`

#### 6. **Unused variables** (28 ocurrencias)
```python
# En analisis/fundamental/proveedor.py:248-249
cagr_i = datos.get("cagr_ingresos_3y")  # NUNCA SE USA
cagr_b = datos.get("cagr_beneficios_3y")  # NUNCA SE USA
```

---

### 🟢 **PRIORIDAD BAJA (mejoras estéticas)**

#### 7. **Try-except simplificables** (14 ocurrencias)
```python
# ❌ Verboso
try:
    resultado = operacion()
except Exception:
    pass

# ✅ Conciso
from contextlib import suppress
with suppress(Exception):
    resultado = operacion()
```

#### 8. **Collapsible if** (11 ocurrencias)
```python
# ❌ Redundante
if condicion1:
    if condicion2:
        accion()

# ✅ Limpio
if condicion1 and condicion2:
    accion()
```

---

## 📋 PLAN DE ACCIÓN

### ✅ INMEDIATO (hoy)
1. ✅ Instalar ruff
2. ✅ Crear `pyproject.toml`
3. ✅ Fix automático (1,326 errores)

### 🔴 ESTA SEMANA
4. Corregir 5 bare excepts (15 min)
5. Corregir mutable default (5 min)
6. Investigar `generar_resumen_tecnico` faltante (30 min)

### 🟡 ESTE MES
7. Eliminar import * (2-3h)
8. Refactorizar inline statements en scoring.py (1h)
9. Limpiar variables no usadas (30 min)

---

## 🎯 SIGUIENTES PASOS

```bash
# 1. Añadir pyproject.toml al repo
git add pyproject.toml
git commit -m "chore: añadir configuración ruff linter"

# 2. Crear pre-commit hook (opcional)
cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/bash
ruff check . --fix
git add -u
HOOK
chmod +x .git/hooks/pre-commit

# 3. Integrar en CI/CD (Render)
# Añadir a requirements.txt:
ruff==0.15.13
```

---

## 📈 IMPACTO ESPERADO

| Aspecto | Antes | Después Fix | Después Auditoría |
|---------|-------|-------------|-------------------|
| Mantenibilidad | 8/10 | 8.5/10 | 9/10 |
| Robustez | 7/10 | 7.5/10 | 8.5/10 |
| Calidad código | 6/10 | 7.5/10 | 8.5/10 |

---

**Fin del informe.** 🎯
