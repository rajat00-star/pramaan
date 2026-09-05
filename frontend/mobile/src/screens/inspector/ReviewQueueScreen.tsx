import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { listScans } from '../../api/scans';
import { friendlyErrorMessage } from '../../api/errors';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import type { InspectorStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';
import type { ScanSummaryOut } from '../../types/api';

type Nav = NativeStackNavigationProp<InspectorStackParamList>;

export function ReviewQueueScreen() {
  const navigation = useNavigation<Nav>();
  const [scans, setScans] = useState<ScanSummaryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      // Inspectors see every citizen's REVIEW-verdict scans (server-side RBAC
      // already grants inspectors cross-user visibility — see routes/scan.py).
      const result = await listScans({ verdictFilter: 'REVIEW', limit: 100 });
      setScans(result);
    } catch (err) {
      setError(friendlyErrorMessage(err));
    }
  }, []);

  React.useEffect(() => {
    const unsubscribe = navigation.addListener('focus', load);
    return unsubscribe;
  }, [navigation, load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (scans === null && !error) return <LoadingState label="Loading review queue…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <Text style={styles.heading}>Review Queue</Text>
      <FlatList
        data={scans ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <EmptyState icon="✅" title="Queue is empty" subtitle="No cases currently require human review." />
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.row} onPress={() => navigation.navigate('CaseDetail', { scanId: item.id })}>
            <View style={styles.rowInfo}>
              <Text style={styles.rowId}>Case {item.id.slice(0, 10)}…</Text>
              <Text style={styles.rowDate}>{new Date(item.created_at).toLocaleString()}</Text>
              {item.overall_confidence !== null && (
                <Text style={styles.rowConfidence}>Confidence: {item.overall_confidence.toFixed(1)}%</Text>
              )}
            </View>
            <Text style={styles.chevron}>›</Text>
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  heading: { fontSize: 22, fontWeight: '800', color: colors.navy, padding: spacing.lg, paddingBottom: spacing.sm },
  list: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl, flexGrow: 1 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  rowInfo: { gap: 2 },
  rowId: { fontSize: 14, fontWeight: '600', color: colors.text },
  rowDate: { fontSize: 12, color: colors.textMuted },
  rowConfidence: { fontSize: 11, color: colors.review, fontWeight: '600' },
  chevron: { fontSize: 22, color: colors.textMuted },
});
