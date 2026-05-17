# CONFIGURACIÓN DE NOTIFICACIONES POR EMAIL

## 📧 Email de destino configurado

Las alertas se envían automáticamente a: **salva.mugica@gmail.com**

---

## 🔑 CONFIGURAR GMAIL PARA ENVIAR EMAILS

Para que el sistema pueda enviar emails, necesitas configurar una "Contraseña de aplicación" de Gmail:

### Paso 1: Activar la verificación en dos pasos

1. Ve a: https://myaccount.google.com/security
2. En "Iniciar sesión en Google", activa **"Verificación en dos pasos"**
3. Sigue el proceso de configuración (necesitarás tu teléfono)

### Paso 2: Crear contraseña de aplicación

1. Ve a: https://myaccount.google.com/apppasswords
2. En "Selecciona la app", elige **"Correo"**
3. En "Selecciona el dispositivo", elige **"Otro (nombre personalizado)"**
4. Escribe: **"MiWeb Trading"**
5. Click en **"Generar"**
6. Gmail te mostrará una contraseña de 16 caracteres (ej: `abcd efgh ijkl mnop`)
7. **Cópiala** (no la podrás volver a ver)

### Paso 3: Configurar en MiWeb

Crea o edita el archivo `.env` en la raíz del proyecto:

```bash
cd D:\a\MiWeb
notepad .env
```

Añade estas líneas:

```
EMAIL_REMITENTE=salva.mugica@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**(Reemplaza `abcdefghijklmnop` con tu contraseña de aplicación generada, SIN ESPACIOS)**

### Paso 4: Reiniciar el servidor

```bash
# Detener servidor (Ctrl+C)
# Reiniciar:
python app.py
```

---

## ✅ PROBAR QUE FUNCIONA

1. Crea una alerta de prueba:
   - **Ticker:** SAN.MC
   - **Tipo:** OBJETIVO
   - **Nivel:** 3.00€ (un precio bajo para que se dispare)

2. Click en **"⚡ Verificar ahora"**

3. Deberías recibir un email en **salva.mugica@gmail.com** con el asunto:
   ```
   🔔 ALERTA: SAN.MC - OBJETIVO
   ```

---

## 🔔 CÓMO FUNCIONAN LAS NOTIFICACIONES

### Cuando se dispara una alerta:

1. ✅ Se marca como disparada en la BD
2. ✅ Aparece en "Historial reciente" (web)
3. ✅ Se envía un EMAIL a `salva.mugica@gmail.com` con:
   - Nombre del valor
   - Tipo de alerta (OBJETIVO / STOP-LOSS)
   - Nivel configurado
   - Precio actual
   - Diferencia en € y %
   - Link directo a la web

---

## ⚠️ SI NO FUNCIONA

### Email no se envía (sin error visible)

**Verifica en los logs del servidor:**
```
⚠️ EMAIL_PASSWORD no configurado. Email no enviado.
📧 [SIMULADO] Alerta disparada: SAN.MC OBJETIVO @ 4.50€
```

→ **Solución:** El archivo `.env` no está bien configurado o el servidor no se reinició

### Error: "Authentication failed"

```
❌ Error enviando email: (535, b'5.7.8 Username and Password not accepted')
```

→ **Solución:** 
- Verifica que la contraseña de aplicación esté correcta
- Asegúrate de copiarla SIN ESPACIOS
- Regenera una nueva contraseña de aplicación

### Error: "Connection refused"

```
❌ Error enviando email: [Errno 10061] No connection could be made
```

→ **Solución:**
- Verifica tu conexión a internet
- Comprueba que el puerto 587 no esté bloqueado por firewall

---

## 🚀 VERIFICACIÓN AUTOMÁTICA (OPCIONAL)

Si quieres que verifique automáticamente cada 5 minutos:

```bash
notepad verificar_automatico.py
```

```python
import time
import requests

print("🤖 Verificador automático iniciado")
print("Verificará alertas cada 5 minutos...")

while True:
    try:
        r = requests.post('http://localhost:5001/alertas/verificar')
        data = r.json()
        
        if data['total_disparadas'] > 0:
            print(f"🔔 {data['total_disparadas']} alertas disparadas! Email enviado.")
        else:
            print(f"✓ {data['verificadas']} alertas verificadas (ninguna disparada)")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(300)  # 5 minutos
```

Ejecuta en segundo plano:
```bash
python verificar_automatico.py
```

---

## 📝 RESUMEN

1. ✅ Email destino: **salva.mugica@gmail.com** (ya configurado)
2. ⚙️ Necesitas: Contraseña de aplicación de Gmail
3. 📄 Crear archivo `.env` con la contraseña
4. 🔄 Reiniciar servidor
5. 🧪 Probar con alerta de test

**¡Y listo! Recibirás un email cada vez que se dispare una alerta.** 📧🔔✅
