import google.generativeai as genai
from typing import Dict, List, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class IncubatorAI:
    """
    Servicio de IA para evaluación de ideas de negocio.
    Integración con Gemma 3 12B bajo enfoque de "Realismo Constructivo".
    """
    
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
        """Inicializar cliente de Gemini"""
        genai.configure(api_key=api_key)
        # Usar gemma-3-12b-it (mejor cuota gratuita, buena calidad)
        self.model = genai.GenerativeModel("gemma-3-12b-it")
        logger.info("✅ Gemma 3 12B inicializado correctamente")
    
    def evaluate_ambiguity(self, raw_idea: str) -> Tuple[float, bool]:
        """
        Evaluar el grado de ambigüedad de una idea.
        
        Returns:
            (variability_score: 0-100, requires_clarification: bool)
        """
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
            response = self.model.generate_content(prompt)
            data = json.loads(response.text)
            return float(data.get("variability_score", 50)), data.get("requires_clarification", True)
        except Exception as e:
            logger.error(f"Error evaluating ambiguity: {e}")
            return 50.0, True
    
    def generate_clarification_questions(self, raw_idea: str, num_questions: int = 3) -> List[str]:
        """
        Generar preguntas de clarificación sobre la idea.
        """
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
            response = self.model.generate_content(prompt)
            data = json.loads(response.text)
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
        
        Args:
            raw_idea: La idea original presentada
            clarifications: Respuestas del usuario a las preguntas de clarificación (opcional)
        
        Returns:
            Dictionary con análisis completo de viabilidad
        """
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
            response = self.model.generate_content(prompt)
            text = response.text
            
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
            logger.error(f"JSON parsing error: {e}. Response: {response.text}")
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
        """
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
            response = self.model.generate_content(prompt)
            text = response.text
            
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
