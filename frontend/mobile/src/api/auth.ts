import { apiClient } from './client';
import type { TokenOut, UserOut } from '../types/api';

export function login(username: string, password: string): Promise<TokenOut> {
  return apiClient.postFormUrlEncoded<TokenOut>('/api/auth/login', { username, password });
}

/** Used on app launch to validate a restored token is still good and to pick
 * up any server-side role change without requiring the user to log in again. */
export function fetchCurrentUser(): Promise<UserOut> {
  return apiClient.get<UserOut>('/api/auth/me');
}
