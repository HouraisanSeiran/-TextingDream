import { describe, expect, it } from 'vitest';
import { DEFAULT_PARAMS, generateWorld } from '../src/gen/world';
import { rasterize } from '../src/gen/raster';
import { rasterizeWindow, zoomSource } from '../src/gen/rasterWindow';

describe('inhabitable cell centres remain land after coast detailing', () => {
  it('preserves coastal town sites in both the overview and zoomed terrain', () => {
    const world = generateWorld({ ...DEFAULT_PARAMS, seed: 11, cells: 5000 });
    const raster = rasterize(world, 1, false);
    const coastal: number[] = [];
    const drowned: number[] = [];
    for (let cell = 0; cell < world.mesh.n; cell++) {
      if (world.water[cell] !== 0) continue;
      const x = Math.floor(world.mesh.x[cell]), y = Math.floor(world.mesh.y[cell]);
      if (raster.water[y * raster.w + x] !== 0) drowned.push(cell);
      const neighbours = world.mesh.adj.subarray(world.mesh.adjStart[cell], world.mesh.adjStart[cell + 1]);
      if (neighbours.some(n => world.water[n] === 1)) coastal.push(cell);
    }
    expect(coastal.length).toBeGreaterThan(10);
    expect(drowned, 'town sites submerged by the rendering pipeline').toEqual([]);
    const source = zoomSource(world, raster);
    for (const cell of coastal.filter((_, i) => i % Math.max(1, Math.floor(coastal.length / 16)) === 0)) {
      for (const scale of [2, 4]) {
        const x = Math.floor(world.mesh.x[cell] * scale), y = Math.floor(world.mesh.y[cell] * scale);
        const tile = rasterizeWindow(source, scale, x - 4, y - 4, 9, 9);
        expect(tile.water[4 * 9 + 4], `cell ${cell} at ${scale}x`).toBe(0);
      }
    }
  }, 30000);
});
