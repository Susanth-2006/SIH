export const API_URL = 'http://localhost:8000'

const TOKEN_KEY = 'uip_auth_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

function authHeaders(extra = {}) {
  const token = getToken()
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra
}

async function handle(res, path, method) {
  if (res.status === 401) {
    setToken(null)
    window.dispatchEvent(new CustomEvent('uip:unauthorized'))
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `${method} ${path} failed: ${res.status}`)
  }
  return res.json()
}

export async function apiGet(path) {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeaders() })
  return handle(res, path, 'GET')
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  return handle(res, path, 'POST')
}

export async function apiPatch(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  return handle(res, path, 'PATCH')
}

export async function apiDelete(path) {
  const res = await fetch(`${API_URL}${path}`, { method: 'DELETE', headers: authHeaders() })
  return handle(res, path, 'DELETE')
}

export async function apiUpload(path, formData) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  return handle(res, path, 'POST')
}

export function resolveMedia(path) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_URL}${path.startsWith('/') ? '' : '/'}${path}`
}

export default { apiGet, apiPost, apiPatch, apiDelete, apiUpload, resolveMedia, getToken, setToken }