#!/usr/bin/env python
"""
Test Script - Valida flujo completo Gemini 1.5
Idea bruta → Ambiguity Check → Interview (si es vaga) → Blueprint → Chat

Uso: python test_gemini_flow.py
"""

import logging
import sys
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar .env
load_dotenv()

from app.services.gemini_service import AIService
from app.services.session_manager import SessionManager


def test_ambiguity_check():
    """Test 1: Ambiguity Check"""
    print("\n" + "="*60)
    print("TEST 1: AMBIGUITY CHECK")
    print("="*60)

    try:
        service = AIService()

        # Idea vaga
        vague_idea = "Una app para conectar gente"
        print(f"\n📝 Idea vaga: {vague_idea}")

        result = service.check_ambiguity(vague_idea)

        print(f"\n✓ Variability Score: {result['variability_score']}")
        print(f"  Clarity Assessment: {result['clarity_assessment'][:100]}...")
        print(f"  Needs Interview: {result['needs_interview']}")

        if result["needs_interview"]:
            print(f"\n🎤 Preguntas sugeridas:")
            for i, q in enumerate(result["suggested_questions"], 1):
                print(f"   {i}. {q}")

        # Idea clara
        print("\n" + "-"*40)
        clear_idea = "SaaS B2B para gestión de riesgos empresariales con IA, dirigido a PyMES del sector financiero, modelo de suscripción mensual"
        print(f"\n📝 Idea clara: {clear_idea}")

        result = service.check_ambiguity(clear_idea)

        print(f"\n✓ Variability Score: {result['variability_score']}")
        print(f"  Clarity Assessment: {result['clarity_assessment'][:100]}...")
        print(f"  Needs Interview: {result['needs_interview']}")

        return True

    except Exception as e:
        logger.error(f"❌ Error en TEST 1: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_flow():
    """Test 2: Flujo completo de sesión"""
    print("\n" + "="*60)
    print("TEST 2: FLUJO COMPLETO DE SESIÓN")
    print("="*60)

    try:
        service = AIService()
        session = SessionManager("proj_123", "user_456", service)

        # Paso 1: Input inicial
        print("\n📝 Paso 1: Input Inicial")
        idea = "Una plataforma para conectar freelancers con empresas"
        result = session.process_initial_input(idea)

        print(f"  Status: {result['status']}")
        print(f"  Variability Score: {result['variability_score']}")

        if result["status"] == "micro_interview_needed":
            print(f"\n🎤 Paso 2: Responder Micro-entrevista")
            answers = [
                "Específicamente para desarrolladores Python y diseñadores UX, pagando por proyecto",
                "Empresas de 10-50 personas que necesitan talento especializado",
                "Algoritmo de matching por skills + reviews + experiencia previa"
            ]

            result = session.process_interview_responses(answers)
            print(f"  Status: {result['status']}")

        # Paso 3: Generar Blueprint
        print(f"\n📋 Paso 3: Generar Blueprint")
        result = session.generate_blueprint_phase()
        print(f"  Status: {result['status']}")

        if "blueprint" in result:
            blueprint = result["blueprint"]
            print(f"  ✓ Blueprint generado")
            if "sections" in blueprint:
                for section, content in blueprint["sections"].items():
                    if content:
                        print(f"    - {section}: {content[:50]}...")

        # Paso 4: Chat contextual
        print(f"\n💬 Paso 4: Chat Contextual")
        questions = [
            "¿Cuál es el CAC estimado para adquirir empresas?",
            "¿Cuáles son los principales competidores en este mercado?"
        ]

        for i, question in enumerate(questions, 1):
            print(f"\n  Mensaje #{i}: {question}")
            result = session.process_chat_message(question)

            print(f"    Response: {result['response'][:150]}...")
            print(f"    Messages remaining: {result['messages_remaining']}")

            if result["messages_remaining"] <= 0:
                print("\n    ⚠️  Hard cap alcanzado")
                break

        # Resumen final
        print(f"\n📊 Resumen de Sesión:")
        summary = session.get_session_summary()
        print(f"  Phase: {summary['phase']}")
        print(f"  Variability Score: {summary['variability_score']}")
        print(f"  Chat Messages: {summary['chat_message_count']}")

        return True

    except Exception as e:
        logger.error(f"❌ Error en TEST 2: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_blueprint_generation():
    """Test 3: Generación de Blueprint específicamente"""
    print("\n" + "="*60)
    print("TEST 3: BLUEPRINT GENERATION")
    print("="*60)

    try:
        service = AIService()

        idea = """
        Plataforma SaaS B2B para gestión de riesgos empresariales con IA.
        
        Dirigida a PyMES del sector financiero que necesitan cumplir regulaciones SIFI.
        Usa machine learning para predecir riesgos operacionales, de crédito y de cumplimiento.
        
        Modelo: Suscripción mensual $500-2000 según número de usuarios.
        Diferenciador: Integración con sistemas legacy, sin necesidad de migración.
        Equipo: 2 co-founders (CTO, CEO), buscando seed $200k.
        """

        print(f"\n📝 Idea a analizar: {idea[:100]}...")

        result = service.generate_blueprint(idea)

        if "error" not in result:
            print(f"\n✓ Blueprint generado exitosamente")
            print(f"  Generated at: {result['generated_at']}")

            sections = result.get("sections", {})
            print(f"\n  Secciones detectadas:")
            for section, content in sections.items():
                if content.strip():
                    lines = content.strip().split("\n")
                    print(f"\n  📌 {section.upper()}:")
                    print(f"     {lines[0][:150]}...")
        else:
            print(f"❌ Error: {result['error']}")

        return True

    except Exception as e:
        logger.error(f"❌ Error en TEST 3: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("[TEST] INICIANDO TESTS DE GEMINI FLOW")
    print("="*60)

    tests = [
        ("Ambiguity Check", test_ambiguity_check),
        ("Session Flow Completo", test_session_flow),
        ("Blueprint Generation", test_blueprint_generation),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrumpidos por usuario")
            break
        except Exception as e:
            logger.error(f"Error ejecutando {test_name}: {e}")
            results[test_name] = False

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print(f"\n[SUCCESS] TODOS LOS TESTS PASARON")
        return 0
    else:
        print(f"\n[WARNING] ALGUNOS TESTS FALLARON")
        return 1


if __name__ == "__main__":
    sys.exit(main())
