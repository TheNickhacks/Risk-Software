#!/usr/bin/env python
"""
Test para verificar que Gemini API esté funcionando
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_gemini_api():
    """Prueba la conexión y uso de Gemini"""
    
    print("=" * 60)
    print("🧪 TEST DE GEMINI API")
    print("=" * 60)
    
    # 1. Verificar API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY no está configurada en .env")
        sys.exit(1)
    
    print(f"\n✅ API Key encontrada: {api_key[:20]}...")
    
    # 2. Importar y configurar Gemini
    try:
        import google.generativeai as genai
        print("✅ google.generativeai importado correctamente")
    except ImportError:
        print("❌ ERROR: No se pudo importar google.generativeai")
        print("   Ejecuta: pip install google-generativeai")
        sys.exit(1)
    
    # 3. Configurar API
    try:
        genai.configure(api_key=api_key)
        print("✅ API configurada correctamente")
    except Exception as e:
        print(f"❌ ERROR al configurar API: {e}")
        sys.exit(1)
    
    # 4. Crear modelo gemma-3-12b-it
    try:
        model = genai.GenerativeModel("gemma-3-12b-it")
        print("✅ Modelo gemma-3-12b-it inicializado")
    except Exception as e:
        print(f"❌ ERROR al inicializar modelo: {e}")
        sys.exit(1)
    
    # 5. Hacer una prueba simple
    try:
        print("\n📝 Enviando prueba simple a Gemini...")
        response = model.generate_content("Responde solo con 'OK' si recibiste este mensaje")
        print(f"✅ Respuesta de Gemini: {response.text[:50]}...")
        print(f"   (completa: {response.text})")
    except Exception as e:
        print(f"❌ ERROR al usar Gemini: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TODO OK - GEMINI API ESTÁ FUNCIONANDO")
    print("=" * 60)
    print("\nUsando: gemma-3-12b-it")
    print("Status: Listo para producción\n")

if __name__ == "__main__":
    test_gemini_api()
