import { expose } from 'comlink';
import { parseNote, buildGraph } from '../utils/graphUtils';

const api = {
  async process(text: string) {
    const tokens = parseNote(text);
    const graph = buildGraph(tokens);
    return graph;
  }
};

expose(api);
