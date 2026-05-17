# 🔔 SISTEMA DE ALERTAS AUTOMÁTICAS

## 🚀 CÓMO USAR

### Arranque Automático (Recomendado)

Simplemente ejecuta:

```cmd
arrancar.bat
```

Esto abrirá **2 ventanas**:

1. **Servidor Flask** - Puerto 5001
2. **Verificador de Alertas** - Cada 5 minutos

Para **detener todo**, cierra la ventana principal o presiona una tecla.

---

## ⚙️ CONFIGURACIÓN

### Cambiar Frecuencia de Verificación

Edita `verificar_automatico.py` línea 10:

```python
INTERVALO_MINUTOS = 5  # Cambiar a 1, 10, 15, 30, etc.
```

**Ejemplos:**
- Cada 1 minuto: `INTERVALO_MINUTOS = 1`
- Cada 10 minutos: `INTERVALO_MINUTOS = 10`
- Cada 30 minutos: `INTERVALO_MINUTOS = 30`

---

## 📊 QUÉ HACE EL VERIFICADOR

Cada X minutos:

1. ✅ Consulta todas las alertas activas en la BD
2. ✅ Obtiene el precio actual de cada ticker (Yahoo Finance)
3. ✅ Compara con los niveles configurados:
   - **OBJETIVO:** Si precio >= nivel → dispara
   - **STOP-LOSS:** Si precio <= nivel → dispara
4. ✅ Si se dispara:
   - Marca la alerta como disparada en BD
   - Aparece en "Historial reciente" (web)
   - 📧 Envía email a salva.mugica@gmail.com
5. ✅ Muestra resumen en consola

---

## 🔍 LOGS DEL VERIFICADOR

**Cuando NO hay alertas disparadas:**
```
[13/05/2026 19:30:00] Verificación #1... ✓ OK - 5 alertas verificadas, ninguna disparada
[13/05/2026 19:35:00] Verificación #2... ✓ OK - 5 alertas verificadas, ninguna disparada
```

**Cuando SÍ hay alertas disparadas:**
```
[13/05/2026 19:40:00] Verificación #3... 🔔 2 ALERTA(S) DISPARADA(S)!
   → BKT.MC STOP-LOSS: 13.57€ (nivel: 13.61€)
   → SAN.MC OBJETIVO: 4.52€ (nivel: 4.50€)
   📧 Email enviado a salva.mugica@gmail.com
```

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Error: "No se pudo conectar al servidor"

**Causa:** El servidor Flask no está corriendo

**Solución:** 
- Asegúrate de que la ventana "MiWeb Flask" esté abierta
- O ejecuta manualmente: `python app.py`

### Error: "Module 'requests' not found"

**Causa:** Falta instalar la librería requests

**Solución:**
```cmd
pip install requests
```

### No recibo emails

**Verifica:**

1. Archivo `.env` existe y tiene la contraseña correcta:
   ```cmd
   type .env
   ```

2. El servidor muestra en consola:
   ```
   ✅ Email enviado: TICKER TIPO @ precio
   ```
   
   Si muestra:
   ```
   ⚠️ EMAIL_PASSWORD no configurado
   ```
   → El archivo `.env` está mal configurado

---

## 🛑 DETENER EL SISTEMA

**Opción 1:** Cierra la ventana principal de `arrancar.bat`

**Opción 2:** Presiona cualquier tecla en la ventana principal

**Opción 3:** Cierra manualmente las 2 ventanas:
- "MiWeb Flask"
- "MiWeb Alertas"

---

## 📝 ARCHIVOS DEL SISTEMA

```
MiWeb/
├── arrancar.bat              ← Arranca todo automáticamente
├── verificar_automatico.py   ← Script del verificador
├── .env                      ← Configuración email (contraseña Gmail)
├── alertas/
│   └── alertas.db           ← Base de datos de alertas
└── alertas/
    └── notificaciones.py     ← Módulo de envío de emails
```

---

## ✅ VERIFICACIÓN MANUAL

Si prefieres verificar manualmente en vez de automático:

1. Ve a: http://localhost:5001/alertas
2. Click en **"⚡ Verificar ahora"**
3. Las alertas disparadas aparecerán inmediatamente

---

## 🎯 EJEMPLO DE USO COMPLETO

1. **Arrancar sistema:**
   ```cmd
   arrancar.bat
   ```

2. **Crear alerta:**
   - Abre: http://localhost:5001/alertas
   - Nueva alerta: BKT.MC, STOP-LOSS, 13.60€

3. **El sistema automáticamente:**
   - Verifica cada 5 minutos
   - Si BKT.MC baja a 13.60€ o menos
   - 📧 Te envía email
   - Aparece en historial web

4. **Para detener:**
   - Cierra la ventana principal

---

**¡Sistema funcionando 24/7 sin intervención manual!** 🚀🔔✅
