import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Button } from './Button';
import { colors, spacing } from '../theme/colors';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator size="large" color={colors.navy} />
      <Text style={styles.muted}>{label}</Text>
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={styles.center}>
      <Text style={styles.errorIcon}>⚠</Text>
      <Text style={styles.errorText}>{message}</Text>
      {onRetry && <Button title="Try again" variant="secondary" onPress={onRetry} style={{ marginTop: spacing.md }} />}
    </View>
  );
}

export function EmptyState({ icon = '—', title, subtitle }: { icon?: string; title: string; subtitle?: string }) {
  return (
    <View style={styles.center}>
      <Text style={styles.emptyIcon}>{icon}</Text>
      <Text style={styles.emptyTitle}>{title}</Text>
      {subtitle ? <Text style={styles.muted}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xxl, gap: spacing.sm },
  muted: { color: colors.textMuted, fontSize: 14, textAlign: 'center' },
  errorIcon: { fontSize: 32, color: colors.review },
  errorText: { color: colors.text, fontSize: 15, textAlign: 'center', maxWidth: 280 },
  emptyIcon: { fontSize: 40, marginBottom: spacing.xs },
  emptyTitle: { color: colors.text, fontSize: 16, fontWeight: '600', textAlign: 'center' },
});
