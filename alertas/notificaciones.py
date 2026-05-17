# alertas/notificaciones.py
"""
Sistema de notificaciones por email para alertas disparadas
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Configuración de email
EMAIL_DESTINO = "salva.mugica@gmail.com"
EMAIL_REMITENTE = os.environ.get('EMAIL_REMITENTE', 'alertas@miweb.trading')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))


def enviar_email_alerta(ticker, nombre, tipo, nivel, precio_actual):
    """Envía un email cuando se dispara una alerta"""
    
    if not EMAIL_PASSWORD:
        logger.warning("⚠️ EMAIL_PASSWORD no configurado. Email no enviado.")
        logger.info(f"📧 [SIMULADO] Alerta disparada: {ticker} {tipo} @ {precio_actual:.2f}€")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔔 ALERTA: {ticker} - {tipo}"
        msg['From'] = EMAIL_REMITENTE
        msg['To'] = EMAIL_DESTINO
        
        emoji = "🎯" if tipo == "OBJETIVO" else "⚠️"
        color = "#10b981" if tipo == "OBJETIVO" else "#ef4444"
        
        diferencia = precio_actual - nivel
        diferencia_pct = (diferencia / nivel) * 100
        
        texto = f"""
🔔 ALERTA DISPARADA - MiWeb

{emoji} {ticker} - {nombre}

Tipo: {tipo}
Nivel: {nivel:.2f}€
Precio: {precio_actual:.2f}€
Diferencia: {diferencia:+.2f}€ ({diferencia_pct:+.2f}%)

{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        
        html = f"""<!DOCTYPE html><html><body style="font-family:Arial;margin:0;padding:20px;background:#f8fafc">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;box-shadow:0 4px 6px rgba(0,0,0,0.1)">
<div style="background:{color};padding:30px;text-align:center"><h1 style="margin:0;color:white">{emoji} ALERTA DISPARADA</h1></div>
<div style="padding:30px">
<div style="background:#f8fafc;padding:20px;border-radius:8px;margin-bottom:20px"><h2 style="margin:0 0 10px 0">{ticker}</h2><p style="margin:0;color:#64748b">{nombre}</p></div>
<table style="width:100%;border-collapse:collapse">
<tr><td style="padding:12px 0;border-bottom:1px solid #e5e7eb"><strong>Tipo:</strong></td><td style="padding:12px 0;border-bottom:1px solid #e5e7eb;text-align:right"><span style="background:{color}22;color:{color};padding:4px 12px;border-radius:6px">{tipo}</span></td></tr>
<tr><td style="padding:12px 0;border-bottom:1px solid #e5e7eb"><strong>Nivel:</strong></td><td style="padding:12px 0;border-bottom:1px solid #e5e7eb;text-align:right">{nivel:.2f}€</td></tr>
<tr><td style="padding:12px 0;border-bottom:1px solid #e5e7eb"><strong>Precio actual:</strong></td><td style="padding:12px 0;border-bottom:1px solid #e5e7eb;text-align:right;color:{color};font-weight:600;font-size:18px">{precio_actual:.2f}€</td></tr>
<tr><td style="padding:12px 0"><strong>Diferencia:</strong></td><td style="padding:12px 0;text-align:right;color:{color};font-weight:600">{diferencia:+.2f}€ ({diferencia_pct:+.2f}%)</td></tr>
</table>
<div style="margin-top:30px;text-align:center"><a href="https://trading.salvanavegacion.es/alertas" style="display:inline-block;background:{color};color:white;padding:14px 32px;text-decoration:none;border-radius:8px;font-weight:600">Ver en MiWeb →</a></div>
</div>
<div style="background:#f8fafc;padding:20px;text-align:center;color:#94a3b8;font-size:12px">{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>
</div></body></html>"""
        
        msg.attach(MIMEText(texto, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email enviado: {ticker} {tipo} @ {precio_actual:.2f}€")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        return False
