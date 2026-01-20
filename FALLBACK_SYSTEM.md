# 🔄 Sistema de Fallback Automático entre Modelos IA

## 📊 **Cómo Funciona**

El sistema **cambia automáticamente** al siguiente modelo cuando se excede la cuota gratuita del modelo actual.

### **Prioridad de Modelos (Mejor → Peor)**

| # | Modelo | Calidad | RPM | TPM | RPD | Uso |
|---|--------|---------|-----|-----|-----|-----|
| 1 | `gemini-2.5-flash` | ⭐⭐⭐⭐⭐ | 5 | 250K | 20 | **PRIMERO** |
| 2 | `gemini-3-flash` | ⭐⭐⭐⭐⭐ | 5 | 250K | 20 | Si 1 falla |
| 3 | `gemini-2.5-flash-lite` | ⭐⭐⭐⭐ | 10 | 250K | 20 | Si 2 falla |
| 4 | `gemma-3-27b-it` | ⭐⭐⭐⭐ | 30 | 15K | 14.4K | Si 3 falla |
| 5 | `gemma-3-12b-it` | ⭐⭐⭐ | 30 | 15K | 14.4K | Si 4 falla |
| 6 | `gemma-3-4b-it` | ⭐⭐ | 30 | 15K | 14.4K | Si 5 falla |
| 7 | `gemma-3-2b-it` | ⭐ | 30 | 15K | 14.4K | Si 6 falla |
| 8 | `gemma-3-1b-it` | ⭐ | 30 | 15K | 14.4K | **ÚLTIMO RECURSO** |

**RPM** = Requests por minuto | **TPM** = Tokens por minuto | **RPD** = Requests por día

---

## 🎯 **Flujo de Fallback**

```
Usuario solicita análisis
    ↓
Intenta con gemini-2.5-flash
    ↓
¿Excedió cuota? (Error 429)
    ├─ NO → ✅ Respuesta exitosa
    └─ SÍ → Cambiar a gemini-3-flash
              ↓
              ¿Excedió cuota?
              ├─ NO → ✅ Respuesta exitosa
              └─ SÍ → Cambiar a gemini-2.5-flash-lite
                       ...y así sucesivamente
```

---

## 💻 **Implementación en Código**

### **ai_service.py**

```python
class IncubatorAI:
    MODEL_PRIORITY = [
        "gemini-2.5-flash",
        "gemini-3-flash",
        "gemini-2.5-flash-lite",
        "gemma-3-27b-it",
        "gemma-3-12b-it",
        "gemma-3-4b-it",
        "gemma-3-2b-it",
        "gemma-3-1b-it",
    ]
    
    def _generate_with_fallback(self, prompt: str, max_retries: int = 3):
        """
        Genera contenido con fallback automático.
        Si detecta error 429 (cuota excedida), prueba el siguiente modelo.
        """
        attempts = 0
        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    # Cuota excedida, cambiar al siguiente modelo
                    if not self._try_next_model():
                        raise Exception("Todos los modelos agotaron su cuota")
                    attempts += 1
                else:
                    raise e
```

---

## 📝 **Logs del Sistema**

### **Inicio normal:**
```
✅ Modelo inicializado: gemini-2.5-flash
```

### **Cuando excede cuota:**
```
⚠️ Cuota excedida para gemini-2.5-flash
⚠️ Cambiando a modelo: gemini-3-flash
```

### **Si todos los modelos fallan:**
```
❌ Todos los modelos disponibles han excedido su cuota gratuita
```

---

## 🧪 **Testing**

Para probar el sistema desde la aplicación Flask:
- Crea un proyecto
- Analiza una idea
- El sistema usa automáticamente el mejor modelo disponible
- Monitorea los logs para ver cambios de modelo

---

## ⚙️ **Configuración**

No requiere configuración adicional. El sistema detecta automáticamente:
- ✅ Error 429 (cuota excedida)
- ✅ Keywords "quota" en el mensaje de error
- ✅ Intenta hasta 3 modelos diferentes

---

## 🎉 **Beneficios**

✅ **Máxima disponibilidad** - Nunca se queda sin IA  
✅ **Optimización de costos** - Usa siempre el mejor modelo disponible  
✅ **Sin intervención manual** - Cambio automático transparente  
✅ **Logs claros** - Sabes qué modelo está usando  

---

**Implementado:** Enero 2026  
**Versión:** 1.0  
**Modelos totales:** 8
