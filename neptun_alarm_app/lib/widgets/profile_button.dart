import 'package:flutter/material.dart';
import '../core/widgets/neptun_card.dart';
import '../services/window_manager.dart';

class ProfileButton extends StatelessWidget {
  const ProfileButton({super.key});

  @override
  Widget build(BuildContext context) {
    return NeptunCard.glass(
      borderRadius: 100,
      padding: const EdgeInsets.all(12),
      onTap: () {
        // Open Settings (MenuPanel)
        // We use the existing WindowManager for now to trigger the panel overlay
        // or effectively navigate to settings page.
        // The previous implementation opened MenuPanel on PanelType.settings
        WindowManager().openPanel(PanelType.settings);
      },
      child: const Icon(Icons.person_outline_rounded, size: 24),
    );
  }
}
