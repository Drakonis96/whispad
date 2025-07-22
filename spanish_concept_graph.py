#!/usr/bin/env python3
"""
Improved Spanish-aware concept graph with better lemmatization and filtering
"""

import networkx as nx
import re
import time
from collections import defaultdict, Counter
from itertools import combinations
from typing import Dict, List, Set, Tuple, Any

# Enhanced Spanish stopwords with more comprehensive coverage
SPANISH_STOPWORDS_COMPREHENSIVE = {
    # Articles
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
    
    # Pronouns
    'yo', 'tú', 'él', 'ella', 'nosotros', 'nosotras', 'vosotros', 'vosotras', 
    'ellos', 'ellas', 'me', 'te', 'se', 'nos', 'os', 'le', 'lo', 'la', 'les',
    'que', 'quien', 'quienes', 'cual', 'cuales', 'esto', 'esta', 'este', 'estos', 'estas',
    'eso', 'esa', 'ese', 'esos', 'esas', 'aquello', 'aquella', 'aquel', 'aquellos', 'aquellas',
    
    # Prepositions (critical for Spanish)
    'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde', 'durante', 'en', 
    'entre', 'hacia', 'hasta', 'mediante', 'para', 'por', 'según', 'sin', 'so', 
    'sobre', 'tras', 'versus', 'vía',
    
    # Conjunctions
    'y', 'e', 'ni', 'o', 'u', 'pero', 'mas', 'sino', 'que', 'porque', 'pues', 
    'aunque', 'si', 'como', 'cuando', 'donde', 'mientras', 'ya',
    
    # Common verbs (auxiliary and modal)
    'ser', 'estar', 'haber', 'tener', 'hacer', 'ir', 'venir', 'dar', 'decir', 
    'poder', 'deber', 'querer', 'saber', 'ver', 'poner', 'salir', 'llegar', 
    'pasar', 'seguir', 'quedar', 'creer', 'llevar', 'dejar', 'sentir', 'volver',
    'encontrar', 'parecer', 'trabajar', 'empezar', 'esperar', 'buscar', 'existir',
    'entrar', 'hablar', 'abrir', 'cerrar', 'vivir', 'morir', 'nacer', 'crecer',
    
    # Adverbs
    'no', 'sí', 'también', 'tampoco', 'muy', 'más', 'menos', 'tan', 'tanto', 
    'bastante', 'poco', 'mucho', 'demasiado', 'algo', 'nada', 'todo', 'siempre',
    'nunca', 'jamás', 'quizás', 'acaso', 'bien', 'mal', 'mejor', 'peor', 'ahora',
    'antes', 'después', 'luego', 'entonces', 'aquí', 'ahí', 'allí', 'allá',
    'donde', 'adonde', 'cuando', 'como', 'así', 'solo', 'solamente', 'únicamente',
    
    # Time expressions
    'hoy', 'ayer', 'mañana', 'tarde', 'temprano', 'pronto', 'ahora', 'antes', 
    'después', 'luego', 'entonces', 'mientras', 'durante', 'hasta', 'desde',
    
    # Numbers
    'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 
    'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'veinte',
    'treinta', 'cuarenta', 'cincuenta', 'cien', 'mil', 'millón',
    
    # Common adjectives that don't add semantic value
    'grande', 'pequeño', 'nuevo', 'viejo', 'bueno', 'malo', 'primero', 'último',
    'mismo', 'otro', 'otra', 'otros', 'otras', 'todo', 'toda', 'todos', 'todas',
    'alguno', 'alguna', 'algunos', 'algunas', 'ninguno', 'ninguna', 'cada', 'cualquier',
    
    # Common expressions
    'por favor', 'gracias', 'de nada', 'por ejemplo', 'es decir', 'sin embargo',
    'por tanto', 'por eso', 'además', 'tal vez', 'quizás', 'sin duda',
    
    # Verb forms that appear frequently
    'es', 'son', 'está', 'están', 'fue', 'fueron', 'era', 'eran', 'sea', 'sean',
    'ha', 'han', 'había', 'habían', 'habrá', 'habrán', 'tiene', 'tienen', 'tenía',
    'tenían', 'tuvo', 'tuvieron', 'hace', 'hacen', 'hacía', 'hacían', 'hizo', 'hicieron',
    'va', 'van', 'iba', 'iban', 'fue', 'fueron', 'irá', 'irán', 'viene', 'vienen',
    'venía', 'venían', 'vino', 'vinieron', 'vendrá', 'vendrán', 'da', 'dan', 'daba',
    'daban', 'dio', 'dieron', 'dará', 'darán', 'dice', 'dicen', 'decía', 'decían',
    'dijo', 'dijeron', 'dirá', 'dirán', 'puede', 'pueden', 'podía', 'podían',
    'pudo', 'pudieron', 'podrá', 'podrán', 'debe', 'deben', 'debía', 'debían',
    'debió', 'debieron', 'deberá', 'deberán',
}

def simple_spanish_lemmatizer(word: str) -> str:
    """
    Simple Spanish lemmatizer for common patterns
    """
    word = word.lower().strip()
    
    # Common verb endings to infinitive
    verb_patterns = [
        # Present tense
        (r'(.+)amos$', r'\1ar'),  # hablamos -> hablar
        (r'(.+)áis$', r'\1ar'),   # habláis -> hablar
        (r'(.+)an$', r'\1ar'),    # hablan -> hablar
        (r'(.+)as$', r'\1ar'),    # hablas -> hablar
        (r'(.+)a$', r'\1ar'),     # habla -> hablar (careful with nouns)
        (r'(.+)emos$', r'\1er'),  # comemos -> comer
        (r'(.+)éis$', r'\1er'),   # coméis -> comer
        (r'(.+)en$', r'\1er'),    # comen -> comer
        (r'(.+)es$', r'\1er'),    # comes -> comer
        (r'(.+)e$', r'\1er'),     # come -> comer (careful with nouns)
        (r'(.+)imos$', r'\1ir'),  # vivimos -> vivir
        (r'(.+)ís$', r'\1ir'),    # vivís -> vivir
        (r'(.+)en$', r'\1ir'),    # viven -> vivir (conflicts with -er)
        
        # Past tense
        (r'(.+)ó$', r'\1ar'),     # habló -> hablar
        (r'(.+)aron$', r'\1ar'),  # hablaron -> hablar
        (r'(.+)ió$', r'\1ir'),    # vivió -> vivir
        (r'(.+)ieron$', r'\1ir'), # vivieron -> vivir
        
        # Gerund
        (r'(.+)ando$', r'\1ar'),  # hablando -> hablar
        (r'(.+)iendo$', r'\1er'), # comiendo -> comer
        (r'(.+)iendo$', r'\1ir'), # viviendo -> vivir
        
        # Participle
        (r'(.+)ado$', r'\1ar'),   # hablado -> hablar
        (r'(.+)ido$', r'\1er'),   # comido -> comer
        (r'(.+)ido$', r'\1ir'),   # vivido -> vivir
    ]
    
    # Try verb patterns first
    for pattern, replacement in verb_patterns:
        if re.match(pattern, word):
            result = re.sub(pattern, replacement, word)
            # Avoid over-lemmatization of short words
            if len(result) >= 3:
                return result
    
    # Noun and adjective patterns
    noun_patterns = [
        # Plural to singular
        (r'(.+)s$', r'\1'),       # libros -> libro, casas -> casa
        
        # Gender variations (be careful)
        (r'(.+)as$', r'\1a'),     # niñas -> niña
        (r'(.+)os$', r'\1o'),     # niños -> niño
    ]
    
    for pattern, replacement in noun_patterns:
        if re.match(pattern, word) and len(word) > 4:  # Only for longer words
            result = re.sub(pattern, replacement, word)
            if len(result) >= 3:
                return result
    
    return word

def extract_spanish_terms(text: str, max_text_length: int = 200000) -> Dict[str, int]:
    """
    Spanish-optimized term extraction with proper lemmatization and filtering
    """
    # Intelligent text truncation
    if len(text) > max_text_length:
        sentences = re.split(r'[.!?]+', text[:max_text_length])
        if len(sentences) > 1:
            text = '. '.join(sentences[:-1]) + '.'
        else:
            text = text[:max_text_length]
    
    # Spanish compound terms for technology and business (enhanced)
    spanish_compounds = {
        # Technology in Spanish
        'inteligencia artificial': 'inteligencia_artificial',
        'aprendizaje automático': 'aprendizaje_automatico',
        'aprendizaje profundo': 'aprendizaje_profundo',
        'redes neuronales': 'redes_neuronales',
        'red neuronal': 'red_neuronal',
        'procesamiento de lenguaje natural': 'procesamiento_lenguaje_natural',
        'visión artificial': 'vision_artificial',
        'visión por computadora': 'vision_computadora',
        'ciencia de datos': 'ciencia_datos',
        'ingeniería de software': 'ingenieria_software',
        'gestión de bases de datos': 'gestion_bases_datos',
        'base de datos': 'base_datos',
        'computación en la nube': 'computacion_nube',
        'ciberseguridad': 'ciberseguridad',
        'seguridad informática': 'seguridad_informatica',
        'internet de las cosas': 'internet_cosas',
        'tecnología blockchain': 'tecnologia_blockchain',
        'cadena de bloques': 'cadena_bloques',
        'computación cuántica': 'computacion_cuantica',
        'realidad virtual': 'realidad_virtual',
        'realidad aumentada': 'realidad_aumentada',
        'big data': 'big_data',
        'computación en el borde': 'computacion_borde',
        'arquitectura de microservicios': 'arquitectura_microservicios',
        'transformación digital': 'transformacion_digital',
        'comercio electrónico': 'comercio_electronico',
        'redes sociales': 'redes_sociales',
        'computación móvil': 'computacion_movil',
        'experiencia de usuario': 'experiencia_usuario',
        'interfaz de usuario': 'interfaz_usuario',
        'desarrollo de software': 'desarrollo_software',
        'desarrollo web': 'desarrollo_web',
        'desarrollo móvil': 'desarrollo_movil',
        'inteligencia de negocios': 'inteligencia_negocios',
        'análisis de datos': 'analisis_datos',
        'minería de datos': 'mineria_datos',
        'almacén de datos': 'almacen_datos',
        'lago de datos': 'lago_datos',
        'pipeline de datos': 'pipeline_datos',
        'automatización robótica': 'automatizacion_robotica',
        'automatización de procesos': 'automatizacion_procesos',
        'gestión de proyectos': 'gestion_proyectos',
        'aseguramiento de calidad': 'aseguramiento_calidad',
        'gestión de cambios': 'gestion_cambios',
        'gestión de riesgos': 'gestion_riesgos',
        'monitoreo de rendimiento': 'monitoreo_rendimiento',
        'proceso de negocio': 'proceso_negocio',
        'marketing digital': 'marketing_digital',
        'experiencia del cliente': 'experiencia_cliente',
        'privacidad de datos': 'privacidad_datos',
        'gestión de identidad': 'gestion_identidad',
        'control de acceso': 'control_acceso',
        'detección de amenazas': 'deteccion_amenazas',
        'evaluación de vulnerabilidades': 'evaluacion_vulnerabilidades',
        'pruebas de penetración': 'pruebas_penetracion',
        'auditoría de seguridad': 'auditoria_seguridad',
        'arquitectura orientada a servicios': 'arquitectura_servicios',
        'arquitectura dirigida por eventos': 'arquitectura_eventos',
        'diseño dirigido por dominio': 'diseno_dominio',
        'desarrollo dirigido por pruebas': 'desarrollo_pruebas',
        'integración continua': 'integracion_continua',
        'despliegue continuo': 'despliegue_continuo',
        'metodología ágil': 'metodologia_agil',
        'prácticas devops': 'practicas_devops',
        'gestión de productos': 'gestion_productos',
        'interfaz de programación': 'interfaz_programacion',
        'sistema de gestión': 'sistema_gestion',
        'administración de sistemas': 'administracion_sistemas',
        'seguridad de red': 'seguridad_red',
        'seguridad de información': 'seguridad_informacion',
        'computación cuántica': 'computacion_cuantica',
        'realidad virtual': 'realidad_virtual',
        'realidad aumentada': 'realidad_aumentada',
        'internet de las cosas': 'internet_cosas',
        'big data': 'big_data',
        'análisis de datos': 'analisis_datos',
        'inteligencia de negocios': 'inteligencia_negocios',
        'transformación digital': 'transformacion_digital',
        'desarrollo de software': 'desarrollo_software',
        'desarrollo web': 'desarrollo_web',
        'desarrollo móvil': 'desarrollo_movil',
        'experiencia de usuario': 'experiencia_usuario',
        'interfaz de usuario': 'interfaz_usuario',
        'arquitectura de microservicios': 'arquitectura_microservicios',
        'seguridad informática': 'seguridad_informatica',
        'ciberseguridad': 'ciberseguridad',
        'gestión de proyectos': 'gestion_proyectos',
        'aseguramiento de calidad': 'aseguramiento_calidad',
        'control de calidad': 'control_calidad',
        'redes sociales': 'redes_sociales',
        'comercio electrónico': 'comercio_electronico',
        'marketing digital': 'marketing_digital',
        
        # Business terms
        'recursos humanos': 'recursos_humanos',
        'servicio al cliente': 'servicio_cliente',
        'cadena de suministro': 'cadena_suministro',
        'plan de negocios': 'plan_negocios',
        'modelo de negocio': 'modelo_negocio',
        'estrategia empresarial': 'estrategia_empresarial',
        'gestión financiera': 'gestion_financiera',
        'análisis financiero': 'analisis_financiero',
        'ventaja competitiva': 'ventaja_competitiva',
        'investigación de mercado': 'investigacion_mercado',
        'segmentación de mercado': 'segmentacion_mercado',
        'propuesta de valor': 'propuesta_valor',
        
        # Common abbreviations
        'ia': 'inteligencia_artificial',
        'ml': 'aprendizaje_automatico',
        'bd': 'base_datos',
        'ti': 'tecnologia_informacion',
        'rh': 'recursos_humanos',
    }
    
    # Process text
    text_processed = text.lower()
    
    # Replace compound terms (order by length to avoid conflicts)
    sorted_compounds = sorted(spanish_compounds.items(), key=lambda x: len(x[0]), reverse=True)
    for compound, replacement in sorted_compounds:
        pattern = r'\b' + re.escape(compound) + r'\b'
        text_processed = re.sub(pattern, replacement, text_processed)
    
    term_freq = Counter()
    
    # Extract preserved compound terms
    for replacement in spanish_compounds.values():
        count = len(re.findall(r'\b' + re.escape(replacement) + r'\b', text_processed))
        if count > 0:
            readable_term = replacement.replace('_', ' ')
            term_freq[readable_term] = count
    
    # Spanish technical vocabulary
    spanish_technical_terms = {
        # Technology
        'algoritmo', 'framework', 'biblioteca', 'librería', 'servidor', 'cliente',
        'interfaz', 'protocolo', 'arquitectura', 'plataforma', 'sistema', 'aplicación',
        'programa', 'software', 'hardware', 'red', 'internet', 'web', 'móvil',
        'escritorio', 'nube', 'almacenamiento', 'memoria', 'procesador', 'cpu',
        'optimización', 'rendimiento', 'escalabilidad', 'seguridad', 'autenticación',
        'autorización', 'encriptación', 'cifrado', 'contenedor', 'automatización',
        'integración', 'migración', 'modernización', 'implementación', 'despliegue',
        'pruebas', 'depuración', 'monitoreo', 'mantenimiento', 'documentación',
        
        # Data and Analytics
        'datos', 'información', 'análisis', 'analítica', 'visualización', 'dashboard',
        'reporte', 'informe', 'métricas', 'estadísticas', 'modelo', 'entrenamiento',
        'predicción', 'clasificación', 'regresión', 'agrupamiento', 'patrón',
        
        # Business
        'negocio', 'empresa', 'organización', 'proceso', 'procedimiento', 'metodología',
        'estrategia', 'gestión', 'administración', 'liderazgo', 'equipo', 'cliente',
        'usuario', 'servicio', 'producto', 'mercado', 'ventas', 'marketing',
        'finanzas', 'presupuesto', 'inversión', 'riesgo', 'oportunidad', 'innovación',
        'calidad', 'eficiencia', 'productividad', 'competitividad', 'crecimiento',
        
        # Research and Development
        'investigación', 'desarrollo', 'innovación', 'experimento', 'prototipo',
        'prueba', 'concepto', 'factibilidad', 'estudio', 'descubrimiento',
        'avance', 'progreso', 'evolución', 'mejora', 'optimización',
    }
    
    # Extract and lemmatize words
    words = re.findall(r'\b[a-záéíóúñü]{3,}\b', text_processed, re.IGNORECASE)
    
    for word in words:
        # Skip compound term tokens
        if word.endswith('_') or '_' in word:
            continue
            
        # Check if it's a technical term
        if word in spanish_technical_terms:
            term_freq[word] += 1
            continue
        
        # Skip stopwords
        if word in SPANISH_STOPWORDS_COMPREHENSIVE:
            continue
        
        # Lemmatize the word
        lemmatized = simple_spanish_lemmatizer(word)
        
        # Additional filtering for Spanish
        if (len(lemmatized) >= 3 and 
            lemmatized not in SPANISH_STOPWORDS_COMPREHENSIVE and
            not re.match(r'^(un|una|el|la|los|las|de|del|en|con|por|para|que|se|le|lo|la)$', lemmatized) and
            lemmatized.isalpha()):
            
            # Boost important domain terms
            boost = 1
            if any(keyword in lemmatized for keyword in 
                   ['tecnología', 'técnico', 'digital', 'sistema', 'gestión', 'desarrollo',
                    'análisis', 'proceso', 'estrategia', 'innovación', 'calidad']):
                boost = 2
            
            term_freq[lemmatized] += boost
    
    # Filter results
    filtered_terms = {}
    min_freq = 1
    
    for term, freq in term_freq.items():
        if (freq >= min_freq and 
            len(term) >= 3 and 
            len(term) <= 50 and
            term not in SPANISH_STOPWORDS_COMPREHENSIVE):
            filtered_terms[term] = freq
    
    return filtered_terms

def build_spanish_concept_graph(text: str, analysis_type: str = 'community') -> Dict[str, Any]:
    """
    Spanish-optimized concept graph builder
    """
    print(f"Construyendo grafo de conceptos para {len(text)} caracteres...")
    start_time = time.time()
    
    # Extract Spanish terms
    terms = extract_spanish_terms(text)
    print(f"Extraídos {len(terms)} términos en {time.time() - start_time:.2f}s")
    
    if not terms:
        return {
            'nodes': [],
            'links': [],
            'insights': {'message': 'No se extrajeron términos del texto'}
        }
    
    # Build graph using the same logic as the English version
    G = nx.Graph()
    
    # Add nodes
    for term, freq in terms.items():
        G.add_node(term, weight=freq, frequency=freq)
    
    # Add edges based on co-occurrence
    edge_weights = defaultdict(int)
    
    # Sentence-level co-occurrence
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences[:200]:  # Limit for performance
        sentence_lower = sentence.lower()
        sentence_terms = []
        
        for term in terms.keys():
            search_variants = [term]
            if ' ' in term:
                search_variants.append(term.replace(' ', '_'))
                search_variants.extend(term.split())
            
            for variant in search_variants:
                if re.search(r'\b' + re.escape(variant) + r'\b', sentence_lower):
                    sentence_terms.append(term)
                    break
        
        # Add co-occurrence edges
        for term1, term2 in combinations(sentence_terms, 2):
            edge_weights[(term1, term2)] += 1
    
    # Add edges to graph
    for (term1, term2), weight in edge_weights.items():
        if weight >= 1:
            G.add_edge(term1, term2, weight=weight)
    
    # Calculate centrality and select important nodes
    if len(G.nodes()) > 0:
        try:
            degree_centrality = nx.degree_centrality(G)
            if len(G.nodes()) <= 100:
                betweenness = nx.betweenness_centrality(G)
                closeness = nx.closeness_centrality(G)
            else:
                # Sample for large graphs
                sample_nodes = list(G.nodes())[:50]
                subgraph = G.subgraph(sample_nodes)
                betweenness_sample = nx.betweenness_centrality(subgraph)
                closeness_sample = nx.closeness_centrality(subgraph)
                
                betweenness = {node: betweenness_sample.get(node, 0.0) for node in G.nodes()}
                closeness = {node: closeness_sample.get(node, 0.0) for node in G.nodes()}
        except:
            degree_centrality = nx.degree_centrality(G)
            betweenness = {node: 0.0 for node in G.nodes()}
            closeness = {node: 0.0 for node in G.nodes()}
    else:
        degree_centrality = betweenness = closeness = {}
    
    # Score nodes
    node_scores = {}
    for node in G.nodes():
        freq_score = terms.get(node, 1) * 2
        degree_score = degree_centrality.get(node, 0) * 100
        between_score = betweenness.get(node, 0) * 75
        close_score = closeness.get(node, 0) * 50
        
        # Boost for compound terms
        compound_boost = 30 if ' ' in node else 0
        
        # Boost for technical terms
        technical_indicators = [
            'inteligencia', 'aprendizaje', 'datos', 'sistema', 'tecnología',
            'desarrollo', 'gestión', 'análisis', 'proceso', 'estrategia'
        ]
        technical_boost = 15 if any(indicator in node.lower() for indicator in technical_indicators) else 0
        
        total_score = freq_score + degree_score + between_score + close_score + compound_boost + technical_boost
        node_scores[node] = total_score
    
    # Select top nodes
    max_nodes = min(60, max(15, len(terms) // 3))
    selected_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
    selected_node_names = [node for node, score in selected_nodes]
    
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
                'importance': node_scores.get(node, 0),
                'type': 'compound' if ' ' in node else 'single'
            })
        
        links = []
        for edge in subgraph.edges(data=True):
            links.append({
                'source': edge[0],
                'target': edge[1],
                'weight': edge[2].get('weight', 1),
                'strength': min(10, edge[2].get('weight', 1))
            })
        
        # Insights
        insights = {
            'total_nodes': len(nodes),
            'total_links': len(links),
            'compound_terms': len([n for n in nodes if n['type'] == 'compound']),
            'single_terms': len([n for n in nodes if n['type'] == 'single']),
            'processing_time': time.time() - start_time
        }
        
        try:
            if len(subgraph.nodes()) > 3:
                communities = nx.community.greedy_modularity_communities(subgraph)
                insights['total_clusters'] = len(communities)
                insights['largest_cluster'] = max(len(c) for c in communities) if communities else 0
        except:
            insights['total_clusters'] = 1
            insights['largest_cluster'] = len(nodes)
        
        total_time = time.time() - start_time
        print(f"Grafo construido en {total_time:.2f}s: {len(nodes)} nodos, {len(links)} enlaces")
        
        return {
            'nodes': nodes,
            'links': links,
            'insights': insights
        }
    
    return {
        'nodes': [],
        'links': [],
        'insights': {'message': 'No se encontraron conexiones significativas'}
    }

if __name__ == "__main__":
    # Test with Spanish text
    test_text = """
    La inteligencia artificial y el aprendizaje automático están transformando la tecnología. 
    El aprendizaje profundo utiliza redes neuronales para procesar patrones complejos de datos. 
    El procesamiento de lenguaje natural permite a las computadoras entender el lenguaje humano. 
    La visión artificial permite a las máquinas interpretar información visual.
    
    La ciencia de datos combina estadísticas, aprendizaje automático y conocimiento del dominio 
    para extraer información valiosa de los datos. La ingeniería de software involucra el diseño 
    sistemático y desarrollo de sistemas de software. La gestión de bases de datos proporciona 
    almacenamiento y recuperación eficiente de información.
    
    La computación en la nube ofrece infraestructura escalable para aplicaciones. La ciberseguridad 
    protege los sistemas digitales de amenazas. El internet de las cosas conecta dispositivos físicos 
    a redes digitales para la recopilación de datos.
    """
    
    result = build_spanish_concept_graph(test_text)
    print(f"\nResultados: {len(result['nodes'])} nodos, {len(result['links'])} enlaces")
    compound_terms = [node['label'] for node in result['nodes'] if node['type'] == 'compound']
    print(f"Términos compuestos: {compound_terms}")
