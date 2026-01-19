# 🛣️ MAPA DE RUTAS - PreIncubadora AI

## Blueprint: auth_bp (URL prefix: "")

```
GET     /                           → index()
        Página de inicio (landing)
        Render: auth/index.html
        
GET     /register                   → register()
        Formulario de registro
        Render: auth/register.html
        
POST    /register                   → register()
        Validar email + RUT + password
        ✓ Crear User con Bcrypt hash
        ✓ Crear AuditLog (user_registration)
        → Redirect /login con flash "success"
        
GET     /login                      → login()
        Formulario de login
        Render: auth/login.html
        
POST    /login                      → login()
        Validar email + password
        ✓ Flask-Login session management
        ✓ Redirect a /dashboard o next
        
GET     /logout                     → logout() [REQUIRED LOGIN]
        Cerrar sesión
        ✓ Clear session
        → Redirect / con flash "success"
```

## Blueprint: dashboard_bp (URL prefix: "/dashboard")

```
GET     /dashboard/                 → dashboard() [REQUIRED LOGIN]
        Dashboard del usuario
        Mostrar:
        - Lista de proyectos (user_id filtered)
        - Variability score por proyecto
        - Botón "Crear proyecto" (si can_create_project)
        - Rate limiting indicator
        Render: dashboard/index.html
```

## Blueprint: project_bp (URL prefix: "/project")

```
GET     /project/create             → create_project() [REQUIRED LOGIN]
        Formulario crear proyecto
        Render: project/create.html
        
POST    /project/create             → create_project() [REQUIRED LOGIN]
        Validar rate limiting (max 2/24h)
        ✓ Crear Project con raw_idea
        ✓ Evaluar ambigüedad con IA
        → IncubatorAI.evaluate_ambiguity() 
           → project.variability_score
        ✓ Crear AuditLog (create_project)
        → Redirect /chat/clarification/<id> si ambiguous
        
GET     /project/<project_id>       → view_project() [REQUIRED LOGIN]
        Ver detalles del proyecto
        - Idea original
        - Variability score
        - BusinessPlan (si existe)
        - 9 Pilares evaluados
        - Botones para interactuar
        Render: project/view.html
```

## Blueprint: chat_bp (URL prefix: "/chat")

```
GET     /chat/clarification/<project_id>
        → clarification_chat() [REQUIRED LOGIN]
        
        Sesión de clarificación de ambigüedad
        ✓ Crear ChatSession (type='clarification') si no existe
        ✓ Generar 3 preguntas:
           → IncubatorAI.generate_clarification_questions()
        ✓ Guardar preguntas como ChatMessage (role='assistant')
        ✓ Mostrar chat interactivo
        
        Render: chat/clarification.html
        Datos en template:
        - project
        - session
        - messages (ordenados por created_at)
        
        
GET     /chat/analysis/<project_id>
        → analysis_chat() [REQUIRED LOGIN]
        
        Sesión de análisis y generación de plan
        ✓ Crear ChatSession (type='analysis') si no existe
        ✓ Mostrar chat para input del usuario
        
        Render: chat/analysis.html
        Datos en template:
        - project
        - session
        - messages
        
        
POST    /chat/send-message          → send_message() [REQUIRED LOGIN]
        Endpoint AJAX para enviar mensajes
        
        INPUT JSON:
        {
            "session_id": "<uuid>",
            "message": "<texto>"
        }
        
        VALIDACIONES:
        ✓ Verificar que sesión existe
        ✓ Verificar que usuario tiene acceso (project.user_id)
        ✓ Verificar message no vacío
        ✓ Verificar no alcanzó límite (max 10 msgs)
        
        LÓGICA:
        1. Guardar ChatMessage (role='user', content)
        2. Incrementar session.message_count
        3. Generar respuesta según session_type:
           - clarification: respuesta contextual
           - analysis: IA.generate_business_plan()
              → Crear BusinessPlan en BD
        4. Guardar ChatMessage (role='assistant', response)
        5. Si message_count >= MAX: lock session
        
        OUTPUT JSON:
        {
            "success": true,
            "response": "<ai-response>",
            "locked": false,
            "message_count": 5,
            "max_messages": 10
        }
        
        ERROR OUTPUT (429):
        {
            "error": "Se alcanzó el límite de mensajes",
            "locked": true
        }
```

---

## 🔐 Auth Flow (Sessions)

```
┌─────────────┐
│   Usuario   │
│  sin login  │
└──────┬──────┘
       │
       v
   /register ──→ POST ──→ Crear User + Hash password
       │                  ✓ Bcrypt hash
       │                  ✓ Validar RUT único
       │                  ✓ AuditLog
       v
   /login  ──→ POST ──→ Verificar credentials
       │               ✓ check_password()
       │               ✓ Flask-Login session
       │
       v
  [SESSION ACTIVE]
       │
       ├─→ GET /dashboard         (muestra proyectos)
       ├─→ POST /project/create   (nuevo proyecto)
       ├─→ GET /project/<id>      (ver proyecto)
       ├─→ GET /chat/...          (interactuar con IA)
       │
       v
   /logout ──→ GET ──→ Cerrar sesión
       │
       v
   [SESSION CLEAR]
```

---

## 📊 Flujo de Datos (Data Flow)

### 1. Crear Proyecto

```
USER
  └─ /project/create (POST)
      ├─ Validar rate_limiting: User.can_create_project()
      ├─ Crear: Project(user_id, title, raw_idea)
      ├─ AI CALL: IncubatorAI.evaluate_ambiguity(raw_idea)
      │           → variability_score (0-100)
      └─ Guardar: Project → PostgreSQL
         
         └─ Si ambiguo (> 66):
            ├─ Crear ChatSession(type='clarification')
            ├─ IA CALL: generate_clarification_questions()
            │           → 3 preguntas
            └─ Guardar: ChatMessage × 3 → PostgreSQL
               → Redirect /chat/clarification/<id>
```

### 2. Chat de Clarificación

```
USER at /chat/clarification/<id>
  ├─ Ver: 3 preguntas (ChatMessage, role='assistant')
  └─ POST /chat/send-message
      ├─ Validar session + user access
      ├─ Guardar: ChatMessage(role='user', message)
      ├─ increment session.message_count
      └─ Generar respuesta contextual
         ├─ Guardar: ChatMessage(role='assistant', response)
         ├─ Check: message_count >= 10?
         │         └─ Si: session.is_locked = True
         └─ Return JSON → Front reload
```

### 3. Análisis de Negocio

```
USER at /chat/analysis/<id>
  ├─ Crear: ChatSession(type='analysis') si no existe
  └─ POST /chat/send-message (trigger)
      ├─ Guardar: ChatMessage(role='user', message)
      ├─ AI CALL: IncubatorAI.generate_business_plan()
      │           → { problem_statement, value_prop, market, ...
      │               viability_score, recommendation }
      ├─ Crear: BusinessPlan → PostgreSQL
      ├─ Guardar: ChatMessage(role='assistant', assessment)
      ├─ Bloquear sesión si message_count >= 10
      └─ User ve reporte en /project/<id>
```

---

## 🔒 Authorization Checks

```
┌─────────────────────────────────────────────────────┐
│ Middleware/Decorator: @login_required               │
├─────────────────────────────────────────────────────┤
│ Rutas protegidas:                                   │
│ - /dashboard                                         │
│ - /project/create, /project/<id>                    │
│ - /chat/clarification/<id>, /chat/analysis/<id>     │
│ - /chat/send-message                                │
│ - /logout                                           │
└─────────────────────────────────────────────────────┘

DENTRO DE CADA RUTA:
  if project.user_id != current_user.id:
      → flash("No autorizado") + redirect
```

---

## 📈 Rate Limiting Implementation

```
RATE LIMITING POINTS:

1. CREATE PROJECT (Hard cap: 2 per 24 hours)
   ├─ Check: User.can_create_project()
   │  └─ Lógica: last_project_creation + 24h < now()
   ├─ Action: Allow or Flash + Redirect
   └─ Update: User.last_project_creation = now()

2. CHAT MESSAGES (Hard cap: 10 per session)
   ├─ Check: ChatSession.can_add_message(max=10)
   │  └─ Lógica: message_count < max_messages
   ├─ Action: Allow or Return 429 (Too Many Requests)
   └─ Update: ChatSession.is_locked = True al límite
```

---

## 📡 API Response Examples

### Success: Send Message

```json
{
  "success": true,
  "response": "Tu idea es interesante. Ahora...",
  "locked": false,
  "message_count": 5,
  "max_messages": 10
}
```

### Error: Rate Limited

```json
{
  "error": "Se alcanzó el límite de mensajes",
  "locked": true
}
```

### Error: Unauthorized

```json
{
  "error": "No autorizado"
}
[HTTP 403]
```

---

## 🗂️ URL Patterns Summary

| HTTP | Path | Handler | Auth | Desc |
|------|------|---------|------|------|
| GET | / | auth.index | ✗ | Landing |
| GET | /register | auth.register | ✗ | Form |
| POST | /register | auth.register | ✗ | Create user |
| GET | /login | auth.login | ✗ | Form |
| POST | /login | auth.login | ✗ | Session |
| GET | /logout | auth.logout | ✓ | Clear |
| GET | /dashboard | dash.dashboard | ✓ | Projects list |
| GET | /project/create | proj.create | ✓ | Form |
| POST | /project/create | proj.create | ✓ | Store |
| GET | /project/<id> | proj.view | ✓ | Details |
| GET | /chat/clarification/<id> | chat.clarif | ✓ | Chat UI |
| GET | /chat/analysis/<id> | chat.analysis | ✓ | Chat UI |
| POST | /chat/send-message | chat.send | ✓ | AJAX msg |

---

## 🧪 Testing URLs Localmente

```bash
# Sin login
curl http://localhost:5000/
curl http://localhost:5000/register
curl http://localhost:5000/login

# Con login (requiere session cookie)
curl -H "Cookie: session=<session-id>" http://localhost:5000/dashboard

# AJAX
curl -X POST http://localhost:5000/chat/send-message \
     -H "Content-Type: application/json" \
     -d '{"session_id":"<id>","message":"test"}'
```

---

**Última Actualización:** 17 de Enero de 2026
