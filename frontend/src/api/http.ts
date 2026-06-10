// 极简 fetch 封装：统一 /api 前缀（开发期由 Vite 代理到 FastAPI:8000）。
// 错误时抛出带 status 的 Error，便于上层按 404 等状态分支处理。

const BASE = '/api'

export interface HttpError extends Error {
  status?: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}${path}`, init)
  } catch (e) {
    const err: HttpError = new Error(e instanceof Error ? e.message : '网络请求失败')
    throw err
  }
  if (!resp.ok) {
    const err: HttpError = new Error(`HTTP ${resp.status}`)
    err.status = resp.status
    throw err
  }
  return resp.json() as Promise<T>
}

export function getJson<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
