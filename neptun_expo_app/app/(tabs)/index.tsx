import { StyleSheet, View } from 'react-native';
import { MapScreen } from '../../src/screens/MapScreen';

/** Explicit flex wrapper — WebView needs measurable parent height in tab navigator. */
export default function MapTabRoute() {
  return (
    <View style={styles.fill}>
      <MapScreen />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: {
    flex: 1,
    minHeight: 0,
    width: '100%',
    overflow: 'hidden',
  },
});
