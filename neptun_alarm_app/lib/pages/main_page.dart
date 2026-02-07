import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/window_manager.dart';

import 'native_map_page.dart';
import '../widgets/dashboard_sheet.dart';
import '../widgets/status_pill.dart';
import '../widgets/profile_button.dart';

// Panels (Legacy support for non-radar panels)
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
          // LAYER 0: Map (Base)
          const NativeMapPage(),

          // LAYER 1: The Intelligent Sheet (Radar Dashboard)
          // Always present, draggable
          // We hide it if a full-screen panel (Safety/Settings) is open
          if (_windowManager.activePanel != PanelType.settings &&
              _windowManager.activePanel != PanelType.safety)
            const DashboardSheet(),

          // LAYER 2: Legacy Panel Overlay (Settings, Safety, etc.)
          if (_windowManager.isPanelOpen &&
              _windowManager.activePanel != PanelType.radar)
            _buildActiveWindowOverlay(),

          // LAYER 3: HUD Controls (Floating)
          // These should sit on top of the map and sheet (when collapsed)
          // But maybe below full screen panels?
          // If settings is open, we probably want to hide these or have settings cover them.
          if (_windowManager.activePanel != PanelType.settings &&
              _windowManager.activePanel != PanelType.safety)
            const SafeArea(
              child: Stack(
                children: [
                  Positioned(top: 16, left: 16, child: StatusPill()),
                  Positioned(top: 16, right: 16, child: ProfileButton()),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildActiveWindowOverlay() {
    Widget child;

    switch (_windowManager.activePanel) {
      case PanelType.radar:
        return const SizedBox.shrink(); // Handled by Sheet
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
      color: colorScheme.surface, // Solid background for full screen panels
      child: Stack(
        children: [
          // Tap to close (if not full screen, but these are full screen mostly)
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
              padding: const EdgeInsets.only(bottom: 0),
              child: child,
            ),
          ),

          // Close button for panels (except settings which has its own back button usually)
          // But MenuPanel might need a close button if it's a panel.
          if (_windowManager.activePanel != PanelType.settings)
            Positioned(
              top: 40,
              left: 16,
              child: GestureDetector(
                onTap: () => _windowManager.closePanel(),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: colorScheme.surface.withValues(alpha: 0.5),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.close_rounded),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
