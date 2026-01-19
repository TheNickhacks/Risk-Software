# GUÍA RÁPIDA - Integrar AI en tu Flask App

## Paso 1: Registrar el Blueprint (3 líneas)

En `app/__init__.py`, agregar después de registrar otros blueprints:

```python
# Línea a agregar
from app.routes.ai_routes import ai_bp

# En create_app()
app.register_blueprint(ai_bp)
```

---

## Paso 2: Crear un Template Básico

`app/templates/project/analyze.html`

```html
{% extends "layout.html" %}

{% block content %}
<div class="container">
    <h1>Analizar Idea de Negocio</h1>
    
    <!-- Fase 1: Input inicial -->
    <div id="phase-initial">
        <form id="ideaForm">
            <textarea id="idea" placeholder="Describe tu idea de negocio..." required></textarea>
            <button type="submit">Analizar</button>
        </form>
    </div>
    
    <!-- Fase 2: Micro-interview (condicional) -->
    <div id="phase-interview" style="display:none;">
        <h3>Clarifica tu idea</h3>
        <form id="interviewForm"></form>
        <button onclick="submitInterview()">Enviar Respuestas</button>
    </div>
    
    <!-- Fase 3: Blueprint -->
    <div id="phase-blueprint" style="display:none;">
        <h3>Tu Análisis de Viabilidad</h3>
        <div id="blueprintContent"></div>
        <button onclick="goToChat()">Hacer Preguntas</button>
    </div>
    
    <!-- Fase 4: Chat -->
    <div id="phase-chat" style="display:none;">
        <h3>Chat Consultivo (Mensajes restantes: <span id="msgRemaining">10</span>)</h3>
        <div id="chatMessages" style="height:400px; overflow-y:auto; border:1px solid #ccc; padding:10px;"></div>
        <input type="text" id="chatInput" placeholder="Escribe tu pregunta...">
        <button onclick="sendMessage()">Enviar</button>
    </div>
</div>

<script>
const projectId = "{{ project.id }}";

// Fase 1: Analizar idea
document.getElementById('ideaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const idea = document.getElementById('idea').value;
    
    const response = await fetch(`/api/ai/projects/${projectId}/analyze`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({raw_idea: idea})
    });
    
    const data = await response.json();
    const result = data.result;
    
    if (result.status === 'micro_interview_needed') {
        // Mostrar preguntas
        showInterview(result.questions);
    } else {
        // Ir a blueprint
        await generateBlueprint();
    }
});

function showInterview(questions) {
    document.getElementById('phase-initial').style.display = 'none';
    document.getElementById('phase-interview').style.display = 'block';
    
    const form = document.getElementById('interviewForm');
    form.innerHTML = '';
    questions.forEach((q, i) => {
        form.innerHTML += `
            <div>
                <label>${q}</label>
                <textarea name="answer${i}" required></textarea>
            </div>
        `;
    });
}

async function submitInterview() {
    const formData = new FormData(document.getElementById('interviewForm'));
    const answers = Array.from(formData.values());
    
    await fetch(`/api/ai/projects/${projectId}/interview`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({answers})
    });
    
    await generateBlueprint();
}

async function generateBlueprint() {
    document.getElementById('phase-interview').style.display = 'none';
    document.getElementById('phase-initial').style.display = 'none';
    
    const response = await fetch(`/api/ai/projects/${projectId}/generate-blueprint`, {
        method: 'POST'
    });
    
    const data = await response.json();
    const blueprint = data.result.blueprint.sections;
    
    const html = `
        <h4>Problema Real y Propuesta de Valor</h4>
        <p>${blueprint.problema_valor}</p>
        
        <h4>Mercado y Modelo de Ingresos</h4>
        <p>${blueprint.mercado_ingresos}</p>
        
        <h4>Costos y Recursos</h4>
        <p>${blueprint.costos_recursos}</p>
        
        <h4>Viabilidad y Riesgos</h4>
        <p>${blueprint.viabilidad_riesgos}</p>
        
        <h4>Roadmap para Iniciar</h4>
        <p>${blueprint.roadmap}</p>
    `;
    
    document.getElementById('blueprintContent').innerHTML = html;
    document.getElementById('phase-blueprint').style.display = 'block';
}

function goToChat() {
    document.getElementById('phase-blueprint').style.display = 'none';
    document.getElementById('phase-chat').style.display = 'block';
}

async function sendMessage() {
    const message = document.getElementById('chatInput').value;
    document.getElementById('chatInput').value = '';
    
    const response = await fetch(`/api/ai/projects/${projectId}/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message})
    });
    
    const data = await response.json();
    const result = data.result;
    
    // Agregar mensajes
    const chatDiv = document.getElementById('chatMessages');
    chatDiv.innerHTML += `<p><strong>Tú:</strong> ${message}</p>`;
    chatDiv.innerHTML += `<p><strong>IA:</strong> ${result.response}</p>`;
    chatDiv.scrollTop = chatDiv.scrollHeight;
    
    document.getElementById('msgRemaining').textContent = result.messages_remaining;
    
    if (result.hard_cap_reached) {
        document.getElementById('chatInput').disabled = true;
        document.getElementById('chatInput').placeholder = 'Consultoría finalizada';
    }
}
</script>
{% endblock %}
```

---

## Paso 3: Agregar Ruta en Flask

En `app/routes.py` o `app/routes/__init__.py`:

```python
@app.route('/projects/<project_id>/analyze')
@login_required
def analyze_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)
    return render_template('project/analyze.html', project=project)
```

---

## Paso 4: Verificar Configuración

Checklist antes de correr:

```bash
# ✅ .env tiene GEMINI_API_KEY
grep GEMINI_API_KEY .env

# ✅ .env tiene DATABASE_URL
grep DATABASE_URL .env

# ✅ requirements.txt actualizado
pip install -r requirements.txt

# ✅ BD sincronizada
python -c "from app.models import db; db.create_all()"
```

---

## Paso 5: Ejecutar Aplicación

```bash
# Terminal 1: Servidor Flask
python main.py

# Terminal 2: (opcional) Monitoreo
tail -f logs/preincubadora.log
```

**URL:** http://localhost:5000/projects/{project_id}/analyze

---

## ⚠️ Solución de Problemas

| Problema | Solución |
|----------|----------|
| "ModuleNotFoundError: No module named 'app.routes.ai_routes'" | Asegúrate que `ai_routes.py` existe en `app/routes/` |
| "GEMINI_API_KEY not found" | Verifica `.env` tenga la clave correcta |
| "Database connection error" | Prueba: `python test_db_connection.py` |
| "429 Quota exceeded" | Upgrade a plan pagado en Google AI |

---

## 📊 Flujo Implementado

```
UI (navigate a /projects/{id}/analyze)
    ↓
Phase 1: Idea Input → POST /api/ai/projects/{id}/analyze
    ↓
[Decision: ¿Idea vaga?]
    ├─ SÍ → Phase 2: Micro-Interview → POST /api/ai/projects/{id}/interview
    │        ↓
    │   Phase 3: Blueprint → POST /api/ai/projects/{id}/generate-blueprint
    │        ↓
    └─ NO → Phase 3: Blueprint (directo)
                ↓
           Phase 4: Chat → POST /api/ai/projects/{id}/chat
                ├─ Msg 1-7: Consultoría normal
                ├─ Msg 8: IA inicia cierre
                └─ Msg 10: Hard cap, sesión completada
```

---

## 🎯 Endpoints Disponibles

```javascript
// Analizar idea
POST /api/ai/projects/{id}/analyze
Body: {raw_idea: "..."}

// Enviar respuestas entrevista
POST /api/ai/projects/{id}/interview
Body: {answers: ["R1", "R2", "R3"]}

// Generar blueprint
POST /api/ai/projects/{id}/generate-blueprint
Body: {}

// Enviar mensaje chat
POST /api/ai/projects/{id}/chat
Body: {message: "..."}

// Obtener resumen
GET /api/ai/projects/{id}/session-summary

// Exportar datos
GET /api/ai/projects/{id}/export
```

---

## ✅ Verificación Final

```bash
# 1. Importar servicios sin errores
python -c "from app.services import AIService, SessionManager; print('OK')"

# 2. Verificar rutas registradas
python -c "from app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'ai' in r.rule])"

# 3. Test de conectividad
python test_db_connection.py
```

---

## 🚀 ¡Listo!

Tu aplicación ya tiene:
- ✅ Análisis inteligente de ideas
- ✅ Micro-entrevistas guiadas
- ✅ Reportes de viabilidad en 5 secciones
- ✅ Chat consultivo con CTA
- ✅ Guardado automático en BD

**Tiempo de integración:** ~10 minutos ⏱️

---

**Soporte:** Ver `GEMINI_INTEGRATION.md` para detalles técnicos completos
