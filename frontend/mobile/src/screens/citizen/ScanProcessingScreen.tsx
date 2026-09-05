import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { createScan } from '../../api/scans';
import { Button } from '../../components/Button';
import { friendlyErrorMessage } from '../../api/errors';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';

type Nav = NativeStackNavigationProp<CitizenStackParamList, 'ScanProcessing'>;
type Rt = RouteProp<CitizenStackParamList, 'ScanProcessing'>;

// Purely cosmetic stage labels shown while the real request is in flight — the
// pipeline itself is one synchronous backend call, so these do not represent
// separately-observed backend progress. The actual verdict always comes from
// the API response, never from this list.
const STAGES = ['Image received', 'Text extraction (OCR)', 'Declaration analysis', 'Legal compliance evaluation'];

export function ScanProcessingScreen() {
  const navigation = useNavigation<Nav>();
  const { params } = useRoute<Rt>();
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    setError(null);
    setStageIndex(0);
    const interval = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, 900);

    createScan(params)
      .then((scan) => {
        if (!mounted.current) return;
        if (scan.status === 'ERROR') {
          setError(scan.error_message || 'The server could not analyze this image.');
          return;
        }
        navigation.replace('ScanResult', { scanId: scan.id });
      })
      .catch((err) => {
        if (mounted.current) setError(friendlyErrorMessage(err));
      })
      .finally(() => clearInterval(interval));

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  if (error) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.content}>
          <Text style={styles.errorIcon}>⚠</Text>
          <Text style={styles.errorTitle}>Analysis failed</Text>
          <Text style={styles.errorMessage}>{error}</Text>
          <View style={styles.buttons}>
            <Button title="Try Again" onPress={() => setAttempt((a) => a + 1)} />
            <Button title="Retake Photo" variant="secondary" onPress={() => navigation.goBack()} />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <ActivityIndicator size="large" color={colors.navy} />
        <Text style={styles.title}>Analyzing package…</Text>
        <View style={styles.stages}>
          {STAGES.map((stage, i) => (
            <Text key={stage} style={[styles.stage, i <= stageIndex && styles.stageDone]}>
              {i < stageIndex ? '✓' : i === stageIndex ? '›' : '·'} {stage}
            </Text>
          ))}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg },
  title: { fontSize: 18, fontWeight: '700', color: colors.navy },
  stages: { alignSelf: 'stretch', gap: spacing.sm },
  stage: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },
  stageDone: { color: colors.text, fontWeight: '600' },
  errorIcon: { fontSize: 40, color: colors.review },
  errorTitle: { fontSize: 18, fontWeight: '700', color: colors.text },
  errorMessage: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },
  buttons: { width: '100%', gap: spacing.sm, marginTop: spacing.md },
});
