import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { fetchDashboardSummary } from '../../api/dashboard';
import { friendlyErrorMessage } from '../../api/errors';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { ErrorState, LoadingState } from '../../components/States';
import { StatTile } from '../../components/StatTile';
import { VerdictPill } from '../../components/VerdictBanner';
import { useAuth } from '../../contexts/AuthContext';
import type { InspectorStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';
import type { DashboardSummaryOut } from '../../types/api';

type Nav = NativeStackNavigationProp<InspectorStackParamList>;

export function InspectorHomeScreen() {
  const navigation = useNavigation<Nav>();
  const { session } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setSummary(await fetchDashboardSummary());
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

  if (summary === null && !error) return <LoadingState label="Loading dashboard…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!summary) return null;

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View>
          <Text style={styles.greeting}>{session?.username}</Text>
          <Text style={styles.logo}>PraMaan Inspector</Text>
        </View>

        <View style={styles.statRow}>
          <StatTile label="Pending Reviews" value={summary.pending_review_count} />
          <StatTile label="Reviewed Today" value={summary.reviews_today} />
          <StatTile label="Total Scans" value={summary.total_scans} />
        </View>

        <Button title="Review Cases" onPress={() => navigation.navigate('InspectorTabs', { screen: 'ReviewQueue' })} />

        <Card title="Recent Cases">
          {summary.recent_scans.length === 0 ? (
            <Text style={styles.muted}>No scans yet.</Text>
          ) : (
            summary.recent_scans.slice(0, 5).map((scan) => (
              <TouchableOpacity
                key={scan.id}
                style={styles.recentRow}
                onPress={() => navigation.navigate('CaseDetail', { scanId: scan.id })}
              >
                <View>
                  <Text style={styles.recentId}>Scan {scan.id.slice(0, 10)}…</Text>
                  <Text style={styles.recentDate}>{new Date(scan.created_at).toLocaleString()}</Text>
                </View>
                <VerdictPill verdict={scan.overall_verdict} />
              </TouchableOpacity>
            ))
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg, gap: spacing.md },
  greeting: { fontSize: 14, color: colors.textMuted },
  logo: { fontSize: 26, fontWeight: '800', color: colors.navy, marginTop: 2, marginBottom: spacing.sm },
  statRow: { flexDirection: 'row', gap: spacing.sm },
  muted: { color: colors.textMuted },
  recentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  recentId: { fontSize: 14, fontWeight: '600', color: colors.text },
  recentDate: { fontSize: 12, color: colors.textMuted },
});
