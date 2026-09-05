import { API_BASE_URL } from './config';
import { ApiError, NetworkError } from './errors';

/** Set by AuthContext at startup so the client can react to a 401 by logging
 * out — avoids a circular import between the client and the auth context. */
let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

/** Exposed so other request paths that don't go through request() below (the
 * scan-upload path — see scans.ts — uses expo-file-system's native upload
 * task instead of fetch()) can still trigger the same "log out on 401"
 * behavior instead of duplicating the onUnauthorized wiring. */
export function notifyUnauthorized(): void {
  onUnauthorized?.();
}

let currentToken: string | null = null;
export function setAuthToken(token: string | null): void {
  currentToken = token;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (!options.skipAuth && currentToken) {
    headers['Authorization'] = `Bearer ${currentToken}`;
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: options.method ?? 'GET', headers, body });
  } catch {
    throw new NetworkError();
  }

  if (response.status === 401 && !options.skipAuth) {
    onUnauthorized?.();
    throw new ApiError(401, 'Session expired');
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data?.detail === 'string') detail = data.detail;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  /** Login uses application/x-www-form-urlencoded (OAuth2PasswordRequestForm on
   * the backend), not JSON — a deliberate exception to the json-by-default rule. */
  postFormUrlEncoded: async <T>(path: string, fields: Record<string, string>): Promise<T> => {
    const body = new URLSearchParams(fields).toString();
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
    } catch {
      throw new NetworkError();
    }
    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        if (typeof data?.detail === 'string') detail = data.detail;
      } catch {
        // ignore
      }
      throw new ApiError(response.status, detail);
    }
    return (await response.json()) as T;
  },
};

/** Builds an authenticated image URL. React Native's <Image> can't attach an
 * Authorization header to a plain uri, so screens fetch the image as a blob
 * and convert it to a data/object URL — see useAuthenticatedImage. */
export function scanImagePath(scanId: string): string {
  return `/api/scans/${scanId}/image`;
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function getAuthToken(): string | null {
  return currentToken;
}
