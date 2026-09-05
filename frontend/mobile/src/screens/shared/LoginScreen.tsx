import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { useAuth } from '../../contexts/AuthContext';
import { colors, spacing } from '../../theme/colors';

export function LoginScreen() {
  const { login, isLoggingIn, loginError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const canSubmit = username.trim().length > 0 && password.length > 0 && !isLoggingIn;

  const handleSubmit = () => {
    if (!canSubmit) return;
    login(username.trim(), password).catch(() => {
      /* loginError is already set by the context */
    });
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.logo}>PraMaan</Text>
          <Text style={styles.tagline}>Packaged Commodity Compliance, Simplified.</Text>
        </View>

        <Card>
          <Text style={styles.cardTitle}>Sign in</Text>

          <Text style={styles.label}>Username</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="e.g. citizen_demo"
            placeholderTextColor={colors.placeholder}
            accessibilityLabel="Username"
            returnKeyType="next"
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="Password"
            placeholderTextColor={colors.placeholder}
            accessibilityLabel="Password"
            returnKeyType="go"
            onSubmitEditing={handleSubmit}
          />

          {loginError && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{loginError}</Text>
            </View>
          )}

          <Button
            title="Sign in"
            onPress={handleSubmit}
            disabled={!canSubmit}
            loading={isLoggingIn}
            style={{ marginTop: spacing.md }}
          />
        </Card>

        <Text style={styles.demoHint}>
          Demo accounts (development only):{'\n'}
          citizen_demo / citizen123 · inspector_demo / inspector123
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.background },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: spacing.lg, gap: spacing.lg },
  header: { alignItems: 'center', marginBottom: spacing.lg },
  logo: { fontSize: 34, fontWeight: '800', color: colors.navy, letterSpacing: 0.3 },
  tagline: { fontSize: 14, color: colors.textMuted, marginTop: spacing.xs, textAlign: 'center' },
  cardTitle: { fontSize: 18, fontWeight: '700', color: colors.navy, marginBottom: spacing.md, textAlign: 'center' },
  label: { fontSize: 13, color: colors.textMuted, marginBottom: spacing.xs, marginTop: spacing.sm },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 14,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  errorBox: { backgroundColor: colors.failBg, borderRadius: 8, padding: spacing.sm, marginTop: spacing.md },
  errorText: { color: colors.fail, fontSize: 13 },
  demoHint: { fontSize: 12, color: colors.textMuted, textAlign: 'center', lineHeight: 18 },
});
