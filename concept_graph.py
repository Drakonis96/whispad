import re
import itertools
import networkx as nx

STOPWORDS = {
    'the','and','a','an','to','of','in','for','on','with','at','by','from','up','about','into','over','after','under','above','below','is','are','was','were','be','been','being','have','has','had','do','does','did','but','if','or','because','as','until','while','than','that','so','such','too','very','can','will','just'
}

def tokenize(text):
    words = re.findall(r"[A-Za-z']+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def build_graph(text):
    sentences = re.split(r'[.!?\n]+', text)
    G = nx.Graph()
    for sentence in sentences:
        tokens = tokenize(sentence)
        unique = sorted(set(tokens))
        for w in unique:
            if not G.has_node(w):
                G.add_node(w)
        for w1, w2 in itertools.combinations(unique, 2):
            if G.has_edge(w1, w2):
                G[w1][w2]['weight'] += 1
            else:
                G.add_edge(w1, w2, weight=1)
    return G


def graph_insights(G, topn=5):
    num_nodes = G.number_of_nodes()
    num_links = G.number_of_edges()
    clusters = list(nx.connected_components(G))
    dominant = sorted(G.degree(weight='weight'), key=lambda x: x[1], reverse=True)[:topn]
    betw = nx.betweenness_centrality(G)
    bridging = sorted(betw.items(), key=lambda x: x[1], reverse=True)[:topn]
    isolated = [n for n in G.nodes if G.degree(n) <= 1]
    return {
        'total_nodes': num_nodes,
        'total_links': num_links,
        'total_clusters': len(clusters),
        'dominant_topics': [n for n,_ in dominant],
        'bridging_concepts': [n for n,_ in bridging],
        'knowledge_gaps': isolated[:topn]
    }


def graph_to_data(G):
    nodes = [{'id': i, 'label': n} for i, n in enumerate(G.nodes())]
    node_index = {n: i for i, n in enumerate(G.nodes())}
    links = [{'source': node_index[u], 'target': node_index[v], 'weight': d['weight']} for u,v,d in G.edges(data=True)]
    return {'nodes': nodes, 'links': links}


def build_concept_graph(text):
    G = build_graph(text)
    return {
        'graph': graph_to_data(G),
        'insights': graph_insights(G)
    }
