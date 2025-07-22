#!/usr/bin/env python3
"""
Quality assessment and balanced optimization
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import build_concept_graph

def test_quality_vs_performance():
    """Test different configurations for quality vs performance trade-offs"""
    print("Quality vs Performance Analysis")
    print("=" * 50)
    
    # Create a comprehensive test text
    test_text = """
    Artificial intelligence and machine learning are transforming technology. Deep learning uses neural networks 
    to process complex data patterns. Natural language processing enables computers to understand human language. 
    Computer vision allows machines to interpret visual information from images and videos.
    
    Data science combines statistics, machine learning, and domain knowledge to extract insights from data. 
    Software engineering involves the systematic design and development of software systems. Database management 
    provides efficient storage and retrieval of information.
    
    Cloud computing offers scalable infrastructure for applications. Cybersecurity protects digital systems 
    from threats. Internet of Things connects physical devices to digital networks for data collection.
    
    Blockchain technology provides secure, decentralized transaction recording. Quantum computing could solve 
    certain problems exponentially faster than classical computers. Virtual reality creates immersive digital 
    experiences that simulate real environments.
    
    Big data analytics processes large datasets to discover patterns and trends. Edge computing brings 
    computation closer to data sources. Microservices architecture breaks applications into independent services.
    
    DevOps integrates development and operations for faster delivery. APIs enable different systems to 
    communicate effectively. User experience design creates intuitive interfaces.
    
    Mobile computing provides access to information through portable devices. Social media facilitates 
    communication and content sharing. E-commerce enables online buying and selling of products.
    
    Digital transformation helps organizations leverage technology for business improvement. Automation 
    reduces manual work and increases efficiency. Robotics combines engineering and computer science.
    """
    
    # Expected key concepts for quality assessment
    expected_concepts = {
        'artificial intelligence', 'machine learning', 'deep learning', 'neural networks',
        'natural language processing', 'computer vision', 'data science', 'software engineering',
        'database management', 'cloud computing', 'cybersecurity', 'internet of things',
        'blockchain', 'quantum computing', 'virtual reality', 'big data', 'edge computing',
        'microservices', 'devops', 'mobile computing', 'social media', 'ecommerce',
        'digital transformation', 'automation', 'robotics'
    }
    
    print(f"Test text size: {len(test_text)} characters")
    print(f"Expected concepts: {len(expected_concepts)}")
    print()
    
    # Test current implementation
    print("Current Implementation:")
    print("-" * 30)
    start_time = time.time()
    result = build_concept_graph(test_text, analysis_type='bridges')
    duration = time.time() - start_time
    
    nodes = result.get('nodes', [])
    node_labels = {node.get('label', '').lower() for node in nodes}
    
    found_concepts = node_labels.intersection(expected_concepts)
    quality_score = len(found_concepts) / len(expected_concepts) * 100
    
    print(f"Time: {duration:.3f}s")
    print(f"Nodes found: {len(nodes)}")
    print(f"Expected concepts found: {len(found_concepts)}/{len(expected_concepts)} ({quality_score:.1f}%)")
    print(f"Found concepts: {sorted(found_concepts)}")
    print(f"Node labels: {sorted(node_labels)}")
    
    return quality_score, duration, len(nodes)

def main():
    quality, time_taken, node_count = test_quality_vs_performance()
    
    print("\n" + "=" * 50)
    print("Assessment Summary:")
    print(f"  Performance: {time_taken:.3f}s - {'✅ EXCELLENT' if time_taken < 2 else '⚠️ SLOW'}")
    print(f"  Node Count: {node_count} - {'✅ GOOD' if 15 <= node_count <= 50 else '⚠️ CHECK'}")
    print(f"  Concept Quality: {quality:.1f}% - {'✅ EXCELLENT' if quality >= 60 else '⚠️ LOW' if quality >= 30 else '❌ POOR'}")
    
    if quality < 50:
        print("\n💡 Recommendation: The filtering might be too aggressive.")
        print("   Consider adjusting centrality thresholds or sampling strategies.")
    elif time_taken > 5:
        print("\n💡 Recommendation: Performance could be improved.")
        print("   Consider more aggressive text truncation or sampling.")
    else:
        print("\n🎯 The current balance seems good!")

if __name__ == "__main__":
    main()
