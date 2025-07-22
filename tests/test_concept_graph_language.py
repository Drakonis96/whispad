#!/usr/bin/env python3
"""
Test script to verify language support in concept_graph.py
"""

from concept_graph import build_graph, get_stopwords

def test_language_support():
    """Test the language support functionality."""
    
    # Test English text
    english_text = """
    Machine learning is a powerful technology that enables computers to learn from data. 
    It involves algorithms that can improve their performance automatically through experience.
    Deep learning is a subset of machine learning that uses neural networks.
    """
    
    # Test Spanish text
    spanish_text = """
    El aprendizaje automático es una tecnología poderosa que permite a las computadoras aprender de los datos.
    Involucra algoritmos que pueden mejorar su rendimiento automáticamente a través de la experiencia.
    El aprendizaje profundo es un subconjunto del aprendizaje automático que utiliza redes neuronales.
    """
    
    print("Testing English stopwords...")
    english_stopwords = get_stopwords('english')
    print(f"English stopwords count: {len(english_stopwords)}")
    print("Sample English stopwords:", list(english_stopwords)[:10])
    
    print("\nTesting Spanish stopwords...")
    spanish_stopwords = get_stopwords('spanish')
    print(f"Spanish stopwords count: {len(spanish_stopwords)}")
    print("Sample Spanish stopwords:", list(spanish_stopwords)[:10])
    
    print("\nTesting English concept graph generation...")
    english_graph = build_graph(english_text, language='english')
    print(f"English graph nodes: {len(english_graph['nodes'])}")
    print("English nodes:", [node['id'] for node in english_graph['nodes'][:5]])
    
    print("\nTesting Spanish concept graph generation...")
    spanish_graph = build_graph(spanish_text, language='spanish')
    print(f"Spanish graph nodes: {len(spanish_graph['nodes'])}")
    print("Spanish nodes:", [node['id'] for node in spanish_graph['nodes'][:5]])
    
    print("\nLanguage support test completed successfully!")

if __name__ == "__main__":
    test_language_support()
