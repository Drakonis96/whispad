#!/usr/bin/env python3
"""
Full pipeline debug
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import tokenize, extract_high_quality_terms, build_graph

# Spanish text
spanish_text = """
La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.

La tecnología blockchain proporciona libros contables seguros. La computación cuántica promete 
resolver problemas complejos. La visión por computadora permite a las máquinas interpretar información visual.

La computación móvil proporciona acceso ubicuo. El comercio electrónico permite compras en línea.
La ingeniería de software asegura el diseño sistemático de sistemas robustos.
"""

print("🔍 DEPURACIÓN COMPLETA DEL PIPELINE")
print("=" * 60)

print("1️⃣ extract_high_quality_terms:")
terms = extract_high_quality_terms(spanish_text, language='spanish')
print(f"   📊 Cantidad: {len(terms)}")
compound_terms = [t for t in terms if ' ' in t]
single_terms = [t for t in terms if ' ' not in t]
print(f"   📝 Compuestos ({len(compound_terms)}): {sorted(compound_terms)}")
print(f"   📝 Simples ({len(single_terms)}): {sorted(single_terms)}")

print()
print("2️⃣ tokenize (max_terms=25):")
tokenized = tokenize(spanish_text, analysis_type='bridges', max_terms=25, language='spanish')
print(f"   📊 Cantidad: {len(tokenized)}")
compound_tokenized = [t for t in tokenized if ' ' in t]
single_tokenized = [t for t in tokenized if ' ' not in t]
print(f"   📝 Compuestos ({len(compound_tokenized)}): {sorted(compound_tokenized)}")
print(f"   📝 Simples ({len(single_tokenized)}): {sorted(single_tokenized)}")

print()
print("3️⃣ build_graph:")
graph_result = build_graph(spanish_text, analysis_type='bridges', language='spanish', max_terms=25)
print(f"   📊 Cantidad de nodos: {len(graph_result['nodes'])}")
node_labels = [node.get('label', '') for node in graph_result['nodes']]
compound_nodes = [l for l in node_labels if ' ' in l]
single_nodes = [l for l in node_labels if ' ' not in l]
print(f"   📝 Compuestos ({len(compound_nodes)}): {sorted(compound_nodes)}")
print(f"   📝 Simples ({len(single_nodes)}): {sorted(single_nodes)}")

print()
print("4️⃣ Análisis de pérdidas:")
lost_compounds = set(compound_terms) - set(compound_nodes)
if lost_compounds:
    print(f"   ❌ Compuestos perdidos: {sorted(lost_compounds)}")
else:
    print("   ✅ No se perdieron compuestos")

expected_compounds = ['computacion nube', 'internet cosas', 'tecnologia blockchain', 'computacion cuantica', 'vision computadora', 'computacion movil', 'comercio electronico', 'ingenieria software']
found_expected = [c for c in expected_compounds if c in node_labels]
print(f"   ✅ Compuestos esperados encontrados: {found_expected}")
missing_expected = [c for c in expected_compounds if c not in node_labels]
print(f"   ❌ Compuestos esperados faltantes: {missing_expected}")
