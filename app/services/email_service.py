"""
Servicio de Email para PreIncubadora AI
Maneja el envío de correos para recuperación de contraseña
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para enviar correos electrónicos"""
    
    def __init__(self):
        """Inicializar configuración de email"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@preincubadora.ai")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.sender_name = "PreIncubadora AI"
    
    def send_password_reset_email(self, recipient_email: str, reset_token: str, user_name: str = "") -> Tuple[bool, str]:
        """
        Enviar correo de recuperación de contraseña
        
        Args:
            recipient_email: Email del usuario
            reset_token: Token de recuperación
            user_name: Nombre del usuario (opcional)
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # URL de recuperación (en producción, cambiar por la URL real)
            reset_url = f"http://127.0.0.1:5000/reset-password/{reset_token}"
            
            # Crear mensaje
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Recupera tu contraseña - PreIncubadora AI"
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = recipient_email
            
            # Cuerpo de texto plano
            text = f"""\
Hola {user_name or 'usuario'},

Has solicitado recuperar tu contraseña de PreIncubadora AI.

Para cambiar tu contraseña, haz clic en el siguiente enlace:
{reset_url}

Este enlace es válido por 1 hora.

Si no solicitaste esta recuperación, ignora este correo.

Saludos,
El equipo de PreIncubadora AI
"""
            
            # Cuerpo HTML
            html = f"""\
<html>
  <body style="font-family: 'Inter', -apple-system, sans-serif; color: #333; line-height: 1.6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <!-- Header -->
      <div style="text-align: center; margin-bottom: 30px; border-bottom: 1px solid #e0e0e0; padding-bottom: 20px;">
        <h2 style="color: #2563EB; margin: 0;">PreIncubadora AI</h2>
        <p style="color: #666; margin: 5px 0 0 0; font-size: 14px;">Recuperación de contraseña</p>
      </div>
      
      <!-- Content -->
      <div style="margin-bottom: 30px;">
        <p style="margin: 0 0 15px 0;">¡Hola <strong>{user_name or 'usuario'}</strong>!</p>
        
        <p style="margin: 0 0 20px 0; color: #555;">
          Has solicitado recuperar tu contraseña de <strong>PreIncubadora AI</strong>. 
          Para continuar, haz clic en el botón de abajo.
        </p>
        
        <!-- CTA Button -->
        <div style="text-align: center; margin: 30px 0;">
          <a href="{reset_url}" 
             style="display: inline-block; background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); 
                    color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; 
                    font-weight: 600; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.39);">
            Cambiar Contraseña
          </a>
        </div>
        
        <!-- Warning -->
        <p style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 12px; 
                  margin: 20px 0; border-radius: 4px; font-size: 13px; color: #78350F;">
          ⏱️ <strong>Válido por 1 hora:</strong> Este enlace expirará en una hora por razones de seguridad.
        </p>
        
        <!-- Alternative -->
        <p style="font-size: 13px; color: #666; margin: 20px 0 0 0;">
          Si el botón no funciona, copia y pega este enlace en tu navegador:
        </p>
        <p style="font-size: 12px; color: #2563EB; word-break: break-all; 
                  background: #f5f5f5; padding: 10px; border-radius: 4px; margin: 10px 0;">
          {reset_url}
        </p>
      </div>
      
      <!-- Security Info -->
      <div style="background: #EEF2FF; border: 1px solid #DBEAFE; padding: 15px; 
                  border-radius: 6px; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 13px; color: #1E40AF;">
          <strong>🔒 Seguridad:</strong> Si no solicitaste esta recuperación, por favor ignora este correo. 
          Tu contraseña permanecerá segura.
        </p>
      </div>
      
      <!-- Footer -->
      <div style="border-top: 1px solid #e0e0e0; padding-top: 20px; text-align: center; 
                  font-size: 12px; color: #999;">
        <p style="margin: 0 0 10px 0;">
          © 2026 PreIncubadora AI. Todos los derechos reservados.
        </p>
        <p style="margin: 0;">
          <a href="https://preincubadora.ai" style="color: #2563EB; text-decoration: none;">
            Visita nuestro sitio web
          </a>
        </p>
      </div>
    </div>
  </body>
</html>
"""
            
            # Adjuntar partes
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            msg.attach(part1)
            msg.attach(part2)
            
            # Enviar correo
            # En desarrollo, mostrar mensaje en logs si no hay SMTP configurado
            if not self.sender_password:
                logger.warning(f"Email no configurado. Se habría enviado reset a: {recipient_email}")
                logger.info(f"Token: {reset_token}")
                return True, "Correo enviado correctamente (desarrollo)"
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Correo de recuperación enviado a: {recipient_email}")
            return True, "Correo de recuperación enviado exitosamente"
            
        except Exception as e:
            logger.error(f"Error al enviar correo de recuperación: {str(e)}")
            return False, f"Error al enviar correo: {str(e)}"


# Instancia global
email_service = EmailService()
