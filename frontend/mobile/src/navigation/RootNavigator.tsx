import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';

import { LoadingState } from '../components/States';
import { useAuth } from '../contexts/AuthContext';
import { LoginScreen } from '../screens/shared/LoginScreen';
import { CitizenNavigator } from './CitizenNavigator';
import { InspectorNavigator } from './InspectorNavigator';
import type { RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { session, isRestoring } = useAuth();

  if (isRestoring) return <LoadingState label="Loading PraMaan…" />;

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!session ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : session.role === 'citizen' ? (
          <Stack.Screen name="CitizenApp" component={CitizenNavigator} />
        ) : (
          // Server-side RBAC is authoritative: both 'inspector' and
          // 'department_admin' can review cases and see dashboard stats,
          // so both use the same Inspector experience on mobile — the
          // department_admin role's primary surface remains the web
          // dashboard (see docs/mobile.md), not a third mobile UI.
          <Stack.Screen name="InspectorApp" component={InspectorNavigator} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
