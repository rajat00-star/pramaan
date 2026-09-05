import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import { Text } from 'react-native';

import { CaseDetailScreen } from '../screens/inspector/CaseDetailScreen';
import { InspectorHomeScreen } from '../screens/inspector/InspectorHomeScreen';
import { ReviewQueueScreen } from '../screens/inspector/ReviewQueueScreen';
import { ProfileScreen } from '../screens/shared/ProfileScreen';
import { colors } from '../theme/colors';
import type { InspectorStackParamList, InspectorTabParamList } from './types';

const Tab = createBottomTabNavigator<InspectorTabParamList>();
const Stack = createNativeStackNavigator<InspectorStackParamList>();

const TAB_ICON: Record<keyof InspectorTabParamList, string> = {
  InspectorHome: '🏠',
  ReviewQueue: '📋',
  Profile: '👤',
};

function InspectorTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.navy,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: () => <Text style={{ fontSize: 20 }}>{TAB_ICON[route.name]}</Text>,
      })}
    >
      <Tab.Screen name="InspectorHome" component={InspectorHomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="ReviewQueue" component={ReviewQueueScreen} options={{ title: 'Review' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
    </Tab.Navigator>
  );
}

export function InspectorNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerStyle: { backgroundColor: colors.navy }, headerTintColor: '#fff' }}>
      <Stack.Screen name="InspectorTabs" component={InspectorTabs} options={{ headerShown: false }} />
      <Stack.Screen name="CaseDetail" component={CaseDetailScreen} options={{ title: 'Case Details' }} />
    </Stack.Navigator>
  );
}
