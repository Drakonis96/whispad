#!/usr/bin/env python3
"""
Test the improved concept graph quality
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph_improved import build_concept_graph_improved

def test_improved_quality():
    """Test the improved implementation quality"""
    print("Improved Concept Graph Quality Test")
    print("=" * 50)
    
    # Test text with expected concepts
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
    
    # Expected compound terms that should be preserved
    expected_concepts = {
        'artificial intelligence', 'machine learning', 'deep learning', 'neural networks',
        'natural language processing', 'computer vision', 'data science', 'software engineering',
        'database management', 'cloud computing', 'cybersecurity', 'internet of things',
        'blockchain', 'quantum computing', 'virtual reality', 'big data', 'edge computing',
        'digital transformation', 'user experience', 'mobile computing', 'social media'
    }
    
    print(f"Test text size: {len(test_text)} characters")
    print(f"Expected concepts: {len(expected_concepts)}")
    print()
    
    # Test improved implementation
    start_time = time.time()
    result = build_concept_graph_improved(test_text, analysis_type='bridges')
    duration = time.time() - start_time
    
    nodes = result.get('nodes', [])
    node_labels = {node.get('label', '').lower() for node in nodes}
    
    # More flexible matching (handle title case and variations)
    found_concepts = set()
    for label in node_labels:
        label_clean = label.replace('_', ' ').strip()
        for expected in expected_concepts:
            if (expected in label_clean or 
                label_clean in expected or
                expected.replace(' ', '') in label_clean.replace(' ', '')):
                found_concepts.add(expected)
    
    quality_score = len(found_concepts) / len(expected_concepts) * 100
    
    print(f"⏱️  Time: {duration:.3f}s")
    print(f"📊 Nodes found: {len(nodes)}")
    print(f"🎯 Expected concepts found: {len(found_concepts)}/{len(expected_concepts)} ({quality_score:.1f}%)")
    print(f"✅ Found concepts: {sorted(found_concepts)}")
    print(f"📝 All node labels: {sorted(node_labels)}")
    
    # Performance vs Quality assessment
    print("\n" + "=" * 50)
    print("Assessment:")
    
    if duration < 2:
        print(f"⚡ Performance: EXCELLENT ({duration:.3f}s)")
    elif duration < 5:
        print(f"✅ Performance: GOOD ({duration:.3f}s)")
    else:
        print(f"⚠️  Performance: NEEDS IMPROVEMENT ({duration:.3f}s)")
    
    if quality_score >= 70:
        print(f"🎯 Quality: EXCELLENT ({quality_score:.1f}%)")
    elif quality_score >= 50:
        print(f"✅ Quality: GOOD ({quality_score:.1f}%)")
    elif quality_score >= 30:
        print(f"⚠️  Quality: FAIR ({quality_score:.1f}%)")
    else:
        print(f"❌ Quality: POOR ({quality_score:.1f}%)")
    
    if 15 <= len(nodes) <= 50:
        print(f"📊 Node Count: OPTIMAL ({len(nodes)} nodes)")
    elif len(nodes) < 15:
        print(f"📊 Node Count: TOO FEW ({len(nodes)} nodes)")
    else:
        print(f"📊 Node Count: TOO MANY ({len(nodes)} nodes)")
    
    return quality_score >= 50 and duration < 5 and 15 <= len(nodes) <= 50

def test_large_document_improved():
    """Test with a larger document"""
    print("\n" + "=" * 50)
    print("Large Document Test (Improved)")
    print("=" * 50)
    
    # Generate larger text
    base_text = """
    Artificial intelligence and machine learning are revolutionizing how we approach complex problems across 
    multiple industries. Deep learning algorithms utilize neural networks with multiple hidden layers to 
    identify intricate patterns within vast datasets, enabling breakthrough applications in computer vision, 
    natural language processing, and predictive analytics.
    
    Data science has emerged as a critical discipline combining statistical analysis, machine learning techniques, 
    and domain expertise to extract actionable insights from structured and unstructured data. Software engineering 
    practices ensure the development of robust, scalable, and maintainable systems that can handle enterprise-level 
    workloads. Database management systems provide the foundation for efficient data storage, retrieval, and 
    manipulation across distributed architectures.
    
    Cloud computing platforms offer elastic infrastructure that can scale automatically based on demand, enabling 
    organizations to optimize costs while maintaining high availability. Cybersecurity measures protect critical 
    digital assets through multi-layered defense strategies, including encryption, access controls, and threat 
    monitoring. The Internet of Things ecosystem connects billions of devices, generating unprecedented amounts 
    of real-time data for analysis and decision-making.
    
    Blockchain technology provides immutable, decentralized ledgers for secure transaction processing and data 
    integrity verification. Quantum computing promises to solve certain computational problems exponentially 
    faster than classical computers, potentially transforming cryptography, optimization, and scientific simulation. 
    Virtual reality and augmented reality technologies create immersive experiences that bridge the physical and 
    digital worlds.
    """
    
    # Repeat to create larger document
    large_text = base_text * 3  # About 3KB
    
    print(f"Document size: {len(large_text)} characters ({len(large_text)/1024:.1f}KB)")
    
    start_time = time.time()
    result = build_concept_graph_improved(large_text)
    duration = time.time() - start_time
    
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    
    print(f"⏱️  Processing time: {duration:.3f}s")
    print(f"📊 Results: {nodes} nodes, {links} links")
    
    if duration < 3:
        print("⚡ Performance: EXCELLENT for large document")
        return True
    elif duration < 10:
        print("✅ Performance: ACCEPTABLE for large document")
        return True
    else:
        print("⚠️  Performance: SLOW for large document")
        return False

def main():
    print("🚀 Testing Improved Concept Graph Implementation")
    print("=" * 60)
    
    # Test quality
    quality_good = test_improved_quality()
    
    # Test performance on large document
    performance_good = test_large_document_improved()
    
    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT")
    print("=" * 60)
    
    if quality_good and performance_good:
        print("🎉 SUCCESS: Both quality and performance are excellent!")
        print("   ✅ Ready for production use")
    elif quality_good:
        print("✅ Quality is good, but performance could be improved")
        print("   ⚠️  Consider further optimizations for large documents")
    elif performance_good:
        print("✅ Performance is good, but quality could be improved")
        print("   ⚠️  Consider adjusting term extraction and filtering")
    else:
        print("⚠️  Both quality and performance need improvement")
        print("   🔄 Continue optimization work")

if __name__ == "__main__":
    main()
