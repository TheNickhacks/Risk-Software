"""
Rutas de Integración AI - Ejemplos de cómo conectar AI Service con Flask
Archivo: app/routes/ai_routes.py

Este módulo orquesta todo el flujo de análisis de ideas usando Gemini 2.5 Pro
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from typing import Dict

from app.models import db, Project, BusinessPlan, ChatSession, ChatMessage
from app.services import AIService, SessionManager
from app.services.gemini_service import SessionState

# Blueprint de rutas AI
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Almacenar sessions en memoria (en prod: usar Redis o DB)
_sessions: Dict[str, SessionManager] = {}


def get_or_create_session(project_id: str) -> SessionManager:
    """Obtener o crear sesión para un proyecto"""
    if project_id not in _sessions:
        ai_service = AIService()
        _sessions[project_id] = SessionManager(
            project_id=project_id,
            user_id=current_user.id,
            ai_service=ai_service
        )
    return _sessions[project_id]


@ai_bp.route('/projects/<project_id>/analyze', methods=['POST'])
@login_required
def analyze_idea(project_id: str):
    """
    Endpoint 1: Iniciar análisis de idea
    
    Request:
    {
        "raw_idea": "Descripción de la idea"
    }
    
    Response:
    {
        "status": "micro_interview_needed" | "blueprint_ready",
        "variability_score": 75,
        "clarity_assessment": "Idea parcialmente vaga...",
        "questions": [...],  // si necesita entrevista
        "next_action": "Responde las preguntas..."
    }
    """
    try:
        project = Project.query.get_or_404(project_id)
        
        # Validar que el usuario es dueño del proyecto
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        data = request.get_json()
        raw_idea = data.get('raw_idea')
        
        if not raw_idea or len(raw_idea) < 10:
            return jsonify({"error": "Idea debe tener al menos 10 caracteres"}), 400
        
        # Obtener/crear sesión
        session = get_or_create_session(project_id)
        
        # Procesar idea
        result = session.process_initial_input(raw_idea)
        
        # Guardar proyecto actualizado
        project.raw_idea = raw_idea
        project.variability_score = result['variability_score']
        
        if result['status'] == 'micro_interview_needed':
            project.status = 'ambiguous'
        else:
            project.status = 'ready'
        
        db.session.commit()
        
        current_app.logger.info(
            f"[AI] Análisis iniciado - Project: {project_id}, "
            f"Score: {result['variability_score']}"
        )
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "result": result
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en analyze_idea: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/projects/<project_id>/interview', methods=['POST'])
@login_required
def submit_interview_responses(project_id: str):
    """
    Endpoint 2: Procesar respuestas de micro-entrevista
    
    Request:
    {
        "answers": [
            "Respuesta a pregunta 1",
            "Respuesta a pregunta 2",
            "Respuesta a pregunta 3"
        ]
    }
    
    Response:
    {
        "status": "ready_for_blueprint",
        "refined_idea": "Idea mejorada con contexto...",
        "next_action": "Analizando viabilidad..."
    }
    """
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        data = request.get_json()
        answers = data.get('answers', [])
        
        if not answers or len(answers) == 0:
            return jsonify({"error": "Debes proporcionar respuestas"}), 400
        
        session = get_or_create_session(project_id)
        result = session.process_interview_responses(answers)
        
        current_app.logger.info(f"[AI] Entrevista procesada - Project: {project_id}")
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "result": result
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en submit_interview_responses: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/projects/<project_id>/generate-blueprint', methods=['POST'])
@login_required
def generate_blueprint(project_id: str):
    """
    Endpoint 3: Generar Blueprint de Viabilidad
    
    Response:
    {
        "status": "blueprint_generated",
        "blueprint": {
            "sections": {
                "problema_valor": "...",
                "mercado_ingresos": "...",
                "costos_recursos": "...",
                "viabilidad_riesgos": "...",
                "roadmap": "..."
            }
        },
        "messages_remaining": 10
    }
    """
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        session = get_or_create_session(project_id)
        result = session.generate_blueprint_phase()
        
        if "error" not in result:
            # Guardar blueprint en DB
            blueprint_data = result.get('blueprint', {})
            
            business_plan = BusinessPlan.query.filter_by(project_id=project_id).first()
            if not business_plan:
                business_plan = BusinessPlan(project_id=project_id)
            
            # Guardar secciones del blueprint
            sections = blueprint_data.get('sections', {})
            business_plan.problem_statement = sections.get('problema_valor')
            business_plan.value_proposition = sections.get('problema_valor')
            business_plan.target_market = sections.get('mercado_ingresos')
            business_plan.revenue_model = sections.get('mercado_ingresos')
            business_plan.cost_analysis = sections.get('costos_recursos')
            business_plan.technical_feasibility = sections.get('costos_recursos')
            business_plan.risks_analysis = sections.get('viabilidad_riesgos')
            business_plan.validation_strategy = sections.get('roadmap')
            business_plan.generated_at = datetime.now()
            
            db.session.add(business_plan)
            project.status = 'approved'
            db.session.commit()
            
            current_app.logger.info(f"[AI] Blueprint generado - Project: {project_id}")
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "result": result
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en generate_blueprint: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/projects/<project_id>/chat', methods=['POST'])
@login_required
def send_chat_message(project_id: str):
    """
    Endpoint 4: Enviar mensaje de chat contextual
    
    Request:
    {
        "message": "¿Cuál es el CAC estimado?"
    }
    
    Response:
    {
        "status": "chat_response",
        "message_number": 5,
        "messages_remaining": 5,
        "response": "Respuesta de la IA...",
        "phase": "contextual_chat" | "close_phase" | "completed",
        "hard_cap_reached": false
    }
    """
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        data = request.get_json()
        message = data.get('message')
        
        if not message or len(message) < 3:
            return jsonify({"error": "Mensaje muy corto"}), 400
        
        session = get_or_create_session(project_id)
        result = session.process_chat_message(message)
        
        # Guardar mensaje en BD
        chat_session = ChatSession.query.filter_by(project_id=project_id).first()
        if not chat_session:
            chat_session = ChatSession(project_id=project_id)
            db.session.add(chat_session)
            db.session.flush()
        
        # Guardar mensaje del usuario
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role='user',
            content=message,
            created_at=datetime.now()
        )
        db.session.add(user_msg)
        
        # Guardar respuesta de IA
        ai_msg = ChatMessage(
            session_id=chat_session.id,
            role='assistant',
            content=result['response'],
            created_at=datetime.now()
        )
        db.session.add(ai_msg)
        
        # Actualizar contador y lock de sesión
        chat_session.message_count = result['message_number']
        if result['message_number'] >= 10:
            chat_session.is_locked = True
            project.status = 'completed'
        
        db.session.commit()
        
        current_app.logger.info(
            f"[AI] Chat mensaje #{result['message_number']} - "
            f"Project: {project_id}"
        )
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "result": result
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en send_chat_message: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/projects/<project_id>/session-summary', methods=['GET'])
@login_required
def get_session_summary(project_id: str):
    """
    Endpoint 5: Obtener resumen de la sesión
    
    Response:
    {
        "phase": "contextual_chat",
        "variability_score": 45,
        "chat_message_count": 5,
        "blueprint_generated": true,
        "created_at": "2026-01-19T..."
    }
    """
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        session = get_or_create_session(project_id)
        summary = session.get_session_summary()
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "summary": summary
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en get_session_summary: {e}")
        return jsonify({"error": str(e)}), 500


@ai_bp.route('/projects/<project_id>/export', methods=['GET'])
@login_required
def export_session_data(project_id: str):
    """
    Endpoint 6: Exportar datos completos de la sesión
    
    Response: Datos para guardar o descargar
    """
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        session = get_or_create_session(project_id)
        export_data = session.export_session_data()
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "data": export_data
        })
    
    except Exception as e:
        current_app.logger.error(f"[AI] Error en export_session_data: {e}")
        return jsonify({"error": str(e)}), 500


# Error handlers
@ai_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Proyecto no encontrado"}), 404


@ai_bp.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Error interno del servidor"}), 500


# Registro del blueprint
# En app/__init__.py agregar:
# from app.routes.ai_routes import ai_bp
# app.register_blueprint(ai_bp)
