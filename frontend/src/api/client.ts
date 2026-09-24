import { API_BASE_URL } from '@/config/env'
import type { RefreshTokenResponse } from '@/types/api'

// IN-MEMORY storage for short-lived access token (never stored in localStorage or console logged)
let inMemoryAccessToken: string | null = null

// Refresh token key in localStorage
const REFRESH_TOKEN_KEY = 'medic_refresh_token'

// Event listener for auth state changes
type AuthChangeListener = (authenticated: boolean) => void
const authChangeListeners: Set<AuthChangeListener> = new Set()

export function onAuthStateChange(listener: AuthChangeListener) {
  authChangeListeners.add(listener)
  return () => {
    authChangeListeners.delete(listener)
  }
}

function notifyAuthState(authenticated: boolean) {
  authChangeListeners.forEach((l) => l(authenticated))
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken
}

export function setAccessToken(token: string | null) {
  inMemoryAccessToken = token
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string | null) {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

export function clearAuth() {
  inMemoryAccessToken = null
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  notifyAuthState(false)
}

// Queue for handling 401 refresh deduplication
let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

export async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) {
    clearAuth()
    return null
  }

  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/token/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh }),
      })

      if (!res.ok) {
        clearAuth()
        return null
      }

      const data: RefreshTokenResponse = await res.json()
      setAccessToken(data.access)
      return data.access
    } catch {
      clearAuth()
      return null
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean
}

/**
 * Robust fetch wrapper handling:
 * - Bearer authorization injection
 * - Automatic silent refresh on 401
 * - Automatic Content-Type header unless FormData
 * - Error unwrapping
 */
export async function apiFetch<T>(endpoint: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipAuth = false, headers = {}, ...rest } = options

  // Normalize endpoint to prevent double slashes or missing base
  let url = endpoint
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    url = `${API_BASE_URL}${cleanEndpoint}`
  }

  const reqHeaders: Record<string, string> = {}

  // Automatically add Content-Type for non-FormData
  if (!(rest.body instanceof FormData)) {
    reqHeaders['Content-Type'] = 'application/json'
  }

  // Merge any custom headers
  if (headers instanceof Headers) {
    headers.forEach((val, key) => {
      reqHeaders[key] = val
    })
  } else if (Array.isArray(headers)) {
    headers.forEach(([key, val]) => {
      reqHeaders[key] = val
    })
  } else if (typeof headers === 'object') {
    Object.assign(reqHeaders, headers)
  }

  // Inject Authorization if not skipped
  if (!skipAuth) {
    let token = getAccessToken()
    if (!token) {
      // Try refresh if we have a refresh token
      token = await refreshAccessToken()
    }
    if (token) {
      reqHeaders['Authorization'] = `Bearer ${token}`
    }
  }

  let response = await fetch(url, {
    ...rest,
    headers: reqHeaders,
  })

  // Silent refresh on 401
  if (response.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      reqHeaders['Authorization'] = `Bearer ${newToken}`
      response = await fetch(url, {
        ...rest,
        headers: reqHeaders,
      })
    } else {
      clearAuth()
      throw new Error('Session expired. Please log in again.')
    }
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status} ${response.statusText}`
    try {
      const errData = await response.json()
      if (errData.detail) {
        errorMessage = errData.detail
      } else if (errData.message) {
        errorMessage = errData.message
      } else if (typeof errData === 'object') {
        const firstKey = Object.keys(errData)[0]
        if (firstKey) {
          const val = errData[firstKey]
          errorMessage = Array.isArray(val) ? `${firstKey}: ${val[0]}` : `${firstKey}: ${val}`
        }
      }
    } catch {
      // Fallback to response status text
    }
    throw new Error(errorMessage)
  }

  // Handle empty responses (like 204 or empty body)
  const contentType = response.headers.get('content-type')
  if (response.status === 204 || !contentType || !contentType.includes('application/json')) {
    return {} as T
  }

  return response.json() as Promise<T>
}

/**
 * Securely fetch wound image file as Blob and return an object URL.
 * Never use plain <img src> with protected clinical media.
 */
export async function fetchSecureImageBlobUrl(fileUrlOrRelativePath: string): Promise<string> {
  let url = fileUrlOrRelativePath
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    const cleanPath = fileUrlOrRelativePath.startsWith('/')
      ? fileUrlOrRelativePath
      : `/${fileUrlOrRelativePath}`
    // If the path already has /api, construct using base without /api
    if (cleanPath.startsWith('/api/')) {
      const rootBase = API_BASE_URL.replace(/\/api$/, '')
      url = `${rootBase}${cleanPath}`
    } else {
      url = `${API_BASE_URL}${cleanPath}`
    }
  }

  let token = getAccessToken()
  if (!token) {
    token = await refreshAccessToken()
  }

  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let response = await fetch(url, { headers })

  if (response.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`
      response = await fetch(url, { headers })
    }
  }

  if (!response.ok) {
    throw new Error(`Failed to load image (${response.status})`)
  }

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
