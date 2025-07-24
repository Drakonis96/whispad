#!/usr/bin/env python3
"""
Script para extraer y validar JSON de respuestas de IA
Soporta múltiples proveedores y modelos, con enfoque en OpenAI GPT-4o

Este script puede procesar respuestas que contengan:
- JSON válido directo
- JSON envuelto en texto markdown
- JSON mezclado con texto explicativo
- Múltiples objetos JSON en una respuesta
"""

import json
import re
import asyncio
import aiohttp
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JSONResponseExtractor:
    """Extractor robusto de JSON de respuestas de IA"""
    
    def __init__(self):
        self.json_patterns = [
            # Patrón para JSON en bloques de código markdown
            r'```(?:json)?\s*(\{.*?\})\s*```',
            # Patrón para JSON sin delimitadores
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
            # Patrón para arrays JSON
            r'(\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])',
            # Patrón más específico para objetos JSON válidos
            r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})',
        ]
    
    def extract_json_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrae todos los objetos JSON válidos de un texto
        
        Args:
            text: Texto que puede contener JSON
            
        Returns:
            Lista de objetos JSON extraídos
        """
        json_objects = []
        
        # Limpiar el texto
        cleaned_text = self._clean_text(text)
        
        # Intentar parsear el texto completo como JSON primero
        try:
            parsed = json.loads(cleaned_text.strip())
            json_objects.append(parsed)
            return json_objects
        except json.JSONDecodeError:
            pass
        
        # Buscar JSON usando patrones regex
        for pattern in self.json_patterns:
            matches = re.finditer(pattern, cleaned_text, re.DOTALL | re.MULTILINE)
            for match in matches:
                json_str = match.group(1)
                try:
                    parsed = json.loads(json_str)
                    if parsed not in json_objects:  # Evitar duplicados
                        json_objects.append(parsed)
                except json.JSONDecodeError:
                    continue
        
        return json_objects
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto para facilitar la extracción de JSON"""
        # Remover caracteres de control y normalizar espacios
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        # Remover líneas que claramente no son JSON
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Mantener líneas que contienen caracteres JSON o están vacías
            if not stripped or any(char in stripped for char in '{}[]":,'):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def validate_json_structure(self, json_obj: Dict[str, Any], expected_schema: Dict[str, Any]) -> bool:
        """
        Valida que un objeto JSON tenga la estructura esperada
        
        Args:
            json_obj: Objeto JSON a validar
            expected_schema: Schema esperado con tipos de campos
            
        Returns:
            True si la estructura es válida
        """
        try:
            for key, expected_type in expected_schema.items():
                if key not in json_obj:
                    logger.warning(f"Campo faltante: {key}")
                    return False
                
                if expected_type == "string" and not isinstance(json_obj[key], str):
                    logger.warning(f"Campo {key} debería ser string, es {type(json_obj[key])}")
                    return False
                elif expected_type == "array" and not isinstance(json_obj[key], list):
                    logger.warning(f"Campo {key} debería ser array, es {type(json_obj[key])}")
                    return False
                elif expected_type == "object" and not isinstance(json_obj[key], dict):
                    logger.warning(f"Campo {key} debería ser object, es {type(json_obj[key])}")
                    return False
                elif expected_type == "number" and not isinstance(json_obj[key], (int, float)):
                    logger.warning(f"Campo {key} debería ser number, es {type(json_obj[key])}")
                    return False
            
            # Validación específica para quiz: debe tener exactamente 4 respuestas
            if 'questions' in json_obj and isinstance(json_obj['questions'], list):
                for i, question in enumerate(json_obj['questions']):
                    if not self._validate_quiz_question(question, i + 1):
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Error validando estructura: {e}")
            return False
    
    def _validate_quiz_question(self, question: Dict[str, Any], question_num: int) -> bool:
        """
        Valida que una pregunta de quiz tenga exactamente 4 respuestas y una correcta
        
        Args:
            question: Objeto de pregunta a validar
            question_num: Número de pregunta para logging
            
        Returns:
            True si la pregunta es válida
        """
        try:
            # Verificar campos requeridos
            required_fields = ['question', 'answers', 'correct']
            for field in required_fields:
                if field not in question:
                    logger.warning(f"Pregunta {question_num}: Campo faltante '{field}'")
                    return False
            
            # Validar que la pregunta sea string
            if not isinstance(question['question'], str) or not question['question'].strip():
                logger.warning(f"Pregunta {question_num}: El campo 'question' debe ser un string no vacío")
                return False
            
            # Validar que answers sea array
            if not isinstance(question['answers'], list):
                logger.warning(f"Pregunta {question_num}: El campo 'answers' debe ser un array")
                return False
            
            # REQUISITO CLAVE: Exactamente 4 respuestas
            if len(question['answers']) != 4:
                logger.warning(f"Pregunta {question_num}: Debe tener exactamente 4 respuestas, encontradas {len(question['answers'])}")
                return False
            
            # Validar que todas las respuestas sean strings no vacíos
            for j, answer in enumerate(question['answers']):
                if not isinstance(answer, str) or not answer.strip():
                    logger.warning(f"Pregunta {question_num}, respuesta {j+1}: Debe ser un string no vacío")
                    return False
            
            # Validar índice de respuesta correcta
            if not isinstance(question['correct'], int):
                logger.warning(f"Pregunta {question_num}: El campo 'correct' debe ser un entero")
                return False
            
            # REQUISITO CLAVE: El índice debe estar entre 0 y 3 (para 4 respuestas)
            if question['correct'] < 0 or question['correct'] >= 4:
                logger.warning(f"Pregunta {question_num}: El índice 'correct' debe estar entre 0 y 3, encontrado {question['correct']}")
                return False
            
            logger.info(f"✅ Pregunta {question_num} válida: 4 respuestas, correcta = {question['correct']} ('{question['answers'][question['correct']]}')")
            return True
            
        except Exception as e:
            logger.error(f"Error validando pregunta {question_num}: {e}")
            return False


class OpenAIClient:
    """Cliente para OpenAI API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
    
    async def generate_response(self, prompt: str, model: str = "gpt-4o") -> str:
        """
        Genera una respuesta usando OpenAI API
        
        Args:
            prompt: Prompt para enviar a la IA
            model: Modelo a usar (gpt-4o por defecto)
            
        Returns:
            Respuesta de la IA
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Usar Structured Outputs para garantizar JSON válido cuando sea posible
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Responde únicamente con JSON válido. No incluyas texto explicativo adicional."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.1
        }
        
        # Si el modelo soporta Structured Outputs, usarlo
        if model in ["gpt-4o", "gpt-4o-mini", "gpt-4o-2024-08-06"]:
            data["response_format"] = {"type": "json_object"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", 
                                   headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")


class TestScenarios:
    """Escenarios de prueba para validar el extractor de JSON"""
    
    def __init__(self, extractor: JSONResponseExtractor):
        self.extractor = extractor
    
    def get_test_responses(self) -> List[Dict[str, Any]]:
        """Retorna respuestas de IA simuladas para pruebas"""
        return [
            {
                "name": "JSON válido directo - 4 respuestas",
                "response": '''{"questions": [{"question": "¿Cuál es la capital de España?", "answers": ["Madrid", "Barcelona", "Valencia", "Sevilla"], "correct": 0}], "total": 1}''',
                "expected_schema": {
                    "questions": "array",
                    "total": "number"
                }
            },
            {
                "name": "JSON en markdown - 4 respuestas",
                "response": '''Aquí está el quiz generado:

```json
{
    "questions": [
        {
            "question": "¿Qué es Python?",
            "answers": ["Un lenguaje de programación", "Una serpiente", "Una biblioteca", "Un framework web"],
            "correct": 0
        }
    ],
    "total": 1
}
```

Este quiz contiene preguntas sobre programación.''',
                "expected_schema": {
                    "questions": "array",
                    "total": "number"
                }
            },
            {
                "name": "JSON con texto explicativo - flashcards",
                "response": '''Te voy a generar las flashcards que solicitaste:

{
    "flashcards": [
        {
            "front": "¿Qué es un algoritmo?",
            "back": "Una secuencia de pasos para resolver un problema"
        },
        {
            "front": "¿Qué es una variable?",
            "back": "Un espacio en memoria para almacenar datos"
        }
    ],
    "count": 2
}

Estas flashcards te ayudarán a estudiar conceptos básicos.''',
                "expected_schema": {
                    "flashcards": "array",
                    "count": "number"
                }
            },
            {
                "name": "Quiz válido con múltiples preguntas - 4 respuestas cada una",
                "response": '''{"questions": [
                    {"question": "¿Qué es JavaScript?", "answers": ["Un lenguaje de programación", "Una base de datos", "Un sistema operativo", "Un navegador web"], "correct": 0},
                    {"question": "¿Cuál es el resultado de 2 + 2?", "answers": ["3", "4", "5", "6"], "correct": 1}
                ]}''',
                "expected_schema": {
                    "questions": "array"
                }
            },
            {
                "name": "❌ Quiz inválido - Solo 2 respuestas (debería fallar)",
                "response": '''{"questions": [{"question": "¿Cuál es la capital de Francia?", "answers": ["París", "Madrid"], "correct": 0}]}''',
                "expected_schema": {
                    "questions": "array"
                },
                "should_fail": True
            },
            {
                "name": "❌ Quiz inválido - 5 respuestas (debería fallar)",
                "response": '''{"questions": [{"question": "¿Qué es HTML?", "answers": ["HyperText Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "Hyper Transfer Markup Language", "Heavy Text Markup Language"], "correct": 0}]}''',
                "expected_schema": {
                    "questions": "array"
                },
                "should_fail": True
            },
            {
                "name": "❌ Quiz inválido - Índice correcto fuera de rango (debería fallar)",
                "response": '''{"questions": [{"question": "¿Qué es CSS?", "answers": ["Cascading Style Sheets", "Computer Style System", "Creative Style Software", "Custom Style Script"], "correct": 4}]}''',
                "expected_schema": {
                    "questions": "array"
                },
                "should_fail": True
            },
            {
                "name": "JSON malformado (para testing)",
                "response": '''{"questions": [{"question": "Test", "answers": ["A", "B"], "correct": 0}''' # JSON incompleto
            },
            {
                "name": "Respuesta sin JSON",
                "response": '''Lo siento, no puedo generar el contenido solicitado en este momento. Por favor, inténtalo de nuevo más tarde.'''
            }
        ]
    
    def run_extraction_tests(self):
        """Ejecuta todas las pruebas de extracción"""
        test_responses = self.get_test_responses()
        
        logger.info("=== INICIANDO PRUEBAS DE EXTRACCIÓN DE JSON ===")
        logger.info("Validación especial: Quiz debe tener exactamente 4 respuestas")
        
        for i, test in enumerate(test_responses, 1):
            logger.info(f"\n--- Prueba {i}: {test['name']} ---")
            logger.info(f"Respuesta original: {test['response'][:100]}...")
            
            # Extraer JSON
            json_objects = self.extractor.extract_json_from_text(test['response'])
            
            if json_objects:
                logger.info(f"✅ JSON extraído exitosamente: {len(json_objects)} objeto(s)")
                
                for j, obj in enumerate(json_objects):
                    logger.info(f"Objeto {j+1}: {json.dumps(obj, indent=2, ensure_ascii=False)}")
                    
                    # Validar estructura si se proporcionó schema esperado
                    if 'expected_schema' in test:
                        is_valid = self.extractor.validate_json_structure(obj, test['expected_schema'])
                        should_fail = test.get('should_fail', False)
                        
                        if should_fail:
                            # Este caso debe fallar la validación
                            if not is_valid:
                                logger.info("✅ Validación correcta - Caso inválido rechazado apropiadamente")
                            else:
                                logger.error("❌ ERROR - Caso inválido fue aceptado incorrectamente")
                        else:
                            # Este caso debe pasar la validación
                            if is_valid:
                                logger.info("✅ Estructura JSON válida")
                            else:
                                logger.warning("⚠️ Estructura JSON no coincide con el schema esperado")
            else:
                logger.warning("❌ No se pudo extraer JSON válido")
        
        logger.info("\n=== PRUEBAS COMPLETADAS ===")
        logger.info("Regla validada: Todas las preguntas de quiz deben tener exactamente 4 respuestas")


async def test_real_api_call():
    """Prueba con llamada real a OpenAI API (requiere API key)"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.warning("No se encontró OPENAI_API_KEY en variables de entorno")
        logger.info("Para probar con API real, configura: export OPENAI_API_KEY='tu-api-key'")
        return
    
    logger.info("\n=== PRUEBA CON API REAL DE OPENAI ===")
    
    extractor = JSONResponseExtractor()
    client = OpenAIClient(api_key)
    
    prompts = [
        {
            "name": "Generación de quiz",
            "prompt": """Genera un quiz sobre Python con 2 preguntas. 
            IMPORTANTE: Cada pregunta DEBE tener exactamente 4 opciones de respuesta.
            
            Formato JSON exacto:
            {
                "questions": [
                    {
                        "question": "texto de la pregunta",
                        "answers": ["opción 1", "opción 2", "opción 3", "opción 4"],
                        "correct": 0
                    }
                ],
                "total": 2
            }
            
            Requisitos obligatorios:
            - Exactamente 4 respuestas por pregunta
            - El índice 'correct' debe estar entre 0 y 3
            - Todas las respuestas deben ser diferentes y plausibles""",
            "schema": {
                "questions": "array",
                "total": "number"
            }
        },
        {
            "name": "Generación de flashcards",
            "prompt": """Genera 2 flashcards sobre JavaScript.
            Formato JSON:
            {
                "flashcards": [
                    {
                        "front": "pregunta o concepto",
                        "back": "respuesta o explicación"
                    }
                ],
                "count": 2
            }""",
            "schema": {
                "flashcards": "array",
                "count": "number"
            }
        }
    ]
    
    for test in prompts:
        logger.info(f"\n--- {test['name']} ---")
        
        try:
            # Llamar a la API
            response = await client.generate_response(test['prompt'], "gpt-4o")
            logger.info(f"Respuesta de OpenAI: {response}")
            
            # Extraer JSON
            json_objects = extractor.extract_json_from_text(response)
            
            if json_objects:
                for obj in json_objects:
                    logger.info(f"JSON extraído: {json.dumps(obj, indent=2, ensure_ascii=False)}")
                    
                    # Validar estructura
                    is_valid = extractor.validate_json_structure(obj, test['schema'])
                    if is_valid:
                        logger.info("✅ API test exitoso - JSON válido y estructura correcta")
                    else:
                        logger.warning("⚠️ API test - JSON extraído pero estructura incorrecta")
            else:
                logger.error("❌ API test fallido - No se pudo extraer JSON")
                
        except Exception as e:
            logger.error(f"❌ Error en API call: {e}")


def main():
    """Función principal"""
    logger.info("JSON Response Extractor - Script de Prueba")
    logger.info("Proveedor: OpenAI | Modelo: GPT-4o")
    logger.info("=" * 50)
    
    # Crear extractor
    extractor = JSONResponseExtractor()
    
    # Crear y ejecutar pruebas
    test_scenarios = TestScenarios(extractor)
    test_scenarios.run_extraction_tests()
    
    # Probar con API real si está disponible
    asyncio.run(test_real_api_call())
    
    logger.info("\n" + "=" * 50)
    logger.info("RESUMEN:")
    logger.info("✅ Script funcional para extraer JSON de respuestas de IA")
    logger.info("✅ Soporta múltiples formatos de respuesta")
    logger.info("✅ Validación de estructura JSON")
    logger.info("✅ Validación específica de quiz: exactamente 4 respuestas por pregunta")
    logger.info("✅ Validación de índice de respuesta correcta (0-3)")
    logger.info("✅ Manejo robusto de errores")
    logger.info("✅ Configurado para OpenAI GPT-4o")
    logger.info("✅ Rechaza automáticamente quiz con número incorrecto de respuestas")


if __name__ == "__main__":
    main()
