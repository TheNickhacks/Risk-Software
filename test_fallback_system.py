#!/usr/bin/env python
"""
Test del sistema de fallback automático entre modelos
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_fallback_system():
    print("=" * 70)
    print("🧪 TEST DE SISTEMA DE FALLBACK AUTOMÁTICO")
    print("=" * 70)
    
    from app.services.ai_service import IncubatorAI
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("\n✅ Inicializando IncubatorAI con fallback system...")
    ai = IncubatorAI(api_key)
    
    print(f"✅ Modelo actual: {ai.MODEL_PRIORITY[ai.current_model_index]}")
    print(f"   Índice: {ai.current_model_index}")
    print(f"   Modelos disponibles en prioridad: {len(ai.MODEL_PRIORITY)}")
    
    print("\n📋 LISTA DE MODELOS PRIORIZADOS:")
    for idx, model in enumerate(ai.MODEL_PRIORITY):
        star = "⭐" if idx == ai.current_model_index else "  "
        print(f"{star} {idx+1}. {model}")
    
    print("\n🧪 Probando evaluación de idea...")
    test_idea = "Una app para conectar estudiantes con tutores"
    
    try:
        score, needs_clarification = ai.evaluate_ambiguity(test_idea)
        print(f"✅ Evaluación exitosa:")
        print(f"   Score de ambigüedad: {score}")
        print(f"   Requiere clarificación: {needs_clarification}")
        print(f"   Modelo usado: {ai.MODEL_PRIORITY[ai.current_model_index]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETADO")
    print("=" * 70)
    print(f"\nEl sistema iniciará con: {ai.MODEL_PRIORITY[0]}")
    print("Si excede cuota, cambiará automáticamente al siguiente modelo.")
    print()

if __name__ == "__main__":
    test_fallback_system()
