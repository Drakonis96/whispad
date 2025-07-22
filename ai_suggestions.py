#!/usr/bin/env python3
"""
AI Suggestions module for generating bridge concepts, knowledge gaps, and exploration suggestions
"""
import asyncio
import json
import aiohttp
from typing import List, Dict, Any, Optional

async def generate_ai_suggestions(note_text: str, current_nodes: List[Dict], 
                                analysis_type: str = 'bridges', ai_provider: str = None, 
                                api_key: str = None, ai_model: str = None, 
                                host: str = None, port: int = None, 
                                language: str = 'english') -> List[Dict[str, Any]]:
    """Generate AI-based suggestions for bridging concepts, knowledge gaps, and exploration areas."""
    
    if not ai_provider or not current_nodes:
        return []
    
    # Handle provider format (string or dict)
    if isinstance(ai_provider, dict):
        ai_provider = ai_provider.get('provider', ai_provider.get('name', 'openai'))
    
    # Extract node labels for context
    node_labels = []
    for node in current_nodes:
        if isinstance(node, dict):
            node_labels.append(node.get('label', ''))
        else:
            node_labels.append(str(node))
    
    # Create specialized prompts for different types of suggestions
    suggestions = []
    
    # 1. Bridge Concepts Suggestion
    bridge_prompt = _create_bridge_concepts_prompt(note_text, node_labels, analysis_type, language)
    bridge_suggestion = await _get_ai_suggestion(bridge_prompt, ai_provider, api_key, ai_model, host, port)
    if bridge_suggestion:
        suggestions.append({
            "type": "bridge_concepts",
            "title": "Bridge Concepts",
            "content": bridge_suggestion,
            "concepts": _extract_concepts_from_text(bridge_suggestion, node_labels)
        })
    
    # 2. Knowledge Gaps Suggestion
    gaps_prompt = _create_knowledge_gaps_prompt(note_text, node_labels, analysis_type, language)
    gaps_suggestion = await _get_ai_suggestion(gaps_prompt, ai_provider, api_key, ai_model, host, port)
    if gaps_suggestion:
        suggestions.append({
            "type": "knowledge_gaps",
            "title": "Knowledge Gaps",
            "content": gaps_suggestion,
            "concepts": _extract_concepts_from_text(gaps_suggestion, node_labels)
        })
    
    # 3. Exploration Areas Suggestion
    exploration_prompt = _create_exploration_areas_prompt(note_text, node_labels, analysis_type, language)
    exploration_suggestion = await _get_ai_suggestion(exploration_prompt, ai_provider, api_key, ai_model, host, port)
    if exploration_suggestion:
        suggestions.append({
            "type": "exploration_areas",
            "title": "Areas to Explore",
            "content": exploration_suggestion,
            "concepts": _extract_concepts_from_text(exploration_suggestion, node_labels)
        })
    
    return suggestions

async def generate_single_ai_suggestion(note_text: str, current_nodes: List[Dict], 
                                       suggestion_type: str, analysis_type: str = 'bridges', 
                                       ai_provider: str = None, api_key: str = None, 
                                       ai_model: str = None, host: str = None, port: int = None, 
                                       language: str = 'english') -> Optional[Dict[str, Any]]:
    """Generate a single AI suggestion of the specified type."""
    
    if not ai_provider or not current_nodes:
        return None
    
    # Handle provider format (string or dict)
    if isinstance(ai_provider, dict):
        ai_provider = ai_provider.get('provider', ai_provider.get('name', 'openai'))
    
    # Extract node labels for context
    node_labels = []
    for node in current_nodes:
        if isinstance(node, dict):
            node_labels.append(node.get('label', ''))
        else:
            node_labels.append(str(node))
    
    # Create prompt based on suggestion type
    prompt = None
    title = ""
    
    if suggestion_type == "bridge_concepts":
        prompt = _create_bridge_concepts_prompt(note_text, node_labels, analysis_type, language)
        title = "Bridge Concepts"
    elif suggestion_type == "knowledge_gaps":
        prompt = _create_knowledge_gaps_prompt(note_text, node_labels, analysis_type, language)
        title = "Knowledge Gaps"
    elif suggestion_type == "exploration_areas":
        prompt = _create_exploration_areas_prompt(note_text, node_labels, analysis_type, language)
        title = "Areas to Explore"
    else:
        return None
    
    # Get AI suggestion
    suggestion_content = await _get_ai_suggestion(prompt, ai_provider, api_key, ai_model, host, port)
    
    if suggestion_content:
        return {
            "type": suggestion_type,
            "title": title,
            "content": suggestion_content,
            "concepts": _extract_concepts_from_text(suggestion_content, node_labels)
        }
    
    return None

def _create_bridge_concepts_prompt(note_text: str, node_labels: List[str], analysis_type: str, language: str) -> str:
    """Create prompt for bridge concepts suggestion."""
    if language == 'spanish':
        return f"""Analiza el siguiente texto y los conceptos identificados para sugerir CONCEPTOS PUENTE que podrían conectar ideas aparentemente separadas.

TEXTO:
{note_text[:1000]}...

CONCEPTOS ACTUALES:
{', '.join(node_labels)}

TIPO DE ANÁLISIS: {analysis_type}

TAREA:
Identifica 3-5 conceptos puente que podrían conectar los conceptos existentes y crear nuevas perspectivas. 
Estos conceptos puente deberían:
- Conectar ideas que parecen separadas
- Revelar relaciones ocultas
- Proporcionar nuevos marcos de comprensión
- Ser específicos y accionables

Responde en español con sugerencias específicas y explica por qué cada concepto puente es valioso."""
    
    return f"""Analyze the following text and identified concepts to suggest BRIDGE CONCEPTS that could connect seemingly separate ideas.

TEXT:
{note_text[:1000]}...

CURRENT CONCEPTS:
{', '.join(node_labels)}

ANALYSIS TYPE: {analysis_type}

TASK:
Identify 3-5 bridge concepts that could connect existing concepts and create new insights. 
These bridge concepts should:
- Connect ideas that seem separate
- Reveal hidden relationships
- Provide new frameworks for understanding
- Be specific and actionable

Respond with specific suggestions and explain why each bridge concept is valuable."""

def _create_knowledge_gaps_prompt(note_text: str, node_labels: List[str], analysis_type: str, language: str) -> str:
    """Create prompt for knowledge gaps suggestion."""
    if language == 'spanish':
        return f"""Analiza el siguiente texto y conceptos para identificar BRECHAS DE CONOCIMIENTO y áreas donde falta información importante.

TEXTO:
{note_text[:1000]}...

CONCEPTOS ACTUALES:
{', '.join(node_labels)}

TIPO DE ANÁLISIS: {analysis_type}

TAREA:
Identifica 3-5 brechas de conocimiento importantes que deberían ser abordadas:
- Conceptos mencionados pero no explicados completamente
- Relaciones implicadas pero no exploradas
- Contexto histórico o teórico que falta
- Aplicaciones prácticas no desarrolladas
- Comparaciones con otros enfoques

Responde en español con sugerencias específicas sobre qué investigar o explorar más."""
    
    return f"""Analyze the following text and concepts to identify KNOWLEDGE GAPS and areas where important information is missing.

TEXT:
{note_text[:1000]}...

CURRENT CONCEPTS:
{', '.join(node_labels)}

ANALYSIS TYPE: {analysis_type}

TASK:
Identify 3-5 important knowledge gaps that should be addressed:
- Concepts mentioned but not fully explained
- Relationships implied but not explored
- Missing historical or theoretical context
- Undeveloped practical applications
- Comparisons with other approaches

Respond with specific suggestions about what to research or explore further."""

def _create_exploration_areas_prompt(note_text: str, node_labels: List[str], analysis_type: str, language: str) -> str:
    """Create prompt for exploration areas suggestion."""
    if language == 'spanish':
        return f"""Basándote en el texto y conceptos analizados, sugiere ÁREAS PARA EXPLORAR que podrían expandir y enriquecer este conocimiento.

TEXTO:
{note_text[:1000]}...

CONCEPTOS ACTUALES:
{', '.join(node_labels)}

TIPO DE ANÁLISIS: {analysis_type}

TAREA:
Sugiere 3-5 áreas de exploración que podrían:
- Expandir el alcance del tema
- Conectar con disciplinas relacionadas
- Revelar aplicaciones innovadoras
- Proporcionar perspectivas alternativas
- Generar nuevas preguntas de investigación

Responde en español con sugerencias específicas y creativas sobre direcciones prometedoras para la exploración."""
    
    return f"""Based on the analyzed text and concepts, suggest AREAS TO EXPLORE that could expand and enrich this knowledge.

TEXT:
{note_text[:1000]}...

CURRENT CONCEPTS:
{', '.join(node_labels)}

ANALYSIS TYPE: {analysis_type}

TASK:
Suggest 3-5 exploration areas that could:
- Expand the scope of the topic
- Connect with related disciplines
- Reveal innovative applications
- Provide alternative perspectives
- Generate new research questions

Respond with specific and creative suggestions about promising directions for exploration."""

async def _get_ai_suggestion(prompt: str, ai_provider: str, api_key: str = None, 
                           ai_model: str = None, host: str = None, port: int = None) -> Optional[str]:
    """Get AI suggestion using the specified provider."""
    try:
        if ai_provider.lower() == 'openai':
            return await _call_openai_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'openrouter':
            return await _call_openrouter_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'google':
            return await _call_google_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'groq':
            return await _call_groq_api(prompt, api_key, ai_model)
        elif ai_provider.lower() == 'lmstudio':
            return await _call_lmstudio_api(prompt, ai_model, host, port)
        elif ai_provider.lower() == 'ollama':
            return await _call_ollama_api(prompt, ai_model, host, port)
        else:
            return None
    except Exception as e:
        print(f"Error getting AI suggestion: {e}")
        return None

async def _call_openai_api(prompt: str, api_key: str, model: str = None) -> Optional[str]:
    """Call OpenAI API for suggestions."""
    if not api_key:
        return None
    
    model = model or "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return None

async def _call_openrouter_api(prompt: str, api_key: str, model: str = None) -> Optional[str]:
    """Call OpenRouter API for suggestions."""
    if not api_key:
        return None
    
    model = model or "anthropic/claude-3.5-sonnet"
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return None

async def _call_google_api(prompt: str, api_key: str, model: str = None) -> Optional[str]:
    """Call Google Gemini API for suggestions."""
    if not api_key:
        return None
    
    model = model or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1000,
            "temperature": 0.7
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                candidates = result.get("candidates", [])
                if candidates and candidates[0].get("content", {}).get("parts"):
                    return candidates[0]["content"]["parts"][0].get("text", "").strip()
    return None

async def _call_groq_api(prompt: str, api_key: str, model: str = None) -> Optional[str]:
    """Call Groq API for suggestions."""
    if not api_key:
        return None
    
    model = model or "llama-3.1-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return None

async def _call_lmstudio_api(prompt: str, model: str, host: str, port: int) -> Optional[str]:
    """Call LM Studio API for suggestions."""
    if not host or not port:
        return None
    
    url = f"http://{host}:{port}/v1/chat/completions"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": model or "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return None

async def _call_ollama_api(prompt: str, model: str, host: str, port: int) -> Optional[str]:
    """Call Ollama API for suggestions."""
    if not host or not port:
        return None
    
    url = f"http://{host}:{port}/api/generate"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": model or "llama3.2",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("response", "").strip()
    return None

def _extract_concepts_from_text(text: str, node_labels: List[str]) -> List[str]:
    """Extract concepts that appear in the suggestion text and match node labels."""
    concepts = []
    text_lower = text.lower()
    
    for label in node_labels:
        if label and label.lower() in text_lower:
            concepts.append(label)
    
    return concepts

def _process_think_tags(text: str) -> Dict[str, str]:
    """Process /think/ tags and separate thinking from response."""
    import re
    
    # Find thinking sections
    think_pattern = r'<think>(.*?)</think>'
    thinking_matches = re.findall(think_pattern, text, re.DOTALL | re.IGNORECASE)
    
    # Remove thinking sections from response
    response_text = re.sub(think_pattern, '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Combine all thinking sections
    thinking_text = '\n'.join(thinking_matches).strip() if thinking_matches else ''
    
    return {
        'thinking': thinking_text,
        'response': response_text,
        'has_thinking': bool(thinking_text)
    }

async def generate_custom_suggestion(question: str, note_text: str, current_nodes: List[Dict],
                                   ai_provider: str = None, api_key: str = None, 
                                   ai_model: str = None, host: str = None, port: int = None,
                                   language: str = 'english') -> Optional[str]:
    """Generate a custom AI suggestion based on user question."""
    
    if not ai_provider or not question:
        return None
    
    # Handle provider format (string or dict)
    if isinstance(ai_provider, dict):
        ai_provider = ai_provider.get('provider', ai_provider.get('name', 'openai'))
    
    # Extract node labels for context
    node_labels = []
    for node in current_nodes:
        if isinstance(node, dict):
            node_labels.append(node.get('label', ''))
        else:
            node_labels.append(str(node))
    
    # Create custom prompt
    if language == 'spanish':
        prompt = f"""Basándote en el siguiente texto y conceptos, responde la pregunta del usuario de manera específica y útil.

TEXTO:
{note_text[:1000]}...

CONCEPTOS ACTUALES:
{', '.join(node_labels)}

PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES:
- Responde de manera específica y útil
- Relaciona tu respuesta con los conceptos existentes cuando sea relevante
- Proporciona ideas prácticas y accionables
- Mantén un enfoque analítico y constructivo
- Responde en español"""
    else:
        prompt = f"""Based on the following text and concepts, answer the user's question in a specific and helpful way.

TEXT:
{note_text[:1000]}...

CURRENT CONCEPTS:
{', '.join(node_labels)}

USER QUESTION:
{question}

INSTRUCTIONS:
- Answer specifically and helpfully
- Relate your answer to existing concepts when relevant
- Provide practical and actionable ideas
- Maintain an analytical and constructive focus
- Respond in English"""
    
    return await _get_ai_suggestion(prompt, ai_provider, api_key, ai_model, host, port)
