import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/window_manager.dart';

class CommandDock extends StatefulWidget {
  final bool isDark;

  const CommandDock({super.key, required this.isDark});

  @override
  State<CommandDock> createState() => _CommandDockState();
}

class _CommandDockState extends State<CommandDock> {
  bool _isExpanded = false;

  void _toggleDock() {
    HapticFeedback.lightImpact();
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final panel = widget.isDark
        ? cs.surfaceContainerHighest.withValues(alpha: 0.95)
        : cs.surfaceContainer;

    return GestureDetector(
      onTap: _isExpanded ? null : _toggleDock,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutBack,
        width: _isExpanded ? MediaQuery.of(context).size.width * 0.85 : 180,
        height: 72,
        margin: const EdgeInsets.only(bottom: 24),
        decoration: BoxDecoration(
          color: panel,
          borderRadius: BorderRadius.circular(36),
          border: Border.all(
            color: cs.outline.withValues(alpha: 0.2),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(36),
          child: _isExpanded ? _buildExpandedControls() : _buildCollapsedStatus(),
        ),
      ),
    );
  }

  Widget _buildCollapsedStatus() {
    final onText = Theme.of(context).colorScheme.onSurface;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.shield_outlined, color: onText, size: 20),
        const SizedBox(width: 12),
        Text(
          'НЕПТУН ОС',
          style: TextStyle(
            color: onText,
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  Widget _buildExpandedControls() {
    final accent = Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _buildDockItem(Icons.map_rounded, 'MAP', () {
          WindowManager().closePanel();
          _toggleDock();
        }, accent),
        _buildDockItem(Icons.radar_rounded, 'RADAR', () {
          WindowManager().openPanel(PanelType.radar);
          _toggleDock();
        }, accent),
        _buildDockItem(Icons.chat_bubble_rounded, 'COMMS', () {
          WindowManager().openPanel(PanelType.comms);
          _toggleDock();
        }, accent),
        _buildDockItem(Icons.shield_rounded, 'SHELTER', () {
          WindowManager().openPanel(PanelType.shelters);
          _toggleDock();
        }, accent),
        _buildDockItem(
          Icons.close_rounded,
          'CLOSE',
          _toggleDock,
          accent,
          isAction: true,
        ),
      ],
    );
  }

  Widget _buildDockItem(
    IconData icon,
    String label,
    VoidCallback onTap,
    Color accent, {
    bool isAction = false,
  }) {
    final muted = Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.45);
    return GestureDetector(
      onTap: () {
        HapticFeedback.mediumImpact();
        onTap();
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon,
            color: isAction ? muted : accent,
            size: 24,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: isAction ? muted : Theme.of(context).colorScheme.onSurface,
              fontSize: 9,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
