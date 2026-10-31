/** The only globals supplied by the TextileDream host page. */
declare global {
  interface Window {
    __textileDreamToken?: string;
    loadSession?: (id: string) => Promise<void>;
  }
}

export const authorToken = () => window.__textileDreamToken || '';
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : String(error);

export function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('服务器返回了无效数据');
  return value as Record<string, unknown>;
}

export async function postHost(path: string, body: unknown): Promise<Record<string, unknown>> {
  const response = await fetch('/api' + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TextileDream-Token': authorToken() },
    body: JSON.stringify(body),
  });
  const result = record(await response.json());
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : '创建探索旅程失败');
  return result;
}
