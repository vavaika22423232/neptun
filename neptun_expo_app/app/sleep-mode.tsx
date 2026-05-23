import { ProFeatureGate } from '../src/components/ProFeatureGate';
import { ProFeature } from '../src/core/pro/proGate';
import { SleepModeScreen } from '../src/screens/SleepModeScreen';

export default function SleepModeRoute() {
  return (
    <ProFeatureGate feature={ProFeature.SleepMode}>
      <SleepModeScreen />
    </ProFeatureGate>
  );
}
