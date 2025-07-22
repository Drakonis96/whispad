#!/usr/bin/env python3
"""
Test integrated Spanish support in main concept_graph.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import build_concept_graph

def test_integrated_spanish():
    """Test Spanish support in main concept graph"""
    print("🇪🇸 PRUEBA DE SOPORTE ESPAÑOL INTEGRADO")
    print("=" * 60)
    
    # Spanish text
    spanish_text = """
    La inteligencia artificial y el aprendizaje automático están transformando la tecnología. 
    Los algoritmos de aprendizaje profundo utilizan redes neuronales para procesar patrones 
    complejos de datos. El procesamiento de lenguaje natural permite a las computadoras entender 
    el lenguaje humano. La visión por computadora permite a las máquinas interpretar información visual.
    
    La ciencia de datos combina análisis estadístico con técnicas de aprendizaje automático. 
    La ingeniería de software asegura el diseño sistemático de sistemas robustos. La gestión 
    de bases de datos proporciona almacenamiento eficiente de información.
    
    La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
    protege los activos digitales. El internet de las cosas conecta dispositivos para generar datos.
    
    La tecnología blockchain proporciona libros contables seguros. La computación cuántica promete 
    resolver problemas complejos. La realidad virtual crea experiencias digitales inmersivas.
    
    El análisis de big data procesa grandes volúmenes de información. La computación en el borde 
    reduce la latencia. La arquitectura de microservicios descompone aplicaciones en servicios.
    
    Las prácticas DevOps integran desarrollo y operaciones. Las APIs permiten comunicación entre 
    sistemas. El diseño de experiencia de usuario crea interfaces intuitivas.
    
    La computación móvil proporciona acceso ubicuo. Las redes sociales facilitan comunicación global. 
    El comercio electrónico permite compras en línea. La transformación digital moderniza organizaciones.
    """
    
    # Expected Spanish concepts
    expected_concepts = {
        'inteligencia artificial', 'aprendizaje automático', 'aprendizaje profundo',
        'redes neuronales', 'procesamiento de lenguaje natural', 'visión por computadora',
        'ciencia de datos', 'ingeniería de software', 'gestión de bases de datos',
        'computación en la nube', 'ciberseguridad', 'internet de las cosas',
        'tecnología blockchain', 'computación cuántica', 'realidad virtual',
        'big data', 'computación en el borde', 'arquitectura de microservicios',
        'experiencia de usuario', 'computación móvil', 'redes sociales',
        'comercio electrónico', 'transformación digital'
    }
    
    print(f"📄 Texto: {len(spanish_text)} caracteres")
    print(f"🎯 Conceptos esperados: {len(expected_concepts)}")
    
    # Test with language detection (auto)
    print("\n🔍 Prueba con detección automática de idioma:")
    start_time = time.time()
    result_auto = build_concept_graph(spanish_text, analysis_type='bridges')
    duration_auto = time.time() - start_time
    
    nodes_auto = result_auto.get('nodes', [])
    print(f"   ⏱️  Tiempo: {duration_auto:.2f}s")
    print(f"   📊 Nodos: {len(nodes_auto)}")
    
    # Extract node labels for quality assessment
    node_labels = {node.get('label', '').lower() for node in nodes_auto}
    
    # Find matches with enhanced Spanish compound term matching
    found_concepts = set()
    for label in node_labels:
        label_clean = label.strip()
        for expected in expected_concepts:
            # Direct match
            if expected in label_clean or label_clean in expected:
                found_concepts.add(expected)
                continue
            
            # Enhanced compound term matching for Spanish
            # Extract key words from both expected and found labels
            expected_words = [w for w in expected.split() if len(w) > 3 and w not in {'las', 'los', 'del', 'por', 'con', 'para'}]
            label_words = [w for w in label_clean.split() if len(w) > 3]
            
            # Check if most key words match
            if len(expected_words) >= 2 and len(label_words) >= 2:
                matches = sum(1 for ew in expected_words for lw in label_words if ew in lw or lw in ew)
                if matches >= len(expected_words) - 1:  # Allow 1 missing word
                    found_concepts.add(expected)
    
    quality_score = len(found_concepts) / len(expected_concepts) * 100
    
    print(f"   🎯 Calidad: {quality_score:.1f}% ({len(found_concepts)}/{len(expected_concepts)})")
    print(f"   ✅ Encontrados: {len(found_concepts)} conceptos")
    print(f"   📝 Conceptos encontrados: {sorted(found_concepts)}")
    print(f"   ❌ Conceptos faltantes: {sorted(set(expected_concepts) - found_concepts)}")
    
    # Check for problematic Spanish words
    problematic_spanish = {
        'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en', 'con', 
        'por', 'para', 'y', 'o', 'que', 'es', 'son', 'está', 'están'
    }
    
    found_problematic = node_labels.intersection(problematic_spanish)
    
    print(f"   🔍 Filtrado: {len(found_problematic)} palabras problemáticas")
    
    if found_problematic:
        print(f"   ⚠️ Problemáticas: {sorted(found_problematic)}")
    else:
        print("   ✅ Sin palabras problemáticas")
    
    print(f"\n📝 Primeros 10 nodos: {sorted(list(node_labels))[:10]}")
    
    return quality_score >= 70, duration_auto <= 10, len(found_problematic) <= 2

def test_mixed_content():
    """Test with mixed Spanish-English content"""
    print("\n" + "=" * 60)
    print("🌐 PRUEBA DE CONTENIDO MIXTO")
    print("=" * 60)
    
    mixed_text = """
    La inteligencia artificial (artificial intelligence) y machine learning están revolucionando 
    la industria tecnológica. Deep learning algorithms utilizan neural networks para procesar 
    información compleja. Data science combina statistical analysis con domain expertise.
    
    Cloud computing platforms ofrecen scalable infrastructure para enterprise applications. 
    Cybersecurity measures protegen digital assets mediante advanced encryption. Internet of Things 
    dispositivos generan massive datasets para real-time analytics.
    
    Software engineering practices aseguran robust system architectures. Database management 
    systems proporcionan efficient data storage y retrieval capabilities.
    """
    
    print(f"📄 Texto mixto: {len(mixed_text)} caracteres")
    
    result = build_concept_graph(mixed_text)
    nodes = result.get('nodes', [])
    
    print(f"📊 Resultado: {len(nodes)} nodos")
    
    # Check for both English and Spanish terms
    node_labels = {node.get('label', '').lower() for node in nodes}
    
    english_terms = {'artificial intelligence', 'machine learning', 'deep learning', 
                    'neural networks', 'data science', 'cloud computing', 'cybersecurity',
                    'internet of things', 'software engineering', 'database management'}
    
    spanish_terms = {'inteligencia artificial', 'aprendizaje automático', 'aprendizaje profundo',
                    'redes neuronales', 'ciencia de datos', 'computación en la nube', 'ciberseguridad',
                    'internet de las cosas', 'ingeniería de software', 'gestión de bases de datos'}
    
    found_english = 0
    found_spanish = 0
    
    for label in node_labels:
        if any(term in label for term in english_terms):
            found_english += 1
        if any(term in label for term in spanish_terms):
            found_spanish += 1
    
    print(f"   🇺🇸 Términos en inglés detectados: {found_english}")
    print(f"   🇪🇸 Términos en español detectados: {found_spanish}")
    
    if found_english > 0 and found_spanish > 0:
        print("   ✅ Manejo exitoso de contenido mixto")
        return True
    else:
        print("   ⚠️ Contenido mixto necesita mejoras")
        return False

def test_performance_large_spanish():
    """Test performance with large Spanish document"""
    print("\n" + "=" * 60)
    print("📈 PRUEBA DE RENDIMIENTO - DOCUMENTO GRANDE")
    print("=" * 60)
    
    # Create large Spanish document
    base_spanish = """
    La inteligencia artificial y el aprendizaje automático están revolucionando los negocios. 
    Los algoritmos de aprendizaje profundo utilizan redes neuronales para análisis de datos complejos. 
    El procesamiento de lenguaje natural permite interacción humano-computadora avanzada. La visión 
    por computadora analiza información visual para automatización de procesos.
    
    La ciencia de datos combina análisis estadístico con experiencia en el dominio. La ingeniería 
    de software asegura sistemas escalables y mantenibles. La gestión de bases de datos proporciona 
    almacenamiento eficiente de información estructurada y no estructurada.
    
    La computación en la nube ofrece infraestructura elástica para aplicaciones empresariales. 
    La ciberseguridad protege activos digitales mediante estrategias de defensa multicapa. El 
    internet de las cosas conecta dispositivos para generar datos en tiempo real.
    """
    
    large_spanish = base_spanish * 15  # About 8KB
    
    print(f"📄 Documento: {len(large_spanish)} caracteres ({len(large_spanish)/1024:.1f}KB)")
    
    start_time = time.time()
    result = build_concept_graph(large_spanish)
    duration = time.time() - start_time
    
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    
    print(f"⏱️ Tiempo: {duration:.2f}s")
    print(f"📊 Resultado: {nodes} nodos, {links} enlaces")
    
    if duration <= 5:
        print("✅ Rendimiento excelente (≤5s)")
        return True
    elif duration <= 10:
        print("✅ Rendimiento aceptable (≤10s)")
        return True
    else:
        print("⚠️ Rendimiento lento (>10s)")
        return False

def main():
    print("🇪🇸 PRUEBA COMPLETA DE SOPORTE ESPAÑOL INTEGRADO")
    print("=" * 70)
    
    # Test 1: Spanish quality
    quality_ok, time_ok, filter_ok = test_integrated_spanish()
    
    # Test 2: Mixed content
    mixed_ok = test_mixed_content()
    
    # Test 3: Performance
    perf_ok = test_performance_large_spanish()
    
    # Final assessment
    print("\n" + "=" * 70)
    print("🎯 EVALUACIÓN FINAL DEL SOPORTE ESPAÑOL")
    print("=" * 70)
    
    tests_passed = sum([quality_ok, time_ok, filter_ok, mixed_ok, perf_ok])
    total_tests = 5
    
    print(f"📊 Pruebas pasadas: {tests_passed}/{total_tests}")
    print(f"   {'✅' if quality_ok else '❌'} Calidad de extracción")
    print(f"   {'✅' if time_ok else '❌'} Rendimiento temporal")
    print(f"   {'✅' if filter_ok else '❌'} Filtrado de palabras")
    print(f"   {'✅' if mixed_ok else '❌'} Contenido mixto")
    print(f"   {'✅' if perf_ok else '❌'} Rendimiento con documentos grandes")
    
    if tests_passed >= 4:
        print("\n🎉 ¡ÉXITO! El soporte español está integrado y funcionando correctamente!")
        print("   ✅ Listo para uso en producción")
    else:
        print("\n⚠️ El soporte español necesita mejoras adicionales")
        print("   🔄 Continuar optimización")

if __name__ == "__main__":
    main()
