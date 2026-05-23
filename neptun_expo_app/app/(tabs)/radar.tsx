import { StyleSheet, View } from 'react-native';
import { RadarScreen } from '../../src/screens/RadarScreen';

/** Як на карті: явний flex + minHeight:0 — інакше таб «стрибає» при дотику. */
export default function RadarTabRoute() {
  return (
    <View style={styles.fill}>
      <RadarScreen />
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
