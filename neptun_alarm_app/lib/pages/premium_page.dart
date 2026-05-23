import 'package:flutter/material.dart';

import '../features/premium/presentation/paywall/premium_paywall_screen.dart';

/// @deprecated Використовуйте [PremiumPaywallScreen] напряму (`/premium` у router).
@Deprecated('Use PremiumPaywallScreen — єдиний paywall')
class PremiumPage extends StatelessWidget {
  const PremiumPage({super.key});

  @override
  Widget build(BuildContext context) => const PremiumPaywallScreen();
}
