import asyncio
import json
import aiohttp
from concept_graph import build_graph

async def ai_reprocess_nodes(note_text, current_nodes, analysis_type='bridges', ai_provider=None, 
                           api_key=None, ai_model=None, host=None, port=None):
    """Use AI to filter and select only the most important nodes from current graph."""
    if not ai_provider or not current_nodes:
        return current_nodes
    
    # Validate parameters based on provider
    if ai_provider in ['openai', 'openrouter', 'google', 'groq'] and not api_key:
        return current_nodes
    
    if ai_provider in ['lmstudio', 'ollama'] and (not host or not port):
        return current_nodes
    
    try:
        # Extract node labels from current nodes
        node_labels = [node['label'] if isinstance(node, dict) else str(node) for node in current_nodes]
        
        # Create AI prompt for node filtering
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
                if any(concept.lower() in node_label.lower() or node_label.lower() in concept.lower() 
                       for concept in filtered_concepts):
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
                return [str(concept).strip() for concept in concepts if concept]
        
        # Fallback: try to parse as JSON directly
        concepts = json.loads(content)
        if isinstance(concepts, list):
            return [str(concept).strip() for concept in concepts if concept]
            
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
        return concepts[:12]
    
    return []

def build_graph_with_selected_nodes(note_text, selected_concepts, analysis_type='bridges'):
    """Build a new concept graph using only the AI-selected concepts."""
    if not selected_concepts:
        # Fallback to original build_graph
        return build_graph(note_text, analysis_type)
    
    # Use the original build_graph function but filter results
    full_result = build_graph(note_text, analysis_type)
    
    if not full_result or 'nodes' not in full_result:
        return full_result
    
    # Filter nodes to include only selected concepts
    filtered_nodes = []
    for node in full_result['nodes']:
        node_label = node.get('label', '').lower()
        if any(concept.lower() in node_label or node_label in concept.lower() 
               for concept in selected_concepts):
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
