import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { listScans } from '../../api/scans';
import { friendlyErrorMessage } from '../../api/errors';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { VerdictPill } from '../../components/VerdictBanner';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';
import type { ScanSummaryOut } from '../../types/api';

type Nav = NativeStackNavigationProp<CitizenStackParamList>;

export function HistoryScreen() {
  const navigation = useNavigation<Nav>();
  const [scans, setScans] = useState<ScanSummaryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const result = await listScans({ limit: 100 });
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

  if (scans === null && !error) return <LoadingState label="Loading history…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <Text style={styles.heading}>Scan History</Text>
      <FlatList
        data={scans ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <EmptyState icon="🕘" title="No scans yet" subtitle="Your scanned products will appear here." />
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.row} onPress={() => navigation.navigate('ScanDetail', { scanId: item.id })}>
            <View style={styles.rowInfo}>
              <Text style={styles.rowId}>Scan {item.id.slice(0, 10)}…</Text>
              <Text style={styles.rowDate}>{new Date(item.created_at).toLocaleString()}</Text>
              {item.overall_confidence !== null && (
                <Text style={styles.rowConfidence}>Confidence: {item.overall_confidence.toFixed(1)}%</Text>
              )}
            </View>
            {item.overall_verdict ? (
              <VerdictPill verdict={item.overall_verdict} />
            ) : (
              <Text style={styles.pending}>{item.status}</Text>
            )}
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
  rowConfidence: { fontSize: 11, color: colors.textMuted },
  pending: { fontSize: 12, color: colors.textMuted, fontWeight: '600' },
});
