import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

/**
 * Secure, encrypted-at-rest storage for the JWT and the minimal session info
 * needed to restore it (username/role), using the platform keychain/keystore
 * via expo-secure-store — never plain AsyncStorage for credentials.
 *
 * expo-secure-store has no web implementation (there is no OS keychain in a
 * browser) — found while verifying this app via `expo start --web` in an
 * environment with no iOS Simulator/Android emulator available. The web
 * target is not a real deliverable for this app (spec: native iOS/Android
 * only); it exists here purely so the flows can be exercised without native
 * tooling. On web we fall back to localStorage, which is NOT secure storage
 * — this is called out explicitly rather than silently downgraded.
 */
const TOKEN_KEY = 'pramaan_access_token';
const SESSION_KEY = 'pramaan_session';

export interface StoredSession {
  token: string;
  username: string;
  role: string;
}

const isWeb = Platform.OS === 'web';

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function getItem(key: string): Promise<string | null> {
  if (isWeb) {
    return localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

async function deleteItem(key: string): Promise<void> {
  if (isWeb) {
    localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function saveSession(session: StoredSession): Promise<void> {
  await setItem(TOKEN_KEY, session.token);
  await setItem(SESSION_KEY, JSON.stringify({ username: session.username, role: session.role }));
}

export async function loadSession(): Promise<StoredSession | null> {
  const [token, sessionJson] = await Promise.all([getItem(TOKEN_KEY), getItem(SESSION_KEY)]);
  if (!token || !sessionJson) return null;
  try {
    const { username, role } = JSON.parse(sessionJson) as { username: string; role: string };
    return { token, username, role };
  } catch {
    return null;
  }
}

export async function clearSession(): Promise<void> {
  await deleteItem(TOKEN_KEY);
  await deleteItem(SESSION_KEY);
}
