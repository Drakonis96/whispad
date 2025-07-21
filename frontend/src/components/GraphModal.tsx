import React, { useState, useMemo, useRef } from 'react';
import ReactDOM from 'react-dom';
import * as THREE from "three";
import { colorByCluster, sizeByCentrality, GraphData } from '../utils/graphUtils';
import { useGraphData } from '../hooks/useGraphData';

interface Props {
  noteId: string;
  text: string;
  onClose: () => void;
}

const LazyGraph = React.lazy(() => import('react-force-graph-3d'));

export function GraphModal({ noteId, text, onClose }: Props) {
  const graph = useGraphData(noteId, text);
  const [sizeMetric, setSizeMetric] = useState<'none' | 'degree' | 'bc'>('bc');
  const container = document.getElementById('modal-root') || document.body;
  const fgRef = useRef<ForceGraph3D | null>(null);

  const data = useMemo<GraphData | undefined>(() => graph, [graph]);

  if (!container) return null;

  return ReactDOM.createPortal(
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', zIndex: 1000
      }}
    >
      <div style={{ position: 'relative', background: '#0d1117', padding: 20, boxShadow: '0 0 15px rgba(0,0,0,0.5)' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 10, right: 10 }}>Cerrar</button>
        <select value={sizeMetric} onChange={e => setSizeMetric(e.target.value as any)}>
          <option value="degree">degree</option>
          <option value="bc">BC</option>
          <option value="none">none</option>
        </select>
        <button
          onClick={() => {
            if (!data) return;
            const nodesCsv = data.nodes.map(n => `${n.id},${n.label},${n.cluster},${n.centrality}`).join('\n');
            const linksCsv = data.links.map(l => `${l.source},${l.target},${l.weight}`).join('\n');
            const blobNodes = new Blob([nodesCsv], { type: 'text/csv' });
            const blobLinks = new Blob([linksCsv], { type: 'text/csv' });
            const a1 = document.createElement('a');
            a1.href = URL.createObjectURL(blobNodes);
            a1.download = 'nodes.csv';
            a1.click();
            const a2 = document.createElement('a');
            a2.href = URL.createObjectURL(blobLinks);
            a2.download = 'links.csv';
            a2.click();
          }}
        >Exportar CSV</button>
        <React.Suspense fallback={<div>Cargando...</div>}>
          {data && (
            <LazyGraph
              ref={fgRef}
              graphData={data}
              backgroundColor="#0d1117"
              nodeAutoColorBy="cluster"
              nodeThreeObject={node => {
                const geometry = new THREE.SphereGeometry(sizeByCentrality(node.centrality), 16, 16);
                const material = new THREE.MeshLambertMaterial({ color: colorByCluster(node.cluster), emissive: colorByCluster(node.cluster) });
                return new THREE.Mesh(geometry, material);
              }}
              onNodeClick={(node) => {
                const cluster = (node as any).cluster;
                if (!data) return;
                fgRef.current?.graphData().nodes.forEach((n: any) => {
                  n.__threeObj.material.opacity = n.cluster === cluster ? 1 : 0.1;
                });
                fgRef.current?.graphData().links.forEach((l: any) => {
                  l.__line.material.opacity = ((l.source as any).cluster === cluster || (l.target as any).cluster === cluster) ? 1 : 0.05;
                });
              }}
              nodeLabel={node => `${node.label} (BC: ${node.centrality.toFixed(2)})\nCluster: ${node.cluster}`}
              linkOpacity={0.3}
              enableNodeDrag={true}
            />
          )}
        </React.Suspense>
      </div>
    </div>,
    container
  );
}
