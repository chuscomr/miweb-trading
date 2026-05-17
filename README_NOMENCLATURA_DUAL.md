# 📊 NOMENCLATURA DUAL - SETUP TÉCNICO vs GLOBAL

## 🎯 CAMBIOS IMPLEMENTADOS (v85.14)

### ANTES (Confuso):
```
Setup: EXCELENTE (10/10)
Tamaño: 38%
```
❓ ¿Por qué "Excelente" recomienda solo 38%?

### DESPUÉS (Claro):
```
📊 Setup Técnico: EXCELENTE (10/10)
💼 Fundamental: 🟡 DÉBIL (4/10)
🎯 Setup Global: BUENO (8.2/10)

📈 Decisión: COMPRA
💰 Tamaño: 38%
```
✅ Ahora se entiende: técnica perfecta, fundamental débil = tamaño reducido

---

## 📋 NOMENCLATURA DETALLADA

### 1️⃣ SETUP TÉCNICO (0-10)
**Evalúa SOLO el gráfico:**
- MM50 > MM200
- Pendiente MM20
- Calidad del pullback (5-8%)
- RSI semanal (40-55)
- Distancia a MM20
- Volumen decreciente

**Clasificación:**
- 8.5-10.0 → EXCELENTE
- 6.5-8.4 → BUENO
- 5.5-6.4 → MEDIOCRE
- 0.0-5.4 → DÉBIL

---

### 2️⃣ FUNDAMENTAL (0-10) con Emoji Visual

**Evalúa la empresa:**
- EV/EBITDA
- ROE
- Deuda/EBITDA
- FCF yield
- Rating sectorial
- Insiders

**Clasificación con emojis:**
- 🟢 SÓLIDO (8.0-10.0) - Verde
- 🟡 ACEPTABLE (6.0-7.9) - Amarillo
- 🟠 DÉBIL (4.0-5.9) - Naranja
- 🔴 RIESGO (0.0-3.9) - Rojo

---

### 3️⃣ SETUP GLOBAL (Combinado)

**Fórmula:**
```
Score Global = (Técnico × 0.70) + (Fundamental × 0.30)
```

**¿Por qué 70-30?**
Somos **traders de momentum**, no value investors.
El gráfico manda, el fundamental es contexto.

**Clasificación:**
- 8.5-10.0 → EXCELENTE
- 7.5-8.4 → MUY BUENO
- 6.5-7.4 → BUENO
- 5.5-6.4 → ACEPTABLE
- 0.0-5.4 → DÉBIL

---

## 📊 EJEMPLOS VISUALES

### EJEMPLO 1: Técnica Perfecta + Fundamental Débil
```
📊 Setup Técnico: EXCELENTE (10/10)
💼 Fundamental: 🟠 DÉBIL (4/10)
🎯 Setup Global: BUENO (8.2/10)

Cálculo: (10 × 0.7) + (4 × 0.3) = 7.0 + 1.2 = 8.2
```
**Interpretación:** Comprar con cautela (tamaño medio-bajo)

---

### EJEMPLO 2: Setup Perfecto
```
📊 Setup Técnico: EXCELENTE (10/10)
💼 Fundamental: 🟢 SÓLIDO (9/10)
🎯 Setup Global: EXCELENTE (9.7/10)

Cálculo: (10 × 0.7) + (9 × 0.3) = 7.0 + 2.7 = 9.7
```
**Interpretación:** Comprar fuerte (tamaño máximo)

---

### EJEMPLO 3: Fundamental Excelente, Técnica Regular
```
📊 Setup Técnico: BUENO (7/10)
💼 Fundamental: 🟢 SÓLIDO (10/10)
🎯 Setup Global: MUY BUENO (7.9/10)

Cálculo: (7 × 0.7) + (10 × 0.3) = 4.9 + 3.0 = 7.9
```
**Interpretación:** Buena empresa pero esperamos mejor entrada técnica

---

### EJEMPLO 4: Empresa en Riesgo
```
📊 Setup Técnico: EXCELENTE (9/10)
💼 Fundamental: 🔴 RIESGO (2/10)
🎯 Setup Global: ACEPTABLE (6.9/10)

Cálculo: (9 × 0.7) + (2 × 0.3) = 6.3 + 0.6 = 6.9
```
**Interpretación:** Trampa de valor - No operar o vigilar

---

## 🎨 DÓNDE SE MUESTRA

### ✅ Sistema Medio Plazo:
- Scanner de oportunidades
- Análisis individual de ticker
- Panel de seguimiento

### ❌ NO se muestra en:
- Sistema Swing (score simple)
- Sistema Posicional (lógica diferente)

---

## 🔧 ARCHIVOS MODIFICADOS

1. **`estrategias/medio/logica_medio.py`**
   - `clasificar_fundamental()` - Nueva función
   - `calcular_setup_global()` - Nueva función

2. **`templates/medio*.html`**
   - Mostrar 3 líneas en vez de 1
   - Emojis de color según fundamental

3. **`estrategias/medio/scanner_medio.py`**
   - Calcular ambos scores
   - Pasar datos adicionales al template

---

## 💡 VENTAJAS DE ESTA NOMENCLATURA

✅ **Clara:** Se ve de un vistazo qué es técnico y qué es fundamental
✅ **Visual:** Emojis de color identifican rápido la calidad fundamental
✅ **Educativa:** El trader entiende por qué un "setup excelente" puede tener tamaño pequeño
✅ **Flexible:** Permite comprar setups técnicos perfectos con fundamental débil
✅ **Realista:** "Excelente Global" es difícil de alcanzar (requiere ambos altos)

---

## ⚙️ CONFIGURACIÓN

Si quieres ajustar la ponderación, edita `logica_medio.py`:

```python
def calcular_setup_global(...):
    PESO_TECNICO = 0.70      # Cambiar a 0.60 para más peso fundamental
    PESO_FUNDAMENTAL = 0.30  # Cambiar a 0.40 para más peso fundamental
```

**Recomendado:** Mantener 70-30 para trading de momentum

---

## 🚀 RESULTADO FINAL

**Comunicación más clara = Mejores decisiones**

Ahora el sistema NO dice "Excelente" a todo lo que tenga buena técnica.
Solo los setups REALMENTE perfectos (técnica + fundamental) merecen "Excelente Global".

**v85.14 - Nomenclatura Dual Implementada** ✅
