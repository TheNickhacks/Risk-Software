"""
AI Service - Gemini 1.5 Pro Integration
Flujo: Ambiguity Check → Blueprint Generation → Contextual Chat → Close to CTA

Arquitectura:
1. Refinamiento Activo: Detecta ideas vagas y lanza micro-entrevista
2. Procesamiento: Genera reporte de viabilidad (5 tópicos)
3. Consultoría: Chat contextual con Hard Cap de 10 mensajes
4. Cierre: Trigger en mensaje #8 para agendar reunión
"""

import os
import json
import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dotenv import load_dotenv

import google.generativeai as genai

load_dotenv()

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Estados del flujo de la sesión"""
    INITIAL_INPUT = "initial_input"
    AMBIGUITY_CHECK = "ambiguity_check"
    MICRO_INTERVIEW = "micro_interview"
    BLUEPRINT_GENERATION = "blueprint_generation"
    CONTEXTUAL_CHAT = "contextual_chat"
    CLOSE_PHASE = "close_phase"
    COMPLETED = "completed"


class AIService:
    """Servicio de IA con Gemini 2.5 Pro"""

    # Configuración
    MODEL_NAME = "gemini-2.5-pro"
    MAX_CHAT_MESSAGES = 10
    CLOSE_TRIGGER_MESSAGE = 8  # Iniciar cierre en mensaje #8

    # System Prompts
    SYSTEM_PROMPT_CONSULTOR = """Eres un Consultor de Negocios Senior - Critical Thinker.

DIRECTRICES DE TONO Y ESTILO:
- Profesional y analítico. No seas condescendiente ni destructivo.
- Usa lenguaje de negocios: Fricción, Barreras de Entrada, Unit Economics, CAC, LTV.
- Sé directo: identifica oportunidades Y limitaciones reales.
- Comunica con confianza pero humildad - conoce lo que no sabes.

OBJETIVO PRINCIPAL:
Ayudar a emprendedores a validar si sus ideas de negocio son viables,
identificando el problema real, el mercado y las rutas de go-to-market.

RESTRICCIÓN CRÍTICA:
Respuestas breves y concisas. Máximo 2-3 párrafos por respuesta."""

    SYSTEM_PROMPT_AMBIGUITY_CHECK = """Eres un analizador de claridad de ideas de negocio.

TAREA: Evalúa la DENSIDAD DE INFORMACIÓN de la idea presentada.

CRITERIOS DE VAGUEDAD (escala 0-100):
- 0-30: Clara y específica (idea lista para blueprint)
- 31-60: Parcialmente vaga (requiere 1-2 preguntas)
- 61-100: Muy vaga (requiere micro-entrevista de 3 preguntas)

RESPONDE EN JSON:
{
    "variability_score": <número 0-100>,
    "clarity_assessment": "<análisis breve>",
    "needs_interview": <true/false>,
    "suggested_questions": [
        "<pregunta 1 si es necesaria>",
        "<pregunta 2 si es necesaria>",
        "<pregunta 3 si es necesaria>"
    ]
}"""

    SYSTEM_PROMPT_BLUEPRINT = """Eres un generador de reportes de viabilidad de negocios.

ESTRUCTURA DEL REPORTE - 5 TÓPICOS INMUTABLES:

1. PROBLEMA REAL Y PROPUESTA DE VALOR
   - ¿Cuál es el problema específico que resuelve?
   - ¿Quién lo sufre y cuándo?
   - Propuesta de valor diferenciada

2. MERCADO Y MODELO DE INGRESOS
   - TAM (Total Addressable Market) estimado
   - Segmento objetivo inicial (SAM - Serviceable Available Market)
   - Modelo de ingresos (SaaS, commission, transaccional, etc.)
   - Pricing strategy indicativa

3. COSTOS Y RECURSOS
   - Inversión inicial estimada (MVP)
   - Recursos clave: personas, tech, partnerships
   - Burn rate mensual proyectado
   - Runway con inversión typical

4. VIABILIDAD Y RIESGOS
   - Barrera de entrada: Alta/Media/Baja
   - Competencia: Directa, Indirecta, None
   - Riesgos top 3 y mitigación
   - Dependencias críticas

5. ROADMAP PARA INICIAR (0-12 meses)
   - Sprint 0: Pre-MVP (semanas 1-4)
   - Sprint 1: MVP (semanas 5-12)
   - Métricas de éxito (KPIs)
   - Next funding milestone

TONO: Profesional, realista, sin suavizaciones. Sé crítico pero constructivo."""

    SYSTEM_PROMPT_CLOSE = """Eres un especialista en cierres de consultoría de negocios.

CONTEXTO: El usuario ha llegado al mensaje #8 de su sesión gratuita de consultoría.

OBJETIVO: Transicionar suavemente hacia el CTA (Call To Action): Agendar Reunión Estratégica

PUNTOS CLAVE PARA EL CIERRE:
1. Reconoce el progreso realizado en la validación de su idea
2. Identifica 2-3 gaps críticos que requieren análisis profundo
3. Sugiere que una "Reunión Estratégica" (30 min) ayudaría a:
   - Refinar el modelo de negocio
   - Conectar con mentores/inversores adecuados
   - Definir próximos pasos concretos
4. Presenta el CTA: "Agendar Reunión Estratégica Gratuita" (sin ser agresivo)

TONO: Profesional, consultivo, no de venta dura."""

    def __init__(self):
        """Inicializar servicio de IA"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en .env")

        genai.configure(api_key=api_key)
        logger.info("✓ Gemini 1.5 Pro configurado")

    def check_ambiguity(self, raw_idea: str) -> Dict:
        """
        Paso 1: Refinamiento Activo - Detectar vaguedad de idea

        Args:
            raw_idea: Descripción bruta de la idea

        Returns:
            Dict con variability_score, assessment y preguntas si es necesario
        """
        logger.info("🔍 Iniciando Ambiguity Check...")

        model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.SYSTEM_PROMPT_AMBIGUITY_CHECK
        )

        prompt = f"""Analiza esta idea de negocio:

\"\"\"{raw_idea}\"\"\"

Evalúa su densidad de información y claridad."""

        try:
            response = model.generate_content(prompt)
            result = json.loads(response.text)

            logger.info(
                f"✓ Ambiguity Check completado - Score: {result['variability_score']}"
            )

            return {
                "variability_score": result.get("variability_score", 50),
                "clarity_assessment": result.get("clarity_assessment", ""),
                "needs_interview": result.get("needs_interview", False),
                "suggested_questions": result.get("suggested_questions", [])
            }

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}")
            # Fallback
            return {
                "variability_score": 50,
                "clarity_assessment": response.text,
                "needs_interview": True,
                "suggested_questions": [
                    "¿Cuál es el problema específico que quieres resolver?",
                    "¿Quién es tu cliente ideal y cuánto pagaría?",
                    "¿Qué te diferencia de soluciones existentes?"
                ]
            }

    def micro_interview(
        self,
        raw_idea: str,
        questions: List[str],
        answers: List[str]
    ) -> str:
        """
        Paso 2a: Micro-entrevista de clarificación (máx 3 preguntas)

        Args:
            raw_idea: Idea original
            questions: Lista de preguntas hechas
            answers: Lista de respuestas del usuario

        Returns:
            Resumen contextual mejorado
        """
        logger.info("🎤 Ejecutando Micro-entrevista...")

        model = genai.GenerativeModel(self.MODEL_NAME)

        qa_context = "\n".join(
            [f"P: {q}\nR: {a}" for q, a in zip(questions, answers)]
        )

        prompt = f"""Basado en esta idea original y las respuestas de la micro-entrevista,
crea un RESUMEN CONTEXTUAL MEJORADO que capture los elementos críticos:

IDEA ORIGINAL:
{raw_idea}

CONTEXTO DE ENTREVISTA:
{qa_context}

PROPORCIONA:
- Idea refinada (1-2 párrafos)
- Problema core identificado
- Segmento de mercado objetivo
- Propuesta de valor clara"""

        try:
            response = model.generate_content(prompt)
            logger.info("✓ Micro-entrevista completada")
            return response.text
        except Exception as e:
            logger.error(f"Error en micro-entrevista: {e}")
            return raw_idea

    def generate_blueprint(self, refined_idea: str) -> Dict:
        """
        Paso 3: Procesamiento - Generar Blueprint de Viabilidad

        Estructura inmutable (5 tópicos):
        1. Problema Real y Propuesta de Valor
        2. Mercado y Modelo de Ingresos
        3. Costos y Recursos
        4. Viabilidad y Riesgos
        5. Roadmap para Iniciar

        Args:
            refined_idea: Idea refinada después de ambiguity check/interview

        Returns:
            Dict con blueprint completo
        """
        logger.info("📋 Generando Blueprint de Viabilidad...")

        model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.SYSTEM_PROMPT_BLUEPRINT
        )

        prompt = f"""Genera un reporte de viabilidad completo para esta idea:

{refined_idea}

Sigue ESTRICTAMENTE la estructura de 5 tópicos inmutables.
Sé crítico pero constructivo. Identifica oportunidades Y limitaciones reales."""

        try:
            response = model.generate_content(prompt)

            # Parsear respuesta en secciones
            blueprint = {
                "raw_response": response.text,
                "sections": self._parse_blueprint_sections(response.text),
                "generated_at": str(__import__('datetime').datetime.now())
            }

            logger.info("✓ Blueprint generado exitosamente")
            return blueprint

        except Exception as e:
            logger.error(f"Error generando blueprint: {e}")
            return {"error": str(e), "raw_response": ""}

    def _parse_blueprint_sections(self, blueprint_text: str) -> Dict:
        """Parsear respuesta del blueprint en sus 5 secciones"""
        sections = {
            "problema_valor": "",
            "mercado_ingresos": "",
            "costos_recursos": "",
            "viabilidad_riesgos": "",
            "roadmap": ""
        }

        # Búsqueda simple de secciones (mejorable con regex más sofisticado)
        lines = blueprint_text.split("\n")
        current_section = None

        for line in lines:
            lower_line = line.lower()

            if "problema" in lower_line and "valor" in lower_line:
                current_section = "problema_valor"
            elif "mercado" in lower_line or "ingresos" in lower_line:
                current_section = "mercado_ingresos"
            elif "costos" in lower_line or "recursos" in lower_line:
                current_section = "costos_recursos"
            elif "viabilidad" in lower_line or "riesgos" in lower_line:
                current_section = "viabilidad_riesgos"
            elif "roadmap" in lower_line or "iniciar" in lower_line:
                current_section = "roadmap"

            if current_section and line.strip():
                sections[current_section] += line + "\n"

        return sections

    def contextual_chat(
        self,
        blueprint: Dict,
        user_message: str,
        chat_history: List[Dict],
        message_count: int
    ) -> Tuple[str, str]:
        """
        Paso 4: Chat Contextual sobre el Blueprint

        Args:
            blueprint: Blueprint generado
            user_message: Mensaje del usuario
            chat_history: Historial previo de mensajes
            message_count: Número actual de mensaje (para trigger de cierre)

        Returns:
            Tuple: (respuesta_ia, estado_siguiente)
        """
        logger.info(f"💬 Chat Contextual - Mensaje #{message_count}")

        # Validar hard cap de 10 mensajes
        if message_count >= self.MAX_CHAT_MESSAGES:
            logger.warning("⚠️  Hard cap alcanzado - Chat bloqueado")
            return (
                "Has alcanzado el límite de mensajes de consultoría gratuita. "
                "Agendar una Reunión Estratégica te permitirá explorar más profundamente tu idea.",
                "completed"
            )

        # Sistema prompt para chat contextual
        blueprint_context = f"""CONTEXTO DEL BLUEPRINT:
{json.dumps(blueprint.get('sections', {}), ensure_ascii=False, indent=2)}

El usuario está haciendo preguntas sobre este análisis."""

        model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.SYSTEM_PROMPT_CONSULTOR
        )

        # Construir mensajes para conversación
        messages = []
        for msg in chat_history[-4:]:  # Últimos 4 mensajes para contexto
            messages.append({
                "role": msg["role"],
                "parts": [{"text": msg["content"]}]
            })

        # Agregar nuevo mensaje
        messages.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        try:
            response = model.generate_content(
                [{"text": blueprint_context}] + messages
            )

            ia_response = response.text

            # Verificar si estamos en fase de cierre (mensaje #8)
            estado = "contextual_chat"
            if message_count == self.CLOSE_TRIGGER_MESSAGE:
                logger.info("🎯 Trigger de cierre en mensaje #8")
                estado = "close_phase"
                # Agregar cierre contextual
                ia_response = self._add_close_context(ia_response)

            logger.info(f"✓ Respuesta contextual generada")
            return (ia_response, estado)

        except Exception as e:
            logger.error(f"Error en chat contextual: {e}")
            return (f"Error procesando tu pregunta: {str(e)}", "error")

    def _add_close_context(self, response: str) -> str:
        """Agregar contexto de cierre al final de la respuesta en mensaje #8"""
        close_message = f"""
---

📅 **PRÓXIMO PASO**

Dado el progreso en tu validación, te recomiendo una **Reunión Estratégica de 30 minutos** 
donde podamos:
- Refinar tu modelo de negocio con casos de referencia
- Conectarte con mentores/inversores según tu etapa
- Definir acciones concretas para las próximas 4 semanas

👉 [Agendar Reunión Estratégica Gratuita]

¿Preguntas antes de agendar?
"""
        return response + close_message

    def generate_closing_message(self, blueprint: Dict, chat_history: List[Dict]) -> str:
        """
        Generar mensaje de cierre profesional con CTA

        Args:
            blueprint: Blueprint completo
            chat_history: Historial de chat

        Returns:
            Mensaje de cierre con CTA
        """
        logger.info("🎯 Generando mensaje de cierre...")

        model = genai.GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.SYSTEM_PROMPT_CLOSE
        )

        chat_context = "\n".join(
            [f"{msg['role'].upper()}: {msg['content'][:200]}" for msg in chat_history[-5:]]
        )

        prompt = f"""Crea un mensaje de cierre/CTA basado en esta sesión:

BLUEPRINT GENERADO:
{json.dumps(blueprint.get('sections', {}), ensure_ascii=False)[:500]}

CONVERSACIÓN RECIENTE:
{chat_context}

Mensaje de cierre profesional con CTA a reunión estratégica."""

        try:
            response = model.generate_content(prompt)
            logger.info("✓ Mensaje de cierre generado")
            return response.text
        except Exception as e:
            logger.error(f"Error generando cierre: {e}")
            return "Gracias por esta sesión de validación. Te invito a agendar una Reunión Estratégica."


# Función auxiliar para testing
def test_ai_service():
    """Test básico del servicio"""
    try:
        service = AIService()

        # Test 1: Ambiguity Check
        test_idea = "Una app para conectar usuarios"
        ambiguity_result = service.check_ambiguity(test_idea)
        print(f"✓ Ambiguity Check: {ambiguity_result['variability_score']}")

        return True
    except Exception as e:
        logger.error(f"Error en test: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_ai_service()
