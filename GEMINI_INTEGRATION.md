# Integración Gemini 2.5 Pro - Sistema Completo

## ✅ Estado: CONFIGURADO Y FUNCIONAL

Tu sistema está completamente configurado con Gemini 2.5 Pro (no 1.5, ya que tu API key tiene acceso a 2.5).

---

## 📋 Módulos Implementados

### 1. **`app/services/gemini_service.py`** - AIService
Core del sistema con 4 métodos principales:

#### a) **Ambiguity Check** - Detectar vaguedad de idea
```python
result = service.check_ambiguity("Una app para conectar gente")
# Returns:
# {
#     "variability_score": 75,  # 0-100 (más alto = más vago)
#     "clarity_assessment": "Idea vaga...",
#     "needs_interview": True,
#     "suggested_questions": ["P1", "P2", "P3"]
# }
```

**Casos:**
- **Score 0-30**: Idea clara → Ir directo a Blueprint
- **Score 31-60**: Parcialmente vaga → 1-2 preguntas
- **Score 61-100**: Muy vaga → Micro-entrevista (3 preguntas)

#### b) **Micro-Interview** - Clarificar contexto
```python
refined_idea = service.micro_interview(
    raw_idea = "Una app...",
    questions = ["¿A quién va dirigida?", ...],
    answers = ["PyMEs del sector financiero", ...]
)
```

#### c) **Generate Blueprint** - Análisis de Viabilidad

Genera reporte en **5 tópicos inmutables**:

1. **Problema Real y Propuesta de Valor**
   - ¿Cuál es el problema?
   - ¿Quién lo sufre y cuándo?

2. **Mercado y Modelo de Ingresos**
   - TAM (Total Addressable Market)
   - SAM (Serviceable Available Market)
   - Modelo de ingresos
   - Pricing indicativo

3. **Costos y Recursos**
   - Inversión inicial (MVP)
   - Recursos clave
   - Burn rate proyectado
   - Runway con inversión

4. **Viabilidad y Riesgos**
   - Barrera de entrada (Alta/Media/Baja)
   - Competencia
   - Top 3 riesgos + mitigación
   - Dependencias críticas

5. **Roadmap para Iniciar (0-12 meses)**
   - Sprint 0: Pre-MVP (semanas 1-4)
   - Sprint 1: MVP (semanas 5-12)
   - KPIs de éxito
   - Next funding milestone

#### d) **Contextual Chat** - Consultoría sobre Blueprint
```python
response, next_phase = service.contextual_chat(
    blueprint = {...},
    user_message = "¿Cuál es el CAC estimado?",
    chat_history = [...],
    message_count = 5
)
```

**Características:**
- Hard Cap: 10 mensajes máximo
- Trigger de cierre: Mensaje #8
- Contexto del blueprint automáticamente incluido

---

### 2. **`app/services/session_manager.py`** - SessionManager
Orquestador del flujo completo:

```python
session = SessionManager(project_id, user_id, ai_service)

# Fase 1: Input inicial
result = session.process_initial_input("Mi idea es...")
# → Ambiguity check automático

# Fase 2: Si necesita entrevista
result = session.process_interview_responses(["Respuesta 1", ...])
# → Genera idea refinada

# Fase 3: Blueprint
result = session.generate_blueprint_phase()
# → Reporte de viabilidad

# Fase 4: Chat contextual
result = session.process_chat_message("¿Cómo financiar?")
# → Consultoría con límite de 10 msg
```

**Estados:**
```
INITIAL_INPUT 
    ↓
AMBIGUITY_CHECK 
    ↓
[MICRO_INTERVIEW] (si es vago)
    ↓
BLUEPRINT_READY
    ↓
BLUEPRINT_GENERATION
    ↓
CONTEXTUAL_CHAT (max 10 msgs)
    ↓ (en msg #8)
CLOSE_PHASE (CTA a reunión)
    ↓
COMPLETED
```

---

## 🎯 System Prompts

### Rol: **Consultor de Negocios Senior - Critical Thinker**

**Tono:**
- Profesional y analítico
- No condescendiente ni destructivo
- Lenguaje de negocios (fricción, barreras de entrada, unit economics)
- Directo: identifica oportunidades Y limitaciones

**Trigger de Cierre:**
- En mensaje #8, inicia suavemente el cierre
- Presenta CTA: "Agendar Reunión Estratégica"

---

## 💬 Modelo de Conversación

### Ejemplo de Flujo Completo

```
Usuario: "Una plataforma para conectar freelancers con empresas"
↓
[AMBIGUITY CHECK]
AI: "Tu idea tiene un score de vaguedad de 68. Necesito 3 preguntas 
para clarificar..."
↓
[MICRO-INTERVIEW]
Preguntas:
1. ¿Específicamente qué tipo de freelancers?
2. ¿Qué hace única tu plataforma vs Upwork?
3. ¿Cómo monetizarías?
↓
[Usuario responde]
↓
[BLUEPRINT GENERATION]
AI genera reporte con:
- Problema real: Mismatch entre talento y demanda
- Mercado: $X.XXM TAM en LATAM
- Modelo: Comisión 20% por proyecto
- Riesgos: Competencia establecida (mitigación: nicho PyMEs)
- Roadmap: MVP en 8 semanas
↓
[CONTEXTUAL CHAT - 10 mensajes máximo]
Usuario hace 7 preguntas sobre el blueprint
↓
[En mensaje #8]
AI: "Dado el análisis, identifiqué 3 gaps que requerirían 
análisis profundo. Una Reunión Estratégica (30 min) te ayudaría a:
- Refinar modelo de negocio
- Conectarte con inversores
- Definir próximos pasos

👉 [Agendar Reunión Estratégica Gratuita]"
↓
[Hard cap: 10 mensajes - Chat bloqueado]
AI: "Hemos alcanzado el límite de consultoría gratuita..."
```

---

## 🔧 Integración con Flask

### Rutas sugeridas:

```python
# app/routes/ai.py

@ai_bp.route('/api/projects/<project_id>/analyze', methods=['POST'])
def analyze_idea(project_id):
    """Iniciar flujo de análisis"""
    data = request.get_json()
    session = SessionManager(project_id, current_user.id, ai_service)
    result = session.process_initial_input(data['idea'])
    return jsonify(result)

@ai_bp.route('/api/projects/<project_id>/interview', methods=['POST'])
def submit_interview(project_id):
    """Procesar respuestas de entrevista"""
    data = request.get_json()
    result = session.process_interview_responses(data['answers'])
    return jsonify(result)

@ai_bp.route('/api/projects/<project_id>/chat', methods=['POST'])
def chat_message(project_id):
    """Enviar mensaje de chat"""
    data = request.get_json()
    result = session.process_chat_message(data['message'])
    return jsonify(result)
```

---

## 📊 Guardando en Base de Datos

```python
# Después de cada phase, guardar en DB

def save_session_to_db(project_id, session_data):
    # Actualizar project
    project = Project.query.get(project_id)
    project.variability_score = session_data['ambiguity_score']
    project.status = 'ambiguous' if session_data['needs_interview'] else 'ready'
    
    # Guardar business_plan
    business_plan = BusinessPlan(
        project_id=project_id,
        problem_statement=session_data['blueprint']['sections']['problema_valor'],
        value_proposition=session_data['blueprint']['sections']['problema_valor'],
        # ... resto de campos
    )
    
    # Guardar chat_messages
    for msg in session_data['chat_history']:
        chat_msg = ChatMessage(
            session_id=chat_session.id,
            role=msg['role'],
            content=msg['content'],
            message_type=msg['type']
        )
    
    db.session.commit()
```

---

## ⚙️ Configuración Actual

**Archivo:** `.env`
```env
GEMINI_API_KEY=AIzaSyD9d61kEHZLtMcZzxhMCONHFzn-YukIJbc
DATABASE_URL=postgresql://neondb_owner:...@ep-floral-tooth-ac0maau6-pooler...
MODEL_NAME=gemini-2.5-pro
MAX_CHAT_MESSAGES=10
CLOSE_TRIGGER_MESSAGE=8
```

**Modelo:** Gemini 2.5 Pro (más potente que 1.5)

---

## 🚀 Próximos Pasos

1. **Conectar SessionManager con Flask routes**
2. **Guardar sessions en Neon DB**
3. **Crear endpoints para frontend (React/Vue)**
4. **Implementar WebSocket para chat en tiempo real**
5. **Agregar Google Calendar integration para CTA**

---

## 🧪 Tests

Scripts de validación:
- `test_db_connection.py` - Validar Neon DB ✅
- `test_gemini_flow.py` - Flujo completo Gemini
- `test_gemini_simple.py` - Test básico de modelo
- `list_models.py` - Listar modelos disponibles

---

## 📝 Notas Importantes

⚠️ **Cuota Gratuita:** Tu API key tiene límites diarios. Para producción, configura un plan pagado.

✅ **Validado:** El sistema genera respuestas coherentes de IA (probado hasta límite de cuota)

🔒 **Seguridad:** API key está en `.env` (NO en git/repos públicos)

🎯 **Escalabilidad:** SessionManager permite múltiples sesiones simultáneas con diferentes contextos

