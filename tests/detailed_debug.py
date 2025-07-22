#!/usr/bin/env python3
"""
Detailed debug of concept graph generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import build_concept_graph

# Spanish text
spanish_text = """
La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.

La tecnología blockchain proporciona libros contables seguros. La computación cuántica promete 
resolver problemas complejos. La visión por computadora permite a las máquinas interpretar información visual.

La computación móvil proporciona acceso ubicuo. El comercio electrónico permite compras en línea.
La ingeniería de software asegura el diseño sistemático de sistemas robustos.
"""

# Expected Spanish concepts
expected_concepts = [
    'computación en la nube', 'ciberseguridad', 'internet de las cosas',
    'tecnología blockchain', 'computación cuántica', 'visión por computadora',
    'computación móvil', 'comercio electrónico', 'ingeniería de software'
]

print("🔍 DEPURACIÓN DETALLADA DEL GRAFO DE CONCEPTOS")
print("=" * 60)
print(f"📄 Texto de prueba: {len(spanish_text)} caracteres")
print()

# Generate concept graph (with auto language detection for Spanish)
result = build_concept_graph(spanish_text, analysis_type='bridges')
print(f"🔍 Estructura del resultado: {list(result.keys())}")

# Check if it's the old format or new format
if 'graph' in result:
    nodes = result['graph']['nodes']
elif 'nodes' in result:
    nodes = result['nodes']
else:
    print(f"❌ Estructura desconocida: {result}")
    exit(1)

print(f"📊 Nodos generados: {len(nodes)}")
print()

# Show all node labels
node_labels = [node.get('label', '').lower() for node in nodes]
print("📝 Todos los nodos generados:")
for i, label in enumerate(sorted(node_labels), 1):
    print(f"  {i:2d}. '{label}'")

print()
print("🎯 Verificando conceptos esperados:")
for expected in expected_concepts:
    found = False
    matched_nodes = []
    
    for label in node_labels:
        # Check various matching strategies
        if expected == label:
            found = True
            matched_nodes.append(f"exact: '{label}'")
        elif expected in label:
            found = True
            matched_nodes.append(f"contains: '{label}'")
        elif label in expected:
            found = True
            matched_nodes.append(f"contained: '{label}'")
        else:
            # Check word overlap
            expected_words = [w for w in expected.split() if len(w) > 3 and w not in {'las', 'los', 'del', 'por', 'con', 'para', 'una', 'las'}]
            label_words = [w for w in label.split() if len(w) > 3]
            
            if len(expected_words) >= 2 and len(label_words) >= 2:
                matches = 0
                for ew in expected_words:
                    for lw in label_words:
                        if ew in lw or lw in ew:
                            matches += 1
                            break
                
                if matches >= len(expected_words) - 1:
                    found = True
                    matched_nodes.append(f"words: '{label}' (matches: {matches}/{len(expected_words)})")
    
    if found:
        print(f"  ✅ '{expected}' - ENCONTRADO: {', '.join(matched_nodes)}")
    else:
        print(f"  ❌ '{expected}' - NO encontrado")

print()
print("🔍 Análisis de palabras clave:")
keywords = ['computación', 'seguridad', 'internet', 'blockchain', 'cuántica', 'visión', 'móvil', 'comercio', 'ingeniería']
for keyword in keywords:
    matching_nodes = [label for label in node_labels if keyword in label]
    if matching_nodes:
        print(f"  🔗 '{keyword}': {matching_nodes}")
    else:
        print(f"  ❌ '{keyword}': sin coincidencias")
