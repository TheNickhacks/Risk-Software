# ✅ CHECKLIST DE VALIDACIÓN - PreIncubadora AI

## 🚀 SETUP & DEPLOYMENT

### Docker & Infraestructura
- [ ] `docker-compose up -d` levanta sin errores
- [ ] PostgreSQL inicia correctamente (healthcheck green)
- [ ] App inicia en puerto 5000
- [ ] Volumes se crean: `postgres_data`, `logs/`
- [ ] `.env` está configurado con GEMINI_API_KEY
- [ ] Base de datos se crea automáticamente (tables exist)

### Archivos Requeridos
- [ ] `main.py` existe y es ejecutable
- [ ] `config.py` tiene 3 configs (dev/prod/test)
- [ ] `requirements.txt` tiene todas las dependencias
- [ ] `Dockerfile` construye correctamente
- [ ] `docker-compose.yml` orquesta dos servicios
- [ ] `.env.example` es una plantilla válida
- [ ] `.gitignore` excluye `.env`, `venv/`, `__pycache__`

---

## 🛠️ BACKEND CORE

### Application Factory (`app/__init__.py`)
- [ ] `create_app()` importa todas las extensiones
- [ ] `db.init_app(app)` configura SQLAlchemy
- [ ] `LoginManager` configurado con `login_view`
- [ ] `user_loader` callback registrado
- [ ] Blueprints registrados (auth, dashboard, project, chat)
- [ ] `db.create_all()` en app context
- [ ] Logging setup con rotación

### Modelos (`app/models.py`)
- [ ] **User**: id, email (unique), password_hash, rut (unique), role, created_at, is_active
  - [x] Método `set_password()` con Bcrypt
  - [x] Método `check_password()` funcional
  - [x] Método `can_create_project()` implementado (24h check)
  - [x] Relaciones: projects, audit_logs
  
- [ ] **Project**: id, user_id (FK), title, raw_idea, variability_score, status, created_at, updated_at
  - [x] Índice en (user_id, created_at)
  - [x] Status enum: ambiguous|ready|in_analysis|completed
  - [x] Relaciones: user, business_plan, chat_sessions
  
- [ ] **BusinessPlan**: id, project_id (unique FK), 9 pilares + assessment
  - [x] Todos 9 campos presentes
  - [x] viability_score (float)
  - [x] recommendation enum
  - [x] generated_at timestamp
  
- [ ] **ChatSession**: id, project_id (FK), message_count, is_locked, session_type, created_at
  - [x] Método `can_add_message(max_messages)`
  - [x] Método `lock_session()`
  - [x] Índice en (project_id, created_at)
  
- [ ] **ChatMessage**: id, session_id (FK), role (user|assistant), content, created_at
  - [x] Índice en (session_id, created_at)
  
- [ ] **AuditLog**: id, user_id (FK), action, resource_type, resource_id, consent_given, ip_address, user_agent, created_at
  - [x] Índice en (user_id, action, created_at)

### Rutas (`app/routes.py`)

#### Auth Blueprint
- [ ] GET `/` - Landing page (template: auth/index.html)
- [ ] GET/POST `/register` - Validar RUT único
  - [x] Email unique check
  - [x] RUT unique check
  - [x] Password min 8 chars
  - [x] Bcrypt hashing
  - [x] AuditLog creation
  
- [ ] GET/POST `/login` - Session management
  - [x] `login_user()` con Flask-Login
  - [x] Remember me checkbox funcional
  - [x] Redirect a next param
  
- [ ] GET `/logout` - Clear session
  - [x] `logout_user()`
  - [x] Flash message

#### Dashboard Blueprint
- [ ] GET `/dashboard` - Lista proyectos
  - [x] Filter por user_id
  - [x] Mostrar variability_score
  - [x] Rate limiting indicator

#### Project Blueprint
- [ ] GET/POST `/project/create`
  - [x] Validar rate limiting (2/24h)
  - [x] IA.evaluate_ambiguity() llamado
  - [x] AuditLog creation
  - [x] Redirect a chat/clarification si ambiguous
  
- [ ] GET `/project/<project_id>` - Ver detalles
  - [x] Auth check (user_id match)
  - [x] Mostrar BusinessPlan si existe
  - [x] Mostrar 9 Pilares evaluados

#### Chat Blueprint
- [ ] GET `/chat/clarification/<project_id>`
  - [x] Crear ChatSession(type='clarification') si no existe
  - [x] IA.generate_clarification_questions() (3 preguntas)
  - [x] Guardar preguntas como ChatMessages
  
- [ ] GET `/chat/analysis/<project_id>`
  - [x] Crear ChatSession(type='analysis') si no existe
  - [x] Mostrar chat interactivo
  
- [ ] POST `/chat/send-message`
  - [x] Validar session_id y user access
  - [x] Guardar ChatMessage(role='user')
  - [x] Incrementar message_count
  - [x] Generar respuesta IA
  - [x] Guardar ChatMessage(role='assistant')
  - [x] Lock session si message_count >= 10
  - [x] Return JSON válido

---

## 🤖 IA SERVICE (`app/services/ai_service.py`)

### IncubatorAI Class
- [ ] Constructor: `__init__(api_key)` - configura Gemini
- [ ] PILLARS constant con 9 pilares
- [ ] SYSTEM_PROMPT definido con "Realismo Constructivo"

### Métodos Implementados
- [ ] `evaluate_ambiguity(raw_idea)` 
  - [x] Returns: (variability_score: float, requires_clarification: bool)
  - [x] Llama a Gemini con prompt correcto
  - [x] Parsea JSON response
  - [x] Fallback a 50.0 en error

- [ ] `generate_clarification_questions(raw_idea, num_questions=3)`
  - [x] Retorna lista de strings
  - [x] 3 preguntas específicas
  - [x] Focused en aspectos vagos
  - [x] Fallback a preguntas genéricas

- [ ] `generate_business_plan(raw_idea, clarifications=None)`
  - [x] Retorna dict con todos los campos
  - [x] Incluye los 9 pilares
  - [x] overall_assessment (síntesis)
  - [x] viability_score (0-100)
  - [x] recommendation (viable|needs_pivot|not_viable)
  - [x] Limpia markdown de respuesta
  - [x] Error handling con _create_fallback_plan()

- [ ] `generate_pivot_session(raw_idea, failing_pillars)`
  - [x] Retorna dict con analysis + pivots
  - [x] 3 pivotes estratégicos
  - [x] Cada pivote con key_changes + score

---

## 🎨 FRONTEND (Templates)

### Base Template (`layout.html`)
- [ ] Navbar sticky con logo + nav links
- [ ] Tailwind CSS configurado (Slate-900, Electric Blue #2563EB)
- [ ] Footer con info
- [ ] Flash messages con categorías (error/success/info)
- [ ] CSS custom variables definidas
- [ ] Responsive design (mobile-first)

### Auth Templates
- [ ] `auth/index.html` - Landing hero + CTA
  - [x] 3 pasos destacados
  - [x] Buttons: Crear cuenta / Iniciar sesión
  
- [ ] `auth/register.html` - Formulario registro
  - [x] Email field
  - [x] RUT field con pattern validation
  - [x] Password field (min 8)
  - [x] Terms checkbox
  
- [ ] `auth/login.html` - Formulario login
  - [x] Email field
  - [x] Password field
  - [x] Remember me checkbox
  - [x] Forgot password link

### Dashboard Template
- [ ] `dashboard/index.html`
  - [x] Welcome message
  - [x] Proyectos grid (responsive)
  - [x] Variability score bar por proyecto
  - [x] Status badges (ambiguous/ready/etc)
  - [x] Fecha creación
  - [x] Rate limiting indicator
  - [x] Empty state con CTA

### Project Templates
- [ ] `project/create.html`
  - [x] Title input
  - [x] Idea textarea (placeholder con guía)
  - [x] Info box: "¿Qué pasará después?"
  - [x] Rate limiting warning
  - [x] Submit button
  
- [ ] `project/view.html`
  - [x] Idea original mostrada
  - [x] Variability score gauge
  - [x] BusinessPlan completo (si existe)
  - [x] 9 Pilares en grid 2x2
  - [x] Overall assessment
  - [x] Recomendación coloreada (verde/amarillo/rojo)
  - [x] Viability score prominente
  - [x] Opción para pivote si needed

### Chat Templates
- [ ] `chat/clarification.html`
  - [x] Messages display (user right, assistant left)
  - [x] Textarea input
  - [x] Message count: X/10
  - [x] Submit button
  - [x] Locked state indicator
  - [x] JavaScript para AJAX
  
- [ ] `chat/analysis.html`
  - [x] Similar a clarification
  - [x] Mensajes mostrados
  - [x] Input para preguntas/comentarios
  - [x] AJAX send-message

### Error Templates
- [ ] `errors/404.html` - Página no encontrada
- [ ] `errors/500.html` - Error servidor

---

## 🔐 SEGURIDAD

### Autenticación
- [ ] Passwords hasheadas con Bcrypt (method='bcrypt')
- [ ] `check_password()` verifica correctamente
- [ ] Flask-Login session management activo
- [ ] `@login_required` en rutas protegidas
- [ ] Redirect a login si no autenticado

### Autorización
- [ ] Verificación user_id en proyectos
- [ ] No acceso a proyectos de otros usuarios
- [ ] Validación en chat_bp.send_message()

### CSRF Protection
- [ ] WTF-CSRF habilitado en config
- [ ] Tokens en formularios (Jinja2 `csrf_token()`)
- [ ] POST requests validados

### Rate Limiting
- [ ] `User.can_create_project()` implementado
- [ ] 24h check para creación de proyectos
- [ ] `ChatSession.can_add_message()` implementado
- [ ] Auto-lock al alcanzar 10 mensajes

### Variables de Entorno
- [ ] `.env` no incluido en Git (`.gitignore`)
- [ ] `.env.example` como plantilla
- [ ] GEMINI_API_KEY se lee desde .env
- [ ] DATABASE_URL configurable
- [ ] SECRET_KEY configurable

### Auditoría & Compliance
- [ ] AuditLog model con todos los campos
- [ ] Registro en: register, create_project, etc
- [ ] consent_given field para GDPR/LPD
- [ ] ip_address guardada
- [ ] user_agent guardada
- [ ] Logging con RotatingFileHandler (10MB)
- [ ] Logs en `logs/preincubadora.log`

---

## 📊 BASE DE DATOS

### PostgreSQL
- [ ] Base de datos `preincubadora_db` creada
- [ ] Todas las tablas creadas (6 tables)
- [ ] Índices creados correctamente
- [ ] Foreign keys activos
- [ ] UUID fields auto-generate
- [ ] Timestamps auto-populate

### Migraciones
- [ ] `db.create_all()` en app context
- [ ] Modelos registrados antes de create_all
- [ ] No hay errores de creación

---

## 📦 DEPENDENCIAS

### requirements.txt
- [ ] Flask==3.0.0
- [ ] Flask-SQLAlchemy==3.1.1
- [ ] Flask-Login==0.6.3
- [ ] Flask-WTF==1.2.1
- [ ] SQLAlchemy==2.0.23
- [ ] psycopg2-binary==2.9.9
- [ ] google-generativeai==0.3.0
- [ ] bcrypt==4.1.1
- [ ] python-dotenv==1.0.0
- [ ] WTForms==3.1.1
- [ ] email-validator==2.1.0

### Instalación
- [ ] `pip install -r requirements.txt` exitoso
- [ ] Todas las versiones pin-eadas (no usar `>=`)
- [ ] Sin conflictos de dependencias

---

## 🐳 DOCKER

### Dockerfile
- [ ] Base: python:3.11-slim
- [ ] WORKDIR /app
- [ ] apt-get update e instalación de gcc, postgresql-client
- [ ] COPY requirements.txt
- [ ] pip install sin cache
- [ ] COPY . .
- [ ] mkdir -p /app/logs
- [ ] EXPOSE 5000
- [ ] CMD flask run --host=0.0.0.0

### docker-compose.yml
- [ ] version: '3.9'
- [ ] services: postgres, app
- [ ] postgres: alpine, port 5432, volumes, healthcheck
- [ ] app: build context, environment vars, depends_on, ports, volumes
- [ ] Network: preincubadora_network
- [ ] Volumes: postgres_data, code mount, logs mount

### Ejecución
- [ ] `docker-compose up -d` levanta sin errores
- [ ] Ambos servicios "running"
- [ ] PostgreSQL healthcheck "healthy"
- [ ] App accessible en localhost:5000

---

## 📝 DOCUMENTACIÓN

### README.md
- [ ] Descripción general clara
- [ ] Stack técnico listado
- [ ] Setup con Docker (5 pasos)
- [ ] Setup local (6 pasos)
- [ ] Requisitos funcionales explicados
- [ ] Modelado de datos documentado
- [ ] Seguridad detallada
- [ ] Estructura de archivos clara

### QUICKSTART.md
- [ ] Quick start con Docker (4 pasos)
- [ ] Comandos útiles Docker
- [ ] Troubleshooting section
- [ ] Primer uso guiado
- [ ] Links a documentación completa

### ESTRUCTURA.md
- [ ] Arquitectura monolítica visual
- [ ] Flujo de usuario completo
- [ ] Esquema de BD con todas las tablas
- [ ] Requisitos implementados
- [ ] Configuración por entorno

### RUTAS_Y_ENDPOINTS.md
- [ ] Todas las rutas listadas
- [ ] Path + method + descripción
- [ ] Auth flow diagram
- [ ] Data flow diagram
- [ ] API response examples

### IMPLEMENTACION_SUMARIO.md
- [ ] Status final de la fase
- [ ] Checklist de validación
- [ ] Métricas de implementación
- [ ] Próximos pasos recomendados

---

## 🧪 TESTING MANUAL

### Flujo Completo (End-to-End)
- [ ] Registrarse (email, RUT, password)
  - [ ] RUT único validado
  - [ ] Password bcrypt hash verificado
  
- [ ] Iniciar sesión
  - [ ] Session cookie creada
  - [ ] Redirect a dashboard
  
- [ ] Dashboard
  - [ ] Lista de proyectos vacía (primer usuario)
  - [ ] Botón "Nuevo Proyecto" disponible
  
- [ ] Crear proyecto
  - [ ] Título e idea guardados
  - [ ] Variability score calculado
  - [ ] Redirect a chat clarification
  
- [ ] Chat clarificación
  - [ ] 3 preguntas mostradas
  - [ ] Chat interactivo funciona
  - [ ] Max 10 mensajes
  
- [ ] Ver reporte
  - [ ] 9 Pilares mostrados
  - [ ] Viability score visible
  - [ ] Recomendación clara

### Tests de Seguridad
- [ ] Intentar acceder a /dashboard sin login → redirect
- [ ] Intentar acceder a proyecto de otro usuario → error
- [ ] SQL injection en inputs → sanitized
- [ ] CSRF token requerido en forms
- [ ] Cookies no tienen flag Secure (local) o tienen (prod)

### Tests de Rate Limiting
- [ ] Crear 2 proyectos → OK
- [ ] Intentar crear 3er proyecto en 24h → Bloqueado
- [ ] Enviar 11 mensajes en chat → 10mo OK, 11vo bloqueado

---

## 📊 LOGS

### Auditoría
- [ ] `/logs/preincubadora.log` existe
- [ ] Contiene logs de:
  - [ ] User registration
  - [ ] Login/Logout
  - [ ] Create project
  - [ ] Chat send message
  - [ ] Errors

### Rotación
- [ ] RotatingFileHandler configurado (10MB max)
- [ ] backupCount = 10 (10 archivos)
- [ ] Formato: timestamp + level + message

---

## ✅ FINAL CHECKLIST

- [ ] Estructura de carpetas completa ✓
- [ ] Todos los archivos creados ✓
- [ ] Modelos BD implementados ✓
- [ ] Rutas funcionales ✓
- [ ] Service IA integrado ✓
- [ ] Templates con Tailwind CSS ✓
- [ ] Docker & Docker Compose ✓
- [ ] Seguridad implementada ✓
- [ ] Auditoría configurada ✓
- [ ] Documentación completa ✓
- [ ] Listo para testing ✓

---

## 🚀 PRÓXIMO PASO

```bash
# 1. Configurar .env con GEMINI_API_KEY
# 2. Levantar servicios
docker-compose up -d

# 3. Acceder a http://localhost:5000
# 4. Registrarse y probar flujo completo
# 5. Revisar logs
cat logs/preincubadora.log
```

---

**Status:** ✅ IMPLEMENTACIÓN FASE 1 COMPLETADA
**Fecha:** 17 de Enero de 2026
**Próxima Fase:** Testing + Features Avanzadas
