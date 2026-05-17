# 📧 GUÍA COMPLETA: CONFIGURAR GMAIL PARA ALERTAS

## 🎯 OBJETIVO
Recibir un email en **salva.mugica@gmail.com** cada vez que se dispare una alerta.

---

## 📋 PASOS DETALLADOS

### PASO 1: Activar Verificación en Dos Pasos en Gmail

1. Abre tu navegador y ve a: **https://myaccount.google.com/security**

2. Busca la sección **"Iniciar sesión en Google"**

3. Click en **"Verificación en dos pasos"**

4. Si NO está activada:
   - Click en **"Empezar"**
   - Introduce tu contraseña de Gmail
   - Elige un método de verificación:
     * **Mensajes de Google** (recomendado - notificación en móvil)
     * **Mensaje de texto SMS**
     * **Llamada de voz**
   - Sigue el proceso hasta completarlo

5. **Verificación:** Debe aparecer como "Activada" ✅

---

### PASO 2: Generar Contraseña de Aplicación

1. Ve a: **https://myaccount.google.com/apppasswords**
   
   *(Si te pide iniciar sesión, usa tu contraseña normal)*

2. En **"Selecciona la app"**:
   - Elige: **"Correo"**

3. En **"Selecciona el dispositivo"**:
   - Elige: **"Otro (nombre personalizado)"**
   - Escribe: **MiWeb Trading**

4. Click en **"Generar"**

5. Gmail te mostrará una **contraseña de 16 caracteres** como esta:
   ```
   abcd efgh ijkl mnop
   ```
   
   **⚠️ IMPORTANTE:**
   - Esta contraseña aparece **UNA SOLA VEZ**
   - Cópiala AHORA (puedes usar Ctrl+C)
   - Si la pierdes, tendrás que generar una nueva

---

### PASO 3: Crear el Archivo .env

1. Abre el **Símbolo del sistema** (CMD) o **PowerShell**

2. Escribe estos comandos **uno por uno**:

   ```cmd
   cd D:\a\MiWeb
   ```

3. Crea el archivo `.env`:

   **OPCIÓN A - Con notepad:**
   ```cmd
   notepad .env
   ```
   
   Si dice "El archivo no existe, ¿desea crearlo?" → Click **Sí**

   **OPCIÓN B - Con echo (más rápido):**
   ```cmd
   echo. > .env
   notepad .env
   ```

4. **Dentro del notepad**, escribe EXACTAMENTE esto:

   ```
   EMAIL_REMITENTE=salva.mugica@gmail.com
   EMAIL_PASSWORD=abcdefghijklmnop
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

   **⚠️ MUY IMPORTANTE:**
   - Reemplaza `abcdefghijklmnop` con tu contraseña de 16 caracteres
   - **SIN ESPACIOS** entre las letras (Gmail te la muestra con espacios, pero tú escríbela sin espacios)
   - NO uses tu contraseña normal de Gmail
   - NO pongas espacios alrededor del `=`

5. **Guarda el archivo**:
   - Archivo → Guardar
   - Cierra el notepad

6. **Verifica que se creó correctamente**:
   ```cmd
   dir .env
   ```
   
   Debería aparecer algo como:
   ```
   13/05/2026  19:30               123 .env
   ```

---

### PASO 4: Verificar el Contenido del .env

Para asegurarte de que está bien escrito:

```cmd
type .env
```

Debe mostrar:
```
EMAIL_REMITENTE=salva.mugica@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**Si hay algún error:**
```cmd
notepad .env
```
Y corrige lo que esté mal.

---

### PASO 5: Reiniciar el Servidor

1. Si el servidor está corriendo:
   - Ve a la ventana de CMD donde está `python app.py`
   - Presiona **Ctrl + C** para detenerlo

2. Inicia el servidor de nuevo:
   ```cmd
   cd D:\a\MiWeb
   python app.py
   ```

3. Deberías ver en la consola (sin errores):
   ```
   * Running on http://127.0.0.1:5001
   ```

---

### PASO 6: Probar que Funciona

1. Abre el navegador en: **http://localhost:5001/alertas**

2. Click en **"+ Nueva alerta"**

3. Crea una alerta de prueba:
   - **Ticker:** SAN.MC
   - **Nombre:** Santander
   - **Tipo:** OBJETIVO
   - **Nivel:** 3.00€ (un precio bajo para que se dispare seguro)

4. Click en **"Crear alerta"**

5. Click en **"⚡ Verificar ahora"**

6. **Deberías recibir un email** en los siguientes 10-30 segundos en **salva.mugica@gmail.com**

   **Asunto del email:**
   ```
   🔔 ALERTA: SAN.MC - OBJETIVO
   ```

---

## ✅ VERIFICACIÓN DE QUE FUNCIONA

### En la Consola del Servidor

Si todo funciona, verás:
```
✅ Email enviado: SAN.MC OBJETIVO @ 4.50€
```

Si NO funciona, verás:
```
⚠️ EMAIL_PASSWORD no configurado. Email no enviado.
📧 [SIMULADO] Alerta disparada: SAN.MC OBJETIVO @ 4.50€
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "EMAIL_PASSWORD no configurado"

**Causa:** El archivo `.env` no existe o está mal ubicado

**Solución:**
```cmd
cd D:\a\MiWeb
dir .env
```

Si NO aparece el archivo, vuelve al **PASO 3**.

---

### Error: "Authentication failed" o "Username and Password not accepted"

**Causa:** La contraseña de aplicación está mal escrita

**Soluciones:**

1. **Verifica la contraseña en el .env:**
   ```cmd
   type .env
   ```
   
   Debe tener los 16 caracteres **SIN ESPACIOS**

2. **Regenera una nueva contraseña:**
   - Ve a: https://myaccount.google.com/apppasswords
   - Genera una nueva (puedes eliminar la anterior)
   - Actualiza el `.env` con la nueva

3. **Verifica que sea la contraseña de APLICACIÓN, no tu contraseña normal**

---

### Error: "Connection refused" o "No connection could be made"

**Causa:** Firewall bloqueando el puerto 587

**Solución:**
- Verifica tu conexión a internet
- Desactiva temporalmente el antivirus/firewall para probar
- Verifica que el puerto 587 no esté bloqueado

---

### El email NO llega (sin errores en consola)

**Posibles causas:**

1. **Está en spam:**
   - Revisa la carpeta de **Spam** en Gmail

2. **Demora del servidor SMTP:**
   - Espera hasta 2-3 minutos

3. **Gmail bloqueó el envío:**
   - Ve a: https://myaccount.google.com/notifications
   - Revisa si hay alertas de seguridad

---

## 📝 RESUMEN RÁPIDO

```bash
# 1. Activar verificación en 2 pasos
https://myaccount.google.com/security

# 2. Generar contraseña de aplicación
https://myaccount.google.com/apppasswords

# 3. Crear .env
cd D:\a\MiWeb
notepad .env

# Contenido (sin espacios en la contraseña):
EMAIL_REMITENTE=salva.mugica@gmail.com
EMAIL_PASSWORD=tu16caracteressinspacios
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# 4. Reiniciar servidor
Ctrl+C
python app.py

# 5. Probar alerta
http://localhost:5001/alertas
```

---

## 🎯 RESULTADO ESPERADO

Una vez configurado, cada vez que una alerta se dispare:

1. ✅ Se marca como disparada en la BD
2. ✅ Aparece en "Historial reciente" de la web
3. ✅ Se envía un email profesional a salva.mugica@gmail.com con:
   - Ticker y nombre del valor
   - Tipo de alerta (OBJETIVO / STOP-LOSS)
   - Precio actual vs nivel configurado
   - Diferencia en € y %
   - Link directo a la web

---

**¿Algún problema? Sigue los pasos de "SOLUCIÓN DE PROBLEMAS" arriba.** 🔧✅
