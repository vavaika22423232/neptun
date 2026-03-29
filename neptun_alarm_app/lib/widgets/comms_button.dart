import 'package:flutter/material.dart';
import '../core/widgets/neptun_card.dart';
import '../services/window_manager.dart';

class CommsButton extends StatelessWidget {
  const CommsButton({super.key});

  @override
  Widget build(BuildContext context) {
    return NeptunCard.glass(
      borderRadius: 100,
      padding: const EdgeInsets.all(12),
      onTap: () {
        WindowManager().openPanel(PanelType.comms);
      },
      child: const Icon(Icons.chat_bubble_outline_rounded, size: 24),
    );
  }
}
