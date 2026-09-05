import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { FieldStatus } from '../types/api';
import { radius, statusColor } from '../theme/colors';

export function StatusBadge({ status }: { status: FieldStatus }) {
  const c = statusColor[status] ?? statusColor.REVIEW;
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.fg }]}>{status.replace('_', ' ')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingVertical: 3, paddingHorizontal: 9, borderRadius: radius.pill, alignSelf: 'flex-start' },
  text: { fontSize: 10, fontWeight: '700', letterSpacing: 0.3 },
});
