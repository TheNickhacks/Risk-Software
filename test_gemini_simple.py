#!/usr/bin/env python
"""
Test simple - Validar Gemini Pro funciona
"""
import sys
import os

# Agregar ruta del proyecto
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

# Test directo sin imports de Flask
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not set")
    sys.exit(1)

genai.configure(api_key=api_key)
print("[OK] Gemini API configured")

# Test simple
model = genai.GenerativeModel('gemini-2.5-pro')
print("[OK] Model 'gemini-2.5-pro' selected")

prompt = "Lista 3 validaciones clave para evaluar una idea de negocio"
response = model.generate_content(prompt)
print("\n[RESPONSE]")
print(response.text[:300])
print("\n[SUCCESS] Gemini Pro working correctly")
