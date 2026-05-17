# 📧 CONFIGURACIÓN DE NOTIFICACIONES EMAIL

## 🎯 RESUMEN

Las alertas ahora envían notificaciones automáticas por email a **salva.mugica@gmail.com** cuando se disparan.

---

## ⚙️ CONFIGURACIÓN (5 MINUTOS)

### **PASO 1: Crear contraseña de aplicación en Gmail**

1. Ve a: https://myaccount.google.com/apppasswords
2. Inicia sesión con tu cuenta de Gmail
3. En "Nombre de la app", escribe: **MiWeb Trading**
4. Click en **"Crear"**
5. **Copia la contraseña de 16 dígitos** (ej: `abcd efgh ijkl mnop`)

---

### **PASO 2: Crear archivo .env**

```bash
cd D:\a\MiWeb
copy .env.example .env
notepad .env
```

Edita el archivo `.env` con tus datos:

```
EMAIL_REMITENTE=tu_email@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**IMPORTANTE:** Usa la contraseña de aplicación que generaste en el paso 1, **NO tu contraseña normal de Gmail**.

---

### **PASO 3: Reiniciar el servidor**

```bash
# Detén el servidor (Ctrl+C)
# Reinicia:
python app.py
```

---

### **PASO 4: Probar**

Ejecuta el test de email:

```bash
python alertas/notificaciones.py
```

Deberías ver:
```
📧 Enviando email de prueba...
✅ Email enviado correctamente a salva.mugica@gmail.com
```

**Y recibirás un email con 2 alertas de prueba** en tu bandeja de entrada.

---

## 🔔 CÓMO FUNCIONA

1. **Creas alertas** en la web (Ej: BKT.MC STOP-LOSS 13.61€)
2. **Click en "⚡ Verificar ahora"**
3. **Si una alerta se dispara:**
   - 🔔 Popup en la web
   - 📧 Email a salva.mugica@gmail.com con detalles

---

## 📧 EJEMPLO DE EMAIL

**Asunto:** 🔔 2 Alerta(s) Disparada(s) - MiWeb Trading

**Contenido:**
```
═══════════════════════════════════════════════════════════
🔔 ALERTAS DISPARADAS - MiWeb Trading
═══════════════════════════════════════════════════════════

Fecha: 12/05/2026 17:45:30
Total: 2 alerta(s)

1. 🛑 BKT.MC - Bankinter
   Tipo: STOP-LOSS
   Nivel configurado: 13.61€
   Precio actual: 13.57€
   Diferencia: -0.04€ (-0.3%)

2. 🎯 ACX.MC - Acerinox
   Tipo: OBJETIVO
   Nivel configurado: 17.90€
   Precio actual: 18.05€
   Diferencia: +0.15€ (+0.8%)
```

---

## 🔧 TROUBLESHOOTING

### **"❌ Error enviando email"**

**Causa:** EMAIL_PASSWORD no configurado o incorrecto

**Solución:**
1. Verifica que `.env` exista en la raíz del proyecto
2. Verifica que `EMAIL_PASSWORD` tenga la contraseña de aplicación
3. Reinicia el servidor Flask

---

### **"Authentication failed"**

**Causa:** Contraseña incorrecta

**Solución:**
1. Genera una nueva contraseña de aplicación en Gmail
2. Actualiza `EMAIL_PASSWORD` en `.env`
3. Reinicia el servidor

---

### **No recibo el email**

**Revisa:**
1. Carpeta de **Spam** en Gmail
2. Log del servidor (`python app.py`) para ver errores
3. Ejecuta `python alertas/notificaciones.py` para test directo

---

## 🚀 VERIFICACIÓN AUTOMÁTICA (OPCIONAL)

Si quieres que verifique alertas cada 5 minutos sin hacer click manual:

```bash
notepad verificar_automatico.py
```

```python
import time
import requests

while True:
    try:
        r = requests.post('http://localhost:5001/alertas/verificar')
        data = r.json()
        if data['total_disparadas'] > 0:
            print(f"🔔 {data['total_disparadas']} alertas disparadas!")
            if data.get('email_enviado'):
                print("📧 Email enviado correctamente")
        else:
            print(f"✓ {data['verificadas']} alertas OK")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(300)  # 5 minutos
```

Ejecuta en otra ventana:
```bash
python verificar_automatico.py
```

---

## 📝 CAMBIAR EMAIL DE DESTINO

Si quieres enviar a otro email:

1. Abre: `alertas/notificaciones.py`
2. Línea 14: cambia `EMAIL_DESTINO = "salva.mugica@gmail.com"`
3. Guarda y reinicia servidor

---

## ✅ RESUMEN

- ✅ Email automático cuando alertas se disparan
- ✅ HTML formateado profesional
- ✅ Detalles completos de cada alerta
- ✅ Link directo a la web
- ✅ Configuración en 5 minutos

**¡Listo! Recibirás emails cada vez que una alerta se dispare! 📧🔔**
