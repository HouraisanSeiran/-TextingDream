import { afterEach, describe, expect, it, vi } from 'vitest';
import { validateParameters } from '../src/dream/parameters';
import { DEFAULT_PARAMS } from '../src/gen/world';
import { readUrl } from '../src/ui/appLocation';
import { listNativeWorlds, nativeWorldMeta } from '../src/dream/bridge';

afterEach(() => vi.unstubAllGlobals());

describe('host API response boundaries', () => {
  const respond = (body: unknown, status = 200) => {
    vi.stubGlobal('window', { __textileDreamToken: 'test' });
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })));
  };
  it('accepts an empty list but does not hide a malformed success response', async () => {
    respond({ worlds: [] });
    await expect(listNativeWorlds()).resolves.toEqual([]);
    respond({ unexpected: [] });
    await expect(listNativeWorlds()).rejects.toThrow('世界清单格式不正确');
  });
  it('rejects records without a selectable source ID', async () => {
    respond({ worlds: [{ world_id: 'w' }] });
    await expect(listNativeWorlds()).rejects.toThrow('世界清单缺少原件编号');
  });
  it('keeps server errors available to the retry UI', async () => {
    respond({ detail: '服务暂不可用' }, 503);
    await expect(listNativeWorlds()).rejects.toThrow('服务暂不可用');
  });
  it('validates metadata before snapshot rendering', async () => {
    respond({ identity: { world_id: 12 }, parts: [] });
    await expect(nativeWorldMeta('source')).rejects.toThrow('文本字段');
  });
});

describe('world form validation before worker creation', () => {
  const params = { ...DEFAULT_PARAMS, cells: 16000, seed: 42 };
  it('accepts supported defaults', () => expect(() => validateParameters(params)).not.toThrow());
  it.each([NaN, Infinity, 0, 90001])('rejects invalid cell count %s', cells => {
    expect(() => validateParameters({ ...params, cells })).toThrow();
  });
  it('rejects fractional integer fields but accepts fractional climate values', () => {
    expect(() => validateParameters({ ...params, seed: 1.5 })).toThrow();
    expect(() => validateParameters({ ...params, rainfall: 1.25 })).not.toThrow();
  });
});

describe('App URL compatibility after extraction', () => {
  it('keeps old satellite links and wraps longitude', () => {
    const result = readUrl({ search: '?style=realistic&lon=540&grat=1', hash: '' });
    expect(result.style).toBe('realistic');
    expect(result.sat).toBe('classic');
    expect(Math.abs(result.lon!)).toBe(180);
    expect(result.grat).toBe(30);
  });
  it('retains defaults for empty and nonnumeric input; clamps finite outliers', () => {
    const result = readUrl({ search: '?seed=&rainfall=NaN&cells=999999999&proj=invalid&gen=bad', hash: '' });
    expect(result.params.seed).toBe(DEFAULT_PARAMS.seed);
    expect(result.params.rainfall).toBe(DEFAULT_PARAMS.rainfall);
    expect(result.params.cells).toBeLessThan(999999999);
    expect(result.proj).toBe('equirect');
    expect(result.gen).toBe(0);
  });
  it('recognizes new map links', () => {
    const result = readUrl({ search: '?map=satellite&sat=classic&fill=polities', hash: '' });
    expect(result.mapView?.base).toBe('satellite');
    expect(result.sat).toBe('classic');
  });
});
