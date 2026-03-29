import 'package:flutter/material.dart';
import '../services/window_manager.dart';

/// Material Design 3 Navigation Bar
/// Replaces custom GlassNavigationBar with standard MD3 component
class MD3NavigationBar extends StatelessWidget {
  const MD3NavigationBar({super.key});

  @override
  Widget build(BuildContext context) {
    final windowManager = WindowManager();

    return ListenableBuilder(
      listenable: windowManager,
      builder: (context, _) {
        final activePanel = windowManager.activePanel;

        // Map PanelType to navigation index
        int selectedIndex = switch (activePanel) {
          PanelType.radar => 0,
          PanelType.comms => 1,
          PanelType.shelters => 2,
          PanelType.settings => 3,
          _ => -1, // No selection for map view
        };

        return NavigationBar(
          selectedIndex: selectedIndex == -1 ? 0 : selectedIndex,
          onDestinationSelected: (index) {
            final panelType = switch (index) {
              0 => PanelType.radar,
              1 => PanelType.comms,
              2 => PanelType.shelters,
              3 => PanelType.settings,
              _ => PanelType.none,
            };

            if (panelType == PanelType.none) {
              windowManager.closePanel();
            } else {
              windowManager.openPanel(panelType);
            }
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.radar_outlined),
              selectedIcon: Icon(Icons.radar),
              label: 'Радар',
            ),
            NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline),
              selectedIcon: Icon(Icons.chat_bubble),
              label: 'Зв\'язок',
            ),
            NavigationDestination(
              icon: Icon(Icons.shield_outlined),
              selectedIcon: Icon(Icons.shield),
              label: 'Укриття',
            ),
            NavigationDestination(
              icon: Icon(Icons.menu_rounded),
              selectedIcon: Icon(Icons.menu_rounded),
              label: 'Меню',
            ),
          ],
        );
      },
    );
  }
}
