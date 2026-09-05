import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, ViewStyle } from 'react-native';

import { colors, radius, spacing } from '../theme/colors';

interface Props {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'link';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function Button({ title, onPress, variant = 'primary', disabled, loading, style, accessibilityLabel }: Props) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      style={({ pressed }) => [
        styles.base,
        variantStyles[variant],
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'secondary' || variant === 'link' ? colors.navy : '#fff'} />
      ) : (
        <Text style={[styles.text, textVariantStyles[variant]]}>{title}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: 13,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  pressed: { opacity: 0.85 },
  disabled: { opacity: 0.5 },
  text: { fontSize: 16, fontWeight: '600' },
});

const variantStyles = StyleSheet.create({
  primary: { backgroundColor: colors.navy },
  secondary: { backgroundColor: colors.surfaceMuted },
  danger: { backgroundColor: colors.fail },
  link: { backgroundColor: 'transparent', minHeight: undefined, paddingVertical: 6 },
});

const textVariantStyles = StyleSheet.create({
  primary: { color: '#fff' },
  secondary: { color: colors.navy },
  danger: { color: '#fff' },
  link: { color: colors.accent, textDecorationLine: 'underline', fontWeight: '500' },
});
