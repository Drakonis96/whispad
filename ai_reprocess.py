import asyncio
import json
import aiohttp
from concept_graph import build_graph

async def ai_reprocess_nodes(note_text, current_nodes, analysis_type='bridges', ai_provider=None, 
                           api_key=None, ai_model=None, host=None, port=None, language='english', enable_lemmatization=True):
    """Use AI to filter out unimportant terms from the original text and regenerate the entire graph."""
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
        
        # Step 1: Extract ALL terms from the original text (not just current nodes)
        # This gives us the complete vocabulary before AI filtering
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
        
        # Step 2: Create AI prompt for term filtering (remove non-important words)
        if language.lower() in ['spanish', 'es', 'español']:
            prompt = f"""
            Eres un experto en análisis semántico y procesamiento de lenguaje natural. Tu tarea es filtrar términos extraídos de un texto para crear un grafo de conceptos de alta calidad.

            CONTENIDO DEL TEXTO:
            {note_text[:1500]}...

            TÉRMINOS EXTRAÍDOS DEL TEXTO:
            {', '.join(term_list[:100])}

            TAREA:
            Filtra la lista de términos para ELIMINAR palabras que NO son conceptos importantes para un grafo de conocimiento:

            ELIMINAR:
            - Artículos: el, la, los, las, un, una, etc.
            - Pronombres: yo, tú, él, ella, nosotros, ellos, esto, eso, etc.
            - Verbos comunes: ser, estar, tener, hacer, ir, venir, etc.
            - Preposiciones: de, en, a, por, para, con, sin, etc.
            - Conjunciones: y, o, pero, si, que, como, etc.
            - Adverbios genéricos: muy, más, menos, bien, mal, etc.
            - Adjetivos vagos: bueno, malo, grande, pequeño, etc.
            - Palabras funcionales sin significado semántico

            MANTENER:
            - Sustantivos conceptuales importantes
            - Nombres propios
            - Términos técnicos y específicos del dominio
            - Conceptos clave del tema
            - Entidades nombradas
            - Términos compuestos importantes

            Responde SOLO con un array JSON de los términos que DEBEN MANTENERSE (los conceptos importantes):
            ["concepto1", "concepto2", "concepto3", ...]
            """
        else:
            prompt = f"""
            You are an expert in semantic analysis and natural language processing. Your task is to filter extracted terms from a text to create a high-quality concept graph.

            TEXT CONTENT:
            {note_text[:1500]}...

            EXTRACTED TERMS FROM TEXT:
            {', '.join(term_list[:100])}

            TASK:
            Filter the term list to REMOVE words that are NOT important concepts for a knowledge graph:

            REMOVE:
            - Articles: the, a, an, this, that, these, those, etc.
            - Pronouns: I, you, he, she, it, we, they, etc.
            - Common verbs: be, have, do, get, make, go, come, etc.
            - Prepositions: of, in, to, for, with, by, from, etc.
            - Conjunctions: and, or, but, if, when, while, etc.
            - Generic adverbs: very, more, most, well, etc.
            - Vague adjectives: good, bad, big, small, etc.
            - Function words without semantic meaning

            KEEP:
            - Important conceptual nouns
            - Proper names
            - Technical and domain-specific terms
            - Key concepts of the topic
            - Named entities
            - Important compound terms

            Respond with ONLY a JSON array of terms that SHOULD BE KEPT (the important concepts):
            ["concept1", "concept2", "concept3", ...]
            """
        
        # Configure API call based on provider
        filtered_terms = []
        
        if ai_provider.lower() == 'openai':
            filtered_terms = await _call_openai_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'openrouter':
            filtered_terms = await _call_openrouter_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'google':
            filtered_terms = await _call_google_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'groq':
            filtered_terms = await _call_groq_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'lmstudio':
            filtered_terms = await _call_lmstudio_api(prompt, ai_model, host, port)
        elif ai_provider.lower() == 'ollama':
            filtered_terms = await _call_ollama_api(prompt, ai_model, host, port)
        else:
            return current_nodes
        
        # Step 3: Use filtered terms as stop word exclusions to regenerate graph
        if filtered_terms:
            # The AI-filtered terms become our "important terms" 
            # Terms NOT in this list are treated as stop words (filtered out)
            print(f"🤖 AI filtered {len(term_list)} terms → {len(filtered_terms)} important terms")
            return filtered_terms  # Return the AI-filtered terms
        
        return current_nodes  # Fallback to current nodes if AI filtering fails
        
    except Exception as e:
        print(f"AI reprocessing error: {str(e)}")
        return current_nodes

async def _call_openai_api(prompt, api_key, model=None):
    """Call OpenAI API for concept filtering."""
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
        "max_tokens": 500,
        "temperature": 0.2
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_filtering_response(content)
    return []

async def _call_openrouter_api(prompt, api_key, model=None):
    """Call OpenRouter API for concept filtering."""
    if not model:
        model = "meta-llama/llama-3.1-8b-instruct:free"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://whispad.local",
        "X-Title": "WhisPad AI"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.2
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_filtering_response(content)
    return []

async def _call_google_api(prompt, api_key, model=None):
    """Call Google Gemini API for concept filtering."""
    if not model:
        model = "gemini-2.0-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                return _parse_filtering_response(content)
    return []

async def _call_groq_api(prompt, api_key, model=None):
    """Call Groq API for concept filtering."""
    if not model:
        model = "llama3-8b-8192"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.2
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_filtering_response(content)
    return []

async def _call_lmstudio_api(prompt, model, host, port):
    """Call LM Studio API for concept filtering."""
    url = f"http://{host}:{port}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": model or "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.2
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return _parse_filtering_response(content)
    return []

async def _call_ollama_api(prompt, model, host, port):
    """Call Ollama API for concept filtering."""
    url = f"http://{host}:{port}/api/chat"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": model or "llama3",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                content = result["message"]["content"]
                return _parse_filtering_response(content)
    return []

def _parse_filtering_response(content):
    """Parse AI response and extract filtered terms list."""
    try:
        # Try to find JSON array in the response
        import re
        
        # Look for JSON array pattern
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            concepts = json.loads(json_str)
            if isinstance(concepts, list):
                # Ensure all concepts are strings and non-empty
                return [str(concept).strip() for concept in concepts if concept and str(concept).strip()]
        
        # Fallback: try to parse as JSON directly
        concepts = json.loads(content)
        if isinstance(concepts, list):
            # Ensure all concepts are strings and non-empty
            return [str(concept).strip() for concept in concepts if concept and str(concept).strip()]
            
    except (json.JSONDecodeError, AttributeError):
        # Fallback: extract concepts from text manually
        lines = content.strip().split('\n')
        concepts = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                concepts.append(line[1:-1])
            elif line.startswith('- '):
                concepts.append(line[2:])
        # Ensure all concepts are strings and non-empty
        return [str(concept).strip() for concept in concepts if concept and str(concept).strip()][:12]
    
    return []

def build_graph_with_selected_nodes(note_text, selected_terms, analysis_type='bridges', language='english', enable_lemmatization=True):
    """Build a new concept graph using only the AI-filtered terms (excluding filtered-out terms)."""
    if not selected_terms:
        # Fallback to original build_graph
        from concept_graph import build_graph
        return build_graph(note_text, analysis_type, language=language, enable_lemmatization=enable_lemmatization)
    
    # Use the selected terms as inclusions and create exclusions list from all other terms
    from concept_graph import build_graph, extract_high_quality_terms
    
    # Step 1: Extract all terms from the text
    language_param = 'spanish' if language.lower() in ['spanish', 'es', 'español'] else 'english'
    all_extracted_terms = extract_high_quality_terms(
        note_text, 
        language=language_param, 
        enable_lemmatization=enable_lemmatization,
        max_text_length=200000
    )
    
    # Convert to list format if it's a dict
    if isinstance(all_extracted_terms, dict):
        all_terms_list = list(all_extracted_terms.keys())
    else:
        all_terms_list = all_extracted_terms
    
    # Step 2: Create exclusions list (terms NOT selected by AI become stop words)
    selected_terms_lower = [term.lower().strip() for term in selected_terms if term]
    exclusions = []
    
    for term in all_terms_list:
        term_lower = term.lower().strip()
        # If this term wasn't selected by AI, add it to exclusions
        if not any(selected_term in term_lower or term_lower in selected_term 
                  for selected_term in selected_terms_lower):
            exclusions.append(term)
    
    print(f"🎯 Building graph with {len(selected_terms)} AI-selected terms, excluding {len(exclusions)} filtered terms")
    
    # Step 3: Build graph with AI-selected terms as inclusions and filtered terms as exclusions
    result = build_graph(
        note_text, 
        analysis_type=analysis_type, 
        language=language_param, 
        enable_lemmatization=enable_lemmatization,
        inclusions=selected_terms,  # Prioritize AI-selected terms
        exclusions=exclusions       # Exclude terms filtered out by AI
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
