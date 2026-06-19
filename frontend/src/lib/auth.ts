// Auth helpers for the BFF.
//
// Token storage: localStorage. This is a deliberate trade-off — it survives page
// reloads (nicer UX, no bounce to login on refresh) at the cost of XSS exposure
// (any injected script can read it; an httpOnly cookie could not). Documented for
// SECURITY.md in Issue #5.

export const PROXY_URL = 'http://localhost:8000'
const TOKEN_KEY = 'auth_token'

// localStorage only exists in the browser; guard for SSR.
export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(TOKEN_KEY)
}

/** Thrown when the proxy rejects the token (401) so callers can redirect. */
export class UnauthorizedError extends Error {}

/** POST credentials to the proxy and store the returned JWT. */
export async function login(username: string, password: string): Promise<void> {
  const res = await fetch(`${PROXY_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error('Invalid username or password')
  const data = (await res.json()) as { access_token: string }
  setToken(data.access_token)
}

/** fetch() against the proxy with the bearer token attached. */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${PROXY_URL}${path}`, { ...init, headers })
  if (res.status === 401) {
    // Token missing/expired/invalid: drop it and let the caller redirect.
    clearToken()
    throw new UnauthorizedError('Unauthorized')
  }
  return res
}
