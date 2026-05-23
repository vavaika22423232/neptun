import { ProFeatureGate } from '../src/components/ProFeatureGate';
import { ProFeature } from '../src/core/pro/proGate';
import { ThreatDashboardScreen } from '../src/screens/ThreatDashboardScreen';

export default function RadarFullRoute() {
  return (
    <ProFeatureGate feature={ProFeature.ExtendedRadar}>
      <ThreatDashboardScreen />
    </ProFeatureGate>
  );
}
