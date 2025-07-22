#!/usr/bin/env python3
"""
Performance test for optimized concept graph generation
"""

import time
from concept_graph import build_concept_graph

def generate_large_text(size_kb=100):
    """Generate a large text for testing performance"""
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
    """
    
    # Repeat the text to reach desired size
    target_chars = size_kb * 1024
    repeats = max(1, target_chars // len(base_text))
    return (base_text * repeats)[:target_chars]

def test_performance():
    """Test performance with different text sizes"""
    print("Performance Test for Optimized Concept Graph Generation")
    print("=" * 60)
    
    # Test different text sizes
    test_sizes = [10, 50, 100, 200]  # KB
    
    for size_kb in test_sizes:
        print(f"\nTesting with {size_kb}KB text...")
        
        # Generate test text
        test_text = generate_large_text(size_kb)
        print(f"Generated text: {len(test_text)} characters")
        
        # Test performance
        start_time = time.time()
        try:
            result = build_concept_graph(test_text, analysis_type='bridges')
            end_time = time.time()
            
            duration = end_time - start_time
            nodes = len(result.get('nodes', []))
            links = len(result.get('links', []))
            
            print(f"✅ Success: {duration:.2f}s - {nodes} nodes, {links} links")
            
            # Performance expectations
            if size_kb <= 50 and duration > 10:
                print(f"⚠️  Warning: Slower than expected for {size_kb}KB")
            elif size_kb <= 100 and duration > 20:
                print(f"⚠️  Warning: Slower than expected for {size_kb}KB")
            elif duration > 30:
                print(f"⚠️  Warning: Very slow processing time")
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"❌ Failed after {duration:.2f}s: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Performance test completed!")

def test_quality():
    """Test that optimizations don't significantly reduce quality"""
    print("\nQuality Test - Checking optimization impact")
    print("-" * 40)
    
    medium_text = generate_large_text(30)  # 30KB text
    
    start_time = time.time()
    result = build_concept_graph(medium_text, analysis_type='bridges')
    duration = time.time() - start_time
    
    nodes = result.get('nodes', [])
    links = result.get('links', [])
    insights = result.get('insights', {})
    
    print(f"Processing time: {duration:.2f}s")
    print(f"Nodes generated: {len(nodes)}")
    print(f"Links generated: {len(links)}")
    print(f"Clusters found: {insights.get('total_clusters', 0)}")
    
    if len(nodes) > 0:
        print(f"Sample nodes: {[node['label'] for node in nodes[:5]]}")
        
    # Quality checks
    quality_score = 0
    if len(nodes) >= 10:
        quality_score += 1
    if len(links) >= 5:
        quality_score += 1
    if insights.get('total_clusters', 0) > 0:
        quality_score += 1
    if any('importance' in node for node in nodes):
        quality_score += 1
    
    print(f"Quality score: {quality_score}/4")
    
    if quality_score >= 3:
        print("✅ Quality maintained after optimization")
    else:
        print("⚠️  Quality may have been impacted")

if __name__ == "__main__":
    test_performance()
    test_quality()
