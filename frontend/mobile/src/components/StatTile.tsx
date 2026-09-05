import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '../theme/colors';

export function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <View style={styles.tile}>
      <Text style={styles.value}>{value}</Text>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minWidth: 100,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    alignItems: 'center',
  },
  value: { fontSize: 24, fontWeight: '800', color: colors.navy },
  label: { fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.3, marginTop: 4, textAlign: 'center' },
});
