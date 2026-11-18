const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export async function apiFetch(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  if (options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
    headers.set('X-FinStep-Request', '1')
  }
  const response = await fetch(`${base}${path}`, { ...options, headers, credentials: 'include' })
  if (response.status === 401) window.dispatchEvent(new Event('finstep-auth-expired'))
  return response
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : '요청을 처리하지 못했습니다. 다시 시도해 주세요.')
  }
  return response.json() as Promise<T>
}
