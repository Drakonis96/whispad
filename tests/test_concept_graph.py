#!/usr/bin/env python3
"""
Test script for concept graph improvements
"""

from concept_graph import extract_key_terms, calculate_term_importance, build_concept_graph

def test_filtering():
    """Test that pronouns and common words are properly filtered out."""
    
    test_text = """
    You should understand that his ideas about artificial intelligence and machine learning 
    are very important. The neural networks use deep learning algorithms to process data. 
    Its performance depends on the training dataset quality. We need to implement 
    better optimization techniques for our model.
    """
    
    print("Testing term extraction and filtering...")
    print("Original text:", test_text[:100] + "...")
    
    # Extract terms
    terms = extract_key_terms(test_text)
    print(f"\nExtracted {len(terms)} terms:")
    print("Terms:", terms)
    
    # Calculate importance
    importance = calculate_term_importance(terms, test_text)
    sorted_terms = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nTop 10 most important terms:")
    for i, (term, score) in enumerate(sorted_terms[:10]):
        print(f"{i+1}. {term}: {score:.4f}")
    
    # Check for problematic words
    problematic_words = {'you', 'his', 'its', 'we', 'our', 'the', 'and', 'very', 'that'}
    found_problematic = [term for term in terms if term in problematic_words]
    
    if found_problematic:
        print(f"\n❌ WARNING: Found problematic words: {found_problematic}")
    else:
        print(f"\n✅ SUCCESS: No problematic pronouns or common words found!")
    
    return len(found_problematic) == 0

def test_concept_graph():
    """Test the full concept graph generation."""
    
    test_text = """
    Machine learning is a subset of artificial intelligence that focuses on algorithms 
    and statistical models. Deep learning uses neural networks with multiple layers 
    to process complex data patterns. Natural language processing enables computers 
    to understand human language. Computer vision allows machines to interpret 
    visual information from images and videos.
    """
    
    print("\n" + "="*50)
    print("Testing concept graph generation...")
    
    try:
        result = build_concept_graph(test_text, analysis_type='bridges')
        
        print(f"Generated graph with {len(result['nodes'])} nodes and {len(result['links'])} links")
        
        if result['nodes']:
            print("\nNodes in graph:")
            for i, node in enumerate(result['nodes'][:10]):  # Show first 10
                print(f"{i+1}. {node['label']} (size: {node.get('size', 'N/A')})")
        
        if result['insights']:
            print(f"\nInsights:")
            print(f"- Analysis type: {result['insights'].get('analysis_type', 'N/A')}")
            print(f"- Total clusters: {result['insights'].get('total_clusters', 'N/A')}")
            print(f"- Dominant topics: {result['insights'].get('dominant_topics', [])[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Testing Concept Graph Improvements")
    print("="*50)
    
    # Run tests
    filtering_success = test_filtering()
    graph_success = test_concept_graph()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"✅ Filtering test: {'PASSED' if filtering_success else 'FAILED'}")
    print(f"✅ Graph generation: {'PASSED' if graph_success else 'FAILED'}")
    
    if filtering_success and graph_success:
        print("\n🎉 All tests passed! The concept graph improvements are working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
