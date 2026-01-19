"""
ESTRUCTURA DEL PROYECTO - PreIncubadora AI
==========================================

📦 Software de Riesgo/
│
├── 📂 app/                          # Núcleo de la aplicación Flask
│   ├── __init__.py                  # Application Factory (init de app)
│   ├── models.py                    # Modelos SQLAlchemy (User, Project, etc.)
│   ├── routes.py                    # Rutas/Blueprints (Auth, Dashboard, Chat)
│   │
│   ├── 📂 services/                 # Servicios de negocio
│   │   ├── __init__.py
│   │   └── ai_service.py            # IncubatorAI - Integración con Gemini 1.5 Flash
│   │
│   └── 📂 templates/                # Templates Jinja2 + Tailwind CSS
│       ├── layout.html              # Base con navbar/footer
│       │
│       ├── 📂 auth/
│       │   ├── index.html           # Landing page (hero + CTA)
│       │   ├── login.html           # Formulario de login
│       │   └── register.html        # Formulario de registro (RUT único)
│       │
│       ├── 📂 dashboard/
│       │   └── index.html           # Dashboard con lista de proyectos
│       │
│       ├── 📂 project/
│       │   ├── create.html          # Formulario crear nuevo proyecto
│       │   └── view.html            # Vista completa de proyecto + plan de negocio
│       │
│       ├── 📂 chat/
│       │   ├── clarification.html   # Chat de triaje/ambigüedad (3 preguntas)
│       │   └── analysis.html        # Chat de análisis (generación de reporte)
│       │
│       └── 📂 errors/
│           ├── 404.html
│           └── 500.html
│
├── 📂 logs/                         # Logs de auditoría (rotación)
│   └── preincubadora.log
│
├── config.py                        # Configuración por entorno (dev/prod/test)
├── main.py                          # Punto de entrada (flask run)
│
├── requirements.txt                 # Dependencias Python
├── Dockerfile                       # Imagen Docker (Python 3.11-slim)
├── docker-compose.yml               # Orquestación (App + PostgreSQL)
│
├── .env.example                     # Plantilla de variables de entorno
├── .gitignore                       # Gitignore estándar
│
└── README.md                        # Documentación completa

═══════════════════════════════════════════════════════════════════════════

🏗️ ARQUITECTURA MONOLÍTICA FULL-STACK
═════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (SSR)                           │
│  Jinja2 Templates + Tailwind CSS (Slate-900 + Electric Blue)    │
│  - Landing Page                                                  │
│  - Auth Forms (Login/Register)                                   │
│  - Dashboard (Proyectos)                                         │
│  - Proyecto Details + Plan de Negocio                            │
│  - Chat (Clarificación + Análisis)                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓ HTTP/JSON
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Flask)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Routes (Blueprints)                                      │   │
│  │ - auth_bp: /login, /register, /logout                    │   │
│  │ - dashboard_bp: /dashboard                               │   │
│  │ - project_bp: /project/create, /project/<id>             │   │
│  │ - chat_bp: /chat/clarification/<id>, /chat/analysis/<id> │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Services                                                 │   │
│  │ - IncubatorAI (ai_service.py)                            │   │
│  │   • evaluate_ambiguity()                                 │   │
│  │   • generate_clarification_questions()                   │   │
│  │   • generate_business_plan()                             │   │
│  │   • generate_pivot_session()                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Models (SQLAlchemy)                                      │   │
│  │ - User                  (Email, RUT único, Passwords)    │   │
│  │ - Project               (Idea raw, Variability score)    │   │
│  │ - BusinessPlan          (9 Pilares de viabilidad)        │   │
│  │ - ChatSession           (Mensajes, Rate limiting)        │   │
│  │ - ChatMessage           (User/Assistant role)            │   │
│  │ - AuditLog              (GDPR/LPD compliance)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓ SQL
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (PostgreSQL 16)                     │
│  - users (email unique, rut unique)                             │
│  - projects (user_id FK, variability_score)                     │
│  - business_plans (project_id unique)                           │
│  - chat_sessions (project_id FK, message_count, is_locked)      │
│  - chat_messages (session_id FK, role, content)                 │
│  - audit_logs (user_id FK, action, consent_given)               │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════

🔄 FLUJO DE USUARIO
═══════════════════

1. REGISTRO/LOGIN
   User → /register o /login → Flask Auth Blueprint
   → Bcrypt hash password → User model → PostgreSQL
   → Flask-Login session management

2. CREAR PROYECTO
   User → /project/create → Flask Project Blueprint
   → Validación Rate Limiting (max 2/24h)
   → Project model → PostgreSQL
   → IncubatorAI.evaluate_ambiguity()
   → ChatSession (clarification type)
   → Redirect /chat/clarification/<project_id>

3. CLARIFICACIÓN (Triaje de Ambigüedad)
   User → /chat/clarification/<project_id>
   → IncubatorAI.generate_clarification_questions() (3 preguntas)
   → ChatSession almacena preguntas
   → User responde (max 10 mensajes)
   → Al completar → Redirect /chat/analysis/<project_id>

4. ANÁLISIS & GENERACIÓN DE PLAN
   User → /chat/analysis/<project_id>
   → IncubatorAI.generate_business_plan()
   → Evaluación bajo 9 Pilares
   → Viability score (0-100)
   → Recommendation (viable | needs_pivot | not_viable)
   → BusinessPlan model → PostgreSQL
   → Mostrar reporte en /project/<project_id>

5. PIVOTE ESTRATÉGICO (si recommendation = needs_pivot)
   User → IncubatorAI.generate_pivot_session()
   → 3 alternativas estratégicas
   → Opción para crear nuevo proyecto

═══════════════════════════════════════════════════════════════════════════

🔐 SEGURIDAD
════════════

✓ AUTENTICACIÓN
  - Flask-Login para sesiones
  - Bcrypt para hash de passwords
  - RUT único (1 cuenta por RUT) → Validación en register

✓ AUTORIZACIÓN
  - Verificación user_id en proyectos
  - No ver proyectos ajenos
  - Rate limiting por usuario

✓ FORMULARIOS
  - WTF-CSRF Protection
  - Validación de inputs
  - Email validation (email-validator)

✓ AUDITORÍA
  - AuditLog model (user, action, resource, consent)
  - IP address y User-Agent guardados
  - Logs rotacionales (/logs/preincubadora.log)
  - Consentimiento GDPR/LPD registrado

✓ AMBIENTE
  - Variables de entorno (.env)
  - GEMINI_API_KEY nunca en código
  - DATABASE_URL configurable
  - SECRET_KEY para sesiones

═══════════════════════════════════════════════════════════════════════════

⚙️ CONFIGURACIÓN POR ENTORNO
═════════════════════════════

config.py:
├── DevelopmentConfig
│   - DEBUG = True
│   - SQLALCHEMY_ECHO = True
│   - SQLite (local) o PostgreSQL
│
├── ProductionConfig
│   - DEBUG = False
│   - DATABASE_URL mandatory
│   - SSL/TLS (via proxy)
│
└── TestingConfig
    - TESTING = True
    - SQLite in-memory
    - CSRF disabled

═══════════════════════════════════════════════════════════════════════════

🚀 DOCKER
═════════

Services:
├── postgres:16-alpine
│   - Volumen: postgres_data
│   - Port: 5432
│   - Health check: pg_isready
│
└── app (Dockerfile)
    - Base: python:3.11-slim
    - Port: 5000
    - Depende de: postgres (healthy)
    - Volume: /app (código)
    - Volume: /app/logs (auditoría)

Network: preincubadora_network (bridge)

═══════════════════════════════════════════════════════════════════════════

📊 ESQUEMA DE BASES DE DATOS
════════════════════════════

users
├── id (UUID, PK)
├── email (VARCHAR 255, UNIQUE)
├── password_hash (VARCHAR 255)
├── rut (VARCHAR 12, UNIQUE)
├── role (ENUM: user|admin|seller)
├── created_at (TIMESTAMP)
├── last_project_creation (TIMESTAMP, NULL)
└── is_active (BOOLEAN)

projects
├── id (UUID, PK)
├── user_id (UUID, FK → users)
├── title (VARCHAR 255)
├── raw_idea (TEXT)
├── variability_score (FLOAT)
├── status (ENUM: ambiguous|ready|in_analysis|completed)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

business_plans
├── id (UUID, PK)
├── project_id (UUID, FK → projects, UNIQUE)
├── problem_statement (TEXT)
├── value_proposition (TEXT)
├── target_market (TEXT)
├── revenue_model (TEXT)
├── cost_analysis (TEXT)
├── technical_feasibility (TEXT)
├── risks_analysis (TEXT)
├── scalability_potential (TEXT)
├── validation_strategy (TEXT)
├── overall_assessment (TEXT)
├── viability_score (FLOAT)
├── recommendation (ENUM: viable|needs_pivot|not_viable)
└── generated_at (TIMESTAMP)

chat_sessions
├── id (UUID, PK)
├── project_id (UUID, FK → projects)
├── message_count (INTEGER)
├── is_locked (BOOLEAN)
├── session_type (ENUM: clarification|analysis|pivot)
└── created_at (TIMESTAMP)

chat_messages
├── id (UUID, PK)
├── session_id (UUID, FK → chat_sessions)
├── role (ENUM: user|assistant)
├── content (TEXT)
└── created_at (TIMESTAMP)

audit_logs
├── id (UUID, PK)
├── user_id (UUID, FK → users)
├── action (VARCHAR 255)
├── resource_type (VARCHAR 50)
├── resource_id (UUID)
├── consent_given (BOOLEAN)
├── ip_address (VARCHAR 45)
├── user_agent (TEXT)
└── created_at (TIMESTAMP)

═══════════════════════════════════════════════════════════════════════════

📋 REQUISITOS IMPLEMENTADOS
═════════════════════════════

✓ VALIDACIÓN DE IDENTIDAD
  - RUT único en BD
  - 1 cuenta por RUT
  - Email único también

✓ RATE LIMITING
  - Max 2 proyectos/usuario/24h
  - Max 10 mensajes/sesión
  - Auto-lock al límite

✓ AISLAMIENTO DE CONTEXTO
  - ChatSession por proyecto
  - No compartir mensajes entre proyectos
  - Validación de acceso (user_id)

✓ TRIAJE DE AMBIGÜEDAD
  - Evaluación 0-100 (variability_score)
  - 3 preguntas de clarificación si ambiguo
  - Loop interactivo

✓ HARD CAP CHAT
  - 10 mensajes máximo
  - Bloqueo automático
  - CTA a agendamiento (futuro)

✓ 9 PILARES DE VIABILIDAD
  1. Problema Real
  2. Propuesta de Valor
  3. Mercado
  4. Modelo de Ingresos
  5. Costos
  6. Viabilidad Técnica
  7. Riesgos
  8. Escalabilidad
  9. Validación

═══════════════════════════════════════════════════════════════════════════
"""
