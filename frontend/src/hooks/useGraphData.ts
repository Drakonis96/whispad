import { useEffect } from 'react';
import { create } from 'zustand';
import { useAsync } from 'react-use';
import { wrap } from 'comlink';
import type { GraphData } from '../utils/graphUtils';

interface GraphStore {
  graphs: Record<string, { hash: string; data: GraphData }>;
  setGraph: (id: string, hash: string, data: GraphData) => void;
}

const useStore = create<GraphStore>((set) => ({
  graphs: {},
  setGraph: (id, hash, data) => set((s) => ({ graphs: { ...s.graphs, [id]: { hash, data } } })),
}));

const workerPromise = import('../workers/graphWorker?worker').then((mod) => new mod.default());

export function useGraphData(noteId: string, text: string) {
  const { graphs, setGraph } = useStore();
  const hash = `${text.length}_${text.charCodeAt(0)}`;
  const existing = graphs[noteId];

  const { value } = useAsync(async () => {
    if (existing && existing.hash === hash) return existing.data;
    const Worker = await workerPromise;
    const worker = wrap<{
      process(text: string): Promise<GraphData>;
    }>(Worker);
    const data = await worker.process(text);
    setGraph(noteId, hash, data);
    worker["terminate" as any]?.();
    return data;
  }, [text]);

  return value;
}
