import asyncio
import json
import aiohttp
from concept_graph import build_graph

async def ai_reprocess_nodes(note_text, current_nodes, analysis_type='bridges', ai_provider=None, 
                           api_key=None, ai_model=None, host=None, port=None, language='english', enable_lemmatization=True):
    """Use AI to filter out ONLY stop words (prepositions, verbs, pronouns, adjectives) and regenerate the entire graph."""
    if not ai_provider:
        return current_nodes
    
    # Ensure ai_provider is a string
    if isinstance(ai_provider, dict):
        # If ai_provider is a dict, try to extract the actual provider name
        ai_provider = ai_provider.get('provider') or ai_provider.get('name') or str(ai_provider)
    
    ai_provider = str(ai_provider).strip()
    
    # Validate parameters based on provider
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return current_nodes
    
    if ai_provider in ['lmstudio', 'ollama'] and (not host or not port):
        return current_nodes
    
    try:
        # Import the term extraction function
        from concept_graph import extract_high_quality_terms
        
        # Step 1: Extract ALL terms from the original text
        language_param = 'spanish' if language.lower() in ['spanish', 'es', 'español'] else 'english'
        all_extracted_terms = extract_high_quality_terms(
            note_text, 
            language=language_param, 
            enable_lemmatization=enable_lemmatization,
            max_text_length=200000
        )
        
        # Convert to list format if it's a dict
        if isinstance(all_extracted_terms, dict):
            term_list = list(all_extracted_terms.keys())
        else:
            term_list = all_extracted_terms
        
        if not term_list:
            return current_nodes
        
        # Step 2: Create AI prompt for STOP WORD identification (words to REMOVE)
        if language.lower() in ['spanish', 'es', 'español']:
            prompt = f"""
            Eres un experto en análisis lingüístico. Tu tarea es identificar únicamente las palabras que son palabras funcionales (stop words) que deben ser ELIMINADAS de una lista de términos extraídos.

            CONTENIDO DEL TEXTO (para contexto):
            {note_text[:1000]}...

            TÉRMINOS EXTRAÍDOS DEL TEXTO:
            {', '.join(term_list[:120])}

            TAREA ESPECÍFICA:
            Identifica ÚNICAMENTE las palabras que son palabras funcionales sin significado conceptual importante:

            ELIMINAR SOLO:
            - Preposiciones: de, en, a, por, para, con, sin, desde, hasta, sobre, bajo, ante, tras, durante, mediante, según, entre, contra, etc.
            - Verbos auxiliares/comunes: ser, estar, tener, haber, hacer, ir, venir, poder, deber, querer, decir, ver, dar, saber, etc.
            - Pronombres: yo, tú, él, ella, nosotros, vosotros, ellos, ellas, me, te, se, nos, os, les, esto, eso, aquello, etc.
            - Adjetivos muy genéricos: bueno, malo, grande, pequeño, nuevo, viejo, mucho, poco, más, menos, mejor, peor, etc.
            - Artículos: el, la, los, las, un, una, unos, unas
            - Conjunciones: y, o, pero, si, que, como, cuando, donde, etc.

            NO ELIMINAR (mantener todos estos):
            - Sustantivos conceptuales (objetos, personas, lugares, ideas)
            - Nombres propios
            - Términos técnicos y específicos
            - Números y fechas
            - Adjetivos descriptivos específicos e importantes
            - Verbos principales con significado conceptual

            Es mejor ser CONSERVADOR y mantener palabras dudosas que eliminar conceptos importantes.

            Responde SOLO con un array JSON de las palabras que DEBEN SER ELIMINADAS (stop words):
            ["palabra1", "palabra2", "palabra3", ...]
            """
        else:
            prompt = f"""
            You are a linguistic analysis expert. Your task is to identify only the functional words (stop words) that should be REMOVED from a list of extracted terms.

            TEXT CONTENT (for context):
            {note_text[:1000]}...

            EXTRACTED TERMS FROM TEXT:
            {', '.join(term_list[:120])}

            SPECIFIC TASK:
            Identify ONLY words that are functional words without important conceptual meaning:

            REMOVE ONLY:
            - Prepositions: of, in, to, for, with, by, from, at, on, under, over, through, during, before, after, etc.
            - Auxiliary/common verbs: be, is, are, was, were, have, has, had, do, does, did, will, would, can, could, should, etc.
            - Pronouns: I, you, he, she, it, we, they, me, him, her, us, them, this, that, these, those, etc.
            - Very generic adjectives: good, bad, big, small, new, old, much, many, more, most, less, better, worse, etc.
            - Articles: the, a, an
            - Conjunctions: and, or, but, if, when, where, how, why, etc.

            DO NOT REMOVE (keep all these):
            - Conceptual nouns (objects, people, places, ideas)
            - Proper names
            - Technical and specific terms
            - Numbers and dates
            - Specific and important descriptive adjectives
            - Main verbs with conceptual meaning

            It's better to be CONSERVATIVE and keep doubtful words than to remove important concepts.

            Respond with ONLY a JSON array of words that SHOULD BE REMOVED (stop words):
            ["word1", "word2", "word3", ...]
            """
        
        # Configure API call based on provider
        stop_words_to_remove = []
        
        if ai_provider.lower() == 'openai':
            stop_words_to_remove = await _call_openai_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'openrouter':
            stop_words_to_remove = await _call_openrouter_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'google':
            stop_words_to_remove = await _call_google_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'groq':
            stop_words_to_remove = await _call_groq_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'lmstudio':
            stop_words_to_remove = await _call_lmstudio_api(prompt, ai_model, host, port)
        elif ai_provider.lower() == 'ollama':
            stop_words_to_remove = await _call_ollama_api(prompt, ai_model, host, port)
        else:
            return current_nodes
        
        # Step 3: Filter out ONLY the AI-identified stop words
        if stop_words_to_remove:
            stop_words_lower = [word.lower().strip() for word in stop_words_to_remove]
            filtered_terms = []
            
            for term in term_list:
                term_lower = term.lower().strip()
                # Only remove if the term is exactly in the stop words list
                if term_lower not in stop_words_lower:
                    filtered_terms.append(term)
            
            print(f"🤖 AI identified {len(stop_words_to_remove)} stop words to remove from {len(term_list)} terms → {len(filtered_terms)} remaining")
            print(f"🚫 Removed stop words: {', '.join(stop_words_to_remove[:10])}")
            
            return filtered_terms  # Return the filtered terms (with stop words removed)
        
        return term_list  # Return original terms if no stop words identified
        
    except Exception as e:
        print(f"AI reprocessing error: {str(e)}")
        return current_nodes

async def _call_openai_api(prompt, api_key, model=None):
    """Call OpenAI API for stop word identification."""
    if not model:
        model = "gpt-4o-mini"
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_stop_words_response(content)
    return []

async def _call_openrouter_api(prompt, api_key, model=None):
    """Call OpenRouter API for stop word identification."""
    if not model:
        model = "meta-llama/llama-3.1-8b-instruct:free"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_stop_words_response(content)
    return []

async def _call_google_api(prompt, api_key, model=None):
    """Call Google Gemini API for stop word identification."""
    if not model:
        model = "gemini-1.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 800
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                if 'candidates' in result and result['candidates']:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return _parse_stop_words_response(content)
    return []

async def _call_groq_api(prompt, api_key, model=None):
    """Call Groq API for stop word identification."""
    if not model:
        model = "llama-3.3-70b-versatile"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_stop_words_response(content)
    return []

async def _call_lmstudio_api(prompt, model, host, port):
    """Call LM Studio API for stop word identification."""
    url = f"http://{host}:{port}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_stop_words_response(content)
    return []

async def _call_ollama_api(prompt, model, host, port):
    """Call Ollama API for stop word identification."""
    url = f"http://{host}:{port}/api/generate"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 800}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result.get("response", "")
                return _parse_stop_words_response(content)
    return []

def _parse_stop_words_response(content):
    """Parse AI response and extract stop words list."""
    try:
        import re
        
        # Try to find JSON array in the response
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            stop_words = json.loads(json_str)
            if isinstance(stop_words, list):
                return [str(word).strip().lower() for word in stop_words if word and str(word).strip()]
        
        # Fallback: try to parse as JSON directly
        stop_words = json.loads(content)
        if isinstance(stop_words, list):
            return [str(word).strip().lower() for word in stop_words if word and str(word).strip()]
            
    except (json.JSONDecodeError, AttributeError):
        # Fallback: extract stop words from text manually
        lines = content.strip().split('\n')
        stop_words = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                stop_words.append(line[1:-1].lower())
            elif line.startswith('- '):
                stop_words.append(line[2:].lower())
            elif ',' in line and '[' not in line:
                # Handle comma-separated list
                words = [w.strip().lower().strip('"\'') for w in line.split(',')]
                stop_words.extend([w for w in words if w and len(w) > 1])
        
        return stop_words[:50]  # Limit to reasonable number
    
    return []

def build_graph_with_selected_nodes(note_text, filtered_terms, analysis_type='bridges', language='english', enable_lemmatization=True):
    """Build a new concept graph using the AI-filtered terms (with stop words removed)."""
    if not filtered_terms:
        # Fallback to original build_graph
        from concept_graph import build_graph
        return build_graph(note_text, analysis_type, language=language, enable_lemmatization=enable_lemmatization)
    
    # Build graph with the filtered terms (stop words have been removed)
    from concept_graph import build_graph
    
    language_param = 'spanish' if language.lower() in ['spanish', 'es', 'español'] else 'english'
    
    print(f"🎯 Building graph with {len(filtered_terms)} AI-filtered terms (stop words removed)")
    
    # Build graph with the filtered terms as inclusions (stop words excluded)
    result = build_graph(
        note_text, 
        analysis_type=analysis_type, 
        language=language_param, 
        enable_lemmatization=enable_lemmatization,
        inclusions=filtered_terms  # Use the AI-filtered terms (stop words removed)
    )
    
    # Wrap result in expected format for the API
    if 'graph' not in result:
        result = {
            'graph': {
                'nodes': result.get('nodes', []),
                'links': result.get('links', [])
            },
            'insights': result.get('insights', {})
        }
    
    return result
