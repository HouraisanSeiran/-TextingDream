import { describe, expect, it } from 'vitest';
import { DEFAULT_PARAMS, generateWorld } from '../src/gen/world';
import { rasterize } from '../src/gen/raster';
import type { NativeWorld } from '../src/dream/bridge';
import type { Civ } from '../src/gen/civ/types';
import { pickMapPoint } from '../src/dream/mapPicking';

describe('map inspector matches what is visible', () => {
  it('reads sea pixels instead of the nearest inland cell and ignores hidden towns', () => {
    const world = generateWorld({ ...DEFAULT_PARAMS, seed: 11, cells: 5000 });
    const raster = rasterize(world, 1, false);
    const loaded: NativeWorld = { world, raster, civ: null, storyRevision: null,
      identity: { contentSha256: null, worldId: null, generator: null, snapshotFormat: null, importId: null } };
    const pixel = raster.water.findIndex((water, i) => water === 1 && world.water[raster.cell[i]] === 0);
    expect(pixel).toBeGreaterThan(-1);
    const picked = pickMapPoint(loaded, new Set(), pixel % raster.w + 0.5, Math.floor(pixel / raster.w) + 0.5, 1)!;
    expect(picked.cityId).toBeNull();
    expect(picked.biome).toBe(raster.biome[pixel]);
    expect(picked.elevation).toBeLessThan(0);
    const cell = raster.cell[pixel];
    loaded.civ = { settlements: [{ id: 7, cell }] } as Civ;
    const x = world.mesh.x[cell], y = world.mesh.y[cell];
    expect(pickMapPoint(loaded, new Set(), x, y, 1)?.cityId).toBeNull();
    expect(pickMapPoint(loaded, new Set([7]), x, y, 1)?.cityId).toBe(7);
    expect(pickMapPoint(loaded, new Set(), world.width, 10, 1)).toBeNull();
    expect(pickMapPoint(loaded, new Set(), 10, world.height, 1)).toBeNull();
  });
});
