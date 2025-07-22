#!/usr/bin/env python3
"""
Stress test for very large documents
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concept_graph import build_concept_graph

def generate_very_large_text(size_kb=500):
    """Generate very large text for stress testing"""
    base_text = """
    Artificial intelligence and machine learning are rapidly transforming the technological landscape across numerous industries. 
    Deep learning algorithms, powered by neural networks with multiple hidden layers, enable computers to recognize complex 
    patterns in vast datasets. Natural language processing systems help machines understand, interpret, and generate human 
    language with increasing sophistication. Computer vision technologies allow machines to analyze and interpret visual 
    information from digital images and videos.
    
    Data science combines statistical analysis, machine learning, and domain expertise to extract valuable insights from 
    large and complex datasets. Software engineering practices ensure the systematic design, development, testing, and 
    maintenance of robust software systems. Database management systems provide efficient storage, retrieval, and 
    manipulation of structured and unstructured data.
    
    Cloud computing platforms offer scalable infrastructure and services for deploying and managing applications at scale. 
    Cybersecurity measures protect digital assets and information systems from threats and vulnerabilities. Internet of 
    Things (IoT) devices collect and transmit data from the physical world to digital systems for analysis and automation.
    
    Blockchain technology provides decentralized and secure methods for recording transactions and maintaining data integrity. 
    Quantum computing promises to solve certain computational problems exponentially faster than classical computers. 
    Augmented reality and virtual reality technologies create immersive digital experiences that blend the physical and 
    digital worlds.
    
    Big data analytics processes large volumes of structured and unstructured data to discover hidden patterns, correlations, 
    and trends. Edge computing brings computation and data storage closer to the sources of data to reduce latency and 
    improve performance. Microservices architecture breaks down applications into smaller, independent services that can 
    be developed, deployed, and scaled independently.
    
    DevOps practices integrate software development and IT operations to improve collaboration and accelerate delivery cycles. 
    Application programming interfaces (APIs) enable different software systems to communicate and share data effectively. 
    User experience (UX) design focuses on creating intuitive and engaging interfaces that meet user needs and expectations.
    
    Mobile computing enables access to information and services from anywhere through smartphones, tablets, and other 
    portable devices. Social media platforms facilitate communication, content sharing, and community building among users 
    worldwide. E-commerce systems enable online buying and selling of goods and services through digital platforms.
    
    Digital transformation initiatives help organizations leverage technology to improve operations, enhance customer 
    experiences, and create new business models. Automation technologies reduce manual work and increase efficiency 
    across various processes and industries. Robotics combines mechanical engineering, electrical engineering, and 
    computer science to create machines that can perform tasks autonomously.
    """
    
    # Calculate repetitions needed
    target_chars = size_kb * 1024
    repeats = max(1, target_chars // len(base_text))
    return (base_text * repeats)[:target_chars]

def stress_test_500kb():
    """Test with 500KB document"""
    print("Stress Test: 500KB Document")
    print("=" * 40)
    
    text = generate_very_large_text(500)
    print(f"Text size: {len(text)} characters ({len(text)/1024:.1f}KB)")
    print(f"Sentences: ~{len(text.split('.'))}")
    
    start_time = time.time()
    try:
        result = build_concept_graph(text, analysis_type='bridges')
        end_time = time.time()
        
        duration = end_time - start_time
        nodes = len(result.get('nodes', []))
        links = len(result.get('links', []))
        insights = result.get('insights', {})
        
        print(f"✅ Completed in {duration:.2f}s")
        print(f"   Nodes: {nodes}")
        print(f"   Links: {links}")
        print(f"   Clusters: {insights.get('total_clusters', 0)}")
        
        # Performance expectations
        if duration < 60:  # Should complete within 1 minute
            print(f"✅ Performance: EXCELLENT (< 60s)")
        elif duration < 120:  # Should complete within 2 minutes
            print(f"⚠️  Performance: ACCEPTABLE (< 120s)")
        else:
            print(f"❌ Performance: POOR (> 120s)")
        
        return duration < 120, nodes > 0
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Failed after {duration:.2f}s: {e}")
        return False, False

def stress_test_1mb():
    """Test with 1MB document"""
    print("\nStress Test: 1MB Document")
    print("=" * 40)
    
    text = generate_very_large_text(1024)  # 1MB
    print(f"Text size: {len(text)} characters ({len(text)/1024:.1f}KB)")
    print(f"Sentences: ~{len(text.split('.'))}")
    
    start_time = time.time()
    try:
        result = build_concept_graph(text, analysis_type='bridges')
        end_time = time.time()
        
        duration = end_time - start_time
        nodes = len(result.get('nodes', []))
        links = len(result.get('links', []))
        insights = result.get('insights', {})
        
        print(f"✅ Completed in {duration:.2f}s")
        print(f"   Nodes: {nodes}")
        print(f"   Links: {links}")
        print(f"   Clusters: {insights.get('total_clusters', 0)}")
        
        # Performance expectations for very large text
        if duration < 120:  # Should complete within 2 minutes
            print(f"✅ Performance: EXCELLENT (< 120s)")
        elif duration < 300:  # Should complete within 5 minutes
            print(f"⚠️  Performance: ACCEPTABLE (< 300s)")
        else:
            print(f"❌ Performance: POOR (> 300s)")
        
        return duration < 300, nodes > 0
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Failed after {duration:.2f}s: {e}")
        return False, False

def memory_usage_test():
    """Simple memory usage observation"""
    print("\nMemory Usage Test")
    print("=" * 40)
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"Initial memory: {initial_memory:.1f}MB")
    
    # Generate large text and process it
    text = generate_very_large_text(200)  # 200KB
    result = build_concept_graph(text, analysis_type='bridges')
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_used = peak_memory - initial_memory
    
    print(f"Peak memory: {peak_memory:.1f}MB")
    print(f"Memory used: {memory_used:.1f}MB")
    
    if memory_used < 100:  # Less than 100MB additional
        print("✅ Memory usage: GOOD")
        return True
    elif memory_used < 500:  # Less than 500MB additional
        print("⚠️  Memory usage: ACCEPTABLE")
        return True
    else:
        print("❌ Memory usage: HIGH")
        return False

def main():
    print("Concept Graph Stress Test")
    print("=" * 50)
    
    tests = []
    
    # Test 500KB
    success_500kb, has_nodes_500kb = stress_test_500kb()
    tests.append(("500KB stress test", success_500kb and has_nodes_500kb))
    
    # Test 1MB
    success_1mb, has_nodes_1mb = stress_test_1mb()
    tests.append(("1MB stress test", success_1mb and has_nodes_1mb))
    
    # Memory test
    try:
        memory_ok = memory_usage_test()
        tests.append(("Memory usage", memory_ok))
    except ImportError:
        print("Skipping memory test (psutil not available)")
    
    # Results
    print("\n" + "=" * 50)
    print("Stress Test Results:")
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} stress tests passed")
    
    if passed == len(tests):
        print("🚀 Excellent! The optimizations handle large documents efficiently.")
    elif passed >= len(tests) * 0.7:  # 70% pass rate
        print("✅ Good! Most optimizations are working well.")
    else:
        print("⚠️  Some performance issues detected.")

if __name__ == "__main__":
    main()
