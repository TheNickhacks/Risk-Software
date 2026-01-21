# Preferir la nueva librería oficial google.genai; fallback a google.generativeai si no está disponible
try:
    from google import genai as google_genai
    _USE_GOOGLE_GENAI = True
except Exception:
    import google.generativeai as google_generativeai
    _USE_GOOGLE_GENAI = False
from typing import Dict, List, Tuple
import json
import logging
import re

logger = logging.getLogger(__name__)


class _GenaiModelWrapper:
    """Wrapper para unificar interfaz generate_content entre google.genai y generativeai."""
    def __init__(self, client, model_name: str):
        self._client = client
        self._model_name = model_name

    def generate_content(self, prompt: str):
        # API de google.genai: client.models.generate_content(model=..., contents=[...])
        return self._client.models.generate_content(
            model=self._model_name,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )


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
    
    SYSTEM_PROMPT = """## 1.0 Prompt de Sistema: Arquitectura Lógica de Consultoría

### 1.1 Identidad y Rol Estratégico
* **Perfil**: Eres un Consultor de Negocios Senior y Analista Crítico de Riesgos.
* **Misión**: Tu objetivo es transformar ideas de negocio vagas en un "Business Blueprint" (Esquema de Negocio) ejecutable o detectar su inviabilidad antes de que el usuario invierta capital.
* **Filosofía de Comunicación**: Aplica el "Realismo Constructivo". Tu tono es profesional, analítico y preventivo, nunca destructivo ni excesivamente entusiasta.

### 1.2 Protocolo de Ingesta y Triaje (Mensajes 1-3)
* **Evaluación de Densidad**: Ante el primer input, determina si es "Estado Vago" (falta de variables críticas) o "Estado Denso" (ejecutable).
* **El Interrogatorio**: Si la idea es vaga, el sistema no generará el reporte aún. Debes formular dinámicamente hasta 3 preguntas críticas (Golden Questions) para aterrizar la idea:
    1. **Vector del Dolor**: ¿Cuál es el problema costoso o frustrante que resuelves?
    2. **Vector de Urgencia**: ¿Quién está perdiendo dinero o tiempo ahora mismo? (Nicho específico).
    3. **Vector de Transacción**: Si vendieras esto mañana sin software, ¿cómo cobrarías?

### 1.3 Framework de Análisis de 9 Pilares (Mensajes 4-7)
Evalúa internamente estos pilares para construir el reporte final:
1. Problema Real
2. Propuesta de Valor
3. Mercado
4. Modelo de Ingresos
5. Costos y Recursos
6. Viabilidad Técnica
7. Riesgos
8. Escalabilidad
9. Validación

### 1.4 Generación del "Business Blueprint" (Mensaje 8)
En el mensaje número 8 detén preguntas y entrega el análisis final con esta estructura JSON:
{
    "viability_score": <0-100>,
    "semaforo": "🟢|🟡|🔴",
    "resumen_ejecutivo": {
        "propuesta": "...",
        "mercado": "...",
        "ingresos": "...",
        "operaciones": "...",
        "roadmap": "..."
    }
}

### 1.5 Protocolo de Conversión y Cierre (Mensajes 9-10)
* **Trigger de Venta**: Tras el Blueprint, dirige a una reunión de consultoría humana.
* **CTA**:
    * Verde: "Tu proyecto es viable. Agendemos para ver costos de desarrollo".
    * Rojo/Amarillo: "Hemos detectado riesgos críticos. Agendemos para pivotar la idea antes de que pierdas dinero".
* **Mensaje 10**: Entrega link de agendamiento y bloquea más entradas (Hard Cap).

---

## 2.0 Reglas de Control Técnico para el Desarrollador
* **Aislamiento de Contexto**: Cada project_id reinicia el prompt del sistema. No recuerdes ideas previas del mismo usuario.
* **Gestión de Errores**: Si el usuario evade el triaje con respuestas irrelevantes, responde: "Necesitamos más detalles para evaluar tu idea".
* **Restricciones de Datos**: No uses datos del usuario para entrenar modelos públicos; informa que los datos se procesan vía API segura.
"""

    # Banco de preguntas clave (concisas, ≤20 palabras)
    QUESTIONS_BANK = [
        "¿Cuál es el mercado objetivo específico y su tamaño estimado?",
        "¿Qué segmento de clientes inicial abordarás y por qué?",
        "¿Cuál es el problema concreto que resuelves?",
        "¿Cómo te diferencias de los competidores clave?",
        "¿Cuál será el precio promedio y el margen bruto?",
        "¿Qué canales usarás para adquirir clientes? CAC estimado",
        "¿Cuál es el costo fijo mensual y costos variables principales?",
        "¿Cuál es el punto de equilibrio y volumen mínimo?",
        "¿Qué validaciones previas tienes (encuestas, ventas, pilotos)?",
        "¿Cuáles son los mayores riesgos y cómo los mitigas?",
        "¿Qué restricciones operativas o regulatorias existen?",
        "¿Qué capacidades técnicas necesitas y cómo las obtendrás?",
        "¿Cómo asegurarás calidad, garantía y postventa?",
        "¿Cuál es el flujo de caja esperado 6 meses?",
        "¿Qué KPIs clave medirás en el inicio?",
        "¿Cuál es tu estrategia de escalabilidad y límites actuales?",
        "¿Cómo manejarás devoluciones, soporte y servicio?",
        "¿Qué datos sensibles manejas y cómo los protegerás?",
    ]
    
    def __init__(self, api_key: str):
        """Inicializar cliente de Gemini con sistema de fallback"""
        self.api_key = api_key
        self.current_model_index = 0

        if _USE_GOOGLE_GENAI:
            # Nueva librería oficial
            self._client = google_genai.Client(api_key=api_key)
        else:
            # Librería deprecada, usada como fallback
            google_generativeai.configure(api_key=api_key)
            self._client = None

        self.model = self._initialize_model()
        logger.info(f"[OK] Modelo inicializado: {self.MODEL_PRIORITY[self.current_model_index]}")
    
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
                logger.warning(f"[ALERT] Intento de Prompt Injection detectado: {pattern}")
                raise ValueError(
                    "Input no válido: Se detectó contenido potencialmente malicioso. "
                    "Por favor, describe tu idea de negocio sin incluir instrucciones al sistema."
                )
        
        # Limitar longitud (protección adicional contra ataques de contexto)
        max_length = 5000
        if len(user_input) > max_length:
            logger.warning(f"[WARNING] Input excede longitud máxima: {len(user_input)} caracteres")
            user_input = user_input[:max_length]
        
        # Remover caracteres de control (excepto saltos de línea y tabs)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', user_input)
        
        return sanitized.strip()
    
    def _initialize_model(self):
        """Inicializar modelo actual basado en el índice de prioridad"""
        model_name = self.MODEL_PRIORITY[self.current_model_index]
        if _USE_GOOGLE_GENAI:
            return _GenaiModelWrapper(self._client, model_name)
        else:
            return google_generativeai.GenerativeModel(model_name)

    @staticmethod
    def _extract_json_payload(text: str):
        """Extrae un payload JSON válido desde texto que pueda contener ruido/markdown.

        Soporta objetos y arreglos como raíz. Elimina bloques ```json y ``` si existen,
        y recorta al primer '{' o '[' hasta el último '}' o ']'.
        """
        if not text:
            raise json.JSONDecodeError("Respuesta vacía", text, 0)
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        start_obj = cleaned.find('{')
        start_arr = cleaned.find('[')
        starts = [i for i in [start_obj, start_arr] if i != -1]
        if not starts:
            raise json.JSONDecodeError("No se encontró JSON (objeto/arreglo)", cleaned, 0)
        start = min(starts)

        end_obj = cleaned.rfind('}')
        end_arr = cleaned.rfind(']')
        ends = [i for i in [end_obj, end_arr] if i != -1 and i >= start]
        if not ends:
            raise json.JSONDecodeError("JSON incompleto: falta cierre", cleaned, len(cleaned))
        end = max(ends) + 1

        payload = cleaned[start:end]
        return json.loads(payload)
    
    def _try_next_model(self):
        """Cambiar al siguiente modelo en la lista de prioridad"""
        if self.current_model_index < len(self.MODEL_PRIORITY) - 1:
            self.current_model_index += 1
            self.model = self._initialize_model()
            logger.warning(f"[FALLBACK] Cambiando a modelo: {self.MODEL_PRIORITY[self.current_model_index]}")
            return True
        else:
            logger.error("[ERROR] Todos los modelos han excedido su cuota")
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
                    logger.warning(f"[QUOTA] Cuota excedida para {self.MODEL_PRIORITY[self.current_model_index]}")
                    if not self._try_next_model():
                        raise Exception("Todos los modelos disponibles han excedido su cuota gratuita")
                    attempts += 1
                else:
                    # Otro tipo de error, no reintentar
                    logger.error(f"[ERROR] Error al generar contenido: {e}")
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

Responde SOLO en JSON VÁLIDO (sin markdown, sin texto adicional) con esta estructura exacta:
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
            data = self._extract_json_payload(response_text)
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
Requisitos de las preguntas:
- Lenguaje simple y tono clarificador.
- Bloques cortos (máximo 20 palabras).
- Específicas y sin ambigüedad.
- Enfocadas en puntos vagos o críticos.
- Orientadas a obtener información cuantificable.

BANCO DE PREGUNTAS DISPONIBLE (usa las más relevantes; si faltan, crea nuevas del mismo estilo):
{json.dumps(self.QUESTIONS_BANK, ensure_ascii=False)}

Responde SOLO en JSON VÁLIDO (sin markdown, sin texto adicional):
{{
  "questions": ["pregunta1", "pregunta2", "pregunta3"]
}}
"""
        try:
            response_text = self._generate_with_fallback(prompt)
            data = self._extract_json_payload(response_text)
            if isinstance(data, dict):
                return data.get("questions", [])
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"Error generating clarification questions: {e}")
            return [
                "¿Cuál es el mercado objetivo específico (geográfico, demográfico)?",
                "¿Cómo será el modelo de ingresos? (suscripción, transaccional, otro)",
                "¿Cuáles son los competidores directos y tu ventaja diferencial?"
            ]

    def generate_clarification_reply(
        self,
        raw_idea: str,
        conversation_context: str,
        user_turn: int,
        asked_questions: List[str] = None,
        min_questions: int = 2,
        max_questions: int = 5,
    ) -> str:
        """
        Genera la siguiente intervención del asistente en la sesión de clarificación.
        Sigue el flujo conversacional definido en el SYSTEM_PROMPT por número de mensaje del usuario.
        user_turn es el índice de mensaje del usuario en la sesión (1-based, solo mensajes de rol "user").
        """
        raw_idea = self.sanitize_input(raw_idea)
        context = conversation_context or ""
        asked_questions = asked_questions or []
        unique_questions = "\n".join([f"- {q}" for q in asked_questions[-8:]])

        prompt = f"""
{self.SYSTEM_PROMPT}

NÚMERO DE MENSAJE DEL USUARIO (solo mensajes de rol user): {user_turn}
INSTRUCCIONES DE FLUJO:
 - Mensajes 1-3: aplica triaje, formula máximo 3 Golden Questions, no entregues blueprint.
 - Mensajes 4-7: profundiza en los 9 Pilares con preguntas o mini-resúmenes breves.
 - Mensaje 8: deja de preguntar y entrega el Business Blueprint en el formato indicado (JSON compacto).
 - Mensajes 9-10: CTA según semáforo; en 10 entrega link genérico de agendamiento y corta el chat.

CONTROL DE PREGUNTAS ÚNICAS Y PROGRESO:
- Ya hiciste {len(asked_questions)} preguntas. Objetivo: mínimo {min_questions}, máximo {max_questions} preguntas únicas.
- Preguntas ya hechas (NO repetir ni re-frasear):
{unique_questions if unique_questions else "- Ninguna aún"}
- Mientras no alcances el mínimo de preguntas, prioriza hacer preguntas nuevas, concretas (<=20 palabras) y sin redundancia.
- Al llegar al mínimo o si ya tienes contexto suficiente, mezcla micro-insights sobre los pilares cubiertos (2-3 frases) y solo pide el siguiente dato crítico faltante.
- No sigas preguntando si ya alcanzaste el máximo o si ya tienes señal suficiente: entrega el blueprint de 9 pilares cuanto antes, sin esperar al mensaje 10.

CONTEXTO DE CONVERSACIÓN (historial):
{context}

IDEA ORIGINAL:
"{raw_idea}"

TAREA:
    - Responde en español con lenguaje simple y bloques cortos.
    - Si faltan datos y no alcanzaste el mínimo: devuelve SOLO una pregunta nueva, clara, específica y corta (<= 20 palabras).
    - Si ya cubriste el mínimo o detectas suficiente señal: devuelve un mini-resumen (2-4 frases) de los pilares ya claros y pide solo el dato crítico faltante.
    - Si ya tienes contexto suficiente (antes del mensaje 10): entrega el análisis ejecutivo con los 9 pilares (texto corrido, no JSON) y un semáforo (🟢/🟡/🔴).
    - Tono clarificador: ayudamos a decidir, no a emprender.
    - No uses formato markdown, viñetas ni código. Respuesta directa.
    - Si ya tienes datos suficientes antes del mensaje 8, entrega el blueprint en texto claro (no envíes JSON al usuario).
    - Si user_turn >= 9: entrega CTA acorde al semáforo (si no hay semáforo previo, asume amarilla) y en 10 agrega "Agenda aquí: https://calendar.app.google/cuDDtC9Y1tZVDPuD7" y señala que el chat se cierra.
"""
        try:
            text = self._generate_with_fallback(prompt)
            # Quitar cercos de código si el modelo los añade
            if text.startswith("```"):
                text = text.strip().strip("`")
            return text.strip()
        except Exception as e:
            logger.error(f"Error generating clarification reply: {e}")
            return "Gracias. ¿Cuál es tu mercado objetivo específico y el volumen estimado?"
    
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
