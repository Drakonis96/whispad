// Utilidades para procesar notas y generar grafos
// Todas las funciones están en TypeScript estricto.

import { UndirectedGraph } from "graphology";
import louvain from "graphology-communities-louvain";
import betweenness from "graphology-metrics/centrality/betweenness";

// Pequeñas listas de stopwords para ES y EN
const STOP_ES = new Set([
  'de','la','que','el','en','y','a','los','del','se','las','por','un','para','con','no','una','su','al','lo','como','más','pero','sus','le','ya','o','este','sí','porque','esta','entre','cuando','muy','sin','sobre','también','me','hasta','hay','donde','quien','desde','todo','nos','durante','todos','uno','les','ni','contra','otros','ese','eso','ante','ellos','e','esto','mí','antes','algunos','qué','unos','yo','otro','otras','otra','él'
]);
const STOP_EN = new Set([
  'the','and','is','in','to','of','a','that','it','for','on','with','as','was','at','by','an','be','this','have','from','or','one','had','not','but','all','were','they','his','her','she','which','we','there','can','their'
]);

// Expresiones regulares para limpieza
const URL_RE = /https?:\/\/[\w./-]+/gi;
const PUNCT_RE = /[.,!?:;()"'¿¡]/g;
const EMOJI_RE = /[\u{1F600}-\u{1F6FF}]/gu;

// Lematizador muy básico para español
function lemmatizeSpanish(token: string): string {
  return token
    .replace(/(mente|amiento|aciones|acion|adoras|adores|adora|ación|aciones|ismos|ables|ible|istas|osos|osas|idad|idades|iva|ivo|ivas|ivos)$/i, '')
    .replace(/(ando|iendo|ar|er|ir|ado|ada|idos|idas)$/i, '')
    .replace(/(es|s)$/i, '');
}

export interface GraphNode { id: string; label: string; cluster: number; centrality: number; }
export interface GraphLink { source: string; target: string; weight: number; }
export interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }

// Pre-procesa texto y devuelve tokens limpios
export function parseNote(text: string): string[] {
  const cleaned = text
    .replace(URL_RE, ' ')
    .replace(EMOJI_RE, '')
    .replace(PUNCT_RE, ' ')
    .toLowerCase();
  const tokens = cleaned.split(/\s+/).filter(Boolean);
  const result: string[] = [];
  for (const t of tokens) {
    if (STOP_ES.has(t) || STOP_EN.has(t)) continue;
    result.push(lemmatizeSpanish(t));
  }
  return result;
}

// Construye el grafo a partir de tokens
export function buildGraph(tokens: string[]): GraphData {
  const graph = new UndirectedGraph() as any;
  const window = 2;
  for (let i = 0; i < tokens.length; i++) {
    const w1 = tokens[i];
    if (!graph.hasNode(w1)) graph.addNode(w1);
    for (let j = i + 1; j < Math.min(tokens.length, i + window); j++) {
      const w2 = tokens[j];
      if (!graph.hasNode(w2)) graph.addNode(w2);
      const edgeKey = graph.edge(w1, w2);
      if (edgeKey) {
        graph.setEdgeAttribute(edgeKey, 'weight', (graph.getEdgeAttribute(edgeKey, 'weight') || 0) + 1);
      } else {
        graph.addEdge(w1, w2, { weight: 1 });
      }
    }
  }

  // Detección de comunidades Louvain
  const communities = louvain(graph);
  for (const node of graph.nodes()) {
    graph.setNodeAttribute(node, 'cluster', communities[node]);
  }

  // Centralidad intermedia (betweenness)
  const centrality = betweenness(graph, { normalized: true });
  for (const node of graph.nodes()) {
    graph.setNodeAttribute(node, 'centrality', centrality[node]);
  }

  const nodes: GraphNode[] = graph.nodes().map((id: any) => ({
    id,
    label: id,
    cluster: graph.getNodeAttribute(id, 'cluster'),
    centrality: graph.getNodeAttribute(id, 'centrality'),
  }));
  const links: GraphLink[] = graph.edges().map((key: any) => {
    const attrs = graph.getEdgeAttributes(key);
    const [source, target] = graph.extremities(key);
    return { source, target, weight: attrs.weight };
  });

  return { nodes, links };
}

// Asigna colores HEX por cluster
export function colorByCluster(cluster: number): string {
  const colors = [
    '#e6194b','#3cb44b','#ffe119','#4363d8','#f58231',
    '#911eb4','#46f0f0','#f032e6','#bcf60c','#fabebe',
    '#008080','#e6beff','#9a6324','#fffac8','#800000'
  ];
  return colors[cluster % colors.length];
}

// Escala lineal de tamaño 5-25px según centralidad (0..1)
export function sizeByCentrality(value: number): number {
  const min = 5, max = 25;
  return min + (max - min) * value;
}
