import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/window_manager.dart';

import '../widgets/glass_navigation_bar.dart'; // MD3NavigationBar
import 'native_map_page.dart';

// Panels
import '../panels/radar_panel.dart';
import '../panels/comms_panel.dart';
import '../panels/shelter_panel.dart';
import '../panels/menu_panel.dart';

import 'safety_page.dart';

class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => _MainPageState();
}

class _MainPageState extends State<MainPage> {
  final WindowManager _windowManager = WindowManager();

  @override
  void initState() {
    super.initState();
    _windowManager.addListener(_onWindowChanged);
  }

  @override
  void dispose() {
    _windowManager.removeListener(_onWindowChanged);
    super.dispose();
  }

  void _onWindowChanged() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: colorScheme.surface,
      body: Stack(
        children: [
          // LAYER 1: Map
          const NativeMapPage(),

          // LAYER 2: Panel Overlay
          if (_windowManager.isPanelOpen) _buildActiveWindowOverlay(),

          // LAYER 3: Bottom Navigation
          Positioned(left: 0, right: 0, bottom: 0, child: MD3NavigationBar()),
        ],
      ),
    );
  }

  Widget _buildActiveWindowOverlay() {
    Widget child;

    switch (_windowManager.activePanel) {
      case PanelType.radar:
        child = const RadarPanel();
        break;
      case PanelType.comms:
        child = const CommsPanel();
        break;
      case PanelType.shelters:
        child = const ShelterPanel();
        break;
      case PanelType.settings:
        child = const MenuPanel();
        break;
      case PanelType.safety:
        child = const SafetyPage();
        break;
      case PanelType.none:
        return const SizedBox.shrink();
    }

    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      color: colorScheme.surface, // Solid background, no transparency
      child: Stack(
        children: [
          // Tap to close
          GestureDetector(
            onTap: () {
              HapticFeedback.lightImpact();
              _windowManager.closePanel();
            },
            child: Container(
              color: Colors.transparent,
              child: const SizedBox.expand(),
            ),
          ),

          // Panel content
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 80),
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}
