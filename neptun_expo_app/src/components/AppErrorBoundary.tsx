import { Component, type ErrorInfo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { appLogger } from '../core/logging/appLogger';
import { PrimaryButton } from './PrimaryButton';
import { Text } from './Text';
import { fonts } from '../theme/fonts';
import { neptunPalette as p } from '../theme/neptunPalette';

type Props = { children: ReactNode };
type State = { error: Error | null };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    appLogger.error('navigation', 'Unhandled render error', { message: error.message, stack: info.componentStack });
  }

  private reload = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (!this.state.error) return this.props.children;

    return (
      <View style={styles.root}>
        <Text title style={styles.title}>
          Щось пішло не так
        </Text>
        <Text muted style={styles.body}>
          Застосунок зустрів неочікувану помилку. Спробуйте перезавантажити екран.
        </Text>
        {__DEV__ ? (
          <Text style={styles.dev}>{this.state.error.message}</Text>
        ) : null}
        <PrimaryButton onPress={this.reload}>Спробувати знову</PrimaryButton>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: p.darkBackground,
    gap: 16,
  },
  title: { textAlign: 'center' },
  body: { textAlign: 'center', lineHeight: 22 },
  dev: {
    fontFamily: fonts.medium,
    fontSize: 12,
    color: p.darkTextMuted,
    textAlign: 'center',
  },
});
