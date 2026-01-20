#!/usr/bin/env python
"""
Listar modelos disponibles en Gemini
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("=" * 60)
print("📋 MODELOS DISPONIBLES EN GEMINI API")
print("=" * 60 + "\n")

try:
    models = genai.list_models()
    for model in models:
        print(f"✅ {model.name}")
except Exception as e:
    print(f"❌ Error: {e}")
