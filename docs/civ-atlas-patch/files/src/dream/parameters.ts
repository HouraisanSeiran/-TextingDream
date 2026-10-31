import type { WorldParams } from '../gen/world';

/** 作者能改的那几项，名字与上游参数一致（不另起一套）。 */
export const PARAM_FIELDS: { key: keyof WorldParams; label: string; min: number; max: number;
                              step: number; hint: string }[] = [
  { key: 'seed', label: '种子', min: 1, max: 2147483646, step: 1,
    hint: '同一个种子 + 同一套参数 = 同一个世界' },
  { key: 'cells', label: '地块数', min: 6000, max: 90000, step: 1000,
    hint: '越多越细、越慢' },
  { key: 'landFraction', label: '陆地比例', min: 0.05, max: 0.95, step: 0.01,
    hint: '整颗星球上陆地的占比' },
  { key: 'plates', label: '板块数', min: 4, max: 80, step: 1,
    hint: '越多陆地越碎、岛越多' },
  { key: 'mountains', label: '山脉强度', min: 0, max: 2, step: 0.05, hint: '' },
  { key: 'temperature', label: '气温偏移', min: -2, max: 2, step: 0.05, hint: '' },
  { key: 'rainfall', label: '降水偏移', min: 0, max: 2, step: 0.05, hint: '' },
  { key: 'continents', label: '主要大陆', min: 0, max: 5, step: 1,
    hint: '0 = 按种子定，2—5 块另有群岛' },
  { key: 'gather', label: '大陆聚拢', min: 0, max: 1, step: 0.05,
    hint: '0 = 彼此尽量远，1 = 挤在一起留大片大洋' },
  { key: 'rugged', label: '破碎度', min: 0, max: 2, step: 0.05,
    hint: '小 = 大陆完整、海岸平直；大 = 支离破碎' },
  { key: 'hardness', label: '板块硬度', min: 0, max: 2, step: 0.05,
    hint: '硬 = 内陆平坦、山脉窄' },
  { key: 'north', label: '陆地偏向半球', min: -1, max: 1, step: 0.05,
    hint: '-1 南，0 均匀，1 北' },
];



/** Validate at the worker boundary too: HTML controls are not the only caller. */
export function validateParameters(params: WorldParams): void {
  for (const field of PARAM_FIELDS) {
    const value = params[field.key];
    if (!Number.isFinite(value) || value < field.min || value > field.max ||
        (field.step === 1 && !Number.isInteger(value))) {
      throw new Error(`${field.label}必须是 ${field.min} 到 ${field.max} 之间的${field.step === 1 ? '整数' : '数值'}`);
    }
  }
}
