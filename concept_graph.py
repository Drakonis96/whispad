import re
import itertools
import networkx as nx
from collections import Counter
import math

# Import NLTK for lemmatization support
try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Initialize NLTK resources if available
if NLTK_AVAILABLE:
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/wordnet')
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        # Download required NLTK data
        import os
        import tempfile
        # Set NLTK data path to a temporary directory
        nltk_data_dir = os.path.join(tempfile.gettempdir(), 'nltk_data')
        nltk.data.path.append(nltk_data_dir)
        try:
            nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
            nltk.download('wordnet', download_dir=nltk_data_dir, quiet=True)
            nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir, quiet=True)
            nltk.download('omw-1.4', download_dir=nltk_data_dir, quiet=True)
        except Exception as e:
            print(f"Warning: Could not download NLTK data: {e}")
            NLTK_AVAILABLE = False

# Extended stopwords including common academic and generic terms
STOPWORDS = {
    # Articles and common words
    'the','and','a','an','to','of','in','for','on','with','at','by','from','up','about','into','over','after',
    'under','above','below','is','are','was','were','be','been','being','have','has','had','do','does','did',
    'but','if','or','because','as','until','while','than','that','so','such','too','very','can','will','just',
    'also','this','these','those','they','them','their','there','here','where','when','what','who','how','why',
    'would','could','should','might','may','must','shall','need','get','got','go','went','come','came','see',
    'saw','know','knew','think','thought','say','said','tell','told','make','made','take','took','give','gave',
    'use','used','find','found','look','looked','work','worked','call','called','try','tried','ask','asked',
    'seem','seemed','feel','felt','become','became','leave','left','put','set','turn','turned','move','moved',
    'right','left','good','bad','new','old','first','last','long','short','high','low','big','small','large',
    'great','little','own','other','another','same','different','each','every','all','some','any','many','much',
    'more','most','less','few','several','both','either','neither','between','among','during','before','after',
    'since','through','throughout','within','without','across','around','down','off','out','up','away','back',
    'again','once','twice','never','always','often','sometimes','usually','really','quite','rather','pretty',
    'only','even','still','yet','already','now','then','soon','later','early','late','today','tomorrow',
    'yesterday','however','therefore','thus','hence','moreover','furthermore','nevertheless','nonetheless',
    'meanwhile','otherwise','instead','besides','indeed','certainly','perhaps','maybe','probably','possibly',
    
    # Pronouns (all forms)
    'i','me','my','mine','myself','you','your','yours','yourself','yourselves','he','him','his','himself',
    'she','her','hers','herself','it','its','itself','we','us','our','ours','ourselves','they','them',
    'their','theirs','themselves','who','whom','whose','which','what','that','this','these','those',
    
    # Demonstratives and quantifiers
    'some','any','none','all','each','every','both','either','neither','one','two','three','four','five',
    'six','seven','eight','nine','ten','many','much','few','little','several','enough','plenty',
    
    # Common verbs that don't add semantic value
    'am','being','been','have','has','had','do','does','did','will','would','could','should','might','may',
    'can','must','shall','ought','need','dare','used','going','getting','making','taking','giving','coming',
    'looking','working','trying','saying','telling','knowing','thinking','feeling','seeming','becoming',
    
    # Generic nouns and adjectives
    'thing','things','stuff','something','anything','everything','nothing','someone','anyone','everyone',
    'no one','nobody','somebody','anybody','everybody','somewhere','anywhere','everywhere','nowhere',
    'way','ways','time','times','place','places','part','parts','kind','kinds','type','types','sort','sorts',
    'side','sides','end','ends','point','points','case','cases','fact','facts','example','examples',
    'idea','ideas','reason','reasons','problem','problems','question','questions','answer','answers',
    'number','numbers','group','groups','level','levels','area','areas','line','lines','word','words',
    'name','names','year','years','day','days','week','weeks','month','months','hour','hours','minute','minutes',
    
    # Common adjectives
    'important','different','large','small','great','good','bad','high','low','long','short','big','little',
    'old','new','young','early','late','best','worst','better','worse','first','last','next','previous',
    'main','major','minor','special','general','particular','certain','sure','clear','possible','impossible',
    'available','free','open','close','closed','easy','hard','difficult','simple','complex','basic','advanced',
    
    # Temporal and spatial terms
    'now','then','here','there','today','tomorrow','yesterday','before','after','during','while','since',
    'until','although','though','unless','because','if','when','where','how','why','what','which','that',
    
    # Numbers and ordinals
    'zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen',
    'fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty','thirty','forty','fifty',
    'sixty','seventy','eighty','ninety','hundred','thousand','million','billion','first','second','third',
    'fourth','fifth','sixth','seventh','eighth','ninth','tenth','last','next','another','other'
}

# Spanish stopwords for concept graph filtering
STOPWORDS_SPANISH = {
    # Articles and determiners
    'el','la','los','las','un','una','unos','unas','este','esta','estos','estas','ese','esa','esos','esas',
    'aquel','aquella','aquellos','aquellas','mi','tu','su','nuestro','nuestra','nuestros','nuestras',
    'vuestro','vuestra','vuestros','vuestras','mio','mia','mios','mias','tuyo','tuya','tuyos','tuyas',
    'suyo','suya','suyos','suyas','mismo','misma','mismos','mismas','otro','otra','otros','otras',
    
    # Pronouns
    'yo','tu','el','ella','nosotros','nosotras','vosotros','vosotras','ellos','ellas','me','te','se',
    'nos','os','le','lo','la','les','que','quien','quienes','cual','cuales','donde','cuando','como',
    'por','para','con','sin','sobre','bajo','entre','durante','antes','despues','hasta','desde',
    
    # Verbs (common auxiliary and modal verbs)
    'ser','estar','haber','tener','hacer','ir','venir','dar','decir','poder','deber','querer','saber',
    'ver','poner','salir','llegar','pasar','seguir','quedar','creer','llevar','dejar','sentir','volver',
    'encontrar','parecer','trabajar','empezar','esperar','buscar','existir','entrar','hablar','abrir',
    'cerrar','vivir','morir','nacer','crecer','aprender','enseñar','estudiar','leer','escribir','pensar',
    'recordar','olvidar','conocer','reconocer','entender','comprender','explicar','preguntar','responder',
    'ayudar','necesitar','usar','utilizar','servir','funcionar','cambiar','mejorar','empeorar','aumentar',
    'disminuir','subir','bajar','caer','levantar','mover','parar','continuar','terminar','acabar','comenzar',
    
    # Prepositions and conjunctions
    'y','o','pero','sino','aunque','si','porque','ya','como','cuando','donde','mientras','hasta','desde',
    'para','por','con','sin','sobre','bajo','ante','tras','durante','mediante','segun','contra','hacia',
    'entre','a','de','en','que','no','ni','también','tampoco','solo','solamente','incluso','además',
    'sin embargo','por tanto','por eso','entonces','luego','después','antes','ahora','ya','aún','todavía',
    
    # Adverbs
    'muy','más','menos','tan','tanto','bastante','poco','mucho','demasiado','algo','nada','todo','siempre',
    'nunca','jamás','a veces','quizás','tal vez','posiblemente','probablemente','seguramente','claro',
    'obviamente','realmente','verdaderamente','exactamente','aproximadamente','casi','apenas','solo',
    'únicamente','especialmente','particularmente','generalmente','normalmente','habitualmente','frecuentemente',
    'raramente','difícilmente','fácilmente','rápidamente','lentamente','bien','mal','mejor','peor',
    
    # Adjectives (common descriptive)
    'bueno','malo','grande','pequeño','nuevo','viejo','joven','mayor','menor','primero','último','siguiente',
    'anterior','próximo','mismo','diferente','igual','similar','distinto','especial','normal','común',
    'raro','extraño','importante','necesario','posible','imposible','fácil','difícil','simple','complejo',
    'claro','oscuro','alto','bajo','largo','corto','ancho','estrecho','gordo','delgado','fuerte','débil',
    'rápido','lento','caliente','frío','dulce','amargo','salado','ácido','suave','duro','blando','seco',
    'húmedo','limpio','sucio','nuevo','usado','caro','barato','rico','pobre','libre','ocupado','lleno',
    'vacío','abierto','cerrado','público','privado','nacional','internacional','local','general','particular',
    
    # Numbers and quantifiers
    'cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve','diez','once','doce','trece',
    'catorce','quince','dieciséis','diecisiete','dieciocho','diecinueve','veinte','treinta','cuarenta','cincuenta',
    'sesenta','setenta','ochenta','noventa','cien','mil','millón','billón','primero','segundo','tercero',
    'cuarto','quinto','sexto','séptimo','octavo','noveno','décimo','algunos','varios','muchos','pocos',
    'todos','ninguno','cada','cualquier','ambos','ningún','algún','cierto','cierta','ciertos','ciertas',
    
    # Time and space
    'hoy','ayer','mañana','ahora','antes','después','luego','entonces','pronto','tarde','temprano',
    'siempre','nunca','a menudo','frecuentemente','raramente','aquí','allí','acá','allá','arriba',
    'abajo','adelante','atrás','izquierda','derecha','cerca','lejos','dentro','fuera','encima','debajo',
    'delante','detrás','al lado','alrededor','través','mediante','durante','mientras','hasta','desde',
    
    # Common phrases and expressions
    'por favor','gracias','perdón','disculpe','lo siento','de nada','por supuesto','claro que sí',
    'tal vez','quizás','sin duda','por cierto','en realidad','en verdad','a propósito','por ejemplo',
    'es decir','o sea','sin embargo','no obstante','por tanto','por eso','además','también','tampoco',
    
    # Interrogatives and exclamatives
    'qué','cuál','cuáles','quién','quiénes','cómo','cuándo','dónde','cuánto','cuánta','cuántos','cuántas',
    'por qué','para qué','ah','oh','uf','ay','vaya','caramba','dios mío','por dios'
}

def get_stopwords(language='english'):
    """Get stopwords for the specified language."""
    if language.lower() in ['spanish', 'es', 'español']:
        return STOPWORDS_SPANISH
    else:
        return STOPWORDS  # Default to English

def get_wordnet_pos(treebank_tag):
    """Convert treebank POS tag to wordnet POS tag for lemmatization."""
    if not NLTK_AVAILABLE:
        return wordnet.NOUN  # Default fallback
    
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN  # Default

def lemmatize_word(word, language='english', enable_lemmatization=True):
    """
    Lemmatize a word if lemmatization is enabled and NLTK is available.
    Falls back to returning the original word if lemmatization fails.
    """
    if not enable_lemmatization or not NLTK_AVAILABLE:
        return word
    
    # Currently only support English lemmatization with NLTK
    if language.lower() not in ['english', 'en']:
        return word
    
    try:
        lemmatizer = WordNetLemmatizer()
        # Get POS tag for better lemmatization
        try:
            tokens = nltk.word_tokenize(word)
            if tokens:
                pos_tags = nltk.pos_tag(tokens)
                if pos_tags:
                    _, pos = pos_tags[0]
                    wordnet_pos = get_wordnet_pos(pos)
                    return lemmatizer.lemmatize(word.lower(), pos=wordnet_pos)
        except:
            # Fallback to simple noun lemmatization
            pass
        
        return lemmatizer.lemmatize(word.lower())
    except Exception as e:
        # If lemmatization fails for any reason, return original word
        return word

def lemmatize_terms(terms, language='english', enable_lemmatization=True):
    """
    Lemmatize a list of terms if lemmatization is enabled.
    """
    if not enable_lemmatization:
        return terms
    
    lemmatized = []
    for term in terms:
        if ' ' in term:  # Multi-word terms - lemmatize each word
            words = term.split()
            lemmatized_words = [lemmatize_word(word, language, enable_lemmatization) for word in words]
            lemmatized.append(' '.join(lemmatized_words))
        else:  # Single word
            lemmatized.append(lemmatize_word(term, language, enable_lemmatization))
    
    return lemmatized

def jenks_natural_breaks_simple(data, n_classes=3):
    """
    Implementación simplificada del algoritmo de Jenks Natural Breaks 
    que no requiere numpy.
    """
    if len(data) <= n_classes:
        return sorted(set(data))
    
    data = sorted(data)
    n = len(data)
    
    # Para datasets pequeños, usar percentiles
    if n <= 10:
        percentiles = [20, 50, 80][:n_classes-1]
        breaks = []
        for p in percentiles:
            idx = int((p / 100.0) * (n - 1))
            breaks.append(data[idx])
        breaks = [data[0]] + breaks + [data[-1]]
        return sorted(set(breaks))
    
    # Algoritmo simplificado para datasets más grandes
    # Dividir en clases aproximadamente iguales y optimizar
    class_size = n // n_classes
    breaks = [data[0]]
    
    for i in range(1, n_classes):
        start_idx = i * class_size
        end_idx = min((i + 1) * class_size, n)
        
        if start_idx < n:
            # Buscar el mejor punto de corte en un rango
            best_break = data[start_idx]
            min_variance = float('inf')
            
            for j in range(max(0, start_idx - 5), min(n, start_idx + 5)):
                if j > 0 and j < n - 1:
                    # Calcular varianza aproximada
                    left_data = data[breaks[-1]:j] if len(breaks) > 1 else data[:j]
                    right_data = data[j:end_idx] if end_idx < n else data[j:]
                    
                    if left_data and right_data:
                        left_var = variance(left_data)
                        right_var = variance(right_data)
                        total_var = left_var + right_var
                        
                        if total_var < min_variance:
                            min_variance = total_var
                            best_break = data[j]
            
            breaks.append(best_break)
    
    breaks.append(data[-1])
    return sorted(set(breaks))

def variance(data):
    """Calcula la varianza de una lista de datos."""
    if len(data) <= 1:
        return 0
    mean = sum(data) / len(data)
    return sum((x - mean) ** 2 for x in data) / len(data)

def percentile(data, p):
    """Calcula el percentil p de los datos."""
    if not data:
        return 0
    sorted_data = sorted(data)
    n = len(sorted_data)
    index = (p / 100.0) * (n - 1)
    
    if index == int(index):
        return sorted_data[int(index)]
    else:
        lower = sorted_data[int(index)]
        upper = sorted_data[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))

def calculate_network_diversity(G, node):
    """
    Calcula la diversidad de conexiones de un nodo basada en 
    la entropía de Shannon de sus conexiones.
    """
    neighbors = list(G.neighbors(node))
    if len(neighbors) <= 1:
        return 0
    
    # Calcular pesos de las conexiones
    weights = []
    for neighbor in neighbors:
        weight = G[node][neighbor].get('weight', 1.0)
        weights.append(weight)
    
    # Normalizar pesos
    total_weight = sum(weights)
    if total_weight == 0:
        return 0
    
    probs = [w / total_weight for w in weights]
    
    # Calcular entropía de Shannon
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    
    # Normalizar por el máximo posible (log2(n))
    max_entropy = math.log2(len(neighbors)) if len(neighbors) > 1 else 1
    return entropy / max_entropy

def extract_high_quality_terms(text, min_length=3, max_length=50, language='english', enable_lemmatization=True, max_text_length=200000, exclusions=None):
    """
    High-quality term extraction prioritizing compound terms and comprehensive coverage
    Target: 80-90% quality for concept graphs
    Enhanced with Spanish language support
    """
    from collections import defaultdict
    
    if exclusions is None:
        exclusions = []
    
    # Convert exclusions to lowercase for case-insensitive matching
    exclusions_lower = [exc.lower() for exc in exclusions]
    
    # Initialize language detection variables
    spanish_count = 0
    english_count = 0
    
    # Detect language if not specified or auto
    if language == 'auto' or language == 'english':  # Default to checking for Spanish indicators
        spanish_indicators = ['el ', 'la ', 'los ', 'las ', 'de ', 'del ', 'en ', 'con ', 'por ', 'para ', 'es ', 'está ', 'son ', 'están ', 'y ', 'o ', 'que ', 'pero ', 'como ']
        english_indicators = ['the ', 'and ', 'of ', 'to ', 'in ', 'for ', 'with ', 'on ', 'by ', 'from ', 'is ', 'are ', 'was ', 'were ', 'that ', 'this ']
        
        text_lower = text.lower()
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
        
        # If we detect Spanish indicators, process as Spanish
        if spanish_count > 2:  # Lower threshold for detection
            language = 'spanish'
        elif english_count > spanish_count:
            language = 'english'
        # For mixed content, we'll process compound terms for both languages
    
    # More generous text length limit for quality
    if len(text) > max_text_length:
        # Intelligent truncation preserving complete sentences
        sentences = re.split(r'[.!?]+', text[:max_text_length])
        if len(sentences) > 1:
            text = '. '.join(sentences[:-1]) + '.'
        else:
            text = text[:max_text_length]
    
    # Language-specific compound terms with mixed content support
    compound_terms = {}
    
    # For mixed content or when Spanish is detected, include Spanish terms
    if language.lower() in ['spanish', 'es', 'español'] or spanish_count > 0:
        spanish_compounds = {
            # Spanish compound terms for technology and business
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
            'automatización robótica': 'automatizacion_robotica',
            'gestión de proyectos': 'gestion_proyectos',
            'aseguramiento de calidad': 'aseguramiento_calidad',
            'marketing digital': 'marketing_digital',
            'experiencia del cliente': 'experiencia_cliente',
            'privacidad de datos': 'privacidad_datos',
            'control de acceso': 'control_acceso',
            'detección de amenazas': 'deteccion_amenazas',
            'integración continua': 'integracion_continua',
            'despliegue continuo': 'despliegue_continuo',
            'metodología ágil': 'metodologia_agil',
            'prácticas devops': 'practicas_devops',
        }
        compound_terms.update(spanish_compounds)
    
    # For mixed content or when English is detected, include English terms  
    if language.lower() not in ['spanish', 'es', 'español'] or english_count > 0:
        english_compounds = {
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
    
    # Language-specific technical terms and stopwords
    if language.lower() in ['spanish', 'es', 'español']:
        # Enhanced Spanish stopwords (more comprehensive)
        spanish_stopwords = {
            # Articles
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            # Prepositions  
            'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'del', 'desde', 'durante', 
            'en', 'entre', 'hacia', 'hasta', 'mediante', 'para', 'por', 'según', 'sin', 
            'so', 'sobre', 'tras', 'versus', 'vía',
            # Conjunctions
            'y', 'e', 'ni', 'o', 'u', 'pero', 'mas', 'sino', 'que', 'porque', 'pues', 
            'aunque', 'si', 'como', 'cuando', 'donde', 'mientras', 'ya',
            # Common verbs
            'ser', 'estar', 'haber', 'tener', 'hacer', 'ir', 'venir', 'dar', 'decir', 
            'poder', 'deber', 'querer', 'saber', 'ver', 'poner', 'salir', 'llegar', 
            'pasar', 'seguir', 'quedar', 'creer', 'llevar', 'dejar', 'sentir', 'volver',
            'encontrar', 'parecer', 'trabajar', 'empezar', 'esperar', 'buscar', 'existir',
            # Adverbs
            'no', 'sí', 'también', 'tampoco', 'muy', 'más', 'menos', 'tan', 'tanto', 
            'bastante', 'poco', 'mucho', 'demasiado', 'algo', 'nada', 'todo', 'siempre',
            'nunca', 'jamás', 'quizás', 'acaso', 'bien', 'mal', 'mejor', 'peor', 'ahora',
            'antes', 'después', 'luego', 'entonces', 'aquí', 'ahí', 'allí', 'allá',
            # Pronouns and determiners
            'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
            'me', 'te', 'se', 'nos', 'os', 'lo', 'la', 'le', 'les',
            'mi', 'tu', 'su', 'nuestro', 'vuestro', 'este', 'esta', 'estos', 'estas',
            'ese', 'esa', 'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas',
            # Time and quantity
            'hoy', 'ayer', 'mañana', 'tarde', 'temprano', 'pronto', 'vez', 'veces',
            'primer', 'primero', 'primera', 'segundo', 'tercero', 'último', 'última',
            # Common adjectives and adverbs that add no meaning
            'nuevo', 'nueva', 'viejo', 'vieja', 'grande', 'pequeño', 'pequeña',
            'bueno', 'buena', 'malo', 'mala', 'mismo', 'misma', 'otro', 'otra',
            'igual', 'diferente', 'similar', 'tal', 'cada', 'cualquier',
        }
        
        technical_terms = {
            # Spanish technical vocabulary
            'algoritmo', 'framework', 'biblioteca', 'servidor', 'cliente',
            'frontend', 'backend', 'despliegue', 'pruebas', 'depuración',
            'optimización', 'rendimiento', 'escalabilidad', 'seguridad', 'autenticación',
            'autorización', 'cifrado', 'protocolo', 'interfaz', 'arquitectura',
            'microservicios', 'monolito', 'contenedor', 'automatización',
            'programación', 'codificación', 'desarrollo', 'ingeniería', 'tecnología',
            'innovación', 'solución', 'plataforma', 'sistema', 'aplicación',
            'software', 'hardware', 'red', 'internet', 'web', 'móvil',
            'escritorio', 'nube', 'almacenamiento', 'memoria', 'procesador',
            'análisis', 'analítica', 'visualización', 'dashboard', 'reporte',
            'integración', 'migración', 'transformación', 'modernización',
            'conjunto', 'modelo', 'entrenamiento', 'predicción', 'clasificación',
            'regresión', 'agrupamiento', 'estadísticas', 'métricas', 'benchmark',
            'flujo', 'proceso', 'procedimiento', 'metodología', 'estrategia',
            'implementación', 'ejecución', 'monitoreo', 'evaluación', 'valoración',
            'requerimiento', 'especificación', 'documentación', 'mantenimiento',
            'soporte', 'servicio', 'cliente', 'usuario', 'stakeholder', 'equipo',
            'estándar', 'cumplimiento', 'gobernanza', 'política', 'procedimiento',
            'práctica', 'guía', 'recomendación', 'revisión', 'auditoría',
            'certificación', 'validación', 'verificación', 'investigación',
            'innovación', 'experimento', 'prototipo', 'piloto', 'prueba',
            'concepto', 'factibilidad', 'estudio', 'investigación', 'descubrimiento',
        }
    else:
        # English stopwords and technical terms (existing)
        spanish_stopwords = set()
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
    
    # Method 3: Enhanced extraction with language-specific stopwords
    stopwords = get_stopwords(language)
    
    # Add our enhanced Spanish stopwords if Spanish
    if language.lower() in ['spanish', 'es', 'español']:
        stopwords.update(spanish_stopwords)
    
    if enable_lemmatization and NLTK_AVAILABLE:
        try:
            # Language-specific additional stopwords
            if language.lower() in ['spanish', 'es', 'español']:
                additional_stopwords = {
                    'usar', 'utilizar', 'hacer', 'crear', 'dar', 'tomar', 'ver', 'saber',
                    'pensar', 'trabajar', 'ayudar', 'necesitar', 'querer', 'gustar',
                    'manera', 'forma', 'cosa', 'tiempo', 'gente', 'persona', 'año',
                    'día', 'bueno', 'mejor', 'nuevo', 'viejo', 'grande', 'pequeño',
                }
            else:
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
            stopwords.update(additional_stopwords)
            
            # Process all remaining words with lemmatization
            for word in words:
                if (len(word) >= 3 and 
                    word not in stopwords and 
                    word not in technical_terms and  # Already processed
                    not word.endswith('_') and  # Skip compound tokens
                    word.isalpha()):
                    
                    lemmatized = lemmatize_word(word, language, enable_lemmatization)
                    if lemmatized not in stopwords and len(lemmatized) >= 3:
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
    filtered_terms = []
    
    for term, freq in term_freq.items():
        if (freq >= min_freq and 
            len(term) >= min_length and 
            len(term) <= max_length):  # Allow longer compound terms
            filtered_terms.append(term)
    
    # Ensure all compound terms are preserved regardless of frequency
    for replacement in compound_terms.values():
        readable_term = replacement.replace('_', ' ')
        if readable_term in term_freq and readable_term not in filtered_terms:
            filtered_terms.append(readable_term)
    
    # Apply user exclusions (filter out excluded words/phrases)
    if exclusions_lower:
        final_terms = []
        for term in filtered_terms:
            term_lower = term.lower()
            # Check if the term or any part of it matches exclusions
            excluded = False
            for exclusion in exclusions_lower:
                if (exclusion in term_lower or term_lower in exclusion or 
                    # Check for word boundary matches
                    any(word in exclusions_lower for word in term_lower.split())):
                    excluded = True
                    break
            if not excluded:
                final_terms.append(term)
        filtered_terms = final_terms
    
    return filtered_terms

def extract_key_terms(text, min_length=3, max_length=25, language='english', enable_lemmatization=True, max_text_length=50000, exclusions=None):
    """Extract meaningful terms using advanced filtering techniques with performance optimizations."""
    if exclusions is None:
        exclusions = []
    
    # Convert exclusions to lowercase for case-insensitive matching
    exclusions_lower = [exc.lower() for exc in exclusions]
    
    stopwords = get_stopwords(language)
    
    # Truncate text if too large to improve performance
    if len(text) > max_text_length:
        text = text[:max_text_length] + "..."
    
    # Split text into sentences and normalize - limit sentence processing
    sentences = re.split(r'[.!?\n]+', text)
    
    # For very long texts, process only a subset of sentences
    if len(sentences) > 200:
        # Take first 50%, middle 25%, and last 25% to maintain text structure
        total_sentences = len(sentences)
        first_half = sentences[:total_sentences//2]
        middle_quarter = sentences[total_sentences//2:3*total_sentences//4:2]  # Sample every 2nd
        last_quarter = sentences[3*total_sentences//4:]
        sentences = first_half + middle_quarter + last_quarter
    
    # Extract potential terms with improved patterns
    terms = []
    term_counter = {}  # Track frequency for early filtering
    
    for sentence in sentences[:100]:  # Limit to first 100 sentences for performance
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:  # Skip very short sentences
            continue
            
        # Find technical terms and proper nouns (capitalized phrases)
        compound_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
        for term in compound_terms:
            if len(term.split()) <= 3 and len(term) >= min_length:
                term_lower = term.lower()
                terms.append(term_lower)
                term_counter[term_lower] = term_counter.get(term_lower, 0) + 1
        
        # Find specific important compound terms (case-insensitive)
        important_compounds = [
            'artificial intelligence', 'machine learning', 'deep learning', 'neural networks',
            'natural language processing', 'computer vision', 'data science', 'software engineering',
            'database management', 'cloud computing', 'quantum computing', 'virtual reality',
            'augmented reality', 'big data', 'edge computing', 'digital transformation',
            'social media', 'user experience', 'mobile computing', 'cyber security',
            'software development', 'web development', 'data analysis'
        ]
        sentence_lower = sentence.lower()
        for compound in important_compounds:
            if compound in sentence_lower:
                terms.append(compound)
                term_counter[compound] = term_counter.get(compound, 0) + 1
        
        # Find hyphenated terms and compound words
        hyphenated = re.findall(r'\b[a-zA-Z]+-[a-zA-Z]+(?:-[a-zA-Z]+)*\b', sentence)
        for term in hyphenated:
            if len(term) >= min_length:
                term_lower = term.lower()
                terms.append(term_lower)
                term_counter[term_lower] = term_counter.get(term_lower, 0) + 1
        
        # Find domain-specific terms (words with numbers, technical patterns)
        technical = re.findall(r'\b[a-zA-Z]*[0-9]+[a-zA-Z]*\b|\b[a-zA-Z]+[0-9]+\b', sentence)
        for term in technical:
            if len(term) >= min_length:
                term_lower = term.lower()
                terms.append(term_lower)
                term_counter[term_lower] = term_counter.get(term_lower, 0) + 1
        
        # Find single meaningful words with improved filtering
        words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        
        # Apply semantic filters for single words
        for word in words:
            if (len(word) >= min_length and len(word) <= max_length and
                word not in stopwords and
                is_meaningful_word(word, language)):
                terms.append(word)
                term_counter[word] = term_counter.get(word, 0) + 1
    
    # Early filtering: keep only terms that appear at least once and are meaningful
    frequent_terms = [term for term, count in term_counter.items() if count >= 1]
    
    # Apply lemmatization if enabled (only on filtered terms)
    if enable_lemmatization and len(frequent_terms) < 1000:  # Skip lemmatization for very large sets
        frequent_terms = lemmatize_terms(frequent_terms, language, enable_lemmatization)
    
    # Enhanced filtering for meaningful terms
    filtered_terms = []
    for term in frequent_terms:
        # Skip stopwords and short/long terms
        if (term not in stopwords and 
            min_length <= len(term) <= max_length and
            not term.isdigit() and
            not re.match(r'^[a-z]{1,2}$', term) and  # Skip single/double letters
            is_content_word(term, language)):
            
            filtered_terms.append(term)
    
    # Apply user exclusions (filter out excluded words/phrases)
    if exclusions_lower:
        final_filtered_terms = []
        for term in filtered_terms:
            term_lower = term.lower()
            # Check if the term or any part of it matches exclusions
            excluded = False
            for exclusion in exclusions_lower:
                if (exclusion in term_lower or term_lower in exclusion or 
                    # Check for word boundary matches
                    any(word in exclusions_lower for word in term_lower.split())):
                    excluded = True
                    break
            if not excluded:
                final_filtered_terms.append(term)
        filtered_terms = final_filtered_terms
    
    # Limit the total number of terms for performance
    return filtered_terms[:500]  # Cap at 500 terms

def is_meaningful_word(word, language='english'):
    """Check if a word is semantically meaningful."""
    # Skip words that are mostly inflected forms without semantic value
    if language.lower() in ['spanish', 'es', 'español']:
        # Spanish-specific inflection patterns
        if word.endswith(('ando', 'endo', 'ado', 'ido', 'ción', 'sión', 'mente')) and len(word) <= 7:
            return False
    else:
        # English inflection patterns
        if word.endswith(('ing', 'ed', 'er', 'est', 'ly', 'tion', 'sion')) and len(word) <= 6:
            return False
    
    # Skip words with repetitive characters (like 'aaa', 'hmm')
    if len(set(word)) <= 2 and len(word) > 2:
        return False
    
    # Language-specific auxiliary verbs and modal verbs
    if language.lower() in ['spanish', 'es', 'español']:
        auxiliary_verbs = {'ser', 'estar', 'haber', 'tener', 'hacer', 'ir', 'venir', 'dar', 'decir', 'poder', 
                          'deber', 'querer', 'saber', 'ver', 'poner', 'salir', 'llegar', 'pasar', 'seguir',
                          'quedar', 'creer', 'llevar', 'dejar', 'sentir', 'volver', 'encontrar', 'parecer'}
    else:
        auxiliary_verbs = {'get', 'got', 'getting', 'gets', 'set', 'put', 'putting', 'puts', 
                          'has', 'had', 'having', 'can', 'could', 'may', 'might', 'will', 
                          'would', 'shall', 'should', 'must', 'ought', 'need', 'needs'}
    
    if word in auxiliary_verbs:
        return False
    
    # Language-specific intensifiers and qualifiers
    if language.lower() in ['spanish', 'es', 'español']:
        qualifiers = {'muy', 'bastante', 'poco', 'mucho', 'demasiado', 'algo', 'nada', 'todo', 'realmente', 
                     'verdaderamente', 'exactamente', 'aproximadamente', 'casi', 'apenas', 'solo',
                     'únicamente', 'especialmente', 'particularmente', 'generalmente', 'normalmente'}
    else:
        qualifiers = {'very', 'quite', 'rather', 'pretty', 'really', 'truly', 'actually', 
                     'basically', 'essentially', 'literally', 'definitely', 'absolutely',
                     'completely', 'totally', 'entirely', 'fully', 'perfectly', 'exactly'}
    
    if word in qualifiers:
        return False
    
    return True

def is_content_word(term, language='english'):
    """Check if a term is a content word (noun, verb, adjective, adverb with semantic meaning)."""
    # Language-specific generic terms
    if language.lower() in ['spanish', 'es', 'español']:
        generic_terms = {
            'cosa', 'cosas', 'algo', 'nada', 'todo', 'alguien', 'nadie', 'todos', 'alguno', 'ninguno',
            'lugar', 'lugares', 'sitio', 'sitios', 'parte', 'partes', 'lado', 'lados', 'zona', 'zonas',
            'tiempo', 'tiempos', 'momento', 'momentos', 'vez', 'veces', 'tipo', 'tipos', 'forma', 'formas',
            'manera', 'maneras', 'modo', 'modos', 'caso', 'casos', 'hecho', 'hechos', 'razón', 'razones',
            'ejemplo', 'ejemplos', 'idea', 'ideas', 'problema', 'problemas', 'pregunta', 'preguntas',
            'respuesta', 'respuestas', 'situación', 'situaciones', 'persona', 'personas', 'gente',
            'mundo', 'vida', 'día', 'días', 'año', 'años', 'vez', 'veces', 'hora', 'horas',
            'información', 'datos', 'resultado', 'resultados', 'cambio', 'cambios',
            'nivel', 'niveles', 'número', 'números', 'cantidad', 'cantidades',
            'grupo', 'grupos', 'equipo', 'equipos', 'miembro', 'miembros',
            'individuo', 'individuos', 'humano', 'humanos'
        }
    else:
        generic_terms = {
            'thing', 'things', 'stuff', 'something', 'anything', 'everything', 'nothing',
            'someone', 'anyone', 'everyone', 'nobody', 'somebody', 'anybody', 'everybody',
            'somewhere', 'anywhere', 'everywhere', 'nowhere',
            'way', 'ways', 'time', 'times', 'kind', 'type', 'sort', 'part', 'parts',
            'place', 'places', 'area', 'areas', 'side', 'sides', 'end', 'ends',
            'point', 'points', 'case', 'cases', 'fact', 'facts', 'reason', 'reasons',
            'example', 'examples', 'idea', 'ideas', 'problem', 'problems',
            'question', 'questions', 'answer', 'answers', 'situation', 'situations',
            'information', 'data', 'result', 'results', 'change', 'changes',
            'level', 'levels', 'number', 'numbers', 'amount', 'amounts',
            'group', 'groups', 'team', 'teams', 'member', 'members',
            'person', 'people', 'individual', 'individuals', 'human', 'humans'
        }
    
    if term in generic_terms:
        return False
    
    # Language-specific discourse markers and connectives
    if language.lower() in ['spanish', 'es', 'español']:
        discourse_markers = {
            'sin embargo', 'por tanto', 'por eso', 'entonces', 'luego', 'después', 'antes', 'además',
            'también', 'tampoco', 'no obstante', 'mientras tanto', 'en cambio', 'por el contrario',
            'es decir', 'o sea', 'por ejemplo', 'por cierto', 'en realidad', 'en verdad',
            'obviamente', 'claramente', 'aparentemente', 'específicamente', 'particularmente',
            'especialmente', 'generalmente', 'típicamente', 'usualmente', 'normalmente',
            'comúnmente', 'frecuentemente', 'a menudo', 'a veces', 'ocasionalmente',
            'quizás', 'tal vez', 'posiblemente', 'probablemente', 'seguramente', 'ciertamente'
        }
    else:
        discourse_markers = {
            'however', 'therefore', 'thus', 'hence', 'moreover', 'furthermore',
            'nevertheless', 'nonetheless', 'meanwhile', 'otherwise', 'instead',
            'besides', 'indeed', 'certainly', 'perhaps', 'maybe', 'probably',
            'possibly', 'obviously', 'clearly', 'apparently', 'specifically',
            'particularly', 'especially', 'generally', 'typically', 'usually',
            'normally', 'commonly', 'frequently', 'often', 'sometimes', 'occasionally'
        }
    
    if term in discourse_markers:
        return False
    
    # Language-specific meta-language terms
    if language.lower() in ['spanish', 'es', 'español']:
        meta_terms = {
            'mencionado', 'discutido', 'descrito', 'explicado', 'establecido', 'notado',
            'indicado', 'sugerido', 'propuesto', 'argumentado', 'afirmado', 'asegurado',
            'concluido', 'determinado', 'encontrado', 'descubierto', 'observado', 'notado',
            'reportado', 'documentado', 'registrado', 'medido', 'calculado',
            'analizado', 'examinado', 'investigado', 'estudiado', 'investigado'
        }
    else:
        meta_terms = {
            'mentioned', 'discussed', 'described', 'explained', 'stated', 'noted',
            'indicated', 'suggested', 'proposed', 'argued', 'claimed', 'asserted',
            'concluded', 'determined', 'found', 'discovered', 'observed', 'noticed',
            'reported', 'documented', 'recorded', 'measured', 'calculated',
            'analyzed', 'examined', 'investigated', 'studied', 'researched'
        }
    
    if term in meta_terms:
        return False
    
    return True

def calculate_term_importance(terms, text, max_sentences=100):
    """Calculate importance scores for terms using enhanced TF-IDF-like approach with performance optimizations."""
    term_freq = Counter(terms)
    total_terms = len(terms)
    unique_terms = len(set(terms))
    
    # Limit sentences for performance
    sentences = re.split(r'[.!?\n]+', text)
    if len(sentences) > max_sentences:
        # Sample sentences for large texts
        step = len(sentences) // max_sentences
        sentences = sentences[::step][:max_sentences]
    
    # Calculate importance scores
    importance_scores = {}
    for term, freq in term_freq.items():
        # Term frequency normalized
        tf = freq / total_terms
        
        # Inverse document frequency approximation (treat sentences as documents)
        sentences_with_term = 0
        for sentence in sentences:
            if term in sentence.lower():
                sentences_with_term += 1
                if sentences_with_term >= 5:  # Early exit for performance
                    break
        
        idf = math.log(len(sentences) / (sentences_with_term + 1))
        
        # Position importance (terms appearing early/late are often more important)
        # Use a simplified approach for large texts
        text_preview = text[:2000].lower()  # Only check first 2000 chars
        first_occurrence = text_preview.find(term)
        position_score = 1.0
        if first_occurrence >= 0:
            # Higher score for terms in beginning
            relative_first = first_occurrence / len(text_preview)
            position_score = 1.0 + (0.5 if relative_first < 0.2 else 0.0)
        
        # Length bonus for multi-word terms and longer words
        length_bonus = len(term.split()) * 0.8 + min(len(term) / 12.0, 1.2)
        
        # Compound term bonus
        compound_bonus = 1.3 if ' ' in term or '-' in term else 1.0
        
        # Semantic significance bonus
        semantic_bonus = calculate_semantic_bonus(term)
        
        # Frequency bonus, but diminishing returns
        freq_bonus = math.log(freq + 1) * 0.4
        
        # Capitalization bonus (proper nouns, technical terms)
        cap_bonus = 1.2 if any(c.isupper() for c in term) else 1.0
        
        # Final importance calculation
        base_score = tf * idf + length_bonus + freq_bonus
        importance_scores[term] = (base_score * position_score * compound_bonus * 
                                 semantic_bonus * cap_bonus)
    
    return importance_scores

def calculate_semantic_bonus(term):
    """Calculate semantic significance bonus for a term."""
    # Technical/domain-specific terms get higher scores
    if re.match(r'.*\d+', term):  # Contains numbers
        return 1.4
    
    # Longer terms are often more specific
    if len(term) > 8:
        return 1.3
    
    # Multi-word terms are usually more specific
    if ' ' in term or '-' in term:
        return 1.5
    
    # Terms with common suffixes indicating concrete concepts
    concept_suffixes = ['tion', 'sion', 'ment', 'ness', 'ity', 'ism', 'ogy', 'ics']
    if any(term.endswith(suffix) for suffix in concept_suffixes):
        return 1.2
    
    # Terms indicating processes or actions
    process_suffixes = ['ing', 'ance', 'ence', 'ure', 'age']
    if any(term.endswith(suffix) for suffix in process_suffixes) and len(term) > 6:
        return 1.1
    
    return 1.0

async def enhance_terms_with_ai(terms, text, ai_provider=None, api_key=None, language='english'):
    """Use AI to enhance term selection and extract semantic relationships."""
    if not ai_provider or not api_key:
        return terms, {}
    
    try:
        import aiohttp
        import json
        
        # Prepare prompt for AI enhancement
        terms_list = list(terms.keys())[:50]  # Limit to top 50 terms
        
        # Language-specific prompts
        if language.lower() in ['spanish', 'es', 'español']:
            prompt = f"""
            Analiza el siguiente texto y la lista de términos extraídos para mejorar el mapeo de conceptos:
            
            TEXTO: {text[:2000]}...
            
            TÉRMINOS EXTRAÍDOS: {', '.join(terms_list)}
            
            Por favor proporciona:
            1. Los 15-20 términos semánticamente más importantes de la lista
            2. Cualquier concepto clave faltante que no esté en la lista
            3. Relaciones semánticas entre términos (qué términos están relacionados)
            
            Responde en formato JSON:
            {{
                "important_terms": ["término1", "término2", ...],
                "missing_concepts": ["concepto1", "concepto2", ...],
                "relationships": [["término1", "término2", "tipo_relación"], ...]
            }}
            """
        else:
            prompt = f"""
            Analyze the following text and list of extracted terms to improve concept mapping:
            
            TEXT: {text[:2000]}...
            
            EXTRACTED TERMS: {', '.join(terms_list)}
            
            Please provide:
            1. The 15-20 most semantically important terms from the list
            2. Any missing key concepts not in the list
            3. Semantic relationships between terms (which terms are related)
            
            Respond in JSON format:
            {{
                "important_terms": ["term1", "term2", ...],
                "missing_concepts": ["concept1", "concept2", ...],
                "relationships": [["term1", "term2", "relationship_type"], ...]
            }}
            """
        
        if ai_provider.lower() == 'openai':
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.3
            }
        
        elif ai_provider.lower() == 'openrouter':
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.3
            }
        
        else:
            return terms, {}  # Unsupported provider
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Parse JSON response
                    try:
                        ai_analysis = json.loads(content)
                        
                        # Enhance terms based on AI feedback
                        enhanced_terms = {}
                        
                        # Boost importance of AI-selected terms
                        for term in ai_analysis.get('important_terms', []):
                            if term.lower() in terms:
                                enhanced_terms[term.lower()] = terms[term.lower()] * 1.5
                        
                        # Add missing concepts
                        for concept in ai_analysis.get('missing_concepts', []):
                            if concept.lower() not in enhanced_terms:
                                enhanced_terms[concept.lower()] = 0.8
                        
                        # Add remaining original terms with reduced weight
                        for term, score in terms.items():
                            if term not in enhanced_terms:
                                enhanced_terms[term] = score * 0.7
                        
                        relationships = ai_analysis.get('relationships', [])
                        return enhanced_terms, relationships
                        
                    except json.JSONDecodeError:
                        pass
                
    except Exception as e:
        print(f"AI enhancement failed: {e}")
    
    return terms, {}

def select_important_nodes_by_centrality(G, analysis_type='bridges', max_nodes_for_full_analysis=100):
    """
    Selecciona nodos importantes basado en diferentes métricas de centralidad
    y usando umbrales naturales de Jenks con optimizaciones de rendimiento.
    
    analysis_type puede ser:
    - 'bridges': Enfoque en conceptos puente (betweenness centrality)
    - 'hubs': Enfoque en conceptos centrales (degree centrality)
    - 'global': Análisis global combinado
    - 'local': Análisis local (clustering)
    """
    if G.number_of_nodes() == 0:
        return [], {}
    
    n_nodes = G.number_of_nodes()
    
    # For large graphs, use sampling or simplified metrics
    if n_nodes > max_nodes_for_full_analysis:
        # Use degree centrality (fast) as primary metric for large graphs
        degree_cent = nx.degree_centrality(G)
        
        # Sample nodes for betweenness calculation
        sample_size = min(50, n_nodes // 2)
        sample_nodes = list(G.nodes())[:sample_size]
        betweenness = nx.betweenness_centrality(G.subgraph(sample_nodes), weight='weight')
        
        # Extend betweenness to all nodes using degree as proxy
        for node in G.nodes():
            if node not in betweenness:
                betweenness[node] = degree_cent[node] * 0.5  # Approximate
        
        # Skip clustering for very large graphs
        clustering = {node: 0.1 for node in G.nodes()}  # Default low clustering
    else:
        # Full analysis for smaller graphs
        betweenness = nx.betweenness_centrality(G, weight='weight')
        degree_cent = nx.degree_centrality(G)
        clustering = nx.clustering(G, weight='weight')
    
    # Calculate diversity for a subset of nodes only
    diversity_sample_size = min(50, n_nodes)
    diversity_nodes = list(G.nodes())[:diversity_sample_size]
    diversity = {}
    for node in G.nodes():
        if node in diversity_nodes:
            diversity[node] = calculate_network_diversity(G, node)
        else:
            diversity[node] = 0.5  # Default medium diversity
    
    # Select métrica principal según el tipo de análisis
    if analysis_type == 'bridges':
        primary_metric = betweenness
        secondary_metric = diversity
        weight_primary = 0.7
    elif analysis_type == 'hubs':
        primary_metric = degree_cent
        secondary_metric = betweenness
        weight_primary = 0.7
    elif analysis_type == 'global':
        # Combinar betweenness y degree con peso equilibrado
        primary_metric = {node: (betweenness[node] + degree_cent[node]) / 2 
                         for node in G.nodes()}
        secondary_metric = diversity
        weight_primary = 0.8
    else:  # local
        # Enfoque en clustering y diversidad local
        primary_metric = clustering
        secondary_metric = degree_cent
        weight_primary = 0.6
    
    # Calcular score combinado
    combined_scores = {}
    for node in G.nodes():
        primary_score = primary_metric.get(node, 0)
        secondary_score = secondary_metric.get(node, 0)
        combined_scores[node] = (weight_primary * primary_score + 
                               (1 - weight_primary) * secondary_score)
    
    # Obtener valores para Jenks
    values = list(combined_scores.values())
    if len(values) == 0:
        return [], {}
    
    # Determinar número de clases basado en el tamaño del grafo
    n_nodes = len(values)
    if n_nodes <= 5:
        n_classes = min(2, n_nodes)
    elif n_nodes <= 15:
        n_classes = 3
    else:
        n_classes = 4
    
    # Aplicar Jenks para encontrar umbrales naturales
    try:
        breaks = jenks_natural_breaks_simple(values, n_classes)
        # Usar el penúltimo umbral como corte (clase alta)
        threshold = breaks[-2] if len(breaks) > 2 else breaks[-1]
    except:
        # Fallback: usar percentil 70
        threshold = percentile(values, 70)
    
    # Seleccionar nodos importantes
    important_nodes = [node for node, score in combined_scores.items() 
                      if score >= threshold]
    
    # Si obtenemos muy pocos nodos, tomar al menos los top 5
    min_nodes = min(5, n_nodes)
    if len(important_nodes) < min_nodes:
        sorted_nodes = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        important_nodes = [node for node, _ in sorted_nodes[:min_nodes]]
    
    # Limit the number of nodes for performance (increased for better quality)
    max_final_nodes = min(40, max(15, n_nodes // 2))  # More flexible cap: 15-40 nodes
    if len(important_nodes) > max_final_nodes:
        sorted_nodes = sorted([(node, combined_scores[node]) for node in important_nodes], 
                             key=lambda x: x[1], reverse=True)
        important_nodes = [node for node, _ in sorted_nodes[:max_final_nodes]]
    
    # Preparar métricas detalladas para los nodos seleccionados
    detailed_metrics = {}
    for node in important_nodes:
        detailed_metrics[node] = {
            'betweenness_centrality': betweenness.get(node, 0),
            'degree_centrality': degree_cent.get(node, 0),
            'diversity': diversity.get(node, 0),
            'clustering': clustering.get(node, 0),
            'combined_score': combined_scores[node],
            'degree': G.degree(node),
            'weighted_degree': sum(G[node][neighbor].get('weight', 1.0) 
                                 for neighbor in G.neighbors(node))
        }
    
    return important_nodes, detailed_metrics

def tokenize(text, analysis_type='bridges', max_terms=50, language='english', enable_lemmatization=True, exclusions=None):
    """Extract and rank the most important terms from text using centrality-based selection."""
    if exclusions is None:
        exclusions = []
    
    terms = extract_high_quality_terms(text, language=language, enable_lemmatization=enable_lemmatization, exclusions=exclusions)
    
    if not terms:
        return []
    
    # Separate compound terms (with spaces or underscores) from single terms
    compound_terms = [term for term in terms if ' ' in term or '_' in term]
    single_terms = [term for term in terms if ' ' not in term and '_' not in term]
    
    # Always preserve compound terms as they are high-quality
    preserved_terms = compound_terms.copy()
    
    # Apply centrality analysis only to single terms to avoid co-occurrence issues
    if single_terms:
        # Create preliminary graph for single terms only
        preliminary_graph = build_preliminary_graph(text, single_terms)
        
        # Select important single terms using centrality
        important_single_terms, metrics = select_important_nodes_by_centrality(
            preliminary_graph, analysis_type)
        
        # Combine preserved compound terms with selected single terms
        all_important_terms = preserved_terms + important_single_terms
    else:
        all_important_terms = preserved_terms
    
    # Limit the number of terms if needed
    if len(all_important_terms) > max_terms:
        # Prioritize compound terms, then sort single terms by centrality
        final_terms = compound_terms.copy()
        
        if len(compound_terms) < max_terms:
            remaining_slots = max_terms - len(compound_terms)
            single_sorted = [term for term in all_important_terms if term not in compound_terms]
            final_terms.extend(single_sorted[:remaining_slots])
        
        return final_terms[:max_terms]
    
    return all_important_terms

def build_preliminary_graph(text, terms):
    """Construye un grafo preliminar para análisis de centralidad."""
    sentences = re.split(r'[.!?\n]+', text)
    G = nx.Graph()
    
    # Agregar nodos
    for term in set(terms):
        G.add_node(term)
    
    # Construir conexiones basadas en co-ocurrencia en oraciones
    for sentence in sentences:
        sentence_lower = sentence.lower()
        sentence_terms = [term for term in terms if term in sentence_lower]
        
        if len(sentence_terms) >= 2:
            for term1, term2 in itertools.combinations(set(sentence_terms), 2):
                # Calcular fuerza de conexión basada en proximidad
                sentence_words = sentence_lower.split()
                try:
                    pos1 = next(i for i, word in enumerate(sentence_words) if term1 in word)
                    pos2 = next(i for i, word in enumerate(sentence_words) if term2 in word)
                    distance = abs(pos1 - pos2)
                    strength = max(0.1, 1.0 - (distance / len(sentence_words)))
                except:
                    strength = 0.5
                
                if G.has_edge(term1, term2):
                    G[term1][term2]['weight'] += strength
                else:
                    G.add_edge(term1, term2, weight=strength)
    
    return G

def build_enhanced_graph(text, important_terms, analysis_type='bridges', connection_threshold=0.3, max_sentences=200):
    """Build enhanced concept graph with improved connection logic and semantic understanding."""
    sentences = re.split(r'[.!?\n]+', text)
    
    # Limit sentences for performance with large texts
    if len(sentences) > max_sentences:
        # Take a representative sample of sentences
        total_sentences = len(sentences)
        step = max(1, total_sentences // max_sentences)
        sentences = sentences[::step][:max_sentences]
    
    G = nx.Graph()
    
    # Add nodes
    for term in important_terms:
        G.add_node(term)
    
    # Build connections with multiple strategies
    connection_cache = {}  # Cache for expensive calculations
    
    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if not sentence_lower or len(sentence_lower) < 10:  # Skip very short sentences
            continue
            
        # Find terms in sentence (optimized with compound term matching)
        sentence_terms = []
        for term in important_terms:
            # Direct match for single terms
            if ' ' not in term:
                if term in sentence_lower:
                    sentence_terms.append(term)
            else:
                # Enhanced matching for compound terms
                term_words = term.split()
                # Check if all significant words of the compound term appear in the sentence
                if len(term_words) >= 2:
                    matches = 0
                    for word in term_words:
                        if len(word) > 3:
                            # Simple accent-tolerant matching
                            word_base = word.replace('a', '[aá]').replace('e', '[eé]').replace('i', '[ií]').replace('o', '[oó]').replace('u', '[uú]').replace('n', '[nñ]').replace('c', '[cç]')
                            pattern = r'\b' + word_base + r'\b'
                            
                            if re.search(pattern, sentence_lower, re.IGNORECASE):
                                matches += 1
                            elif word in sentence_lower:  # Fallback to simple match
                                matches += 1
                    
                    # If most words match, consider the compound term present
                    if matches >= len(term_words) - 1 or matches >= 2:
                        sentence_terms.append(term)
                else:
                    # Fallback for single-word compounds
                    if term in sentence_lower:
                        sentence_terms.append(term)
        
        # Only create connections if we have multiple terms in the sentence
        if len(sentence_terms) >= 2:
            for i, term1 in enumerate(sentence_terms):
                for term2 in sentence_terms[i+1:]:  # Avoid duplicate pairs
                    
                    # Use cache for repeated term pairs
                    pair_key = tuple(sorted([term1, term2]))
                    if pair_key in connection_cache:
                        final_strength = connection_cache[pair_key]
                    else:
                        # Calculate connection strength using multiple factors
                        sentence_words = sentence_lower.split()
                        
                        try:
                            # Find positions of terms in sentence
                            pos1 = next(i for i, word in enumerate(sentence_words) 
                                       if term1 in word or word in term1)
                            pos2 = next(i for i, word in enumerate(sentence_words) 
                                       if term2 in word or word in term2)
                            
                            distance = abs(pos1 - pos2)
                            sentence_length = len(sentence_words)
                            
                            # Base strength based on proximity
                            proximity_strength = max(0.1, 1.0 - (distance / sentence_length))
                            
                            # Boost for shorter sentences (more focused connections)
                            sentence_bonus = 1.0 + (1.0 / max(sentence_length, 5))
                            
                            final_strength = proximity_strength * sentence_bonus
                            
                        except:
                            final_strength = 0.3  # Default strength
                        
                        # Cache the result
                        connection_cache[pair_key] = final_strength
                    
                    if G.has_edge(term1, term2):
                        G[term1][term2]['weight'] += final_strength
                    else:
                        G.add_edge(term1, term2, weight=final_strength)
    
    # Remove weak connections based on dynamic threshold
    if G.number_of_edges() > 0:
        edge_weights = [d['weight'] for u, v, d in G.edges(data=True)]
        # Use adaptive threshold based on weight distribution
        adaptive_threshold = max(connection_threshold, 
                               sum(edge_weights) / len(edge_weights) * 0.5)
        
        weak_edges = [(u, v) for u, v, d in G.edges(data=True) 
                     if d['weight'] < adaptive_threshold]
        G.remove_edges_from(weak_edges)
    
    # Remove isolated nodes
    isolated_nodes = [node for node in G.nodes() if G.degree(node) == 0]
    G.remove_nodes_from(isolated_nodes)
    
    # Add enhanced node attributes (optimized for large graphs)
    if G.number_of_nodes() > 0:
        n_nodes = G.number_of_nodes()
        
        # For large graphs, use simplified calculations
        if n_nodes > 50:
            # Use degree centrality (fast) as main metric
            degree_cent = nx.degree_centrality(G)
            # Approximate betweenness using degree
            betweenness = {node: degree_cent[node] * 0.5 for node in G.nodes()}
            # Skip clustering for large graphs
            clustering = {node: 0.1 for node in G.nodes()}
        else:
            # Full calculations for smaller graphs
            betweenness = nx.betweenness_centrality(G, weight='weight')
            degree_cent = nx.degree_centrality(G)
            clustering = nx.clustering(G, weight='weight')
        
        for node in G.nodes():
            diversity = calculate_network_diversity(G, node) if n_nodes <= 50 else 0.5
            G.nodes[node]['betweenness_centrality'] = betweenness.get(node, 0)
            G.nodes[node]['degree_centrality'] = degree_cent.get(node, 0)
            G.nodes[node]['diversity'] = diversity
            G.nodes[node]['clustering'] = clustering.get(node, 0)
            G.nodes[node]['degree'] = G.degree(node)
            
            # Calculate weighted degree
            weighted_degree = sum(G[node][neighbor].get('weight', 1.0) 
                                for neighbor in G.neighbors(node))
            G.nodes[node]['weighted_degree'] = weighted_degree
    
    return G

def build_graph(text, analysis_type='bridges', connection_threshold=0.5, language='english', enable_lemmatization=True, max_terms=25, exclusions=None):
    """Build a more intelligent concept graph with centrality-based node selection and performance optimizations."""
    if exclusions is None:
        exclusions = []
    
    # Use improved tokenization with centrality analysis
    important_terms = tokenize(text, analysis_type=analysis_type, max_terms=max_terms, language=language, enable_lemmatization=enable_lemmatization, exclusions=exclusions)
    
    if len(important_terms) < 2:
        # Fallback to basic approach if no important terms found
        all_terms = extract_high_quality_terms(text, language=language, enable_lemmatization=enable_lemmatization)
        important_terms = list(set(all_terms))[:max_terms]
    
    # Ensure we don't process too many terms for performance
    important_terms = important_terms[:max_terms]
    
    # Build enhanced graph
    G = build_enhanced_graph(text, important_terms, analysis_type, connection_threshold)
    
    if G.number_of_nodes() == 0:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Connections'
            }
        }
    
    # Generate insights and convert to data format
    insights = graph_insights(G, analysis_type=analysis_type)
    graph_data = graph_to_data(G, analysis_type)
    
    return {
        'nodes': graph_data['nodes'],
        'links': graph_data['links'],
        'insights': insights
    }

def graph_insights(G, topn=5, analysis_type='bridges'):
    """Enhanced graph insights with centrality-based metrics."""
    if G.number_of_nodes() == 0:
        return {
            'total_nodes': 0,
            'total_links': 0,
            'total_clusters': 0,
            'dominant_topics': [],
            'bridging_concepts': [],
            'knowledge_gaps': [],
            'analysis_type': analysis_type,
            'centrality_threshold': 0
        }
    
    num_nodes = G.number_of_nodes()
    num_links = G.number_of_edges()
    
    # Find connected components (clusters)
    clusters = list(nx.connected_components(G))
    
    # Get centrality measures
    betweenness = nx.betweenness_centrality(G, weight='weight')
    degree_cent = nx.degree_centrality(G)
    
    # Find dominant topics based on analysis type
    if analysis_type == 'bridges':
        # Prioritize betweenness centrality for bridges
        dominant_metric = betweenness
        dominant_label = "Bridge Concepts"
    elif analysis_type == 'hubs':
        # Prioritize degree centrality for hubs
        dominant_metric = degree_cent
        dominant_label = "Hub Concepts"
    else:
        # Combined approach
        combined_scores = {node: (betweenness.get(node, 0) + degree_cent.get(node, 0)) / 2 
                          for node in G.nodes()}
        dominant_metric = combined_scores
        dominant_label = "Central Concepts"
    
    dominant = sorted(dominant_metric.items(), key=lambda x: x[1], reverse=True)[:topn]
    
    # Find bridging concepts (always use betweenness for this)
    bridging = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:topn]
    
    # Find knowledge gaps using Jenks natural breaks
    bc_values = list(betweenness.values())
    if len(bc_values) > 0:
        try:
            breaks = jenks_natural_breaks_simple(bc_values, min(3, len(bc_values)))
            threshold = breaks[0] if len(breaks) > 1 else 0  # Lowest break
        except:
            threshold = sorted(bc_values)[len(bc_values)//4] if bc_values else 0
    else:
        threshold = 0
    
    # Nodes with low betweenness centrality are potential knowledge gaps
    knowledge_gaps = [node for node, bc in betweenness.items() if bc <= threshold][:topn]
    
    return {
        'total_nodes': num_nodes,
        'total_links': num_links,
        'total_clusters': len(clusters),
        'dominant_topics': [n for n, _ in dominant if n],
        'bridging_concepts': [n for n, _ in bridging if n],
        'knowledge_gaps': knowledge_gaps,
        'analysis_type': analysis_type,
        'centrality_threshold': threshold,
        'dominant_label': dominant_label
    }


def graph_to_data(G, analysis_type='bridges'):
    """Convert graph to data format with enhanced centrality-based properties."""
    if G.number_of_nodes() == 0:
        return {'nodes': [], 'links': []}
    
    nodes = []
    node_index = {}
    
    # Get centrality measures
    betweenness = nx.betweenness_centrality(G, weight='weight')
    degree_cent = nx.degree_centrality(G)
    
    # Calculate node sizes based on analysis type
    for i, node in enumerate(G.nodes()):
        node_data = G.nodes[node]
        
        bc_score = betweenness.get(node, 0)
        dc_score = degree_cent.get(node, 0)
        diversity = node_data.get('diversity', 0)
        importance = node_data.get('importance', 0)
        
        # Size based on analysis type
        if analysis_type == 'bridges':
            # Size based on betweenness centrality for bridge analysis
            size = max(8, min(25, bc_score * 100 + 8))
        elif analysis_type == 'hubs':
            # Size based on degree centrality for hub analysis
            size = max(8, min(25, dc_score * 50 + 8))
        else:
            # Combined size for global analysis
            size = max(8, min(25, importance * 40 + 8))
        
        nodes.append({
            'id': i,
            'label': node,
            'size': size,
            'importance': importance,
            'betweenness_centrality': bc_score,
            'degree_centrality': dc_score,
            'diversity': diversity,
            'degree': G.degree(node),
            'analysis_type': analysis_type
        })
        node_index[node] = i
    
    # Create links with proper weights
    links = []
    for u, v, data in G.edges(data=True):
        weight = data.get('weight', 1.0)
        links.append({
            'source': node_index[u],
            'target': node_index[v],
            'weight': weight,
            'strength': min(5, max(1, weight * 3))  # For visual thickness
        })
    
    return {'nodes': nodes, 'links': links}


def build_concept_graph(text, analysis_type='bridges', language='auto', exclusions=None):
    """
    Main function to build concept graph with centrality-based algorithms.
    
    analysis_type options:
    - 'bridges': Focus on bridging concepts (betweenness centrality)
    - 'hubs': Focus on hub concepts (degree centrality) 
    - 'global': Global analysis (combined metrics)
    - 'local': Local analysis (clustering focus)
    
    language options:
    - 'auto': Detect language automatically
    - 'spanish' or 'es': Process as Spanish
    - 'english' or 'en': Process as English
    """
    if exclusions is None:
        exclusions = []
        
    if not text or len(text.strip()) < 50:
        return {
            'graph': {'nodes': [], 'links': []},
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'centrality_threshold': 0
            }
        }
    
    # Auto-detect language if needed
    if language == 'auto':
        # Quick Spanish detection
        spanish_indicators = [
            'la ', 'el ', 'de ', 'en ', 'que ', 'y ', 'del ', 'los ', 'las ',
            'con ', 'por ', 'para ', 'son ', 'está ', 'están ', 'ser ', 'es ',
            'tecnología', 'datos', 'sistemas', 'aplicaciones', 'desarrollo',
            'inteligencia', 'automático', 'artificial', 'computación'
        ]
        
        text_lower = text.lower()
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        
        # Detect if Spanish
        if spanish_count > 3:
            language = 'spanish'
        else:
            language = 'english'
    
    G = build_graph(text, analysis_type=analysis_type, language=language, exclusions=exclusions)
    return {
        'graph': graph_to_data(G, analysis_type=analysis_type),
        'insights': graph_insights(G, analysis_type=analysis_type)
    }

async def build_enhanced_graph_with_ai(note_text, analysis_type='bridges', ai_provider=None, api_key=None, language='english', enable_lemmatization=True, max_text_length=100000, exclusions=None):
    """Build concept graph with AI enhancement and improved term selection with performance optimizations."""
    
    if exclusions is None:
        exclusions = []
    
    if not note_text or len(note_text.strip()) < 20:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Data'
            }
        }
    
    # Truncate very large texts for performance
    if len(note_text) > max_text_length:
        # Take first 70% and last 30% to preserve structure
        first_part = note_text[:int(max_text_length * 0.7)]
        last_part = note_text[-int(max_text_length * 0.3):]
        note_text = first_part + "\n...\n" + last_part
    
    # Step 1: Extract terms with improved filtering
    terms = extract_key_terms(note_text, language=language, enable_lemmatization=enable_lemmatization, max_text_length=max_text_length, exclusions=exclusions)
    if not terms:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Terms Found'
            }
        }
    
    # Step 2: Calculate term importance
    term_importance = calculate_term_importance(terms, note_text, max_sentences=100)
    
    # Step 3: AI Enhancement (if available and text is not too large)
    if ai_provider and api_key and len(note_text) <= 50000:  # Skip AI for very large texts
        try:
            enhanced_terms, ai_relationships = await enhance_terms_with_ai(
                term_importance, note_text, ai_provider, api_key, language)
            term_importance = enhanced_terms
        except Exception as e:
            print(f"AI enhancement failed: {e}")
    
    # Step 4: Select top terms for graph construction
    sorted_terms = sorted(term_importance.items(), key=lambda x: x[1], reverse=True)
    
    # Dynamic term selection based on text length
    text_length = len(note_text)
    if text_length > 50000:
        max_terms = min(20, len(sorted_terms))
    elif text_length > 20000:
        max_terms = min(25, len(sorted_terms))
    elif text_length > 10000:
        max_terms = min(30, len(sorted_terms))
    else:
        max_terms = min(35, len(sorted_terms))
    
    important_terms = [term for term, score in sorted_terms[:max_terms]]
    
    # Step 5: Build graph with improved connection logic
    G = build_enhanced_graph(note_text, important_terms, analysis_type, max_sentences=min(200, len(note_text.split('.')) // 2))
    
    if G.number_of_nodes() == 0:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Connections'
            }
        }
    
    # Step 6: Generate insights and convert to data format
    insights = graph_insights(G, analysis_type=analysis_type)
    graph_data = graph_to_data(G, analysis_type)
    
    return {
        'nodes': graph_data['nodes'],
        'links': graph_data['links'],
        'insights': insights
    }

def build_concept_graph(note_text, analysis_type='bridges', max_text_length=100000, exclusions=None):
    """Synchronous wrapper for concept graph generation (backward compatibility) with performance optimizations."""
    
    if exclusions is None:
        exclusions = []
    
    # Handle very large texts
    if len(note_text) > max_text_length:
        # Take first 70% and last 30% to preserve structure
        first_part = note_text[:int(max_text_length * 0.7)]
        last_part = note_text[-int(max_text_length * 0.3):]
        note_text = first_part + "\n...\n" + last_part
    
    # Determine max_terms based on text length for HIGH QUALITY (more generous limits)
    text_length = len(note_text)
    if text_length > 50000:
        max_terms = 80  # Significantly increased for quality
    elif text_length > 20000:
        max_terms = 100  # Significantly increased for quality
    else:
        max_terms = 120  # Significantly increased for quality
    
    # Extract terms using HIGH-QUALITY method for 80-90% quality
    all_terms = extract_high_quality_terms(note_text, max_length=50, enable_lemmatization=True, max_text_length=200000, exclusions=exclusions)
    
    # Convert to the format expected by the rest of the function
    if isinstance(all_terms, list):
        important_terms = all_terms[:max_terms]
    else:
        # If it returns a dict with frequencies, sort by frequency and take top terms
        sorted_terms = sorted(all_terms.items(), key=lambda x: x[1], reverse=True)
        important_terms = [term for term, freq in sorted_terms[:max_terms]]
    
    if not important_terms:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Terms Found'
            }
        }
    
    # Build graph using enhanced method with limited sentences for large texts
    max_sentences = min(200, len(note_text.split('.')) // 2) if text_length > 20000 else 200
    G = build_enhanced_graph(note_text, important_terms, analysis_type, max_sentences=max_sentences)
    
    if G.number_of_nodes() == 0:
        return {
            'nodes': [],
            'links': [],
            'insights': {
                'total_nodes': 0,
                'total_links': 0,
                'total_clusters': 0,
                'dominant_topics': [],
                'bridging_concepts': [],
                'knowledge_gaps': [],
                'analysis_type': analysis_type,
                'dominant_label': 'No Connections'
            }
        }
    
    # Generate insights
    insights = graph_insights(G, analysis_type=analysis_type)
    
    # Convert to data format
    graph_data = graph_to_data(G, analysis_type)
    
    return {
        'nodes': graph_data['nodes'],
        'links': graph_data['links'],
        'insights': insights
    }
