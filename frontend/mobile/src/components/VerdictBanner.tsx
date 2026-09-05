import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { Verdict } from '../types/api';
import { radius, spacing, verdictColor } from '../theme/colors';

const VERDICT_LABEL: Record<Verdict, string> = {
  COMPLIANT: 'COMPLIANT',
  NON_COMPLIANT: 'NON-COMPLIANT',
  REVIEW: 'REVIEW REQUIRED',
};

const VERDICT_ICON: Record<Verdict, string> = {
  COMPLIANT: '✓',
  NON_COMPLIANT: '✕',
  REVIEW: '⚠',
};

export function VerdictBanner({ verdict, confidence }: { verdict: Verdict; confidence: number | null }) {
  const c = verdictColor[verdict] ?? verdictColor.REVIEW;
  return (
    <View style={[styles.banner, { backgroundColor: c.bg, borderColor: c.fg }]}>
      <Text style={[styles.text, { color: c.fg }]}>
        {VERDICT_ICON[verdict]} {VERDICT_LABEL[verdict]}
      </Text>
      {confidence !== null && (
        <Text style={[styles.confidence, { color: c.fg }]}>Overall confidence: {confidence.toFixed(1)}%</Text>
      )}
    </View>
  );
}

export function VerdictPill({ verdict }: { verdict: Verdict | null }) {
  if (!verdict) return null;
  const c = verdictColor[verdict] ?? verdictColor.REVIEW;
  return (
    <View style={[styles.pill, { backgroundColor: c.bg }]}>
      <Text style={[styles.pillText, { color: c.fg }]}>{verdict.replace('_', ' ')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    borderWidth: 2,
    borderRadius: radius.lg,
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
  },
  text: { fontSize: 20, fontWeight: '800', letterSpacing: 0.3 },
  confidence: { fontSize: 13, marginTop: spacing.xs, fontWeight: '500' },
  pill: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: radius.pill, alignSelf: 'flex-start' },
  pillText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.3 },
});
