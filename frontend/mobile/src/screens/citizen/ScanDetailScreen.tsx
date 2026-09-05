import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScanDetailView } from '../../components/ScanDetailView';
import { ErrorState, LoadingState } from '../../components/States';
import { useScan } from '../../hooks/useScan';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';

type Rt = RouteProp<CitizenStackParamList, 'ScanDetail'>;

export function ScanDetailScreen() {
  const { params } = useRoute<Rt>();
  const { scan, error, loading, reload } = useScan(params.scanId);

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      {loading && <LoadingState label="Loading scan…" />}
      {!loading && error && <ErrorState message={error} onRetry={reload} />}
      {!loading && scan && (
        <ScrollView contentContainerStyle={styles.scroll}>
          <ScanDetailView scan={scan} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg },
});
