import { AppEmptyState } from './AppEmptyState';

type Props = {
  title?: string;
  subtitle?: string;
  onRetry?: () => void;
};

export function AppErrorState({
  title = 'Помилка',
  subtitle = 'Спробуйте ще раз',
  onRetry,
}: Props) {
  return (
    <AppEmptyState
      icon="cloud-offline-outline"
      title={title}
      subtitle={subtitle}
      actionLabel={onRetry ? 'Повторити' : undefined}
      onAction={onRetry}
    />
  );
}
