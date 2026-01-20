import google.generativeai as genai
from typing import Dict, List, Tuple
import json
import logging
import re

logger = logging.getLogger(__name__)


class IncubatorAI:
    """
    Servicio de IA para evaluación de ideas de negocio.
    Sistema de fallback automático entre modelos (mejor → peor calidad).
    Cambia automáticamente cuando se excede cuota gratuita.
    Incluye sanitización anti-Prompt Injection para proteger el sistema.
    """
    
    # Patrones de Prompt Injection detectados
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above|prior)\s+instructions?",
        r"disregard\s+(previous|all|above|prior)\s+instructions?",
        r"forget\s+(previous|all|above|prior)\s+(instructions?|prompts?)",
        r"(new|different|updated)\s+instructions?:",
        r"system\s*:\s*you\s+are",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"roleplay\s+as",
        r"act\s+as\s+(if|though|a|an)",
        r"pretend\s+(you|to\s+be)",
        r"<\s*script\s*>",
        r"javascript\s*:",
        r"eval\s*\(",
        r"exec\s*\(",
    ]
    
    # Modelos priorizados para análisis de texto (mejor → peor)
    MODEL_PRIORITY = [
        "gemini-2.5-flash",      # ⭐⭐⭐⭐⭐ RPM: 5, TPM: 250K
        "gemini-3-flash",         # ⭐⭐⭐⭐⭐ RPM: 5, TPM: 250K
        "gemini-2.5-flash-lite",  # ⭐⭐⭐⭐ RPM: 10, TPM: 250K
        "gemma-3-27b-it",         # ⭐⭐⭐⭐ RPM: 30, TPM: 15K (mejor Gemma)
        "gemma-3-12b-it",         # ⭐⭐⭐ RPM: 30, TPM: 15K (actual)
        "gemma-3-4b-it",          # ⭐⭐ RPM: 30, TPM: 15K
        "gemma-3-2b-it",          # ⭐ RPM: 30, TPM: 15K
        "gemma-3-1b-it",          # ⭐ RPM: 30, TPM: 15K (último recurso)
    ]
    
    # Los 9 Pilares de Viabilidad
    PILLARS = [
        "Problema Real",
        "Propuesta de Valor",
        "Mercado",
        "Modelo de Ingresos",
        "Costos",
        "Viabilidad Técnica",
        "Riesgos",
        "Escalabilidad",
        "Validación"
    ]
    
    SYSTEM_PROMPT = """Eres un analista de viabilidad de negocios experto. 
Tu rol es evaluar ideas de negocio de forma rigurosa bajo un enfoque de "Realismo Constructivo".

PRINCIPIOS FUNDAMENTALES:
1. Sé analítico y basado en datos. Evita optimismo excesivo.
2. Si una idea es inviable, presente el análisis completo y sugiera pivotes estratégicos.
3. Estructura toda respuesta bajo los 9 Pilares de Viabilidad.
4. Mantén un tono profesional, educativo y constructivo.
5. Proporciona accionables específicos, no genéricos.

ESCALA DE VIABILIDAD:
- 80-100: Viable y escalable (VERDE)
- 60-79: Viable con ajustes (AMARILLO)
- 40-59: Requiere pivote estratégico (NARANJA)
- 0-39: No viable en contexto actual (ROJO)
"""
    
    def __init__(self, api_key: str):
        """Inicializar cliente de Gemini con sistema de fallback"""
        genai.configure(api_key=api_key)
        self.api_key = api_key
        self.current_model_index = 0
        self.model = self._initialize_model()
        logger.info(f"✅ Modelo inicializado: {self.MODEL_PRIORITY[self.current_model_index]}")
    
    @staticmethod
    def sanitize_input(user_input: str) -> str:
        """
        Sanitizar input de usuario para prevenir Prompt Injection.
        
        Args:
            user_input: Texto ingresado por el usuario
            
        Returns:
            Texto sanitizado o excepción si se detecta ataque
            
        Raises:
            ValueError: Si se detecta intento de Prompt Injection
        """
        if not user_input or not isinstance(user_input, str):
            return ""
        
        # Normalizar a minúsculas para detección
        normalized = user_input.lower()
        
        # Detectar patrones maliciosos
        for pattern in IncubatorAI.INJECTION_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                logger.warning(f"🚨 Intento de Prompt Injection detectado: {pattern}")
                raise ValueError(
                    "Input no válido: Se detectó contenido potencialmente malicioso. "
                    "Por favor, describe tu idea de negocio sin incluir instrucciones al sistema."
                )
        
        # Limitar longitud (protección adicional contra ataques de contexto)
        max_length = 5000
        if len(user_input) > max_length:
            logger.warning(f"⚠️ Input excede longitud máxima: {len(user_input)} caracteres")
            user_input = user_input[:max_length]
        
        # Remover caracteres de control (excepto saltos de línea y tabs)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', user_input)
        
        return sanitized.strip()
    
    def _initialize_model(self):
        """Inicializar modelo actual basado en el índice de prioridad"""
        model_name = self.MODEL_PRIORITY[self.current_model_index]
        return genai.GenerativeModel(model_name)
    
    def _try_next_model(self):
        """Cambiar al siguiente modelo en la lista de prioridad"""
        if self.current_model_index < len(self.MODEL_PRIORITY) - 1:
            self.current_model_index += 1
            self.model = self._initialize_model()
            logger.warning(f"⚠️ Cambiando a modelo: {self.MODEL_PRIORITY[self.current_model_index]}")
            return True
        else:
            logger.error("❌ Todos los modelos han excedido su cuota")
            return False
    
    def _generate_with_fallback(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generar contenido con fallback automático si se excede cuota.
        Intenta con el modelo actual, si falla por cuota (429), prueba el siguiente.
        """
        attempts = 0
        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                # Error 429 = Cuota excedida
                if "429" in error_str or "quota" in error_str.lower():
                    logger.warning(f"⚠️ Cuota excedida para {self.MODEL_PRIORITY[self.current_model_index]}")
                    if not self._try_next_model():
                        raise Exception("Todos los modelos disponibles han excedido su cuota gratuita")
                    attempts += 1
                else:
                    # Otro tipo de error, no reintentar
                    logger.error(f"❌ Error al generar contenido: {e}")
                    raise e
        
        raise Exception(f"Falló después de {max_retries} intentos con diferentes modelos")
    
    def evaluate_ambiguity(self, raw_idea: str) -> Tuple[float, bool]:
        """
        Evaluar el grado de ambigüedad de una idea.
        Incluye sanitización anti-Prompt Injection.
        
        Returns:
            (variability_score: 0-100, requires_clarification: bool)
        """
        # Sanitizar input del usuario
        raw_idea = self.sanitize_input(raw_idea)
        
        prompt = f"""Analiza el siguiente pitch de negocio e indica su grado de ambigüedad.

PITCH: "{raw_idea}"

Responde SOLO en JSON con esta estructura:
{{
  "variability_score": <número 0-100>,
  "requires_clarification": <true/false>,
  "unclear_aspects": [<lista de aspectos ambiguos>]
}}

Donde:
- variability_score: 0 = completamente claro, 100 = completamente vago
- Considera variables como: falta de target market específico, modelo de ingresos ambiguo, etc.
"""
        try:
            response_text = self._generate_with_fallback(prompt)
            data = json.loads(response_text)
            return float(data.get("variability_score", 50)), data.get("requires_clarification", True)
        except Exception as e:
            logger.error(f"Error evaluating ambiguity: {e}")
            return 50.0, True
    
    def generate_clarification_questions(self, raw_idea: str, num_questions: int = 3) -> List[str]:
        """
        Generar preguntas de clarificación sobre la idea.
        Incluye sanitización anti-Prompt Injection.
        """
        # Sanitizar input del usuario
        raw_idea = self.sanitize_input(raw_idea)
        
        prompt = f"""El usuario presentó esta idea de negocio:

"{raw_idea}"

Genera exactamente {num_questions} preguntas clave para CLARIFICAR y VALIDAR la idea.
Las preguntas deben ser:
- Específicas y sin ambigüedad
- Enfocadas en los puntos débiles o vagos
- Orientadas a obtener información cuantificable

Responde SOLO en JSON:
{{
  "questions": ["pregunta1", "pregunta2", "pregunta3"]
}}
"""
        try:
            response_text = self._generate_with_fallback(prompt)
            data = json.loads(response_text)
            return data.get("questions", [])
        except Exception as e:
            logger.error(f"Error generating clarification questions: {e}")
            return [
                "¿Cuál es el mercado objetivo específico (geográfico, demográfico)?",
                "¿Cómo será el modelo de ingresos? (suscripción, transaccional, otro)",
                "¿Cuáles son los competidores directos y tu ventaja diferencial?"
            ]
    
    def generate_business_plan(self, raw_idea: str, clarifications: str = None) -> Dict:
        """
        Generar plan de negocio estructurado bajo los 9 Pilares.
        Incluye sanitización anti-Prompt Injection.
        
        Args:
            raw_idea: La idea original presentada
            clarifications: Respuestas del usuario a las preguntas de clarificación (opcional)
        
        Returns:
            Dictionary con análisis completo de viabilidad
        """
        # Sanitizar ambos inputs
        raw_idea = self.sanitize_input(raw_idea)
        if clarifications:
            clarifications = self.sanitize_input(clarifications)
        
        context = f"IDEA ORIGINAL:\n{raw_idea}"
        if clarifications:
            context += f"\n\nCLARIFICACIONES DEL USUARIO:\n{clarifications}"
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

EVALÚA LA IDEA bajo los 9 Pilares y responde en JSON VÁLIDO con esta estructura exacta:
{{
  "problem_statement": "Descripción del problema que la idea resuelve",
  "value_proposition": "Propuesta de valor diferencial",
  "target_market": "Descripción del mercado objetivo (TAM, segmento, geografía)",
  "revenue_model": "Modelo de ingresos y proyección de base revenue",
  "cost_analysis": "Análisis de costos operativos y de lanzamiento",
  "technical_feasibility": "Viabilidad técnica y requerimientos",
  "risks_analysis": "Principales riesgos y mitiga estrategias",
  "scalability_potential": "Potencial de escalabilidad y crecimiento",
  "validation_strategy": "Estrategia para validar la idea en mercado",
  "overall_assessment": "Síntesis ejecutiva de 3-4 párrafos",
  "viability_score": <número 0-100>,
  "recommendation": "viable|needs_pivot|not_viable",
  "pivot_suggestions": ["sugerencia1", "sugerencia2"] si recommendation != "viable"
}}

INSTRUCCIONES CRÍTICAS:
1. Sé honesto: si la idea no es viable, explícalo claramente.
2. Proporciona datos y referencias cuando sea posible.
3. Si recomiendas "needs_pivot", incluye alternativas estratégicas.
4. La puntuación debe reflejar viabilidad REALISTA, no optimista.
"""
        try:
            text = self._generate_with_fallback(prompt)
            
            # Limpiar respuesta de posibles marcas de markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            plan = json.loads(text.strip())
            return plan
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}. Response: {text}")
            return self._create_fallback_plan(raw_idea)
        except Exception as e:
            logger.error(f"Error generating business plan: {e}")
            return self._create_fallback_plan(raw_idea)
    
    def _create_fallback_plan(self, raw_idea: str) -> Dict:
        """Plan de negocio por defecto en caso de error"""
        return {
            "problem_statement": "Requiere análisis más detallado",
            "value_proposition": "Por definir",
            "target_market": "Por definir",
            "revenue_model": "Por definir",
            "cost_analysis": "Por definir",
            "technical_feasibility": "Por definir",
            "risks_analysis": "Por definir",
            "scalability_potential": "Por definir",
            "validation_strategy": "Por definir",
            "overall_assessment": "Error en generación automática. Por favor, intenta de nuevo.",
            "viability_score": 0,
            "recommendation": "not_viable",
            "pivot_suggestions": ["Refina la propuesta de valor", "Define mejor tu mercado objetivo"]
        }
    
    def generate_pivot_session(self, raw_idea: str, failing_pillars: List[str]) -> Dict:
        """
        Generar sesión de pivote estratégico cuando la idea no es viable.
        Incluye sanitización anti-Prompt Injection.
        """
        # Sanitizar input del usuario
        raw_idea = self.sanitize_input(raw_idea)
        
        prompt = f"""{self.SYSTEM_PROMPT}

IDEA ORIGINAL: "{raw_idea}"

Esta idea fue calificada como NO VIABLE porque falló en estos pilares:
{', '.join(failing_pillars)}

Tu tarea: Proporciona 3 PIVOTES ESTRATÉGICOS alternativos que:
1. Mantengan la esencia de la idea original
2. Aborden los pilares fallidos
3. Sean viables en el contexto actual

Responde en JSON:
{{
  "analysis": "Análisis de por qué falla la idea original",
  "pivots": [
    {{
      "title": "Pivote 1",
      "description": "Descripción",
      "key_changes": ["cambio1", "cambio2"],
      "improved_score_estimate": <número>
    }},
    {{
      "title": "Pivote 2",
      "description": "Descripción",
      "key_changes": ["cambio1", "cambio2"],
      "improved_score_estimate": <número>
    }},
    {{
      "title": "Pivote 3",
      "description": "Descripción",
      "key_changes": ["cambio1", "cambio2"],
      "improved_score_estimate": <número>
    }}
  ]
}}
"""
        try:
            text = self._generate_with_fallback(prompt)
            
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            pivot_data = json.loads(text.strip())
            return pivot_data
        except Exception as e:
            logger.error(f"Error generating pivot session: {e}")
            return {
                "analysis": "Error en generación. Intenta refinar tu idea y presentarla de nuevo.",
                "pivots": []
            }
