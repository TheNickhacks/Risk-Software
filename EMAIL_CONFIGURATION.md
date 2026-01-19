# Configuración de Email para Sistema de Recuperación de Contraseña

## Descripción General

El sistema de recuperación de contraseña de PreIncubadora AI utiliza correo electrónico para enviar enlaces seguros de cambio de contraseña. Esta guía te muestra cómo configurar el servicio de email.

## Configuración Rápida

### 1. Opción: Gmail (Recomendado para desarrollo)

#### Pasos:

1. **Habilitar "Acceso a aplicaciones menos seguras":**
   - Accede a tu cuenta de Google: https://myaccount.google.com
   - Ve a "Seguridad" (panel izquierdo)
   - Busca "Contraseñas de aplicaciones"
   - Si no ves esta opción, primero debes habilitar la verificación en dos pasos

2. **Generar contraseña de aplicación:**
   - En "Contraseñas de aplicaciones", selecciona:
     - Aplicación: "Correo"
     - Dispositivo: "Windows, Mac u otro dispositivo"
   - Google generará una contraseña de 16 caracteres

3. **Configurar `.env`:**
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=tu-email@gmail.com
   SENDER_PASSWORD=xxxx xxxx xxxx xxxx  # La contraseña generada de 16 caracteres
   SENDER_NAME=PreIncubadora AI
   ```

### 2. Opción: Outlook/Office365

```
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SENDER_EMAIL=tu-email@outlook.com
SENDER_PASSWORD=tu-password
SENDER_NAME=PreIncubadora AI
```

### 3. Opción: Servidor SMTP Personalizado

```
SMTP_SERVER=mail.tudominio.com
SMTP_PORT=587
SENDER_EMAIL=noreply@tudominio.com
SENDER_PASSWORD=tu-password-smtp
SENDER_NAME=PreIncubadora AI
```

## Modo de Desarrollo (Sin Email Real)

Si no deseas configurar email en desarrollo, el sistema funcionará en "modo desarrollo":
- El token se mostrará en los logs
- Se puede usar directamente para testing
- Los correos se loguearán en lugar de enviarse

Para activar el modo desarrollo:
- Simplemente no configures las variables `SENDER_EMAIL` y `SENDER_PASSWORD` en `.env`

## Validación de Configuración

### Verificar que el email está configurado correctamente:

1. **Revisión manual del .env:**
   ```bash
   cat .env | grep -i smtp
   ```

2. **Probar conexión SMTP:**
   ```python
   import smtplib
   
   server = smtplib.SMTP("smtp.gmail.com", 587)
   server.starttls()
   server.login("tu-email@gmail.com", "tu-app-password")
   print("✓ Conexión exitosa")
   server.quit()
   ```

3. **Ver logs de la aplicación:**
   - Si el email se configura correctamente, verás mensajes de éxito en los logs
   - Si hay errores, verás mensajes descriptivos

## Seguridad

### Mejores Prácticas:

1. **Nunca commits credenciales:**
   - `.env` nunca debe estar en Git (está en `.gitignore`)
   - Usa variables de entorno en producción

2. **Contraseñas de aplicación vs contraseñas principales:**
   - Siempre usa contraseñas de aplicación específicas (ej: Gmail)
   - Nunca uses tu contraseña principal

3. **Tokens de recuperación:**
   - Expiran después de 1 hora
   - Son UUIDs seguros (36 caracteres aleatorios)
   - Se limpian después de usarse

## Troubleshooting

### Error: "SMTP authentication failed"
- Verifica que `SENDER_EMAIL` y `SENDER_PASSWORD` sean correctos
- Para Gmail, asegúrate de usar la contraseña de aplicación, no la principal

### Error: "Connection timeout"
- Verifica que `SMTP_SERVER` y `SMTP_PORT` sean correctos
- Si usas VPN o firewall, asegúrate de permitir conexiones SMTP

### El correo no llega
- Revisa la carpeta de spam
- Verifica que el `SENDER_EMAIL` sea correcto
- Revisa los logs de la aplicación para mensajes de error

### No veo logs de email
- Si no configuraste SMTP, el sistema mostrará el token en logs
- Busca en los logs: "Password reset email would be sent"

## Configuración en Producción

Para producción, considera:

1. **Usar servicio de email dedicado:**
   - SendGrid (https://sendgrid.com)
   - Mailgun (https://www.mailgun.com)
   - AWS SES (https://aws.amazon.com/ses)

2. **Configurar URL correcta:**
   - En el archivo `app/services/email_service.py`, cambiar:
   ```python
   reset_url = f"http://127.0.0.1:5000/reset-password/{reset_token}"
   ```
   - Por tu URL de producción:
   ```python
   reset_url = f"https://tu-dominio.com/reset-password/{reset_token}"
   ```

3. **Variables de entorno seguras:**
   - Usar Secrets Manager (AWS Secrets Manager, Azure Key Vault, etc.)
   - No almacenar credenciales en archivos

4. **Certificados SSL/TLS:**
   - Usar `SMTP_PORT=465` con SSL completo
   - O `SMTP_PORT=587` con STARTTLS (más compatible)

## Flujo de Recuperación de Contraseña

### 1. Usuario olvida contraseña
```
Usuario → Click "Olvide mi contraseña"
```

### 2. Ingresa email
```
Usuario → Ingresa email en formulario
```

### 3. Sistema genera token
```
- Token: UUID de 36 caracteres
- Expira: En 1 hora
- Se almacena en BD asociado al usuario
```

### 4. Email enviado
```
Sistema → Envía correo con enlace
Enlace: https://dominio.com/reset-password/{token}
```

### 5. Usuario abre enlace
```
Usuario → Hace click en correo
Sistema → Valida token (existe, no expirado)
```

### 6. Usuario cambia contraseña
```
Usuario → Ingresa nueva contraseña (2 veces)
Sistema → Valida (8+ caracteres, coinciden)
Sistema → Encripta con bcrypt
Sistema → Limpia token
Sistema → Redirecciona a login
```

## Preguntas Frecuentes

### ¿Cuál es el tiempo de expiración del token?
**1 hora desde la generación**

### ¿Puedo reutilizar un token?
**No, se limpia después del primer uso**

### ¿Puedo generar múltiples tokens?
**Sí, cada solicitud genera uno nuevo (el anterior se sobrescribe)**

### ¿Es seguro el sistema?
**Sí:**
- Tokens son UUIDs aleatorios (no guessables)
- Se guardan hasheados en BD (NO en texto plano)
- Expiran automáticamente
- Se limpian después de usar
- La nueva contraseña se encripta con bcrypt

### ¿Dónde veo los correos enviados?
**En los logs de la aplicación:**
- Correos exitosos: "Password reset email sent successfully"
- Errores: Mensajes descriptivos
- Modo desarrollo: Token visible en logs

