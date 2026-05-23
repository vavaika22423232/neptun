export type MainTabParamList = {
  Map: undefined;
  Radar: undefined;
  Regions: undefined;
  Chat: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Onboarding: undefined;
  MainTabs: { screen?: keyof MainTabParamList } | undefined;
  Premium: undefined;
  AlarmHistory: undefined;
  PersonalAnalytics: undefined;
  Heatmap: undefined;
  SleepMode: undefined;
  ChatAdmin: undefined;
  Complaints: undefined;
  WebEmbed: { url: string; title?: string };
};
