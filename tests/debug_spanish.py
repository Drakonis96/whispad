#!/usr/bin/env python3
"""
Debug Spanish concept extraction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import extract_high_quality_terms

# Test specific text that should contain missing terms
test_text = """
La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.

La tecnología blockchain proporciona libros contables seguros. La computación cuántica promete 
resolver problemas complejos. La visión por computadora permite a las máquinas interpretar información visual.

La computación móvil proporciona acceso ubicuo. El comercio electrónico permite compras en línea.
La ingeniería de software asegura el diseño sistemático de sistemas robustos.
"""

print("🔍 DEPURACIÓN DE EXTRACCIÓN DE TÉRMINOS ESPAÑOLES")
print("=" * 60)
print(f"📄 Texto de prueba: {len(test_text)} caracteres")
print()

# Test the extraction function directly
print("🎯 Conceptos esperados en el texto:")
expected_in_text = [
    'computación en la nube', 'ciberseguridad', 'internet de las cosas',
    'tecnología blockchain', 'computación cuántica', 'visión por computadora',
    'computación móvil', 'comercio electrónico', 'ingeniería de software'
]
for concept in expected_in_text:
    if concept in test_text.lower():
        print(f"  ✅ '{concept}' - ENCONTRADO en texto")
    else:
        print(f"  ❌ '{concept}' - NO encontrado en texto")

print()
print("🔍 Ejecutando extract_high_quality_terms...")
extracted_terms = extract_high_quality_terms(test_text, language='spanish')
print(f"📊 Términos extraídos: {len(extracted_terms)}")
print(f"📝 Términos: {sorted(extracted_terms)}")

print()
print("🎯 Verificando conceptos esperados en términos extraídos:")
for concept in expected_in_text:
    if concept in extracted_terms:
        print(f"  ✅ '{concept}' - EXTRAÍDO correctamente")
    else:
        print(f"  ❌ '{concept}' - NO extraído")

print()
print("🔍 Términos extraídos que contienen palabras clave:")
keywords = ['computación', 'seguridad', 'internet', 'blockchain', 'cuántica', 'visión', 'móvil', 'comercio', 'ingeniería']
for term in extracted_terms:
    for keyword in keywords:
        if keyword in term:
            print(f"  🔗 '{term}' contiene '{keyword}'")
            break
