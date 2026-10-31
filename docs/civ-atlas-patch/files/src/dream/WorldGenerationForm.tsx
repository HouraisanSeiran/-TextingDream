import type { Dispatch, SetStateAction } from 'react';
import { defaultAuthorParams, PARAM_FIELDS, type GenerateProgress, type WorldParams } from './generate';

export function WorldGenerationForm({ params, setParams, creating, progress, onGenerate }: {
  params: WorldParams; setParams: Dispatch<SetStateAction<WorldParams>>;
  creating: boolean; progress: GenerateProgress | null; onGenerate: () => Promise<void>;
}) {
  return <form className="dream-create" onSubmit={event => { event.preventDefault(); void onGenerate(); }}>
    <div className="dream-create-heading"><strong>生成参数</strong><span>使用预设，或调整这张世界的基础数据。</span></div>
    <div className="dream-param-grid">
      {PARAM_FIELDS.map(field => <label key={field.key} title={field.hint}>
        {field.label}
        <input type="number" required value={Number.isNaN(params[field.key]) ? '' : params[field.key]}
          min={field.min} max={field.max} step={field.step} disabled={creating}
          onChange={event => {
            const value = event.currentTarget.valueAsNumber;
            setParams(old => ({ ...old, [field.key]: value }));
          }} />
      </label>)}
    </div>
    {creating && progress && <progress aria-label="世界生成进度" value={progress.pct} max={100} />}
    <div className="dream-create-actions">
      <button type="button" disabled={creating} onClick={() => setParams(old => ({ ...old, seed: defaultAuthorParams().seed }))}>随机种子</button>
      <button type="submit" disabled={creating} className="primary">{creating ? '生成中…' : '生成并登记'}</button>
    </div>
  </form>;
}
