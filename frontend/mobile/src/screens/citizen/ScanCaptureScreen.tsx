import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import * as ImagePicker from 'expo-image-picker';
import React, { useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '../../components/Button';
import type { CitizenStackParamList } from '../../navigation/types';
import { colors, spacing } from '../../theme/colors';

type Nav = NativeStackNavigationProp<CitizenStackParamList, 'ScanCapture'>;

function mimeTypeForUri(uri: string): string {
  const ext = uri.split('.').pop()?.toLowerCase();
  if (ext === 'png') return 'image/png';
  if (ext === 'webp') return 'image/webp';
  return 'image/jpeg';
}

export function ScanCaptureScreen() {
  const navigation = useNavigation<Nav>();
  const [busy, setBusy] = useState(false);

  const goToPreview = (asset: ImagePicker.ImagePickerAsset) => {
    navigation.navigate('ScanPreview', {
      uri: asset.uri,
      mimeType: asset.mimeType ?? mimeTypeForUri(asset.uri),
      fileName: asset.fileName ?? `scan-${Date.now()}.jpg`,
    });
  };

  const takePhoto = async () => {
    setBusy(true);
    try {
      const permission = await ImagePicker.requestCameraPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          'Camera access needed',
          'PraMaan needs camera access to photograph a product label. You can enable it in Settings.'
        );
        return;
      }
      const result = await ImagePicker.launchCameraAsync({ quality: 0.9, allowsEditing: false });
      if (!result.canceled && result.assets[0]) goToPreview(result.assets[0]);
    } catch {
      Alert.alert('Camera error', 'Could not open the camera. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const chooseFromGallery = async () => {
    setBusy(true);
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          'Photo library access needed',
          'PraMaan needs photo library access to choose a product photo. You can enable it in Settings.'
        );
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        quality: 0.9,
        allowsEditing: false,
      });
      if (!result.canceled && result.assets[0]) goToPreview(result.assets[0]);
    } catch {
      Alert.alert('Gallery error', 'Could not open your photo library. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <View style={styles.content}>
        <Text style={styles.icon}>📦</Text>
        <Text style={styles.title}>Scan a product label</Text>
        <Text style={styles.subtitle}>
          Photograph the panel with the manufacturer, net quantity, MRP, and other declarations — usually the back
          or side of the package.
        </Text>

        <View style={styles.buttons}>
          <Button title="📷  Take Photo" onPress={takePhoto} disabled={busy} />
          <Button title="🖼  Choose From Gallery" variant="secondary" onPress={chooseFromGallery} disabled={busy} />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flex: 1, padding: spacing.xl, alignItems: 'center', justifyContent: 'center', gap: spacing.md },
  icon: { fontSize: 56 },
  title: { fontSize: 22, fontWeight: '800', color: colors.navy, textAlign: 'center' },
  subtitle: { fontSize: 14, color: colors.textMuted, textAlign: 'center', lineHeight: 20, marginBottom: spacing.lg },
  buttons: { width: '100%', gap: spacing.md },
});
