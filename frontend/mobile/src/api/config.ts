/**
 * API base URL configuration.
 *
 * Set via the EXPO_PUBLIC_API_URL environment variable (Expo loads any
 * EXPO_PUBLIC_* var from a .env file at the project root automatically —
 * see .env.example). Never hardcode "localhost": on a physical device
 * "localhost" refers to the phone itself, not your development machine.
 *
 * See ../../../../docs/mobile.md for the exact URL to use per target
 * (iOS simulator, Android emulator, physical device).
 */
const DEFAULT_DEV_URL = 'http://localhost:8000';

export const API_BASE_URL: string = process.env.EXPO_PUBLIC_API_URL?.trim() || DEFAULT_DEV_URL;

if (__DEV__ && !process.env.EXPO_PUBLIC_API_URL) {
  // eslint-disable-next-line no-console
  console.warn(
    `[PraMaan] EXPO_PUBLIC_API_URL is not set — falling back to ${DEFAULT_DEV_URL}. ` +
      'This only works for the iOS Simulator. For a physical device or Android emulator, ' +
      'set EXPO_PUBLIC_API_URL in frontend/mobile/.env — see docs/mobile.md.'
  );
}
