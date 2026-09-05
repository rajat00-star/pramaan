import type { NavigatorScreenParams } from '@react-navigation/native';

export type CitizenTabParamList = {
  CitizenHome: undefined;
  History: undefined;
  Profile: undefined;
};

export type CitizenStackParamList = {
  CitizenTabs: NavigatorScreenParams<CitizenTabParamList>;
  ScanCapture: undefined;
  ScanPreview: { uri: string; mimeType: string; fileName: string };
  ScanProcessing: { uri: string; mimeType: string; fileName: string };
  ScanResult: { scanId: string };
  ScanDetail: { scanId: string };
};

export type InspectorTabParamList = {
  InspectorHome: undefined;
  ReviewQueue: undefined;
  Profile: undefined;
};

export type InspectorStackParamList = {
  InspectorTabs: NavigatorScreenParams<InspectorTabParamList>;
  CaseDetail: { scanId: string };
};

export type RootStackParamList = {
  Login: undefined;
  CitizenApp: NavigatorScreenParams<CitizenStackParamList>;
  InspectorApp: NavigatorScreenParams<InspectorStackParamList>;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
