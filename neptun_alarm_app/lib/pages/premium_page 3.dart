import 'package:flutter/material.dart';

import '../features/premium/presentation/paywall/premium_paywall_screen.dart';

/// Маршрут до екрана PRO — реалізація в [PremiumPaywallScreen].
class PremiumPage extends StatelessWidget {
  const PremiumPage({super.key});

  @override
  Widget build(BuildContext context) => const PremiumPaywallScreen();
}
