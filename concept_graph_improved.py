#!/usr/bin/env python3
"""
Improved concept graph with better term preservation
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

def extract_key_terms_improved(text: str, max_text_length: int = 75000) -> Dict[str, int]:
    """
    Improved term extraction that preserves compound terms and important concepts
    """
    # Truncate text if too long, but intelligently
    if len(text) > max_text_length:
        # Try to truncate at sentence boundaries
        sentences = re.split(r'[.!?]+', text[:max_text_length])
        if len(sentences) > 1:
            text = '. '.join(sentences[:-1]) + '.'
        else:
            text = text[:max_text_length]
    
    # Define important compound terms (technology-related)
    compound_terms = {
        'artificial intelligence': 'artificial_intelligence',
        'machine learning': 'machine_learning',
        'deep learning': 'deep_learning',
        'neural networks': 'neural_networks',
        'neural network': 'neural_network',
        'natural language processing': 'natural_language_processing',
        'computer vision': 'computer_vision',
        'data science': 'data_science',
        'software engineering': 'software_engineering',
        'database management': 'database_management',
        'cloud computing': 'cloud_computing',
        'internet of things': 'internet_of_things',
        'quantum computing': 'quantum_computing',
        'virtual reality': 'virtual_reality',
        'augmented reality': 'augmented_reality',
        'big data': 'big_data',
        'edge computing': 'edge_computing',
        'digital transformation': 'digital_transformation',
        'social media': 'social_media',
        'user experience': 'user_experience',
        'mobile computing': 'mobile_computing',
        'block chain': 'blockchain',
        'cyber security': 'cybersecurity',
        'software development': 'software_development',
        'web development': 'web_development',
        'data analysis': 'data_analysis',
        'business intelligence': 'business_intelligence',
        'project management': 'project_management',
        'quality assurance': 'quality_assurance',
    }
    
    # Replace compound terms with single tokens
    text_processed = text.lower()
    for compound, replacement in compound_terms.items():
        text_processed = re.sub(r'\b' + re.escape(compound) + r'\b', replacement, text_processed)
    
    # Extract terms using multiple methods
    term_freq = Counter()
    
    # Method 1: Preserved compound terms
    for replacement in compound_terms.values():
        count = len(re.findall(r'\b' + re.escape(replacement) + r'\b', text_processed))
        if count > 0:
            # Convert back to readable form
            readable_term = replacement.replace('_', ' ')
            term_freq[readable_term] = count
    
    # Method 2: Important single terms (technical vocabulary)
    important_terms = {
        'api', 'algorithm', 'framework', 'library', 'database', 'server', 'client',
        'frontend', 'backend', 'fullstack', 'deployment', 'testing', 'debugging',
        'optimization', 'performance', 'scalability', 'security', 'authentication',
        'authorization', 'encryption', 'protocol', 'interface', 'architecture',
        'microservices', 'monolith', 'container', 'docker', 'kubernetes',
        'automation', 'devops', 'cicd', 'git', 'repository', 'version',
        'programming', 'coding', 'development', 'engineering', 'technology',
        'innovation', 'solution', 'platform', 'system', 'application',
        'software', 'hardware', 'network', 'internet', 'web', 'mobile',
        'desktop', 'cloud', 'storage', 'memory', 'processor', 'cpu',
        'analysis', 'analytics', 'visualization', 'dashboard', 'report',
        'integration', 'migration', 'transformation', 'modernization',
    }
    
    # Extract single terms with frequency
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text_processed)
    for word in words:
        if word in important_terms:
            term_freq[word] += 1
    
    # Method 3: NLTK-based extraction for additional terms
    if nltk:
        try:
            stop_words = set(stopwords.words('english'))
            lemmatizer = WordNetLemmatizer()
            
            # Additional stopwords for technical text
            tech_stopwords = {
                'use', 'used', 'using', 'user', 'users', 'make', 'makes', 'making',
                'get', 'getting', 'take', 'taking', 'give', 'giving', 'put', 'putting',
                'go', 'going', 'come', 'coming', 'see', 'seeing', 'know', 'knowing',
                'think', 'thinking', 'work', 'working', 'help', 'helping', 'need', 'needing',
                'want', 'wanting', 'like', 'liking', 'time', 'times', 'way', 'ways',
                'thing', 'things', 'people', 'person', 'man', 'woman', 'child', 'children',
                'year', 'years', 'day', 'days', 'week', 'weeks', 'month', 'months',
                'good', 'better', 'best', 'bad', 'worse', 'worst', 'new', 'old',
                'big', 'small', 'large', 'little', 'high', 'low', 'long', 'short',
                'different', 'same', 'other', 'another', 'first', 'second', 'last',
            }
            stop_words.update(tech_stopwords)
            
            # Process remaining words
            for word in words:
                if (len(word) >= 4 and 
                    word not in stop_words and 
                    word not in important_terms and  # Already processed
                    not word.endswith('_') and  # Skip compound term tokens
                    word.isalpha()):
                    
                    lemmatized = lemmatizer.lemmatize(word)
                    if lemmatized not in stop_words and len(lemmatized) >= 3:
                        term_freq[lemmatized] += 1
        
        except Exception as e:
            print(f"NLTK processing error: {e}")
    
    # Filter terms by frequency (keep terms that appear at least 2 times or are very important)
    min_freq = 1 if len(term_freq) < 20 else 2
    filtered_terms = {term: freq for term, freq in term_freq.items() 
                     if freq >= min_freq and len(term) >= 3}
    
    # Always keep compound terms even if low frequency
    for replacement in compound_terms.values():
        readable_term = replacement.replace('_', ' ')
        if readable_term in term_freq and readable_term not in filtered_terms:
            filtered_terms[readable_term] = term_freq[readable_term]
    
    return filtered_terms

def build_concept_graph_improved(text: str, analysis_type: str = 'community') -> Dict[str, Any]:
    """
    Improved concept graph builder with better quality preservation
    """
    print(f"Building improved concept graph for {len(text)} characters...")
    start_time = time.time()
    
    # Extract terms with improved method
    terms = extract_key_terms_improved(text)
    print(f"Extracted {len(terms)} terms in {time.time() - start_time:.2f}s")
    
    if not terms:
        return {
            'nodes': [],
            'links': [],
            'insights': {'message': 'No terms extracted from text'}
        }
    
    # Build co-occurrence graph
    G = nx.Graph()
    
    # Add nodes with scores
    for term, freq in terms.items():
        G.add_node(term, weight=freq, frequency=freq)
    
    # Add edges based on co-occurrence in sentences
    sentences = re.split(r'[.!?]+', text)
    max_sentences = min(200, len(sentences))  # Limit for performance
    
    for sentence in sentences[:max_sentences]:
        sentence_lower = sentence.lower()
        sentence_terms = []
        
        # Find terms in this sentence
        for term in terms.keys():
            # Handle compound terms
            if '_' in term or ' ' in term:
                search_term = term.replace('_', ' ')
                if search_term in sentence_lower:
                    sentence_terms.append(term)
            else:
                if re.search(r'\b' + re.escape(term) + r'\b', sentence_lower):
                    sentence_terms.append(term)
        
        # Add edges between co-occurring terms
        for term1, term2 in combinations(sentence_terms, 2):
            if G.has_edge(term1, term2):
                G[term1][term2]['weight'] += 1
            else:
                G.add_edge(term1, term2, weight=1)
    
    # Calculate centrality measures
    if len(G.nodes()) > 0:
        try:
            degree_centrality = nx.degree_centrality(G)
            if len(G.nodes()) <= 100:  # Full analysis for smaller graphs
                betweenness = nx.betweenness_centrality(G)
                closeness = nx.closeness_centrality(G)
            else:  # Sampling for larger graphs
                sample_nodes = list(G.nodes())[:50]
                betweenness = nx.betweenness_centrality(G.subgraph(sample_nodes))
                closeness = nx.closeness_centrality(G.subgraph(sample_nodes))
                # Fill missing nodes with default values
                for node in G.nodes():
                    if node not in betweenness:
                        betweenness[node] = 0.0
                    if node not in closeness:
                        closeness[node] = 0.0
        except:
            # Fallback to degree centrality only
            degree_centrality = nx.degree_centrality(G)
            betweenness = {node: 0.0 for node in G.nodes()}
            closeness = {node: 0.0 for node in G.nodes()}
    else:
        degree_centrality = {}
        betweenness = {}
        closeness = {}
    
    # Select important nodes (less aggressive filtering)
    node_scores = {}
    for node in G.nodes():
        freq_score = terms.get(node, 1)
        degree_score = degree_centrality.get(node, 0) * 100
        between_score = betweenness.get(node, 0) * 50
        close_score = closeness.get(node, 0) * 25
        
        # Boost compound terms and important concepts
        compound_boost = 0
        if ' ' in node or any(word in node for word in ['artificial', 'machine', 'neural', 'quantum', 'cloud', 'cyber']):
            compound_boost = 20
        
        total_score = freq_score + degree_score + between_score + close_score + compound_boost
        node_scores[node] = total_score
    
    # Keep more nodes for better quality (top 40 instead of top 15)
    max_nodes = min(40, max(15, len(terms) // 3))
    selected_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
    selected_node_names = [node for node, score in selected_nodes]
    
    # Create subgraph with selected nodes
    if selected_node_names:
        subgraph = G.subgraph(selected_node_names)
        
        # Prepare output
        nodes = []
        for node in subgraph.nodes():
            nodes.append({
                'id': node,
                'label': node.replace('_', ' ').title(),
                'size': min(50, max(10, terms.get(node, 1) * 3)),
                'frequency': terms.get(node, 1),
                'centrality': degree_centrality.get(node, 0),
                'importance': node_scores.get(node, 0)
            })
        
        links = []
        for edge in subgraph.edges(data=True):
            links.append({
                'source': edge[0],
                'target': edge[1],
                'weight': edge[2].get('weight', 1),
                'strength': min(10, edge[2].get('weight', 1))
            })
        
        # Community detection for insights
        insights = {'total_nodes': len(nodes), 'total_links': len(links)}
        try:
            if len(subgraph.nodes()) > 2:
                communities = nx.community.greedy_modularity_communities(subgraph)
                insights['total_clusters'] = len(communities)
                insights['largest_cluster'] = max(len(c) for c in communities) if communities else 0
        except:
            insights['total_clusters'] = 1
            insights['largest_cluster'] = len(nodes)
        
        total_time = time.time() - start_time
        print(f"Graph built in {total_time:.2f}s: {len(nodes)} nodes, {len(links)} links")
        
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

# Test the improved version
if __name__ == "__main__":
    test_text = """
    Artificial intelligence and machine learning are transforming technology. Deep learning uses neural networks 
    to process complex data patterns. Natural language processing enables computers to understand human language. 
    Computer vision allows machines to interpret visual information from images and videos.
    
    Data science combines statistics, machine learning, and domain knowledge to extract insights from data. 
    Software engineering involves the systematic design and development of software systems. Database management 
    provides efficient storage and retrieval of information.
    """
    
    result = build_concept_graph_improved(test_text)
    print(f"\nResults: {len(result['nodes'])} nodes, {len(result['links'])} links")
    print("Node labels:", [node['label'] for node in result['nodes']])
