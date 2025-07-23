import asyncio
import json
import re
from groq import AsyncGroq

async def ai_filter_stop_words(note_text, all_terms, language='english', api_key=None, model='llama-3.3-70b-versatile'):
    """
    Use AI to identify ONLY stop words (prepositions, verbs, pronouns, adjectives) 
    to be REMOVED from the terms list, keeping all other words intact.
    """
    if not api_key or not all_terms:
        return []
    
    # Limit terms to process to avoid token limits
    terms_to_process = all_terms[:150] if len(all_terms) > 150 else all_terms
    
    # Create AI prompt that focuses ONLY on identifying stop words to remove
    if language.lower() in ['spanish', 'es', 'español']:
        prompt = f"""
        Eres un experto en análisis lingüístico. Tu tarea es identificar únicamente las palabras que deben ser ELIMINADAS de una lista de términos extraídos de un texto.

        TEXTO ORIGINAL (para contexto):
        {note_text[:800]}...

        TÉRMINOS EXTRAÍDOS:
        {', '.join(terms_to_process)}

        TAREA ESPECÍFICA:
        Identifica ÚNICAMENTE las palabras que son:
        1. Preposiciones: de, en, a, por, para, con, sin, desde, hasta, sobre, bajo, ante, tras, durante, mediante, según, etc.
        2. Verbos comunes/auxiliares: ser, estar, tener, haber, hacer, ir, venir, poder, deber, querer, decir, ver, dar, etc.
        3. Pronombres: yo, tú, él, ella, nosotros, vosotros, ellos, ellas, me, te, se, nos, os, les, esto, eso, aquello, etc.
        4. Adjetivos muy genéricos/vagos: bueno, malo, grande, pequeño, nuevo, viejo, mucho, poco, más, menos, etc.
        
        NO ELIMINAR:
        - Sustantivos (conceptos, objetos, personas, lugares)
        - Nombres propios
        - Términos técnicos o específicos
        - Números y fechas
        - Adjetivos específicos y descriptivos importantes
        - Cualquier palabra con significado conceptual relevante

        Responde SOLO con un array JSON de las palabras que DEBEN SER ELIMINADAS:
        ["palabra1", "palabra2", "palabra3", ...]
        """
    else:
        prompt = f"""
        You are a linguistic analysis expert. Your task is to identify ONLY the words that should be REMOVED from a list of terms extracted from text.

        ORIGINAL TEXT (for context):
        {note_text[:800]}...

        EXTRACTED TERMS:
        {', '.join(terms_to_process)}

        SPECIFIC TASK:
        Identify ONLY words that are:
        1. Prepositions: of, in, to, for, with, by, from, at, on, under, over, through, during, before, after, etc.
        2. Common/auxiliary verbs: be, is, are, was, were, have, has, had, do, does, did, will, would, can, could, should, etc.
        3. Pronouns: I, you, he, she, it, we, they, me, him, her, us, them, this, that, these, those, etc.
        4. Very generic/vague adjectives: good, bad, big, small, new, old, much, many, more, most, less, etc.

        DO NOT REMOVE:
        - Nouns (concepts, objects, people, places)
        - Proper names
        - Technical or specific terms
        - Numbers and dates
        - Specific and important descriptive adjectives
        - Any word with relevant conceptual meaning

        Respond with ONLY a JSON array of words that SHOULD BE REMOVED:
        ["word1", "word2", "word3", ...]
        """
    
    try:
        client = AsyncGroq(api_key=api_key)
        
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=model,
            temperature=0.1,
            max_tokens=800,
        )
        
        content = chat_completion.choices[0].message.content
        return _parse_stop_words_response(content)
        
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}")
        return []

def _parse_stop_words_response(content):
    """Parse AI response and extract stop words list."""
    try:
        # Try to find JSON array in the response
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            stop_words = json.loads(json_str)
            if isinstance(stop_words, list):
                return [str(word).strip().lower() for word in stop_words if word]
        
        # Fallback: try to parse as JSON directly
        stop_words = json.loads(content)
        if isinstance(stop_words, list):
            return [str(word).strip().lower() for word in stop_words if word]
            
    except (json.JSONDecodeError, AttributeError):
        # Fallback: extract from text manually
        lines = content.strip().split('\n')
        stop_words = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                stop_words.append(line[1:-1].lower())
            elif line.startswith('- '):
                stop_words.append(line[2:].lower())
            elif ',' in line:
                # Handle comma-separated list
                words = [w.strip().lower() for w in line.split(',')]
                stop_words.extend([w for w in words if w and not w.startswith('[') and not w.endswith(']')])
        
        return stop_words[:50]  # Limit to reasonable number
    
    return []

def apply_stop_word_filter(original_terms, stop_words_to_remove):
    """
    Filter out only the AI-identified stop words, keeping all other terms.
    """
    if not stop_words_to_remove:
        return original_terms
    
    stop_words_lower = [word.lower() for word in stop_words_to_remove]
    filtered_terms = []
    
    for term in original_terms:
        term_lower = term.lower().strip()
        # Only remove if the term is exactly in the stop words list
        if term_lower not in stop_words_lower:
            filtered_terms.append(term)
    
    return filtered_terms

# Test function to simulate the concept graph term extraction
def mock_extract_terms(text, language='english'):
    """
    Mock function to simulate term extraction.
    In real implementation, this would call the actual concept_graph.extract_high_quality_terms
    """
    # Simple word extraction for testing
    import string
    words = text.translate(str.maketrans('', '', string.punctuation)).split()
    # Remove very short words and duplicates
    terms = list(set([word for word in words if len(word) > 2]))
    return terms

async def test_ai_reprocessing(sample_text, language='english', api_key=None):
    """Test the improved AI reprocessing functionality."""
    print("🔍 Testing AI Stop Word Filtering")
    print(f"📝 Sample text: {sample_text[:100]}...")
    print(f"🌐 Language: {language}")
    
    # Step 1: Extract all terms (mock implementation)
    all_terms = mock_extract_terms(sample_text, language)
    print(f"📊 Extracted {len(all_terms)} terms: {', '.join(all_terms[:20])}...")
    
    # Step 2: Use AI to identify stop words to remove
    stop_words = await ai_filter_stop_words(sample_text, all_terms, language, api_key)
    print(f"🚫 AI identified {len(stop_words)} stop words to remove: {', '.join(stop_words[:15])}...")
    
    # Step 3: Apply filter (remove only the stop words)
    filtered_terms = apply_stop_word_filter(all_terms, stop_words)
    print(f"✅ Final filtered terms ({len(filtered_terms)} remaining): {', '.join(filtered_terms[:20])}...")
    
    # Statistics
    removed_count = len(all_terms) - len(filtered_terms)
    retention_rate = (len(filtered_terms) / len(all_terms)) * 100 if all_terms else 0
    
    print(f"\n📈 Results:")
    print(f"   Original terms: {len(all_terms)}")
    print(f"   Removed terms: {removed_count}")
    print(f"   Remaining terms: {len(filtered_terms)}")
    print(f"   Retention rate: {retention_rate:.1f}%")
    
    return {
        'original_terms': all_terms,
        'stop_words': stop_words,
        'filtered_terms': filtered_terms,
        'retention_rate': retention_rate
    }

if __name__ == "__main__":
    # Test with sample text
    sample_en = """
    Artificial intelligence is a rapidly evolving field that encompasses machine learning, 
    natural language processing, and computer vision. Many researchers are working on 
    developing new algorithms and models to improve the performance of AI systems.
    """
    
    sample_es = """
    La inteligencia artificial es un campo que evoluciona rápidamente y que abarca el 
    aprendizaje automático, el procesamiento de lenguaje natural y la visión por computadora. 
    Muchos investigadores están trabajando en el desarrollo de nuevos algoritmos y modelos.
    """
    
    # You need to set your GROQ_API_KEY environment variable or replace with actual key
    import os
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("⚠️  Please set GROQ_API_KEY environment variable to test with Groq API")
        print("Example: export GROQ_API_KEY='your_api_key_here'")
    else:
        print("🧪 Testing with English text...")
        asyncio.run(test_ai_reprocessing(sample_en, 'english', api_key))
        
        print("\n" + "="*50 + "\n")
        
        print("🧪 Testing with Spanish text...")
        asyncio.run(test_ai_reprocessing(sample_es, 'spanish', api_key))
