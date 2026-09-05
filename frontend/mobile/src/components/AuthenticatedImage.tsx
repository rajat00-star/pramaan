import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, ImageStyle, StyleProp, StyleSheet, View } from 'react-native';

import { apiUrl, getAuthToken, scanImagePath } from '../api/client';
import { colors } from '../theme/colors';

interface Props {
  scanId: string;
  style?: StyleProp<ImageStyle>;
}

/**
 * Renders the REAL uploaded product image for a scan via the authenticated
 * `GET /api/scans/{id}/image` endpoint.
 *
 * React Native's <Image> supports per-request `headers` on a remote `uri`
 * source on iOS/Android, but react-native-web's Image maps to a plain
 * browser <img> tag, which cannot attach a custom Authorization header at
 * all — verified directly (the image silently never loaded under web
 * preview, the only way to test this app without a physical device/
 * simulator in this environment). Fetching the bytes manually with fetch()
 * and converting to a data URI works identically on every platform, so
 * that's what this component does instead of relying on the native-only
 * headers option.
 */
export function AuthenticatedImage({ scanId, style }: Props) {
  const [dataUri, setDataUri] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDataUri(null);
    setFailed(false);

    (async () => {
      const token = getAuthToken();
      try {
        const response = await fetch(apiUrl(scanImagePath(scanId)), {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (!response.ok) throw new Error(`image fetch failed: ${response.status}`);
        const blob = await response.blob();
        const reader = new FileReader();
        reader.onloadend = () => {
          if (!cancelled) setDataUri(reader.result as string);
        };
        reader.onerror = () => {
          if (!cancelled) setFailed(true);
        };
        reader.readAsDataURL(blob);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [scanId]);

  if (failed) {
    return <View style={[styles.fallback, style]} />;
  }

  return (
    <View style={[styles.clip, style]}>
      {dataUri ? (
        <Image source={{ uri: dataUri }} style={StyleSheet.absoluteFill} resizeMode="cover" />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.loadingOverlay]}>
          <ActivityIndicator color={colors.navy} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden' },
  fallback: {
    backgroundColor: colors.surfaceMuted,
  },
  loadingOverlay: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceMuted,
    borderRadius: 12,
  },
});
