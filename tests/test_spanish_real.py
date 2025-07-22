#!/usr/bin/env python3
"""
Test Spanish concept graph with actual Spanish text
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spanish_concept_graph import build_spanish_concept_graph

def test_spanish_with_spanish_text():
    """Test with comprehensive Spanish text"""
    print("🇪🇸 PRUEBA DE CONCEPTO ESPAÑOL")
    print("=" * 60)
    
    # Comprehensive Spanish text with expected concepts
    spanish_text = """
    La inteligencia artificial y el aprendizaje automático están transformando la tecnología en múltiples industrias. 
    Los algoritmos de aprendizaje profundo utilizan redes neuronales con múltiples capas ocultas para procesar 
    patrones complejos en grandes conjuntos de datos. El procesamiento de lenguaje natural permite a las computadoras 
    entender, interpretar y generar el lenguaje humano con sofisticación creciente. La visión por computadora permite 
    a las máquinas analizar e interpretar información visual de imágenes y videos digitales.
    
    La ciencia de datos combina análisis estadístico, técnicas de aprendizaje automático y experiencia en el dominio 
    para extraer conocimientos valiosos de grandes datasets. La ingeniería de software asegura el diseño sistemático, 
    desarrollo, prueba y mantenimiento de sistemas de software robustos. Los sistemas de gestión de bases de datos 
    proporcionan almacenamiento eficiente, recuperación y manipulación de datos estructurados y no estructurados.
    
    Las plataformas de computación en la nube ofrecen infraestructura escalable y servicios para implementar 
    aplicaciones a escala empresarial. Las medidas de ciberseguridad protegen los activos digitales a través de 
    estrategias de defensa multicapa. El Internet de las Cosas conecta miles de millones de dispositivos, 
    generando cantidades sin precedentes de datos en tiempo real para análisis y toma de decisiones.
    
    La tecnología blockchain proporciona libros contables inmutables y descentralizados para el procesamiento 
    seguro de transacciones y verificación de integridad de datos. La computación cuántica promete resolver 
    ciertos problemas computacionales exponencialmente más rápido que las computadoras clásicas. La realidad 
    virtual y la realidad aumentada crean experiencias digitales inmersivas que combinan perfectamente los 
    entornos físicos y digitales.
    
    El análisis de big data procesa volúmenes masivos de información estructurada y no estructurada para 
    descubrir patrones ocultos, correlaciones y tendencias. La computación en el borde acerca el cómputo 
    y almacenamiento de datos a las fuentes de datos para reducir la latencia y mejorar el rendimiento. 
    La arquitectura de microservicios descompone las aplicaciones en servicios más pequeños e independientes.
    
    Las prácticas DevOps integran el desarrollo de software y las operaciones de TI para mejorar la colaboración 
    y acelerar los ciclos de entrega. Las interfaces de programación de aplicaciones permiten la comunicación 
    fluida entre diferentes sistemas de software. El diseño de experiencia de usuario se enfoca en crear 
    interfaces intuitivas y atractivas que satisfagan las necesidades y expectativas del usuario.
    
    La computación móvil proporciona acceso ubicuo a información y servicios a través de teléfonos inteligentes, 
    tabletas y dispositivos portátiles. Las plataformas de redes sociales facilitan la comunicación global, 
    el intercambio de contenido y la construcción de comunidades. Los sistemas de comercio electrónico permiten 
    la compra y venta segura de bienes y servicios en línea.
    
    Las iniciativas de transformación digital ayudan a las organizaciones a aprovechar la tecnología para 
    mejorar las operaciones, mejorar las experiencias del cliente y crear modelos de negocio innovadores. 
    Las tecnologías de automatización reducen el trabajo manual y aumentan la eficiencia operacional. 
    La robótica combina ingeniería mecánica, ingeniería eléctrica y ciencias de la computación.
    """
    
    # Expected Spanish compound terms
    expected_spanish_concepts = {
        'inteligencia artificial', 'aprendizaje automático', 'aprendizaje profundo', 
        'redes neuronales', 'procesamiento de lenguaje natural', 'visión por computadora',
        'ciencia de datos', 'ingeniería de software', 'gestión de bases de datos',
        'computación en la nube', 'ciberseguridad', 'internet de las cosas',
        'tecnología blockchain', 'computación cuántica', 'realidad virtual', 
        'realidad aumentada', 'big data', 'computación en el borde',
        'arquitectura de microservicios', 'transformación digital', 'comercio electrónico',
        'redes sociales', 'computación móvil', 'experiencia de usuario'
    }
    
    print(f"📄 Texto en español: {len(spanish_text)} caracteres")
    print(f"🎯 Conceptos esperados: {len(expected_spanish_concepts)}")
    print()
    
    # Test Spanish implementation
    start_time = time.time()
    result = build_spanish_concept_graph(spanish_text)
    duration = time.time() - start_time
    
    nodes = result.get('nodes', [])
    links = result.get('links', [])
    
    # Extract node labels
    node_labels = {node.get('label', '').lower() for node in nodes}
    
    # Find matches with flexible matching for Spanish
    found_concepts = set()
    for label in node_labels:
        label_clean = label.strip()
        for expected in expected_spanish_concepts:
            # Multiple matching strategies
            if (expected in label_clean or 
                label_clean in expected or
                # Match key words (e.g., "inteligencia" matches "inteligencia artificial")
                any(word in label_clean for word in expected.split()[:2] if len(word) > 3)):
                found_concepts.add(expected)
    
    quality_score = len(found_concepts) / len(expected_spanish_concepts) * 100
    
    print("📊 RESULTADOS:")
    print(f"   ⏱️  Tiempo: {duration:.2f}s")
    print(f"   📈 Nodos totales: {len(nodes)}")
    print(f"   🔗 Enlaces totales: {len(links)}")
    print(f"   🎯 Calidad: {quality_score:.1f}% ({len(found_concepts)}/{len(expected_spanish_concepts)})")
    print()
    
    print("✅ CONCEPTOS ENCONTRADOS:")
    for concept in sorted(found_concepts):
        print(f"   ✅ {concept}")
    
    missing_concepts = expected_spanish_concepts - found_concepts
    if missing_concepts:
        print(f"\n❌ CONCEPTOS FALTANTES ({len(missing_concepts)}):")
        for concept in sorted(missing_concepts):
            print(f"   ❌ {concept}")
    
    print(f"\n📝 TODAS LAS ETIQUETAS DE NODOS ({len(node_labels)}):")
    for i, label in enumerate(sorted(node_labels)):
        if i < 20:  # Show first 20
            print(f"   • {label}")
        elif i == 20:
            print(f"   ... y {len(node_labels) - 20} más")
            break
    
    # Check for problematic words (prepositions, articles, etc.)
    problematic_words = {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'de', 'del', 'en', 'con', 'por', 'para', 'sin', 'sobre',
        'entre', 'desde', 'hasta', 'hacia', 'bajo', 'tras',
        'y', 'o', 'pero', 'si', 'que', 'como', 'cuando', 'donde',
        'es', 'son', 'está', 'están', 'ser', 'estar', 'tener', 'hacer'
    }
    
    found_problematic = node_labels.intersection(problematic_words)
    if found_problematic:
        print(f"\n⚠️ PALABRAS PROBLEMÁTICAS ENCONTRADAS ({len(found_problematic)}):")
        for word in sorted(found_problematic):
            print(f"   ⚠️ {word}")
    else:
        print("\n✅ NO SE ENCONTRARON PALABRAS PROBLEMÁTICAS")
    
    return quality_score, duration, len(found_problematic)

def test_spanish_vs_english():
    """Compare Spanish and English processing"""
    print("\n" + "=" * 60)
    print("🔄 COMPARACIÓN ESPAÑOL vs INGLÉS")
    print("=" * 60)
    
    # Same content in both languages
    english_text = """
    Artificial intelligence and machine learning are transforming technology. Deep learning algorithms use neural 
    networks to process complex data patterns. Natural language processing enables computers to understand human 
    language. Computer vision allows machines to interpret visual information.
    """
    
    spanish_text = """
    La inteligencia artificial y el aprendizaje automático están transformando la tecnología. Los algoritmos de 
    aprendizaje profundo utilizan redes neuronales para procesar patrones complejos de datos. El procesamiento de 
    lenguaje natural permite a las computadoras entender el lenguaje humano. La visión por computadora permite a 
    las máquinas interpretar información visual.
    """
    
    print("Probando texto en inglés...")
    from high_quality_concept_graph import build_high_quality_concept_graph
    english_result = build_high_quality_concept_graph(english_text)
    english_nodes = len(english_result.get('nodes', []))
    
    print("Probando texto en español...")
    spanish_result = build_spanish_concept_graph(spanish_text)
    spanish_nodes = len(spanish_result.get('nodes', []))
    
    print(f"\n📊 Comparación:")
    print(f"   🇺🇸 Inglés: {english_nodes} nodos")
    print(f"   🇪🇸 Español: {spanish_nodes} nodos")
    
    if spanish_nodes >= english_nodes * 0.8:  # Spanish should get at least 80% of English quality
        print("   ✅ El procesamiento en español es comparable al inglés")
        return True
    else:
        print("   ⚠️ El procesamiento en español necesita mejoras")
        return False

def main():
    print("🇪🇸 PRUEBA COMPLETA DE IMPLEMENTACIÓN ESPAÑOLA")
    print("=" * 70)
    
    # Test 1: Spanish text quality
    quality_score, time_taken, problematic_count = test_spanish_with_spanish_text()
    
    # Test 2: Compare with English
    comparison_ok = test_spanish_vs_english()
    
    # Final assessment
    print("\n" + "=" * 70)
    print("🎯 EVALUACIÓN FINAL")
    print("=" * 70)
    
    quality_excellent = quality_score >= 70
    time_acceptable = time_taken <= 10
    filtering_good = problematic_count <= 3
    
    print(f"📊 Calidad: {quality_score:.1f}%")
    if quality_excellent:
        print("   🎉 EXCELENTE CALIDAD (≥70%)")
    else:
        print("   ⚠️ NECESITA MEJORAS")
    
    print(f"⏱️ Rendimiento: {time_taken:.2f}s")
    if time_acceptable:
        print("   ✅ RENDIMIENTO ACEPTABLE (≤10s)")
    else:
        print("   ⚠️ DEMASIADO LENTO")
    
    print(f"🔍 Filtrado: {problematic_count} palabras problemáticas")
    if filtering_good:
        print("   ✅ BUEN FILTRADO (≤3 problemáticas)")
    else:
        print("   ⚠️ FILTRADO NECESITA MEJORAS")
    
    print(f"🔄 Comparación: {'✅ BUENA' if comparison_ok else '⚠️ NECESITA MEJORAS'}")
    
    if quality_excellent and time_acceptable and filtering_good and comparison_ok:
        print("\n🎉 ¡ÉXITO! La implementación española está lista para producción!")
    else:
        print("\n⚠️ La implementación española necesita optimizaciones adicionales.")

if __name__ == "__main__":
    main()
