#!/usr/bin/env python3
"""
Debug tokenize function
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import tokenize, extract_high_quality_terms

# Spanish text
spanish_text = """
La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.

La tecnología blockchain proporciona libros contables seguros.
"""

print("🔍 DEPURACIÓN DE LA FUNCIÓN TOKENIZE")
print("=" * 60)

print("1️⃣ Términos extraídos por extract_high_quality_terms:")
terms = extract_high_quality_terms(spanish_text, language='spanish')
print(f"   📊 Cantidad: {len(terms)}")
print(f"   📝 Términos: {sorted(terms)}")

print()
print("2️⃣ Términos procesados por tokenize:")
tokenized_terms = tokenize(spanish_text, analysis_type='bridges', language='spanish')
print(f"   📊 Cantidad: {len(tokenized_terms)}")
print(f"   📝 Términos: {sorted(tokenized_terms)}")

print()
print("3️⃣ Comparación:")
missing_in_tokenize = set(terms) - set(tokenized_terms)
if missing_in_tokenize:
    print(f"   ❌ Perdidos en tokenize: {sorted(missing_in_tokenize)}")
else:
    print("   ✅ No se perdieron términos en tokenize")

added_in_tokenize = set(tokenized_terms) - set(terms)
if added_in_tokenize:
    print(f"   ➕ Añadidos en tokenize: {sorted(added_in_tokenize)}")
