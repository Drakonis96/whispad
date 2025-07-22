#!/usr/bin/env python3
"""
Test the optimized concept graph implementation in virtual environment
"""

import time
import sys
import os

# Add the current directory to the path so we can import concept_graph
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import build_concept_graph

def generate_test_text(size_kb=50):
    """Generate test text of specified size"""
    base_text = """
    Machine learning is a subset of artificial intelligence that focuses on algorithms 
    and statistical models. Deep learning uses neural networks with multiple layers 
    to process complex data patterns. Natural language processing enables computers 
    to understand human language. Computer vision allows machines to interpret 
    visual information from images and videos.
    
    The development of artificial intelligence has been driven by advances in 
    computational power, algorithm design, and data availability. Modern AI systems
    can perform tasks that were previously thought to require human intelligence,
    such as playing complex games, driving cars, and diagnosing medical conditions.
    
    Neural networks are inspired by the structure and function of biological neural
    networks. They consist of interconnected nodes that process and transmit information.
    Training these networks involves adjusting the connections between nodes based on
    examples of input-output pairs.
    
    Data science combines statistics, computer science, and domain expertise to extract
    insights from data. It involves collecting, cleaning, analyzing, and interpreting
    large datasets to make informed decisions. Visualization tools help communicate
    findings to stakeholders and support data-driven decision making.
    
    Computer science is a broad field that encompasses programming, algorithms,
    data structures, software engineering, and systems design. It provides the
    foundation for many modern technologies and applications.
    
    Software engineering involves the systematic approach to designing, developing,
    and maintaining software systems. It includes requirements analysis, system
    design, implementation, testing, and deployment.
    
    Database systems are used to store, organize, and retrieve large amounts of
    information efficiently. They support concurrent access, data integrity,
    and complex queries across multiple tables and relationships.
    """
    
    # Calculate how many times to repeat the text
    target_chars = size_kb * 1024
    repeats = max(1, target_chars // len(base_text))
    generated_text = (base_text * repeats)[:target_chars]
    
    return generated_text

def test_small_text():
    """Test with small text (5KB)"""
    print("Testing with small text (5KB)...")
    text = generate_test_text(5)
    
    start_time = time.time()
    result = build_concept_graph(text, analysis_type='bridges')
    end_time = time.time()
    
    duration = end_time - start_time
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    insights = result.get('insights', {})
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Nodes: {nodes}")
    print(f"  Links: {links}")
    print(f"  Clusters: {insights.get('total_clusters', 0)}")
    
    return duration < 5, nodes > 0, links > 0

def test_medium_text():
    """Test with medium text (25KB)"""
    print("Testing with medium text (25KB)...")
    text = generate_test_text(25)
    
    start_time = time.time()
    result = build_concept_graph(text, analysis_type='bridges')
    end_time = time.time()
    
    duration = end_time - start_time
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    insights = result.get('insights', {})
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Nodes: {nodes}")
    print(f"  Links: {links}")
    print(f"  Clusters: {insights.get('total_clusters', 0)}")
    
    return duration < 15, nodes > 0, links > 0

def test_large_text():
    """Test with large text (100KB)"""
    print("Testing with large text (100KB)...")
    text = generate_test_text(100)
    
    start_time = time.time()
    result = build_concept_graph(text, analysis_type='bridges')
    end_time = time.time()
    
    duration = end_time - start_time
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    insights = result.get('insights', {})
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Nodes: {nodes}")
    print(f"  Links: {links}")
    print(f"  Clusters: {insights.get('total_clusters', 0)}")
    
    return duration < 30, nodes > 0, links > 0

def test_analysis_types():
    """Test different analysis types"""
    print("Testing different analysis types...")
    text = generate_test_text(15)
    
    analysis_types = ['bridges', 'hubs', 'global', 'local']
    results = {}
    
    for analysis_type in analysis_types:
        start_time = time.time()
        result = build_concept_graph(text, analysis_type=analysis_type)
        duration = time.time() - start_time
        
        results[analysis_type] = {
            'duration': duration,
            'nodes': len(result.get('nodes', [])),
            'links': len(result.get('links', [])),
            'insights': result.get('insights', {})
        }
        
        print(f"  {analysis_type}: {duration:.2f}s, {results[analysis_type]['nodes']} nodes, {results[analysis_type]['links']} links")
    
    # All should complete in reasonable time
    all_fast = all(r['duration'] < 10 for r in results.values())
    all_have_nodes = all(r['nodes'] > 0 for r in results.values())
    
    return all_fast, all_have_nodes

def test_quality_check():
    """Test that optimization doesn't break quality"""
    print("Testing concept quality...")
    
    # Use a text with known concepts
    text = """
    Artificial intelligence and machine learning are transforming technology.
    Neural networks use deep learning algorithms to process data.
    Natural language processing helps computers understand human language.
    Computer vision enables image recognition and object detection.
    Data science combines statistics with programming to analyze datasets.
    Software engineering involves systematic development of applications.
    Database systems store and retrieve information efficiently.
    """
    
    result = build_concept_graph(text, analysis_type='bridges')
    nodes = result.get('nodes', [])
    insights = result.get('insights', {})
    
    # Extract node labels
    node_labels = [node['label'] for node in nodes]
    
    print(f"  Generated {len(nodes)} nodes:")
    for i, label in enumerate(node_labels[:10]):  # Show first 10
        print(f"    {i+1}. {label}")
    
    # Check for expected concepts
    expected_concepts = ['artificial', 'intelligence', 'machine', 'learning', 'neural', 'networks', 'data']
    found_concepts = sum(1 for concept in expected_concepts 
                        if any(concept in label.lower() for label in node_labels))
    
    quality_ratio = found_concepts / len(expected_concepts)
    print(f"  Quality check: {found_concepts}/{len(expected_concepts)} expected concepts found ({quality_ratio:.1%})")
    
    return quality_ratio > 0.5, len(nodes) > 5

def main():
    print("Concept Graph Performance Test")
    print("=" * 50)
    
    test_results = []
    
    try:
        # Test 1: Small text
        fast_small, has_nodes_small, has_links_small = test_small_text()
        test_results.append(("Small text", fast_small and has_nodes_small and has_links_small))
        
        # Test 2: Medium text
        fast_medium, has_nodes_medium, has_links_medium = test_medium_text()
        test_results.append(("Medium text", fast_medium and has_nodes_medium and has_links_medium))
        
        # Test 3: Large text
        fast_large, has_nodes_large, has_links_large = test_large_text()
        test_results.append(("Large text", fast_large and has_nodes_large and has_links_large))
        
        # Test 4: Analysis types
        fast_types, has_nodes_types = test_analysis_types()
        test_results.append(("Analysis types", fast_types and has_nodes_types))
        
        # Test 5: Quality check
        good_quality, sufficient_nodes = test_quality_check()
        test_results.append(("Quality check", good_quality and sufficient_nodes))
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 All tests passed! The optimizations are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
