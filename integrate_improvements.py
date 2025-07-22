#!/usr/bin/env python3
"""
Integration script to update concept_graph.py with improved term extraction
"""

import re

def create_improved_extract_key_terms():
    """Create the improved extract_key_terms function"""
    return '''def extract_key_terms(text, min_length=3, max_length=25, language='english', enable_lemmatization=True, max_text_length=75000):
    """
    Improved term extraction that preserves compound terms and important concepts
    """
    from collections import Counter
    
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
        text_processed = re.sub(r'\\b' + re.escape(compound) + r'\\b', replacement, text_processed)
    
    # Extract terms using multiple methods
    term_freq = Counter()
    
    # Method 1: Preserved compound terms
    for replacement in compound_terms.values():
        count = len(re.findall(r'\\b' + re.escape(replacement) + r'\\b', text_processed))
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
    words = re.findall(r'\\b[a-zA-Z]{3,}\\b', text_processed)
    for word in words:
        if word in important_terms:
            term_freq[word] += 1
    
    # Method 3: Use existing NLTK processing if available
    stopwords = get_stopwords(language)
    if enable_lemmatization:
        try:
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
            stopwords.update(tech_stopwords)
            
            # Process remaining words
            for word in words:
                if (len(word) >= 4 and 
                    word not in stopwords and 
                    word not in important_terms and  # Already processed
                    not word.endswith('_') and  # Skip compound term tokens
                    word.isalpha() and
                    is_meaningful_word(word, language) and
                    is_content_word(word, language)):
                    
                    if enable_lemmatization:
                        lemmatized_terms = lemmatize_terms([word], language, enable_lemmatization)
                        for lemmatized in lemmatized_terms:
                            if lemmatized not in stopwords and len(lemmatized) >= 3:
                                term_freq[lemmatized] += 1
                    else:
                        term_freq[word] += 1
        
        except Exception as e:
            print(f"Advanced processing error: {e}")
    
    # Filter terms by frequency and relevance
    min_freq = 1 if len(term_freq) < 20 else 2
    filtered_terms = []
    
    for term, freq in term_freq.items():
        if (freq >= min_freq and 
            len(term) >= min_length and 
            len(term) <= max_length and
            term not in stopwords):
            filtered_terms.append(term)
    
    # Always preserve compound terms even if low frequency
    for replacement in compound_terms.values():
        readable_term = replacement.replace('_', ' ')
        if readable_term in term_freq and readable_term not in filtered_terms:
            filtered_terms.append(readable_term)
    
    return filtered_terms[:500]  # Cap at 500 terms for performance'''

def main():
    print("Creating improved extract_key_terms function...")
    improved_function = create_improved_extract_key_terms()
    
    with open('/Users/jorgepb96/Desktop/whispad-52dumn-codex-add-ai-generated-node-graph-modal/extract_key_terms_improved.py', 'w') as f:
        f.write(improved_function)
    
    print("✅ Created extract_key_terms_improved.py")
    print("Next: Manually integrate this function into concept_graph.py")

if __name__ == "__main__":
    main()
