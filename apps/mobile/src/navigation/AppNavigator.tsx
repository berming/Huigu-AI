import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';

import { MarketScreen } from '../screens/Market/MarketScreen';
import { StockDetailScreen } from '../screens/Market/StockDetailScreen';
import { SearchScreen } from '../screens/Market/SearchScreen';
import { SentimentScreen } from '../screens/Sentiment/SentimentScreen';
import { ResearchScreen } from '../screens/Research/ResearchScreen';
import { ProfileScreen } from '../screens/Profile/ProfileScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function TabIcon({ icon, focused }: { icon: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>{icon}</Text>
  );
}

function MarketStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="MarketHome" component={MarketScreen} />
      <Stack.Screen name="StockDetail" component={StockDetailScreen} />
      <Stack.Screen name="Search" component={SearchScreen} />
    </Stack.Navigator>
  );
}

function SentimentStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="SentimentHome" component={SentimentScreen} />
      <Stack.Screen name="StockDetail" component={StockDetailScreen} />
    </Stack.Navigator>
  );
}

function ResearchStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="ResearchHome" component={ResearchScreen} />
      <Stack.Screen name="StockDetail" component={StockDetailScreen} />
    </Stack.Navigator>
  );
}

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: styles.tabBar,
          tabBarActiveTintColor: Colors.brand.primary,
          tabBarInactiveTintColor: Colors.text.muted,
          tabBarLabelStyle: styles.tabLabel,
        }}
      >
        <Tab.Screen
          name="Market"
          component={MarketStack}
          options={{
            tabBarLabel: '行情',
            tabBarIcon: ({ focused }) => <TabIcon icon="📊" focused={focused} />,
          }}
        />
        <Tab.Screen
          name="Sentiment"
          component={SentimentStack}
          options={{
            tabBarLabel: '热议',
            tabBarIcon: ({ focused }) => <TabIcon icon="💬" focused={focused} />,
          }}
        />
        <Tab.Screen
          name="Research"
          component={ResearchStack}
          options={{
            tabBarLabel: 'AI研究',
            tabBarIcon: ({ focused }) => <TabIcon icon="🤖" focused={focused} />,
          }}
        />
        <Tab.Screen
          name="Profile"
          component={ProfileScreen}
          options={{
            tabBarLabel: '我的',
            tabBarIcon: ({ focused }) => <TabIcon icon="👤" focused={focused} />,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: Colors.bg.secondary,
    borderTopColor: Colors.bg.border,
    borderTopWidth: 1,
    height: 80,
    paddingBottom: 16,
    paddingTop: 8,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
  },
});
