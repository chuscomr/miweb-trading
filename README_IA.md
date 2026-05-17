# MiWeb - Análisis Técnico con IA

## 🚀 Funcionalidad: Análisis IA de Zonas del Gráfico

### ¿Qué hace?

Selecciona **cualquier zona del gráfico** y recibe un **análisis profesional con IA** explicando:
- Patrones chartistas detectados (incluso imperfectos)
- Contexto y estructura del mercado
- Escenarios alcistas/bajistas con probabilidades
- Recomendaciones específicas de trading

**No más detectores algorítmicos rígidos.** Claude Vision ve el gráfico completo y lo analiza como un trader experto.

---

## ⚙️ Configuración (5 minutos)

### 1. Obtener API Key de Anthropic

1. Ve a https://console.anthropic.com/settings/keys
2. Crea cuenta (gratis con $5 de crédito inicial)
3. Click en "Create Key"
4. Copia la API key (empieza con `sk-ant-api03-...`)

### 2. Configurar en MiWeb

**Opción A: Archivo .env (Recomendado)**

```bash
# En la raíz del proyecto
cp .env.example .env

# Edita .env y agrega:
ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui
```

**Opción B: Variable de entorno**

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-api03-tu-key-aqui"

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui

# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui
```

### 3. Reiniciar

```bash
# Detén el servidor (Ctrl+C)
# Vuelve a iniciar:
python app.py
```

---

## 🎯 Cómo Usar

1. **Abre cualquier gráfico** (IBEX o Continuo)
2. **Click en "🔍 Analizar Zona"** (botón azul en toolbar)
3. **Arrastra el ratón** sobre la zona que quieres analizar
4. Espera 2-3 segundos
5. **Modal muestra análisis IA completo**
6. **Arrastra el modal** por el header si tapa el gráfico

---

## 💡 Ejemplo de Análisis

**Zona seleccionada:** HCH en BBVA (14.01.26 - 26.02.26)

**Claude responde:**

```
🤖 ANÁLISIS IA - BBVA.MC

Veo un patrón Hombro-Cabeza-Hombro bajista muy bien 
formado en este gráfico.

**Patrones Detectados:**

• HCH Bajista (Confianza: 85%)
  - H1: 20.62€ (14.01.26)
  - Cabeza: 21.62€ (03.02.26) - volumen alto
  - H2: 19.71€ (23.02.26) - volumen decreciente
  - Neckline: 19.07€

Aunque el H2 está ligeramente más bajo, la estructura
es clara. El volumen confirma agotamiento comprador.

**Escenarios:**

📉 Bajista (80% prob): Rotura neckline → 16.42€
📈 Alcista (20% prob): Rebote en 19.07€

**Recomendaciones:**

• Entrada: Rotura confirmada con volumen >150%
• Stop: Por encima de 20.00€
• TP1: 17.50€ (50% posición)
• TP2: 16.42€ (resto)
```

---

## 💰 Costos

| Uso | Costo |
|-----|-------|
| Por análisis | ~$0.003 |
| 100 análisis | $0.30 |
| 1000 análisis | $3.00 |

**Muy económico** para el valor profesional que aporta.

---

## ❓ Troubleshooting

**"ANTHROPIC_API_KEY no configurada"**
→ Verifica el archivo `.env` o variable de entorno
→ Reinicia la aplicación

**"Authentication failed"**
→ API key incorrecta o sin créditos
→ Verifica en console.anthropic.com

**Modal tapa el gráfico**
→ Arrastra el modal desde el header (cursor de mover)

**Análisis lento (>5 seg)**
→ Normal en primera llamada
→ Siguientes análisis serán más rápidos

---

## 🎨 Características

✅ **Análisis directo con IA** - Sin detectores locales intermedios  
✅ **Modal arrastrable** - Mueve donde quieras  
✅ **Explicaciones detalladas** - Entiende patrones complejos  
✅ **Contexto completo** - Volumen, momentum, confluencias  
✅ **Recomendaciones específicas** - Entradas, stops, objetivos  

---

**Versión:** 85.3 - Solo IA (sin detectores locales)
