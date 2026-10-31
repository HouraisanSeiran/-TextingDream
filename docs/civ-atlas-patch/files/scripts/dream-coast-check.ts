// Read-only diagnostic against an exported world; no world data is rewritten.
import { readFileSync } from 'node:fs';
import { splitParts } from '../src/dream/bridge';
import { readPart } from '../src/gen/snapshot';
import { rasterize, rasterBase } from '../src/gen/raster';
import type { World } from '../src/gen/world';
import type { Civ } from '../src/gen/civ/types';
const { parts } = splitParts(new Uint8Array(readFileSync(process.argv[2])));
const world = await readPart(parts.find(p => p.name === 'map')!) as World;
const civ = await readPart(parts.find(p => p.name === 'civ')!) as Civ;
const raster = rasterize(world, 1, true);
const base = rasterBase(world, 1);
const wet = civ.settlements.flatMap(s => {
  const x = world.mesh.x[s.cell], y = world.mesh.y[s.cell];
  const pixel = Math.min(raster.h - 1, Math.floor(y * raster.scale)) * raster.w + ((Math.floor(x * raster.scale) % raster.w) + raster.w) % raster.w;
  const xyz = world.mesh.xyz;
  const projectedX = (Math.atan2(xyz[3*s.cell+1], xyz[3*s.cell]) + Math.PI) / (2*Math.PI) * world.width;
  const projectedY = (Math.PI/2-Math.asin(xyz[3*s.cell+2])) / Math.PI * world.height;
  return raster.water[pixel] ? [{ name: s.name, cell: s.cell, x, y, coordinateError: Math.hypot(x-projectedX,y-projectedY), worldWater: world.water[s.cell], elevation: world.elevation[s.cell], water: raster.water[pixel], pixelElevation: raster.elev[pixel], base: base.elev[pixel], nearest: raster.cell[pixel], weights: [base.wa[pixel],base.wb[pixel]] }] : [];
});
console.log(JSON.stringify({ settlements: civ.settlements.length, wet: wet.length, examples: wet.slice(0, 12) }, null, 2));
if (wet.length) process.exitCode = 1;
