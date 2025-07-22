#!/usr/bin/env python3
"""
High-quality concept graph implementation prioritizing 80-90% quality
Allows 5-10 seconds processing time for large documents
"""

import networkx as nx
import re
import time
from collections import defaultdict, Counter
from itertools import combinations
from typing import Dict, List, Set, Tuple, Any

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    # Download required NLTK data if not present
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
except ImportError:
    print("Warning: NLTK not available. Using basic text processing.")
    nltk = None

def extract_high_quality_terms(text: str, max_text_length: int = 200000) -> Dict[str, int]:
    """
    High-quality term extraction prioritizing compound terms and comprehensive coverage
    """
    # More generous text length limit for quality
    if len(text) > max_text_length:
        # Intelligent truncation preserving complete sentences
        sentences = re.split(r'[.!?]+', text[:max_text_length])
        if len(sentences) > 1:
            text = '. '.join(sentences[:-1]) + '.'
        else:
            text = text[:max_text_length]
    
    # Comprehensive compound terms dictionary
    compound_terms = {
        # AI/ML Core
        'artificial intelligence': 'artificial_intelligence',
        'machine learning': 'machine_learning', 
        'deep learning': 'deep_learning',
        'neural networks': 'neural_networks',
        'neural network': 'neural_network',
        'natural language processing': 'natural_language_processing',
        'computer vision': 'computer_vision',
        'reinforcement learning': 'reinforcement_learning',
        'supervised learning': 'supervised_learning',
        'unsupervised learning': 'unsupervised_learning',
        'transfer learning': 'transfer_learning',
        'generative ai': 'generative_ai',
        'large language model': 'large_language_model',
        'transformer model': 'transformer_model',
        
        # Data & Analytics
        'data science': 'data_science',
        'big data': 'big_data',
        'data analysis': 'data_analysis',
        'data mining': 'data_mining',
        'data visualization': 'data_visualization',
        'predictive analytics': 'predictive_analytics',
        'business intelligence': 'business_intelligence',
        'data warehouse': 'data_warehouse',
        'data lake': 'data_lake',
        'data pipeline': 'data_pipeline',
        
        # Software Development
        'software engineering': 'software_engineering',
        'software development': 'software_development',
        'web development': 'web_development',
        'mobile development': 'mobile_development',
        'full stack': 'full_stack',
        'frontend development': 'frontend_development',
        'backend development': 'backend_development',
        'api development': 'api_development',
        'user interface': 'user_interface',
        'user experience': 'user_experience',
        'responsive design': 'responsive_design',
        
        # Infrastructure & Systems
        'cloud computing': 'cloud_computing',
        'edge computing': 'edge_computing',
        'quantum computing': 'quantum_computing',
        'distributed computing': 'distributed_computing',
        'parallel computing': 'parallel_computing',
        'high performance computing': 'high_performance_computing',
        'database management': 'database_management',
        'system administration': 'system_administration',
        'network security': 'network_security',
        'information security': 'information_security',
        
        # Emerging Technologies
        'internet of things': 'internet_of_things',
        'blockchain technology': 'blockchain_technology',
        'virtual reality': 'virtual_reality',
        'augmented reality': 'augmented_reality',
        'mixed reality': 'mixed_reality',
        'digital transformation': 'digital_transformation',
        'automation technology': 'automation_technology',
        'robotic process automation': 'robotic_process_automation',
        
        # Architecture & Methodologies
        'microservices architecture': 'microservices_architecture',
        'service oriented architecture': 'service_oriented_architecture',
        'event driven architecture': 'event_driven_architecture',
        'domain driven design': 'domain_driven_design',
        'test driven development': 'test_driven_development',
        'continuous integration': 'continuous_integration',
        'continuous deployment': 'continuous_deployment',
        'agile methodology': 'agile_methodology',
        'devops practices': 'devops_practices',
        
        # Business & Management
        'project management': 'project_management',
        'product management': 'product_management',
        'quality assurance': 'quality_assurance',
        'change management': 'change_management',
        'risk management': 'risk_management',
        'performance monitoring': 'performance_monitoring',
        'business process': 'business_process',
        'digital marketing': 'digital_marketing',
        'customer experience': 'customer_experience',
        'social media': 'social_media',
        'mobile computing': 'mobile_computing',
        'e commerce': 'e_commerce',
        
        # Security & Privacy
        'cyber security': 'cyber_security',
        'data privacy': 'data_privacy',
        'identity management': 'identity_management',
        'access control': 'access_control',
        'threat detection': 'threat_detection',
        'vulnerability assessment': 'vulnerability_assessment',
        'penetration testing': 'penetration_testing',
        'security audit': 'security_audit',
        
        # Common variations and abbreviations
        'ai': 'artificial_intelligence',
        'ml': 'machine_learning',
        'dl': 'deep_learning',
        'nlp': 'natural_language_processing',
        'cv': 'computer_vision',
        'iot': 'internet_of_things',
        'vr': 'virtual_reality',
        'ar': 'augmented_reality',
        'ui': 'user_interface',
        'ux': 'user_experience',
        'api': 'application_programming_interface',
        'cms': 'content_management_system',
        'crm': 'customer_relationship_management',
        'erp': 'enterprise_resource_planning',
    }
    
    # Process text with compound term preservation
    text_processed = text.lower()
    
    # Replace compound terms with tokens (preserving order by length)
    sorted_compounds = sorted(compound_terms.items(), key=lambda x: len(x[0]), reverse=True)
    for compound, replacement in sorted_compounds:
        pattern = r'\b' + re.escape(compound) + r'\b'
        text_processed = re.sub(pattern, replacement, text_processed)
    
    # Initialize term frequency counter
    term_freq = Counter()
    
    # Method 1: Extract preserved compound terms
    for replacement in compound_terms.values():
        count = len(re.findall(r'\b' + re.escape(replacement) + r'\b', text_processed))
        if count > 0:
            readable_term = replacement.replace('_', ' ')
            term_freq[readable_term] = count
    
    # Method 2: Technical vocabulary (expanded)
    technical_terms = {
        # Programming & Development
        'algorithm', 'framework', 'library', 'database', 'server', 'client',
        'frontend', 'backend', 'fullstack', 'deployment', 'testing', 'debugging',
        'optimization', 'performance', 'scalability', 'security', 'authentication',
        'authorization', 'encryption', 'protocol', 'interface', 'architecture',
        'microservices', 'monolith', 'container', 'docker', 'kubernetes',
        'automation', 'devops', 'pipeline', 'repository', 'version', 'control',
        'programming', 'coding', 'development', 'engineering', 'technology',
        'innovation', 'solution', 'platform', 'system', 'application',
        'software', 'hardware', 'network', 'internet', 'web', 'mobile',
        'desktop', 'cloud', 'storage', 'memory', 'processor', 'cpu', 'gpu',
        
        # Data & Analytics
        'analysis', 'analytics', 'visualization', 'dashboard', 'report',
        'integration', 'migration', 'transformation', 'modernization',
        'dataset', 'model', 'training', 'prediction', 'classification',
        'regression', 'clustering', 'statistics', 'metrics', 'benchmark',
        
        # Business & Process
        'workflow', 'process', 'procedure', 'methodology', 'strategy',
        'implementation', 'execution', 'monitoring', 'evaluation', 'assessment',
        'requirement', 'specification', 'documentation', 'maintenance',
        'support', 'service', 'customer', 'user', 'stakeholder', 'team',
        
        # Quality & Standards
        'standard', 'compliance', 'governance', 'policy', 'procedure',
        'best', 'practice', 'guideline', 'recommendation', 'review',
        'audit', 'certification', 'validation', 'verification', 'testing',
        
        # Innovation & Research
        'research', 'innovation', 'experiment', 'prototype', 'pilot',
        'proof', 'concept', 'feasibility', 'study', 'investigation',
        'discovery', 'breakthrough', 'advancement', 'progress', 'evolution',
    }
    
    # Extract technical terms
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text_processed)
    for word in words:
        if word in technical_terms and not word.endswith('_'):
            term_freq[word] += 1
    
    # Method 3: NLTK-enhanced extraction for comprehensive coverage
    if nltk:
        try:
            stop_words = set(stopwords.words('english'))
            lemmatizer = WordNetLemmatizer()
            
            # Minimal additional stopwords (preserve more terms for quality)
            additional_stopwords = {
                'use', 'used', 'using', 'make', 'makes', 'making',
                'get', 'getting', 'take', 'taking', 'give', 'giving',
                'go', 'going', 'come', 'coming', 'see', 'seeing',
                'know', 'knowing', 'think', 'thinking', 'work', 'working',
                'help', 'helping', 'need', 'needing', 'want', 'wanting',
                'like', 'liking', 'way', 'ways', 'thing', 'things',
                'time', 'times', 'people', 'person', 'year', 'years',
                'day', 'days', 'good', 'better', 'best', 'new', 'old',
            }
            stop_words.update(additional_stopwords)
            
            # Process all remaining words with lemmatization
            for word in words:
                if (len(word) >= 3 and 
                    word not in stop_words and 
                    word not in technical_terms and  # Already processed
                    not word.endswith('_') and  # Skip compound tokens
                    word.isalpha()):
                    
                    lemmatized = lemmatizer.lemmatize(word)
                    if lemmatized not in stop_words and len(lemmatized) >= 3:
                        # Boost frequency for domain-relevant terms
                        boost = 1
                        if any(keyword in lemmatized for keyword in 
                               ['tech', 'data', 'system', 'manage', 'develop', 
                                'design', 'create', 'build', 'implement', 'analyze']):
                            boost = 2
                        term_freq[lemmatized] += boost
        
        except Exception as e:
            print(f"NLTK processing error: {e}")
    
    # Quality-focused filtering (less aggressive)
    min_freq = 1  # Keep all terms that appear at least once
    filtered_terms = {}
    
    for term, freq in term_freq.items():
        if (freq >= min_freq and 
            len(term) >= 3 and 
            len(term) <= 50):  # Allow longer compound terms
            filtered_terms[term] = freq
    
    # Ensure all compound terms are preserved regardless of frequency
    for replacement in compound_terms.values():
        readable_term = replacement.replace('_', ' ')
        if readable_term in term_freq:
            filtered_terms[readable_term] = term_freq[readable_term]
    
    return filtered_terms

def build_high_quality_concept_graph(text: str, analysis_type: str = 'community') -> Dict[str, Any]:
    """
    High-quality concept graph builder prioritizing 80-90% quality
    """
    print(f"Building high-quality concept graph for {len(text)} characters...")
    start_time = time.time()
    
    # Extract terms with high-quality method
    terms = extract_high_quality_terms(text)
    print(f"Extracted {len(terms)} terms in {time.time() - start_time:.2f}s")
    
    if not terms:
        return {
            'nodes': [],
            'links': [],
            'insights': {'message': 'No terms extracted from text'}
        }
    
    # Build comprehensive co-occurrence graph
    G = nx.Graph()
    
    # Add all nodes with weights
    for term, freq in terms.items():
        G.add_node(term, weight=freq, frequency=freq)
    
    # Enhanced edge detection with multiple methods
    edge_weights = defaultdict(int)
    
    # Method 1: Sentence-level co-occurrence (primary)
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        sentence_lower = sentence.lower()
        sentence_terms = []
        
        # Find all terms in this sentence
        for term in terms.keys():
            search_variants = [term]
            if ' ' in term:
                search_variants.append(term.replace(' ', '_'))
                search_variants.extend(term.split())
            
            found = False
            for variant in search_variants:
                if re.search(r'\b' + re.escape(variant) + r'\b', sentence_lower):
                    sentence_terms.append(term)
                    found = True
                    break
        
        # Add co-occurrence edges
        for term1, term2 in combinations(sentence_terms, 2):
            edge_weights[(term1, term2)] += 1
    
    # Method 2: Paragraph-level co-occurrence (secondary)
    paragraphs = re.split(r'\n\s*\n', text)
    for paragraph in paragraphs:
        paragraph_lower = paragraph.lower()
        paragraph_terms = []
        
        for term in terms.keys():
            search_variants = [term]
            if ' ' in term:
                search_variants.append(term.replace(' ', '_'))
            
            for variant in search_variants:
                if re.search(r'\b' + re.escape(variant) + r'\b', paragraph_lower):
                    paragraph_terms.append(term)
                    break
        
        # Add weaker paragraph-level connections
        for term1, term2 in combinations(paragraph_terms, 2):
            edge_weights[(term1, term2)] += 0.5
    
    # Add edges to graph
    for (term1, term2), weight in edge_weights.items():
        if weight >= 1:  # Minimum threshold for connection
            G.add_edge(term1, term2, weight=weight)
    
    # Calculate comprehensive centrality measures
    centrality_scores = {}
    if len(G.nodes()) > 0:
        try:
            degree_centrality = nx.degree_centrality(G)
            
            # For quality, calculate full centrality even for larger graphs (allow more time)
            if len(G.nodes()) <= 200:
                betweenness = nx.betweenness_centrality(G)
                closeness = nx.closeness_centrality(G)
                eigenvector = nx.eigenvector_centrality(G, max_iter=1000)
            else:
                # Sample-based approach for very large graphs
                sample_size = min(100, len(G.nodes()))
                sample_nodes = sorted(G.nodes(), key=lambda x: terms.get(x, 0), reverse=True)[:sample_size]
                subgraph = G.subgraph(sample_nodes)
                
                betweenness_sample = nx.betweenness_centrality(subgraph)
                closeness_sample = nx.closeness_centrality(subgraph)
                eigenvector_sample = nx.eigenvector_centrality(subgraph, max_iter=1000)
                
                # Extend to all nodes
                betweenness = {node: betweenness_sample.get(node, 0.0) for node in G.nodes()}
                closeness = {node: closeness_sample.get(node, 0.0) for node in G.nodes()}
                eigenvector = {node: eigenvector_sample.get(node, 0.0) for node in G.nodes()}
                
        except Exception as e:
            print(f"Centrality calculation error: {e}")
            degree_centrality = nx.degree_centrality(G)
            betweenness = {node: 0.0 for node in G.nodes()}
            closeness = {node: 0.0 for node in G.nodes()}
            eigenvector = {node: 0.0 for node in G.nodes()}
    else:
        degree_centrality = betweenness = closeness = eigenvector = {}
    
    # Comprehensive node scoring for maximum quality
    node_scores = {}
    for node in G.nodes():
        # Base frequency score
        freq_score = terms.get(node, 1) * 2
        
        # Centrality scores (weighted for importance)
        degree_score = degree_centrality.get(node, 0) * 100
        between_score = betweenness.get(node, 0) * 75
        close_score = closeness.get(node, 0) * 50
        eigen_score = eigenvector.get(node, 0) * 60
        
        # Quality boosts for important term types
        compound_boost = 0
        technical_boost = 0
        
        # Major boost for compound terms (AI, ML, etc.)
        compound_indicators = [
            'artificial', 'machine', 'deep', 'neural', 'natural', 'computer',
            'data', 'software', 'cloud', 'quantum', 'virtual', 'augmented',
            'digital', 'internet', 'blockchain', 'cyber', 'business', 'user'
        ]
        if any(indicator in node.lower() for indicator in compound_indicators):
            compound_boost = 30
        
        # Boost for technical terms
        technical_indicators = [
            'algorithm', 'framework', 'database', 'architecture', 'security',
            'development', 'analysis', 'system', 'platform', 'technology'
        ]
        if any(indicator in node.lower() for indicator in technical_indicators):
            technical_boost = 15
        
        # Length bonus for compound terms
        length_bonus = min(20, len(node.split()) * 10) if ' ' in node else 0
        
        total_score = (freq_score + degree_score + between_score + 
                      close_score + eigen_score + compound_boost + 
                      technical_boost + length_bonus)
        
        node_scores[node] = total_score
        centrality_scores[node] = {
            'degree': degree_centrality.get(node, 0),
            'betweenness': betweenness.get(node, 0),
            'closeness': closeness.get(node, 0),
            'eigenvector': eigenvector.get(node, 0),
            'total_score': total_score
        }
    
    # Select nodes for maximum quality (allow more nodes)
    # For quality focus, keep more nodes but ensure they're meaningful
    min_nodes = 20
    max_nodes = min(80, max(min_nodes, len(terms) // 2))  # More generous
    
    selected_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Ensure we have minimum nodes even if scores are low
    if len(selected_nodes) < min_nodes:
        selected_node_names = [node for node, score in selected_nodes]
    else:
        selected_node_names = [node for node, score in selected_nodes[:max_nodes]]
    
    # Create final subgraph
    if selected_node_names:
        subgraph = G.subgraph(selected_node_names)
        
        # Prepare high-quality output
        nodes = []
        for node in subgraph.nodes():
            centrality_data = centrality_scores.get(node, {})
            nodes.append({
                'id': node,
                'label': node.replace('_', ' ').title(),
                'size': min(60, max(15, terms.get(node, 1) * 4)),
                'frequency': terms.get(node, 1),
                'centrality': degree_centrality.get(node, 0),
                'betweenness': betweenness.get(node, 0),
                'closeness': closeness.get(node, 0),
                'eigenvector': eigenvector.get(node, 0),
                'importance': node_scores.get(node, 0),
                'type': 'compound' if ' ' in node else 'single'
            })
        
        links = []
        for edge in subgraph.edges(data=True):
            links.append({
                'source': edge[0],
                'target': edge[1],
                'weight': edge[2].get('weight', 1),
                'strength': min(15, edge[2].get('weight', 1) * 2)
            })
        
        # Enhanced insights
        insights = {
            'total_nodes': len(nodes),
            'total_links': len(links),
            'compound_terms': len([n for n in nodes if n['type'] == 'compound']),
            'single_terms': len([n for n in nodes if n['type'] == 'single']),
            'avg_centrality': sum(n['centrality'] for n in nodes) / len(nodes) if nodes else 0,
            'processing_time': time.time() - start_time
        }
        
        # Community detection for clustering insights
        try:
            if len(subgraph.nodes()) > 3:
                communities = nx.community.greedy_modularity_communities(subgraph)
                insights['total_clusters'] = len(communities)
                insights['largest_cluster'] = max(len(c) for c in communities) if communities else 0
                insights['modularity'] = nx.community.modularity(subgraph, communities)
        except Exception as e:
            insights['total_clusters'] = 1
            insights['largest_cluster'] = len(nodes)
            insights['modularity'] = 0.0
        
        total_time = time.time() - start_time
        print(f"High-quality graph built in {total_time:.2f}s: {len(nodes)} nodes, {len(links)} links")
        
        return {
            'nodes': nodes,
            'links': links,
            'insights': insights
        }
    
    return {
        'nodes': [],
        'links': [],
        'insights': {'message': 'No significant connections found'}
    }

if __name__ == "__main__":
    # Test with sample text
    test_text = """
    Artificial intelligence and machine learning are transforming technology. Deep learning uses neural networks 
    to process complex data patterns. Natural language processing enables computers to understand human language. 
    Computer vision allows machines to interpret visual information from images and videos.
    
    Data science combines statistics, machine learning, and domain knowledge to extract insights from data. 
    Software engineering involves the systematic design and development of software systems. Database management 
    provides efficient storage and retrieval of information.
    """
    
    result = build_high_quality_concept_graph(test_text)
    print(f"\nHigh-Quality Results: {len(result['nodes'])} nodes, {len(result['links'])} links")
    print("Compound terms found:", [node['label'] for node in result['nodes'] if node['type'] == 'compound'])
