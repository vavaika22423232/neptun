import type { ReactNode } from 'react';
import { memo } from 'react';
import { NeptunTopBar } from './NeptunTopBar';

export type TabScreenHeaderProps = {
  title: string;
  subtitle?: string;
  isLive?: boolean;
  actions?: ReactNode;
  onTitlePress?: () => void;
};

function TabScreenHeaderInner(props: TabScreenHeaderProps) {
  return <NeptunTopBar {...props} />;
}

export const TabScreenHeader = memo(TabScreenHeaderInner);
