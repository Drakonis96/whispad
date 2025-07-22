#!/usr/bin/env python3
"""
Debug specific failing terms
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

# Test our regex pattern
terms_to_test = ['vision computadora', 'comercio electronico']

sentences = re.split(r'[.!?\n]+', spanish_text)
sentences = [s.strip().lower() for s in sentences if s.strip()]

print("🔍 DEBUG DE TÉRMINOS ESPECÍFICOS")
print("=" * 60)

for term in terms_to_test:
    print(f"\n🎯 Término: '{term}'")
    term_words = term.split()
    
    for i, sentence in enumerate(sentences):
        print(f"\n   📄 Oración {i+1}: '{sentence}'")
        
        matches = 0
        for word in term_words:
            if len(word) > 3:
                # Test our regex patterns
                word_variants = [
                    word,
                    word.replace('a', '[aá]').replace('e', '[eé]').replace('i', '[ií]').replace('o', '[oó]').replace('u', '[uú]').replace('n', '[nñ]')
                ]
                
                found = False
                for variant in word_variants:
                    pattern = r'\b' + variant + r'\b'
                    if re.search(pattern, sentence):
                        print(f"      ✅ '{word}' encontrado con patrón '{pattern}'")
                        matches += 1
                        found = True
                        break
                
                if not found:
                    print(f"      ❌ '{word}' NO encontrado")
                    # Test what words ARE in the sentence
                    sentence_words = sentence.split()
                    similar_words = [w for w in sentence_words if word[:3] in w or w[:3] in word]
                    if similar_words:
                        print(f"         🔍 Palabras similares: {similar_words}")
        
        print(f"      📊 Coincidencias: {matches}/{len(term_words)}")
        if matches >= len(term_words) - 1 or matches >= 2:
            print(f"      ✅ TÉRMINO DEBERÍA SER ENCONTRADO")
        else:
            print(f"      ❌ Término no califica")
