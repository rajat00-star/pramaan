import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import { Text } from 'react-native';

import { CitizenHomeScreen } from '../screens/citizen/CitizenHomeScreen';
import { HistoryScreen } from '../screens/citizen/HistoryScreen';
import { ScanCaptureScreen } from '../screens/citizen/ScanCaptureScreen';
import { ScanDetailScreen } from '../screens/citizen/ScanDetailScreen';
import { ScanPreviewScreen } from '../screens/citizen/ScanPreviewScreen';
import { ScanProcessingScreen } from '../screens/citizen/ScanProcessingScreen';
import { ScanResultScreen } from '../screens/citizen/ScanResultScreen';
import { ProfileScreen } from '../screens/shared/ProfileScreen';
import { colors } from '../theme/colors';
import type { CitizenStackParamList, CitizenTabParamList } from './types';

const Tab = createBottomTabNavigator<CitizenTabParamList>();
const Stack = createNativeStackNavigator<CitizenStackParamList>();

const TAB_ICON: Record<keyof CitizenTabParamList, string> = {
  CitizenHome: '🏠',
  History: '🕘',
  Profile: '👤',
};

function CitizenTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.navy,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: () => <Text style={{ fontSize: 20 }}>{TAB_ICON[route.name]}</Text>,
      })}
    >
      <Tab.Screen name="CitizenHome" component={CitizenHomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="History" component={HistoryScreen} options={{ title: 'History' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
    </Tab.Navigator>
  );
}

export function CitizenNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerStyle: { backgroundColor: colors.navy }, headerTintColor: '#fff' }}>
      <Stack.Screen name="CitizenTabs" component={CitizenTabs} options={{ headerShown: false }} />
      <Stack.Screen name="ScanCapture" component={ScanCaptureScreen} options={{ title: 'Scan Product' }} />
      <Stack.Screen name="ScanPreview" component={ScanPreviewScreen} options={{ title: 'Review Photo' }} />
      <Stack.Screen
        name="ScanProcessing"
        component={ScanProcessingScreen}
        options={{ title: 'Analyzing', headerBackVisible: false, gestureEnabled: false }}
      />
      <Stack.Screen name="ScanResult" component={ScanResultScreen} options={{ title: 'Result', headerBackVisible: false }} />
      <Stack.Screen name="ScanDetail" component={ScanDetailScreen} options={{ title: 'Scan Details' }} />
    </Stack.Navigator>
  );
}
