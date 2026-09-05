import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { useAuth } from '../../contexts/AuthContext';
import { colors, spacing } from '../../theme/colors';

const ROLE_LABEL: Record<string, string> = {
  citizen: 'Citizen',
  inspector: 'Inspector',
  department_admin: 'Department Admin',
};

export function ProfileScreen() {
  const { session, logout } = useAuth();

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.heading}>Profile</Text>

        <Card>
          <View style={styles.row}>
            <Text style={styles.label}>Signed in as</Text>
            <Text style={styles.value}>{session?.username}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Role</Text>
            <Text style={styles.value}>{session ? ROLE_LABEL[session.role] ?? session.role : '—'}</Text>
          </View>
        </Card>

        <Card title="About PraMaan">
          <Text style={styles.body}>
            PraMaan checks packaged-commodity labels against the Legal Metrology (Packaged Commodities) Rules, 2011.
            Every verdict comes from real OCR, real field extraction, and a deterministic, versioned legal rule
            engine — never from an AI model deciding what the law means.
          </Text>
          <Text style={[styles.body, styles.limitation]}>
            This is an MVP: OCR accuracy varies with photo quality, extraction covers 7 core declarations, and
            "REVIEW" means a human must verify the label directly, not that something is wrong with the app.
          </Text>
        </Card>

        <Button title="Sign out" variant="danger" onPress={() => logout()} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg, gap: spacing.md },
  heading: { fontSize: 24, fontWeight: '800', color: colors.navy, marginBottom: spacing.xs },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs },
  label: { color: colors.textMuted, fontSize: 14 },
  value: { color: colors.text, fontSize: 14, fontWeight: '600' },
  body: { color: colors.text, fontSize: 14, lineHeight: 20 },
  limitation: { marginTop: spacing.sm, color: colors.textMuted, fontStyle: 'italic' },
});
