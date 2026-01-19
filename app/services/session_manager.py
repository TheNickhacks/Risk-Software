"""
Session Manager - Orquesta el flujo completo de la sesión
De idea bruta → Blueprint → Chat contextual → Cierre

Estados:
1. INITIAL_INPUT → Idea bruta ingresada
2. AMBIGUITY_CHECK → Se evalúa claridad
3. MICRO_INTERVIEW → Si es vaga, preguntar
4. BLUEPRINT_GENERATION → Generar reporte
5. CONTEXTUAL_CHAT → Chat sobre blueprint (max 10 msgs)
6. CLOSE_PHASE → Mensaje #8, iniciar cierre
7. COMPLETED → Reunión agendada
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SessionPhase(Enum):
    """Fases del flujo de sesión"""
    INITIAL_INPUT = "initial_input"
    AMBIGUITY_CHECK = "ambiguity_check"
    MICRO_INTERVIEW = "micro_interview"
    BLUEPRINT_READY = "blueprint_ready"
    CONTEXTUAL_CHAT = "contextual_chat"
    CLOSE_PHASE = "close_phase"
    COMPLETED = "completed"


class SessionManager:
    """Orquestador del flujo completo de la sesión"""

    def __init__(self, project_id: str, user_id: str, ai_service):
        """
        Inicializar sesión

        Args:
            project_id: ID del proyecto
            user_id: ID del usuario
            ai_service: Instancia de AIService (Gemini)
        """
        self.project_id = project_id
        self.user_id = user_id
        self.ai_service = ai_service

        # Estado de la sesión
        self.phase = SessionPhase.INITIAL_INPUT
        self.raw_idea = ""
        self.refined_idea = ""
        self.blueprint = {}
        self.ambiguity_result = {}
        self.interview_questions = []
        self.interview_answers = []
        self.chat_history = []
        self.message_count = 0

        logger.info(f"📊 Nueva sesión creada - Project: {project_id}")

    def process_initial_input(self, raw_idea: str) -> Dict:
        """
        Fase 1: Procesar idea bruta y hacer ambiguity check

        Args:
            raw_idea: Descripción de la idea del usuario

        Returns:
            Dict con resultado del ambiguity check
        """
        logger.info(f"📝 Procesando idea bruta para proyecto {self.project_id}")

        self.raw_idea = raw_idea
        self.phase = SessionPhase.AMBIGUITY_CHECK

        # 1. Ambiguity Check
        self.ambiguity_result = self.ai_service.check_ambiguity(raw_idea)

        # Guardar en historial
        self._add_to_history("system", f"Idea ingresada: {raw_idea}", "system")

        # Determinar siguiente paso
        if self.ambiguity_result.get("needs_interview", False):
            self.phase = SessionPhase.MICRO_INTERVIEW
            self.interview_questions = self.ambiguity_result.get("suggested_questions", [])

            logger.info(f"⚠️  Idea vaga detectada (Score: {self.ambiguity_result['variability_score']})")
            logger.info(f"🎤 Iniciando micro-entrevista con {len(self.interview_questions)} preguntas")

            return {
                "status": "micro_interview_needed",
                "variability_score": self.ambiguity_result["variability_score"],
                "clarity_assessment": self.ambiguity_result["clarity_assessment"],
                "questions": self.interview_questions,
                "next_action": "Responde las preguntas para clarificar tu idea"
            }
        else:
            # Idea clara, ir directo a blueprint
            self.refined_idea = raw_idea
            self.phase = SessionPhase.BLUEPRINT_READY

            logger.info(f"✓ Idea clara (Score: {self.ambiguity_result['variability_score']})")
            logger.info("📋 Generando blueprint...")

            return {
                "status": "blueprint_ready",
                "variability_score": self.ambiguity_result["variability_score"],
                "clarity_assessment": self.ambiguity_result["clarity_assessment"],
                "next_action": "Generando análisis de viabilidad..."
            }

    def process_interview_responses(self, answers: List[str]) -> Dict:
        """
        Fase 2a: Procesar respuestas de micro-entrevista

        Args:
            answers: Lista de 1-3 respuestas del usuario

        Returns:
            Dict indicando que blueprint está listo
        """
        if self.phase != SessionPhase.MICRO_INTERVIEW:
            logger.warning("⚠️  No estamos en fase de micro-entrevista")
            return {"error": "No hay preguntas pendientes"}

        logger.info(f"📥 Procesando {len(answers)} respuestas de entrevista")

        self.interview_answers = answers

        # Generar resumen contextual mejorado
        self.refined_idea = self.ai_service.micro_interview(
            self.raw_idea,
            self.interview_questions,
            self.interview_answers
        )

        # Guardar respuestas en historial
        for q, a in zip(self.interview_questions, answers):
            self._add_to_history("user", a, "answer", metadata={"question": q})

        # Transicionar a blueprint
        self.phase = SessionPhase.BLUEPRINT_READY

        logger.info("✓ Micro-entrevista completada")
        logger.info("📋 Generando blueprint con contexto mejorado...")

        return {
            "status": "ready_for_blueprint",
            "refined_idea": self.refined_idea,
            "next_action": "Analizando viabilidad con contexto completo..."
        }

    def generate_blueprint_phase(self) -> Dict:
        """
        Fase 3: Generar Blueprint de Viabilidad

        Returns:
            Dict con blueprint completo
        """
        if self.phase != SessionPhase.BLUEPRINT_READY:
            logger.warning("⚠️  Aún no estamos listos para blueprint")
            return {"error": "Idea no está clarificada"}

        logger.info(f"📋 Generando blueprint para proyecto {self.project_id}")

        # Generar blueprint
        self.blueprint = self.ai_service.generate_blueprint(self.refined_idea)

        if "error" in self.blueprint:
            logger.error(f"Error generando blueprint: {self.blueprint['error']}")
            return {"error": "No se pudo generar el blueprint"}

        # Guardar en historial
        self._add_to_history(
            "assistant",
            self.blueprint.get("raw_response", ""),
            "blueprint"
        )

        # Transicionar a chat contextual
        self.phase = SessionPhase.CONTEXTUAL_CHAT
        self.message_count = 0

        logger.info("✓ Blueprint generado exitosamente")
        logger.info("💬 Iniciando sesión de chat contextual (Max 10 mensajes)")

        return {
            "status": "blueprint_generated",
            "blueprint": self.blueprint,
            "next_action": "Puedes hacer preguntas sobre el análisis",
            "messages_remaining": self.ai_service.MAX_CHAT_MESSAGES
        }

    def process_chat_message(self, user_message: str) -> Dict:
        """
        Fase 4: Chat Contextual sobre Blueprint

        Args:
            user_message: Pregunta/comentario del usuario

        Returns:
            Dict con respuesta de IA y estado
        """
        if self.phase not in [SessionPhase.CONTEXTUAL_CHAT, SessionPhase.CLOSE_PHASE]:
            logger.warning(f"⚠️  No estamos en fase de chat (fase actual: {self.phase})")
            return {"error": "No hay blueprint para consultar"}

        self.message_count += 1

        logger.info(f"💬 Chat Mensaje #{self.message_count}")
        logger.info(f"   Usuario: {user_message[:100]}...")

        # Guardar mensaje del usuario
        self._add_to_history("user", user_message, "question")

        # Generar respuesta contextual
        ia_response, next_phase = self.ai_service.contextual_chat(
            self.blueprint,
            user_message,
            self.chat_history,
            self.message_count
        )

        # Guardar respuesta de IA
        self._add_to_history("assistant", ia_response, "answer")

        # Actualizar fase si es necesario
        if next_phase == "close_phase":
            self.phase = SessionPhase.CLOSE_PHASE
            logger.info("🎯 Fase de CIERRE iniciada (Mensaje #8)")
        elif next_phase == "completed":
            self.phase = SessionPhase.COMPLETED
            logger.info("✓ Sesión completada")

        result = {
            "status": "chat_response",
            "message_number": self.message_count,
            "messages_remaining": self.ai_service.MAX_CHAT_MESSAGES - self.message_count,
            "response": ia_response,
            "phase": self.phase.value
        }

        # Validar hard cap
        if self.message_count >= self.ai_service.MAX_CHAT_MESSAGES:
            result["hard_cap_reached"] = True
            self.phase = SessionPhase.COMPLETED
            logger.warning("⚠️  Hard cap de mensajes alcanzado")

        return result

    def get_session_summary(self) -> Dict:
        """Obtener resumen completo de la sesión"""
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "phase": self.phase.value,
            "raw_idea": self.raw_idea,
            "refined_idea": self.refined_idea,
            "variability_score": self.ambiguity_result.get("variability_score"),
            "blueprint_generated": bool(self.blueprint),
            "chat_message_count": self.message_count,
            "chat_history_length": len(self.chat_history),
            "created_at": datetime.now().isoformat()
        }

    def _add_to_history(self, role: str, content: str, message_type: str, metadata: Optional[Dict] = None) -> None:
        """
        Agregar mensaje al historial de chat

        Args:
            role: 'user', 'assistant', 'system'
            content: Contenido del mensaje
            message_type: Tipo ('question', 'answer', 'system', 'blueprint', etc)
            metadata: Datos adicionales
        """
        message = {
            "role": role,
            "content": content,
            "type": message_type,
            "timestamp": datetime.now().isoformat()
        }

        if metadata:
            message["metadata"] = metadata

        self.chat_history.append(message)

        logger.debug(f"📝 Mensaje agregado al historial: {role}/{message_type}")

    def export_session_data(self) -> Dict:
        """
        Exportar datos completos de la sesión (para guardar en DB)

        Returns:
            Dict con todos los datos formateados
        """
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "phase": self.phase.value,
            "raw_idea": self.raw_idea,
            "refined_idea": self.refined_idea,
            "ambiguity_score": self.ambiguity_result.get("variability_score"),
            "blueprint": self.blueprint,
            "interview_questions": self.interview_questions,
            "interview_answers": self.interview_answers,
            "total_chat_messages": self.message_count,
            "chat_history": self.chat_history,
            "timestamp": datetime.now().isoformat()
        }
