#!/usr/bin/env python3
"""
Debug test to understand concept extraction quality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import extract_key_terms, build_concept_graph

def debug_term_extraction():
    """Debug the term extraction process"""
    text = """
    Artificial intelligence and machine learning are transforming technology.
    Neural networks use deep learning algorithms to process data.
    Natural language processing helps computers understand human language.
    Computer vision enables image recognition and object detection.
    Data science combines statistics with programming to analyze datasets.
    Software engineering involves systematic development of applications.
    Database systems store and retrieve information efficiently.
    """
    
    print("Debug: Term Extraction")
    print("=" * 40)
    print(f"Text length: {len(text)} characters")
    
    # Test term extraction
    terms = extract_key_terms(text, language='english', enable_lemmatization=True)
    print(f"Extracted {len(terms)} terms:")
    for i, term in enumerate(terms):
        print(f"  {i+1}. {term}")
    
    # Test full graph build
    print("\nDebug: Full Graph Build")
    print("=" * 40)
    result = build_concept_graph(text, analysis_type='bridges')
    nodes = result.get('nodes', [])
    links = result.get('links', [])
    insights = result.get('insights', {})
    
    print(f"Generated {len(nodes)} nodes, {len(links)} links")
    print("Node details:")
    for node in nodes:
        print(f"  - {node['label']} (size: {node.get('size', 0):.1f}, centrality: {node.get('betweenness_centrality', 0):.3f})")
    
    print(f"\nInsights:")
    print(f"  Dominant topics: {insights.get('dominant_topics', [])}")
    print(f"  Bridge concepts: {insights.get('bridging_concepts', [])}")
    print(f"  Knowledge gaps: {insights.get('knowledge_gaps', [])}")

def test_with_simple_text():
    """Test with very simple, clear text"""
    text = """
    Machine learning is important. Artificial intelligence is useful.
    Neural networks and deep learning work together.
    Natural language processing helps computers.
    Computer vision recognizes images.
    """
    
    print("\nDebug: Simple Text Test")
    print("=" * 40)
    print(f"Text: {text.strip()}")
    
    result = build_concept_graph(text, analysis_type='bridges')
    nodes = result.get('nodes', [])
    
    print(f"Generated {len(nodes)} nodes:")
    for node in nodes:
        print(f"  - {node['label']}")

if __name__ == "__main__":
    debug_term_extraction()
    test_with_simple_text()
