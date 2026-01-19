# 🚀 GUÍA DE INICIO RÁPIDO - PreIncubadora AI

## ⚡ Quick Start (Docker - Recomendado)

### 1. Requisitos
- Docker Desktop instalado
- Terminal/PowerShell
- Una API Key de Google Gemini (obtén en: https://aistudio.google.com/app/apikeys)

### 2. Pasos

```bash
# 1. Navega al directorio del proyecto
cd "Software de Riesgo"

# 2. Copia el archivo .env.example
cp .env.example .env
# En Windows PowerShell:
# Copy-Item .env.example .env

# 3. Edita .env y agrega tu GEMINI_API_KEY
# Abre .env en tu editor favorito y reemplaza:
# GEMINI_API_KEY=tu-api-key-aqui

# 4. Levanta los servicios
docker-compose up -d

# 5. Espera a que PostgreSQL esté listo (10 segundos)
# Ver logs: docker-compose logs -f

# 6. Abre en el navegador
# http://localhost:5000
```

**¡Listo!** La app está corriendo. Puedes:
- Registrarte con un RUT único
- Crear un proyecto
- Interactuar con la IA

---

## 🛠️ Setup Local (Sin Docker)

### 1. Requisitos
- Python 3.11+
- PostgreSQL 16 (con servidor corriendo)
- pip / virtualenv

### 2. Pasos

```bash
# 1. Crea entorno virtual
python -m venv venv

# 2. Activa el entorno
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Copia .env
cp .env.example .env

# 5. Configura .env
# Edita con tu GEMINI_API_KEY y DATABASE_URL correcta
# Ej: DATABASE_URL=postgresql://postgres:password@localhost:5432/preincubadora_db

# 6. Crea la BD (si es nueva)
# La app lo hace automáticamente en __init__.py

# 7. Ejecuta el servidor
flask run

# 8. Abre http://localhost:5000
```

---

## 📝 Comandos Útiles (Docker)

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# Ejecutar comandos en el contenedor
docker-compose exec app flask shell

# Detener servicios
docker-compose down

# Reconstruir imagen
docker-compose up -d --build

# Ver estado de servicios
docker-compose ps

# Limpiar todo (volúmenes también)
docker-compose down -v
```

---

## 🔑 Obtener API Key de Google Gemini

1. Ve a: https://aistudio.google.com/app/apikeys
2. Click en "Create API Key"
3. Selecciona tu proyecto (o crea uno nuevo)
4. Copia la key
5. Pega en `.env`:
   ```
   GEMINI_API_KEY=tu-key-aqui
   ```

---

## ✅ Checklist de Configuración

- [ ] Docker instalado (`docker --version`)
- [ ] API Key de Gemini obtenida
- [ ] Archivo `.env` configurado
- [ ] `docker-compose up -d` ejecutado exitosamente
- [ ] PostgreSQL corriendo (healthcheck green)
- [ ] App accessible en `http://localhost:5000`
- [ ] Puedes registrarte sin errores

---

## 🐛 Troubleshooting

### Error: "Connection refused" en PostgreSQL
```bash
# Verifica que PostgreSQL esté listo
docker-compose logs postgres

# Espera 15 segundos y reinicia la app
docker-compose restart app
```

### Error: "GEMINI_API_KEY not found"
```bash
# Verifica que .env exista y tenga la key
cat .env | grep GEMINI_API_KEY

# Si no está, agrega la key manualmente
```

### Error: "Port 5000 already in use"
```bash
# Cambia el puerto en docker-compose.yml:
# Busca "ports:" y cambia "5000:5000" a "5001:5000"
```

### Error: "CREATE TABLE already exists"
```bash
# Limpia las tablas e reinicia
docker-compose down -v
docker-compose up -d
```

---

## 📊 Arquitectura de Carpetas

```
Software de Riesgo/
├── app/
│   ├── __init__.py          ← Application Factory
│   ├── models.py            ← Base de datos
│   ├── routes.py            ← Rutas principales
│   ├── services/
│   │   └── ai_service.py    ← Integración Gemini
│   └── templates/           ← HTML (Jinja2)
├── main.py                  ← Punto de entrada
├── config.py                ← Configuración
├── requirements.txt         ← Dependencias Python
├── Dockerfile               ← Imagen Docker
├── docker-compose.yml       ← Orquestación
└── .env                     ← Variables secretas (NO COMMITEAR)
```

---

## 🎯 Primer Uso

1. **Registrarse:**
   - Email: tu@email.com
   - RUT: 12345678-9 (formato con guión)
   - Contraseña: min 8 caracteres
   - ✓ Acepta términos (consentimiento GDPR/LPD)

2. **Crear Proyecto:**
   - Título: "Mi App de Delivery"
   - Idea: Describe tu concepto de negocio
   - Submit → La IA evalúa ambigüedad

3. **Responder Preguntas:**
   - 3 preguntas de clarificación
   - Max 10 mensajes en la sesión
   - Chat se auto-cierra al límite

4. **Ver Análisis:**
   - 9 Pilares de Viabilidad
   - Puntuación de viabilidad (0-100)
   - Recomendación (viable/needs_pivot/not_viable)

---

## 📞 Soporte

- Revisa los logs: `docker-compose logs -f`
- Verifica la configuración de `.env`
- Consulta `README.md` para más detalles

---

## 🚀 Próximo Paso

Después de verificar que todo funciona:
1. Explora el dashboard
2. Crea varios proyectos
3. Verifica los reportes de viabilidad
4. Revisa los logs en `/logs/preincubadora.log`

**¡Bienvenido a PreIncubadora AI!** 🎉
