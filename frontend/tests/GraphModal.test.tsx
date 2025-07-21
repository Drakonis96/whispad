import { parseNote } from '../src/utils/graphUtils';

test('parseNote elimina stopwords y lematiza', () => {
  const txt = 'Los perros comen y los gatos duermen.';
  const tokens = parseNote(txt);
  expect(tokens).toEqual(['perro','comen','gato','duermen']);
});

// import { test as it, expect } from '@playwright/test';
// import React from 'react';
// import { render, fireEvent } from '@testing-library/react';
// // import { GraphModal } from '../src/components/GraphModal';
// // 
// it('abre modal y muestra canvas', async ({ page }) => {
//   const { getByText } = render(<GraphModal noteId="1" text="hola mundo" onClose={() => {}} />);
//   await page.waitForSelector('canvas');
//   expect(page.locator('canvas')).toBeTruthy();
// });

test('performance 5000 words', () => {
  const longText = Array(5000).fill('palabra').join(' ');
  const start = performance.now();
  const tokens = parseNote(longText);
  const graph = require('../src/utils/graphUtils').buildGraph(tokens);
  const end = performance.now();
  const fps = 1000 / (end - start);
  expect(fps).toBeGreaterThanOrEqual(55);
});
