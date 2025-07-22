import asyncio
import json
import aiohttp
from concept_graph import build_graph

async def ai_reprocess_nodes(note_text, current_nodes, analysis_type='bridges', ai_provider=None, 
                           api_key=None, ai_model=None, host=None, port=None, language='english', enable_lemmatization=True):
    """Use AI to filter and select only the most important nodes from current graph."""
    if not ai_provider or not current_nodes:
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
        # Extract node labels from current nodes
        node_labels = [node['label'] if isinstance(node, dict) else str(node) for node in current_nodes]
        
        # Create AI prompt for node filtering
        if language.lower() in ['spanish', 'es', 'español']:
            prompt = f"""
            Eres un experto en análisis semántico y mapeo de conceptos. Dado el siguiente texto y lista de conceptos extraídos,
            por favor selecciona solo los 8-12 conceptos semánticamente más importantes y significativos que mejor representen las ideas centrales.

            CONTENIDO DEL TEXTO:
            {note_text[:1500]}...

            CONCEPTOS ACTUALES:
            {', '.join(node_labels)}

            TIPO DE ANÁLISIS: {analysis_type}
            {"(Enfócate en conceptos que conecten diferentes temas)" if analysis_type == 'bridges' else ""}
            {"(Enfócate en conceptos centrales como hubs)" if analysis_type == 'hubs' else ""}

            TAREA:
            1. Eliminar palabras genéricas, pronombres, verbos comunes y términos sin significado
            2. Seleccionar 8-12 conceptos semánticamente más significativos
            3. Priorizar términos específicos del dominio, nombres propios y conceptos clave
            4. Asegurar que los conceptos seleccionados representen los temas principales del texto

            REGLAS:
            - Eliminar: pronombres (tú, su, ellos, etc.), palabras genéricas (cosa, manera, tiempo), verbos comunes (hacer, tener, ser)
            - Mantener: términos técnicos, nombres propios, conceptos específicos del dominio, temas clave
            - Apuntar a máximo 8-12 conceptos finales
            - Enfocarse en conceptos que añadan valor semántico

            Responde SOLO con un array JSON de las etiquetas de conceptos seleccionados:
            ["concepto1", "concepto2", "concepto3", ...]
            """
        else:
            prompt = f"""
            You are an expert in semantic analysis and concept mapping. Given the following text and list of extracted concepts, 
            please select only the 8-12 most semantically important and meaningful concepts that best represent the core ideas.

            TEXT CONTENT:
            {note_text[:1500]}...

            CURRENT CONCEPTS:
            {', '.join(node_labels)}

            ANALYSIS TYPE: {analysis_type}
            {"(Focus on concepts that bridge different topics)" if analysis_type == 'bridges' else ""}
            {"(Focus on central hub concepts)" if analysis_type == 'hubs' else ""}

            TASK:
            1. Remove generic words, pronouns, common verbs, and non-meaningful terms
            2. Select 8-12 concepts that are most semantically significant
            3. Prioritize domain-specific terms, proper nouns, and key concepts
            4. Ensure selected concepts represent the main themes of the text

            RULES:
            - Remove: pronouns (you, his, its, they, etc.), generic words (thing, way, time), common verbs (get, make, have)
            - Keep: technical terms, proper nouns, domain-specific concepts, key themes
            - Aim for 8-12 final concepts maximum
            - Focus on concepts that add semantic value

            Respond with ONLY a JSON array of the selected concept labels:
            ["concept1", "concept2", "concept3", ...]
            """
        
        # Configure API call based on provider
        filtered_concepts = []
        
        if ai_provider.lower() == 'openai':
            filtered_concepts = await _call_openai_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'openrouter':
            filtered_concepts = await _call_openrouter_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'google':
            filtered_concepts = await _call_google_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'groq':
            filtered_concepts = await _call_groq_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'lmstudio':
            filtered_concepts = await _call_lmstudio_api(prompt, ai_model, host, port)
        elif ai_provider.lower() == 'ollama':
            filtered_concepts = await _call_ollama_api(prompt, ai_model, host, port)
        else:
            return current_nodes
        
        # Filter current nodes to only include AI-selected concepts
        if filtered_concepts:
            filtered_nodes = []
            for node in current_nodes:
                node_label = node['label'] if isinstance(node, dict) else str(node)
                # Ensure all concepts are strings and convert to lowercase safely
                safe_concepts = [str(concept).lower() for concept in filtered_concepts if concept]
                if any(concept in node_label.lower() or node_label.lower() in concept 
                       for concept in safe_concepts):
                    filtered_nodes.append(node)
            
            # Ensure we have at least a few nodes
            if len(filtered_nodes) < 3 and len(current_nodes) >= 3:
                # Fallback: return top nodes by importance if available
                sorted_nodes = sorted(current_nodes, 
                                    key=lambda x: x.get('importance', 0) if isinstance(x, dict) else 0, 
                                    reverse=True)
                return sorted_nodes[:8]
            
            return filtered_nodes[:12]  # Limit to 12 nodes max
        
        return current_nodes
        
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
                return _parse_concepts_response(content)
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
                return _parse_concepts_response(content)
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
                return _parse_concepts_response(content)
    return []

async def _call_groq_api(prompt, api_key, model=None):
    """Call Groq API for concept filtering."""
    if not model:
        model = "llama-3.1-70b-versatile"
    
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
                return _parse_concepts_response(content)
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
                return _parse_concepts_response(content)
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
                return _parse_concepts_response(content)
    return []

def _parse_concepts_response(content):
    """Parse AI response and extract concept list."""
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

def build_graph_with_selected_nodes(note_text, selected_concepts, analysis_type='bridges', language='english', enable_lemmatization=True):
    """Build a new concept graph using only the AI-selected concepts."""
    if not selected_concepts:
        # Fallback to original build_graph
        return build_graph(note_text, analysis_type, language=language, enable_lemmatization=enable_lemmatization)
    
    # Use the original build_graph function but filter results
    full_result = build_graph(note_text, analysis_type, language=language, enable_lemmatization=enable_lemmatization)
    
    if not full_result or 'nodes' not in full_result:
        return full_result
    
    # Extract concept strings from selected_concepts (handle both strings and dictionaries)
    concept_strings = []
    for concept in selected_concepts:
        if isinstance(concept, dict):
            # If it's a node dictionary, extract the label
            concept_strings.append(concept.get('label', '').lower())
        elif isinstance(concept, str):
            # If it's already a string, use it directly
            concept_strings.append(concept.lower())
        else:
            # Convert to string as fallback
            concept_strings.append(str(concept).lower())
    
    # Filter nodes to include only selected concepts
    filtered_nodes = []
    for node in full_result['nodes']:
        node_label = node.get('label', '').lower()
        if any(concept_str in node_label or node_label in concept_str 
               for concept_str in concept_strings if concept_str):
            filtered_nodes.append(node)
    
    # Filter edges to only include edges between filtered nodes
    filtered_node_ids = {node['id'] for node in filtered_nodes}
    filtered_links = []
    for link in full_result.get('links', []):
        if link['source'] in filtered_node_ids and link['target'] in filtered_node_ids:
            filtered_links.append(link)
    
    # Update the result
    result = full_result.copy()
    result['graph'] = {
        'nodes': filtered_nodes,
        'links': filtered_links
    }
    
    # Update insights to reflect the filtered graph
    if 'insights' in result:
        result['insights']['total_nodes'] = len(filtered_nodes)
        result['insights']['total_edges'] = len(filtered_links)
        if len(filtered_nodes) > 1:
            result['insights']['density'] = len(filtered_links) / (len(filtered_nodes) * (len(filtered_nodes) - 1) / 2)
        else:
            result['insights']['density'] = 0
    
    return result
