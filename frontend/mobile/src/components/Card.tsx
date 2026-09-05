import React, { PropsWithChildren } from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';

import { colors, radius, spacing } from '../theme/colors';

export function Card({ children, style, title }: PropsWithChildren<{ style?: ViewStyle; title?: string }>) {
  return (
    <View style={[styles.card, style]}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
  title: {
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
});
