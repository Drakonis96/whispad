#!/usr/bin/env python3
"""
Comprehensive quality test for high-quality concept graph
Target: 80-90% quality with 5-10 second processing time for large documents
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from high_quality_concept_graph import build_high_quality_concept_graph

def comprehensive_quality_test():
    """Test high-quality implementation with comprehensive text"""
    print("🎯 HIGH-QUALITY CONCEPT GRAPH TEST")
    print("Target: 80-90% quality within 5-10 seconds")
    print("=" * 60)
    
    # Comprehensive test text with many expected concepts
    test_text = """
    Artificial intelligence and machine learning are revolutionizing technology across multiple industries. 
    Deep learning algorithms utilize neural networks with multiple hidden layers to process complex data patterns. 
    Natural language processing enables computers to understand, interpret, and generate human language with 
    increasing sophistication. Computer vision systems allow machines to analyze and interpret visual information 
    from digital images and videos with remarkable accuracy.
    
    Data science combines statistical analysis, machine learning techniques, and domain expertise to extract 
    valuable insights from large datasets. Software engineering practices ensure systematic design, development, 
    testing, and maintenance of robust software systems. Database management systems provide efficient storage, 
    retrieval, and manipulation of structured and unstructured data across distributed architectures.
    
    Cloud computing platforms offer scalable infrastructure and services for deploying applications at enterprise 
    scale. Cybersecurity measures protect digital assets through multi-layered defense strategies. The Internet 
    of Things connects billions of devices, generating unprecedented amounts of real-time data for analysis and 
    decision-making processes.
    
    Blockchain technology provides immutable, decentralized ledgers for secure transaction processing and data 
    integrity verification. Quantum computing promises to solve certain computational problems exponentially 
    faster than classical computers. Virtual reality and augmented reality technologies create immersive digital 
    experiences that seamlessly blend physical and digital environments.
    
    Big data analytics processes massive volumes of structured and unstructured information to discover hidden 
    patterns, correlations, and trends. Edge computing brings computation and data storage closer to data sources 
    to reduce latency and improve performance. Microservices architecture decomposes applications into smaller, 
    independent services for better scalability and maintainability.
    
    DevOps practices integrate software development and IT operations to improve collaboration and accelerate 
    delivery cycles. Application programming interfaces enable seamless communication between different software 
    systems and platforms. User experience design focuses on creating intuitive and engaging interfaces that 
    meet user needs and expectations effectively.
    
    Mobile computing provides ubiquitous access to information and services through smartphones, tablets, and 
    wearable devices. Social media platforms facilitate global communication, content sharing, and community 
    building among users worldwide. E-commerce systems enable secure online buying and selling of goods and 
    services through integrated digital marketplaces.
    
    Digital transformation initiatives help organizations leverage technology to improve operations, enhance 
    customer experiences, and create innovative business models. Automation technologies reduce manual work 
    and increase operational efficiency across various industries. Robotics combines mechanical engineering, 
    electrical engineering, and computer science to create autonomous machines.
    
    Business intelligence tools transform raw data into actionable insights for strategic decision-making. 
    Project management methodologies ensure successful delivery of complex initiatives within time and budget 
    constraints. Quality assurance processes maintain high standards throughout software development lifecycles.
    
    Web development frameworks accelerate the creation of responsive and interactive web applications. 
    Mobile development platforms enable cross-platform app development for iOS and Android ecosystems. 
    Full-stack development encompasses both frontend and backend development capabilities for comprehensive 
    application creation.
    """
    
    # Comprehensive list of expected compound terms
    expected_concepts = {
        # Core AI/ML
        'artificial intelligence', 'machine learning', 'deep learning', 'neural networks',
        'natural language processing', 'computer vision', 'data science', 
        
        # Development & Engineering  
        'software engineering', 'web development', 'mobile development', 'full stack',
        'software development', 'frontend', 'backend', 'user experience', 'user interface',
        
        # Infrastructure & Computing
        'cloud computing', 'edge computing', 'quantum computing', 'mobile computing',
        'database management', 'big data', 'data analysis', 'business intelligence',
        
        # Emerging Technologies
        'internet of things', 'blockchain technology', 'virtual reality', 'augmented reality',
        'digital transformation', 'social media', 'e commerce', 'automation',
        
        # Architecture & Practices
        'microservices architecture', 'devops', 'application programming', 'cybersecurity',
        'project management', 'quality assurance', 'data analytics', 'robotics'
    }
    
    print(f"📄 Test text: {len(test_text)} characters ({len(test_text)/1024:.1f}KB)")
    print(f"🎯 Expected concepts: {len(expected_concepts)}")
    print()
    
    # Run high-quality test
    start_time = time.time()
    result = build_high_quality_concept_graph(test_text)
    duration = time.time() - start_time
    
    nodes = result.get('nodes', [])
    insights = result.get('insights', {})
    
    # Extract node labels for comparison
    node_labels = {node.get('label', '').lower() for node in nodes}
    compound_nodes = [node for node in nodes if node.get('type') == 'compound']
    
    # Quality assessment with flexible matching
    found_concepts = set()
    for label in node_labels:
        label_clean = label.replace('_', ' ').strip()
        for expected in expected_concepts:
            # Multiple matching strategies for higher accuracy
            if (expected in label_clean or 
                label_clean in expected or
                expected.replace(' ', '') in label_clean.replace(' ', '') or
                all(word in label_clean for word in expected.split()[:2])):  # Match first 2 words
                found_concepts.add(expected)
    
    quality_score = len(found_concepts) / len(expected_concepts) * 100
    
    print("📊 RESULTS:")
    print(f"   ⏱️  Processing Time: {duration:.2f}s")
    print(f"   📈 Total Nodes: {len(nodes)}")
    print(f"   🔗 Total Links: {len(result.get('links', []))}")
    print(f"   🧩 Compound Terms: {len(compound_nodes)}")
    print(f"   📊 Single Terms: {insights.get('single_terms', 0)}")
    print(f"   🎯 Quality Score: {quality_score:.1f}%")
    print(f"   ✅ Found Concepts: {len(found_concepts)}/{len(expected_concepts)}")
    print()
    
    print("🎯 FOUND CONCEPTS:")
    for concept in sorted(found_concepts):
        print(f"   ✅ {concept}")
    
    missing_concepts = expected_concepts - found_concepts
    if missing_concepts:
        print(f"\n❌ MISSING CONCEPTS ({len(missing_concepts)}):")
        for concept in sorted(missing_concepts):
            print(f"   ❌ {concept}")
    
    print(f"\n📝 ALL NODE LABELS ({len(node_labels)}):")
    for label in sorted(node_labels):
        print(f"   • {label}")
    
    return quality_score, duration, len(nodes)

def large_document_stress_test():
    """Test with very large document (target: 5-10 seconds)"""
    print("\n" + "=" * 60)
    print("🚀 LARGE DOCUMENT STRESS TEST")
    print("Target: 80-90% quality within 10 seconds")
    print("=" * 60)
    
    # Generate large document with rich content
    base_content = """
    Artificial intelligence and machine learning technologies are revolutionizing business operations across 
    multiple sectors. Deep learning neural networks enable sophisticated pattern recognition in complex datasets. 
    Natural language processing systems facilitate human-computer interaction through conversational interfaces. 
    Computer vision applications analyze visual data for automated decision-making processes.
    
    Data science methodologies combine statistical analysis with machine learning algorithms to extract business 
    insights. Software engineering best practices ensure scalable and maintainable system architectures. Database 
    management solutions handle massive volumes of structured and unstructured information efficiently.
    
    Cloud computing infrastructures provide elastic scalability for enterprise applications. Cybersecurity frameworks 
    protect sensitive data through advanced encryption and access control mechanisms. Internet of Things ecosystems 
    generate continuous streams of sensor data for real-time analytics and monitoring.
    
    Blockchain technology ensures data integrity through distributed consensus mechanisms. Quantum computing research 
    promises breakthrough capabilities for complex optimization problems. Virtual reality and augmented reality 
    platforms create immersive user experiences for training and entertainment applications.
    
    Big data analytics platforms process petabytes of information to identify market trends and customer behaviors. 
    Edge computing architectures reduce latency by processing data closer to its source. Microservices design 
    patterns enable flexible and scalable application development approaches.
    
    DevOps automation streamlines software delivery pipelines through continuous integration and deployment. 
    Application programming interfaces facilitate seamless integration between heterogeneous systems. User experience 
    design principles guide the creation of intuitive and accessible digital interfaces.
    
    Digital transformation initiatives modernize legacy systems and business processes. Robotic process automation 
    eliminates repetitive manual tasks through intelligent workflow orchestration. Business intelligence dashboards 
    provide real-time visibility into key performance indicators and operational metrics.
    """
    
    # Create very large document (repeat content multiple times)
    large_document = base_content * 12  # Approximately 25KB
    
    print(f"📄 Document size: {len(large_document)} characters ({len(large_document)/1024:.1f}KB)")
    
    start_time = time.time()
    result = build_high_quality_concept_graph(large_document)
    duration = time.time() - start_time
    
    nodes = len(result.get('nodes', []))
    links = len(result.get('links', []))
    compound_terms = len([n for n in result.get('nodes', []) if n.get('type') == 'compound'])
    
    print(f"⏱️  Processing Time: {duration:.2f}s")
    print(f"📊 Results: {nodes} nodes, {links} links")
    print(f"🧩 Compound Terms: {compound_terms}")
    
    # Assessment
    time_acceptable = duration <= 10.0
    quality_acceptable = compound_terms >= 15  # Should find many compound terms
    
    print("\n📈 ASSESSMENT:")
    if time_acceptable:
        print(f"   ✅ Time: EXCELLENT ({duration:.2f}s ≤ 10s)")
    else:
        print(f"   ⚠️  Time: TOO SLOW ({duration:.2f}s > 10s)")
    
    if quality_acceptable:
        print(f"   ✅ Quality: GOOD ({compound_terms} compound terms)")
    else:
        print(f"   ⚠️  Quality: INSUFFICIENT ({compound_terms} compound terms)")
    
    return time_acceptable and quality_acceptable

def main():
    print("🎯 HIGH-QUALITY CONCEPT GRAPH VALIDATION")
    print("Target: 80-90% quality with acceptable performance")
    print("=" * 70)
    
    # Test 1: Quality assessment
    quality_score, time_taken, node_count = comprehensive_quality_test()
    
    # Test 2: Large document performance
    stress_passed = large_document_stress_test()
    
    # Final assessment
    print("\n" + "=" * 70)
    print("🎯 FINAL ASSESSMENT")
    print("=" * 70)
    
    quality_excellent = quality_score >= 80
    quality_good = quality_score >= 60
    performance_excellent = time_taken <= 2
    performance_good = time_taken <= 10
    
    print(f"📊 Quality Score: {quality_score:.1f}%")
    if quality_excellent:
        print("   🎉 EXCELLENT QUALITY (≥80%)")
    elif quality_good:
        print("   ✅ GOOD QUALITY (≥60%)")
    else:
        print("   ⚠️  NEEDS IMPROVEMENT")
    
    print(f"⏱️  Performance: {time_taken:.2f}s")
    if performance_excellent:
        print("   ⚡ EXCELLENT PERFORMANCE (≤2s)")
    elif performance_good:
        print("   ✅ ACCEPTABLE PERFORMANCE (≤10s)")
    else:
        print("   ⚠️  TOO SLOW")
    
    print(f"📈 Node Count: {node_count}")
    print(f"🚀 Stress Test: {'✅ PASSED' if stress_passed else '❌ FAILED'}")
    
    if quality_excellent and performance_good and stress_passed:
        print("\n🎉 SUCCESS! Ready for production with high-quality concept extraction!")
    elif quality_good and performance_good:
        print("\n✅ GOOD! Quality and performance are acceptable.")
    else:
        print("\n⚠️  Needs further optimization.")

if __name__ == "__main__":
    main()
