import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { listScans } from '../../api/scans';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/States';
import { VerdictPill } from '../../components/VerdictBanner';
import { useAuth } from '../../contexts/AuthContext';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';
import type { ScanSummaryOut } from '../../types/api';

type Nav = NativeStackNavigationProp<CitizenStackParamList>;

export function CitizenHomeScreen() {
  const navigation = useNavigation<Nav>();
  const { session } = useAuth();
  const [recent, setRecent] = useState<ScanSummaryOut[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const scans = await listScans({ limit: 3 });
      setRecent(scans);
    } catch {
      setRecent([]);
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

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View>
          <Text style={styles.greeting}>Hello, {session?.username}</Text>
          <Text style={styles.logo}>PraMaan</Text>
          <Text style={styles.tagline}>Packaged Commodity Compliance, Simplified.</Text>
        </View>

        <Button title="📷  Scan Product" onPress={() => navigation.navigate('ScanCapture')} style={styles.scanButton} />

        <Card title="Recent Scans">
          {recent === null ? (
            <Text style={styles.muted}>Loading…</Text>
          ) : recent.length === 0 ? (
            <EmptyState icon="🔍" title="No scans yet" subtitle="Tap Scan Product to check your first label." />
          ) : (
            recent.map((scan) => (
              <TouchableOpacity
                key={scan.id}
                style={styles.recentRow}
                onPress={() => navigation.navigate('ScanDetail', { scanId: scan.id })}
              >
                <View style={styles.recentInfo}>
                  <Text style={styles.recentId}>Scan {scan.id.slice(0, 8)}…</Text>
                  <Text style={styles.recentDate}>{new Date(scan.created_at).toLocaleString()}</Text>
                </View>
                <VerdictPill verdict={scan.overall_verdict} />
              </TouchableOpacity>
            ))
          )}
        </Card>

        <Card title="How PraMaan Works">
          <Text style={styles.howItWorks}>
            1. Take or choose a photo of a product label{'\n'}
            2. PraMaan runs real OCR to read the text{'\n'}
            3. Declarations are extracted from the label{'\n'}
            4. A deterministic legal rule engine checks them against the Legal Metrology (Packaged Commodities)
            Rules, 2011{'\n'}
            5. You get an evidence-backed verdict — never a guess
          </Text>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg, gap: spacing.md },
  greeting: { fontSize: 14, color: colors.textMuted },
  logo: { fontSize: 30, fontWeight: '800', color: colors.navy, marginTop: 2 },
  tagline: { fontSize: 13, color: colors.textMuted, marginTop: 2, marginBottom: spacing.sm },
  scanButton: { paddingVertical: 18 },
  muted: { color: colors.textMuted },
  recentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  recentInfo: { gap: 2 },
  recentId: { fontSize: 14, fontWeight: '600', color: colors.text },
  recentDate: { fontSize: 12, color: colors.textMuted },
  howItWorks: { fontSize: 13, color: colors.text, lineHeight: 21 },
});
