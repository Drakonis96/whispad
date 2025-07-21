import ast
import spacy
import networkx as nx
import itertools
from collections import Counter
from pathlib import Path

nlp = spacy.load('en_core_web_sm')

source = Path('backend.py').read_text()
mod = ast.parse(source)
for node in mod.body:
    if isinstance(node, ast.FunctionDef) and node.name == 'build_concept_graph':
        func_code = ast.Module(body=[node], type_ignores=[])
        compiled = compile(ast.fix_missing_locations(func_code), filename='backend_snippet', mode='exec')
        ns = {
            'nlp': nlp,
            'nx': nx,
            'itertools': itertools,
            'Counter': Counter
        }
        exec(compiled, ns)
        build_concept_graph = ns['build_concept_graph']
        break
else:
    raise RuntimeError('Function not found')


def test_build_concept_graph_basic():
    text = 'AI connects ideas. Ideas inspire innovation. Innovation drives progress.'
    G, cluster_map, insights = build_concept_graph(text)
    assert insights['total_nodes'] >= 4
    assert insights['total_links'] > 0
