# 🚀 PreIncubadora AI - Plataforma SaaS de Pre-Incubación

## Descripción General

**PreIncubadora AI** es una plataforma SaaS de pre-incubación monolítica que transforma ideas de negocio en reportes estructurados de viabilidad bajo un enfoque de "Realismo Constructivo".

**Stack Técnico:**
- **Backend:** Python 3.11 + Flask
- **Frontend:** SSR con Jinja2 + Tailwind CSS
- **Base de Datos:** PostgreSQL 16
- **IA:** Google Gemini 1.5 Flash
- **Infra:** Docker & Docker Compose

---

## ⚙️ Requisitos Previos

- Docker & Docker Compose instalados
- Python 3.11+ (si ejecutas localmente sin Docker)
- PostgreSQL 16+ (si no usas Docker)
- API Key de Google Gemini (obtén en [Google AI Studio](https://aistudio.google.com/app/apikeys))

---

## 🔧 Instalación y Setup

### Opción 1: Con Docker (Recomendado)

#### 1. Clonar y navegar al proyecto
```bash
cd "Software de Riesgo"
```

#### 2. Configurar variables de entorno
```bash
cp .env.example .env
```

Edita `.env` y agrega tu `GEMINI_API_KEY`:
```
GEMINI_API_KEY=tu-api-key-aqui
DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/preincubadora_db
SECRET_KEY=tu-secret-key-para-produccion
```

#### 3. Levantar servicios con Docker Compose
```bash
docker-compose up -d
```

La aplicación estará disponible en: **http://localhost:5000**

**Comandos útiles:**
```bash
# Ver logs
docker-compose logs -f app

# Ejecutar migraciones (si aplica)
docker-compose exec app flask db upgrade

# Detener servicios
docker-compose down
```

---

### Opción 2: Instalación Local

#### 1. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

#### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

#### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

#### 4. Crear base de datos (PostgreSQL debe estar ejecutándose)
```bash
flask shell
>>> from app.models import db
>>> db.create_all()
>>> exit()
```

#### 5. Ejecutar servidor de desarrollo
```bash
flask run
```

---

## 📋 Requisitos Funcionales Implementados

### ✅ Validación de Identidad
- Registro único por RUT (1 cuenta por RUT)
- Validación de email único
- Hash seguro de contraseñas con Bcrypt

### ✅ Rate Limiting
- Máximo 2 proyectos por usuario cada 24 horas
- Máximo 10 mensajes por sesión de chat
- Bloqueo automático al alcanzar límites

### ✅ Aislamiento de Contexto
- Cada proyecto tiene sesiones de chat independientes
- Los mensajes no se comparten entre proyectos
- Validación de acceso por usuario

### ✅ Triaje de Ambigüedad
- Evaluación automática de variabilidad (0-100 escala)
- Generación de 3 preguntas de clarificación si es necesario
- Loop interactivo antes de generar reporte

### ✅ Generación de Reportes
- Análisis bajo **9 Pilares de Viabilidad**:
  1. Problema Real
  2. Propuesta de Valor
  3. Mercado
  4. Modelo de Ingresos
  5. Costos
  6. Viabilidad Técnica
  7. Riesgos
  8. Escalabilidad
  9. Validación

---

## 🗄️ Modelado de Datos

### User
```
- id (UUID)
- email (único)
- password_hash (bcrypt)
- rut (único, 1 por usuario)
- role (user | admin | seller)
- created_at
- last_project_creation (para rate limiting)
- is_active
```

### Project
```
- id (UUID)
- user_id (FK)
- title
- raw_idea
- variability_score (0-100)
- status (ambiguous | ready | in_analysis | completed)
- created_at, updated_at
```

### BusinessPlan
```
- id (UUID)
- project_id (FK, unique)
- problem_statement, value_proposition, target_market, ...
- overall_assessment
- viability_score (0-100)
- recommendation (viable | needs_pivot | not_viable)
- generated_at
```

### ChatSession
```
- id (UUID)
- project_id (FK)
- message_count
- is_locked (bool)
- session_type (clarification | analysis | pivot)
- created_at
```

### ChatMessage
```
- id (UUID)
- session_id (FK)
- role (user | assistant)
- content
- created_at
```

### AuditLog
```
- id (UUID)
- user_id (FK)
- action, resource_type, resource_id
- consent_given (GDPR/LPD)
- ip_address, user_agent
- created_at
```

---

## 🔐 Seguridad Implementada

### ✅ Autenticación & Autorización
- Flask-Login para gestión de sesiones
- CSRF Protection en formularios (WTF-CSRF)
- Rate limiting por usuario
- Validación de acceso por proyecto (no ver proyectos ajenos)

### ✅ Hashing & Encriptación
- Passwords hasheadas con Bcrypt
- Secret Key para sesiones (configurable)

### ✅ Auditoría & Cumplimiento
- Logs de todas las acciones (creación de proyectos, generación de reportes)
- Registro de consentimiento informado (GDPR/LPD)
- IP address y User-Agent guardados para auditoría

### ✅ Variables de Entorno
- `GEMINI_API_KEY` protegida (nunca en código)
- `DATABASE_URL` configurable
- `SECRET_KEY` para producción

---

## 📊 Estructura de Archivos

```
Software de Riesgo/
├── app/
│   ├── __init__.py           (Application Factory)
│   ├── models.py             (Modelos SQLAlchemy)
│   ├── routes.py             (Rutas: Auth, Dashboard, Project, Chat)
│   ├── services/
│   │   ├── __init__.py
│   │   └── ai_service.py     (Clase IncubatorAI - Gemini API)
│   └── templates/
│       ├── layout.html       (Base con Tailwind CSS)
│       ├── auth/
│       │   ├── login.html
│       │   ├── register.html
│       │   └── index.html
│       ├── dashboard/
│       │   └── index.html
│       ├── project/
│       │   ├── create.html
│       │   └── view.html
│       ├── chat/
│       │   ├── clarification.html
│       │   └── analysis.html
│       └── errors/
│           ├── 404.html
│           └── 500.html
├── logs/                      (Logs de auditoría)
├── config.py                  (Configuración por entorno)
├── main.py                    (Punto de entrada)
├── requirements.txt           (Dependencias Python)
├── Dockerfile                 (Imagen Docker)
├── docker-compose.yml         (Orquestación)
├── .env.example               (Variables de entorno plantilla)
└── README.md                  (Este archivo)
```

---

## 🧪 Testing & Validación

### Ejecutar Tests (Próximamente)
```bash
pytest tests/
```

### Validar Modelos de IA
```bash
python -m app.services.ai_service
```

---

## 📖 Guía de Uso

### Para Usuarios
1. **Registrarse:** Email + Contraseña + RUT único
2. **Crear Proyecto:** Presentar idea en formato libre
3. **Clarificar:** Responder 3 preguntas de ambigüedad
4. **Analizar:** Recibir reporte de viabilidad bajo 9 Pilares
5. **Actuar:** Si es "viable", proceder; si "needs_pivot", explorar alternativas

### Para Administradores
- Acceder a logs de auditoría: `/var/log/preincubadora.log` (en Docker) o `logs/preincubadora.log`
- Monitorear uso de API (rate limiting, tokens)
- Gestionar usuarios y proyectos

---

## 🎨 Diseño UI/UX

**Paleta de Colores:**
- Fondo: Slate-900 (`#0f172a`)
- Acentos: Electric Blue (`#2563EB`)
- Texto: Slate-100 (`#e2e8f0`)
- Cards: Slate-800 (`#1e293b`)

**Framework:** Tailwind CSS v3

---

## 🚀 Próximos Pasos

- [ ] Implementar Google OAuth 2.0
- [ ] Agregar soporte de pivote estratégico con alternativas
- [ ] Dashboard de métricas (proyectos generados, viabilidad promedio)
- [ ] Exportación de reportes (PDF, DOCX)
- [ ] Notificaciones por email
- [ ] Panel de administración
- [ ] Tests unitarios e integración
- [ ] CI/CD con GitHub Actions
- [ ] Soporte multiidioma (ES, EN, PT)

---

## 📞 Soporte

Para soporte o reportar bugs:
- Email: hola@preincubadora.ai
- Issues: GitHub Issues
- Docs: [Documentación Técnica](./docs/)

---

## 📜 Licencia

Propietario © 2026 PreIncubadora AI. Todos los derechos reservados.

---

## 🙏 Créditos

Desarrollado con ❤️ como una plataforma SaaS de referencia para pre-incubación de negocios.
