# 🔧 FIX: Gráficos y Scripts No Se Cargan

## ❌ PROBLEMAS DETECTADOS

### 1. **Plotly versión deprecated (v1.58.5 de 2021)**
```
WARNING: plotly-latest.min.js and plotly-latest.js are NO LONGER the latest releases
```

### 2. **Script grafico.js no se carga**
```
Ha fallado la carga del <script> con origen 
"http://127.0.0.1:5001/indicadores/static/js/grafico.js%3Fv=20260516"

Uncaught TypeError: window.grafico.cargar is not a function
```

---

## 🔍 CAUSA RAÍZ

### Problema 1: Plotly deprecated
- Usando `plotly-latest.min.js` (v1.58.5, julio 2021)
- Esta versión ya no se actualiza
- CDN apunta a versión obsoleta

### Problema 2: URL incorrecta para archivos estáticos
- **Incorrecto:** `url_for('indicadores.static', filename='js/grafico.js')`
- **Genera:** `/indicadores/static/js/grafico.js` (404 - No existe)
- **Correcto:** `url_for('static', filename='js/grafico.js')`
- **Genera:** `/static/js/grafico.js` ✅

**Por qué estaba mal:**
Los blueprints de Flask (`indicadores_bp`) pueden tener su propia carpeta `static`, 
pero en este proyecto **no la tienen**. Toda la carpeta `static/` es global.

---

## ✅ SOLUCIONES APLICADAS

### 1. Actualizar Plotly a v2.27.0 (2024)

**Archivos modificados:**
- `analisis/tecnico/grafico_avanzado.py` (2 funciones)
- `templates/indicadores.html` línea 7
- `templates/index.html` línea 232

**Cambio:**
```python
# ❌ ANTES
fig.to_html(full_html=False, include_plotlyjs="cdn")
# Usa plotly-latest.min.js (deprecated)

# ✅ DESPUÉS
fig.to_html(
    full_html=False, 
    include_plotlyjs='https://cdn.plot.ly/plotly-2.27.0.min.js'
)
```

```html
<!-- ❌ ANTES -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<!-- ✅ DESPUÉS -->
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
```

---

### 2. Corregir URLs de archivos estáticos

**Archivos modificados:**
- `templates/indicadores.html` línea 1834
- `templates/index.html` líneas 233 y 320

**Cambios:**
```jinja2
{# ❌ ANTES #}
<script src="{{ url_for('indicadores.static', filename='js/grafico.js?v=20260516') }}"></script>
<link rel="stylesheet" href="{{ url_for('indicadores.static', filename='css/indicadores.css') }}">

{# ✅ DESPUÉS #}
<script src="{{ url_for('static', filename='js/grafico.js') }}?v=20260516"></script>
<link rel="stylesheet" href="{{ url_for('static', filename='css/indicadores.css') }}">
```

**Nota:** El `?v=20260516` va FUERA de `url_for()` para evitar encoding.

---

## 📊 ARCHIVOS MODIFICADOS (5)

1. `analisis/tecnico/grafico_avanzado.py`
   - `crear_grafico_analisis_tecnico()` → Plotly 2.27.0
   - `crear_grafico_simple_sr()` → Plotly 2.27.0

2. `templates/indicadores.html`
   - Línea 7: Plotly CDN actualizado
   - Línea 1834: `url_for('static', ...)` en lugar de `indicadores.static`

3. `templates/index.html`
   - Línea 232: Plotly CDN actualizado
   - Línea 233: CSS corregido
   - Línea 320: JS grafico.js corregido

---

## ✅ RESULTADO ESPERADO

Después de estos cambios:

1. **✅ Plotly 2.27.0** (versión moderna)
2. **✅ grafico.js se carga** desde `/static/js/grafico.js`
3. **✅ CSS se carga** desde `/static/css/indicadores.css`
4. **✅ `window.grafico.cargar()` disponible**
5. **✅ Scanner funciona** correctamente

---

## 🎯 VERIFICACIÓN

```bash
# Reiniciar servidor
python app.py

# En navegador, abrir consola (F12) y verificar:
# 1. No hay error de plotly-latest deprecated
# 2. grafico.js se carga sin 404
# 3. typeof window.grafico === 'object'
# 4. typeof window.grafico.cargar === 'function'
```

---

## 📝 LECCIÓN APRENDIDA

**Flask Blueprints y archivos estáticos:**

- Si el blueprint tiene carpeta `static/` propia → `url_for('blueprint.static', ...)`
- Si usa la carpeta `static/` global → `url_for('static', ...)`

En este proyecto, `indicadores_bp` **NO tiene** su propia carpeta static, por lo tanto:
- ❌ `url_for('indicadores.static', ...)` → 404
- ✅ `url_for('static', ...)` → Correcto

---

**Fin del fix.** 🎯
