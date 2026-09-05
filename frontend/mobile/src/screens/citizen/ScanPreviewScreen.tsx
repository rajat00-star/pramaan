import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import React from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/Button';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';

type Nav = NativeStackNavigationProp<CitizenStackParamList, 'ScanPreview'>;
type Rt = RouteProp<CitizenStackParamList, 'ScanPreview'>;

export function ScanPreviewScreen() {
  const navigation = useNavigation<Nav>();
  const { params } = useRoute<Rt>();

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <View style={styles.content}>
        <Text style={styles.title}>Review your photo</Text>
        <Image source={{ uri: params.uri }} style={styles.image} resizeMode="contain" />
        <Text style={styles.hint}>Make sure the declaration text is in focus and fully visible.</Text>

        <View style={styles.buttons}>
          <Button title="Analyze Product" onPress={() => navigation.replace('ScanProcessing', params)} />
          <Button title="Retake" variant="secondary" onPress={() => navigation.goBack()} />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: spacing.lg, gap: spacing.md },
  title: { fontSize: 20, fontWeight: '800', color: colors.navy, textAlign: 'center' },
  image: { flex: 1, borderRadius: 12, backgroundColor: colors.surfaceMuted },
  hint: { fontSize: 13, color: colors.textMuted, textAlign: 'center' },
  buttons: { gap: spacing.sm },
});
