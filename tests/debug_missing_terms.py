#!/usr/bin/env python3
"""
Debug missing compound terms
"""

import re

spanish_text = """
La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.

La tecnología blockchain proporciona libros contables seguros. La computación cuántica promete 
resolver problemas complejos. La visión por computadora permite a las máquinas interpretar información visual.

La computación móvil proporciona acceso ubicuo. El comercio electrónico permite compras en línea.
La ingeniería de software asegura el diseño sistemático de sistemas robustos.
"""

# Missing compound terms
missing_terms = ['comercio electronico', 'computacion cuantica', 'computacion movil', 'vision computadora']

print("🔍 ANÁLISIS DE TÉRMINOS FALTANTES")
print("=" * 60)

sentences = re.split(r'[.!?\n]+', spanish_text)
sentences = [s.strip() for s in sentences if s.strip()]

for term in missing_terms:
    print(f"\n🎯 Analizando: '{term}'")
    term_words = term.split()
    print(f"   📝 Palabras del término: {term_words}")
    
    found_in_sentences = []
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        matches = sum(1 for word in term_words if len(word) > 3 and word in sentence_lower)
        
        if matches > 0:
            print(f"   📄 Oración {i+1}: '{sentence}'")
            print(f"      🔍 Coincidencias: {matches}/{len(term_words)}")
            for word in term_words:
                if len(word) > 3:
                    if word in sentence_lower:
                        print(f"         ✅ '{word}' encontrado")
                    else:
                        print(f"         ❌ '{word}' NO encontrado")
            found_in_sentences.append(i)
    
    if not found_in_sentences:
        print(f"   ❌ No se encontraron coincidencias en ninguna oración")

print(f"\n📝 Total de oraciones: {len(sentences)}")
for i, sentence in enumerate(sentences):
    print(f"   {i+1}. '{sentence}'")
