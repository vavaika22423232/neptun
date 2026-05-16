import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/window_manager.dart';

import 'dart:ui';

class CommandDock extends StatefulWidget {
  final bool isDark;

  const CommandDock({super.key, required this.isDark});

  @override
  State<CommandDock> createState() => _CommandDockState();
}

class _CommandDockState extends State<CommandDock>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;

  void _toggleDock() {
    HapticFeedback.lightImpact();
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _isExpanded ? null : _toggleDock, // Tap to expand if collapsed
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutBack,
        width: _isExpanded ? MediaQuery.of(context).size.width * 0.85 : 180,
        height: 72,
        margin: const EdgeInsets.only(bottom: 24),
        decoration: BoxDecoration(
          color: widget.isDark
              ? Colors.black.withValues(alpha: 0.4)
              : Colors.white.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(36),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.2),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 16,
              spreadRadius: 0,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(36),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
            child: _isExpanded
                ? _buildExpandedControls()
                : _buildCollapsedStatus(),
          ),
        ),
      ),
    );
  }

  Widget _buildCollapsedStatus() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.shield_outlined, color: Colors.white, size: 20),
        const SizedBox(width: 12),
        const Text(
          'НЕПТУН ОС',
          style: TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w700,
            shadows: [Shadow(blurRadius: 5, color: Colors.white)],
          ),
        ),
      ],
    );
  }

  Widget _buildExpandedControls() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _buildDockItem(Icons.map_rounded, 'MAP', () {
          WindowManager().closePanel(); // Show desktop (map)
          _toggleDock();
        }),
        _buildDockItem(Icons.radar_rounded, 'RADAR', () {
          WindowManager().openPanel(PanelType.radar);
          _toggleDock();
        }),
        _buildDockItem(Icons.chat_bubble_rounded, 'COMMS', () {
          WindowManager().openPanel(PanelType.comms);
          _toggleDock();
        }),
        _buildDockItem(Icons.shield_rounded, 'SHELTER', () {
          WindowManager().openPanel(PanelType.shelters);
          _toggleDock();
        }),
        _buildDockItem(
          Icons.close_rounded,
          'CLOSE',
          _toggleDock,
          isAction: true,
        ),
      ],
    );
  }

  Widget _buildDockItem(
    IconData icon,
    String label,
    VoidCallback onTap, {
    bool isAction = false,
  }) {
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
            color: isAction ? Colors.white54 : const Color(0xFF38BDF8),
            size: 24,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: isAction ? Colors.white54 : Colors.white,
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
