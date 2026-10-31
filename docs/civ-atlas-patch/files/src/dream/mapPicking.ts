import type { NativeWorld } from './bridge';

export interface MapSelection {
  cell: number; cityId: number | null; x: number; y: number;
  biome: number; elevation: number; temperature: number; precipitation: number;
}

export function selectCity(loaded: NativeWorld, cityId: number, cell: number): MapSelection {
  const w = loaded.world;
  return { cell, cityId, x: w.mesh.x[cell], y: w.mesh.y[cell], biome: w.biome[cell],
    elevation: w.elevation[cell], temperature: w.temperature[cell], precipitation: w.precipitation[cell] };
}

/** Hit only visible symbols, then inspect the exact terrain pixel under the pointer. */
export function pickMapPoint(loaded: NativeWorld, visible: ReadonlySet<number>, x: number, y: number, scale: number): MapSelection | null {
  const { world: w, raster: r } = loaded;
  if (x < 0 || y < 0 || x >= w.width || y >= w.height) return null;
  let nearest = null;
  let distance = 12;
  for (const city of loaded.civ?.settlements ?? []) {
    if (!visible.has(city.id)) continue;
    const d = Math.hypot(w.mesh.x[city.cell] - x, w.mesh.y[city.cell] - y) * scale;
    if (d < distance) { distance = d; nearest = city; }
  }
  if (nearest) return selectCity(loaded, nearest.id, nearest.cell);
  const pixel = Math.floor(y * r.scale) * r.w + Math.floor(x * r.scale);
  return { cell: r.cell[pixel], cityId: null, x, y, biome: r.biome[pixel],
    elevation: r.elev[pixel], temperature: r.temp[pixel], precipitation: r.precip[pixel] };
}
