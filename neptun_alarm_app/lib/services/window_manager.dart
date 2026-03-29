import 'package:flutter/material.dart';

enum PanelType {
  none,
  radar, // Aviation
  comms, // Chat
  shelters,
  settings,
  safety,
}

class WindowManager extends ChangeNotifier {
  static final WindowManager _instance = WindowManager._internal();
  factory WindowManager() => _instance;
  WindowManager._internal();

  // Active panel (only one can be focused/maximized at a time for simplicity on mobile)
  PanelType _activePanel = PanelType.none;
  PanelType get activePanel => _activePanel;

  // Minimized panels (can be quickly restored)
  final Set<PanelType> _minimizedPanels = {};

  bool get isPanelOpen => _activePanel != PanelType.none;

  void openPanel(PanelType type) {
    if (_activePanel == type) return;

    _activePanel = type;
    _minimizedPanels.remove(type);
    notifyListeners();
  }

  void closePanel() {
    _activePanel = PanelType.none;
    notifyListeners();
  }

  void minimizePanel() {
    if (_activePanel != PanelType.none) {
      _minimizedPanels.add(_activePanel);
      _activePanel = PanelType.none;
      notifyListeners();
    }
  }

  void togglePanel(PanelType type) {
    if (_activePanel == type) {
      minimizePanel();
    } else {
      openPanel(type);
    }
  }

  bool isMinimized(PanelType type) => _minimizedPanels.contains(type);
}
