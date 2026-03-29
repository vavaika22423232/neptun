import 'package:flutter/material.dart';
import 'dart:ui';
import 'dart:io';
class GlassButton extends StatelessWidget {
  final VoidCallback onTap;
  final String label;
  final IconData? icon;
  final bool isPrimary;

  const GlassButton({
    super.key,
    required this.onTap,
    required this.label,
    this.icon,
    this.isPrimary = true,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: isPrimary
              ? LinearGradient(
                  colors: isDark
                      ? [
                          const Color(0xFFa8d8ea).withValues(alpha: 0.6),
                          const Color(0xFFb8b5ff).withValues(alpha: 0.6),
                        ]
                      : [const Color(0xFFa8d8ea), const Color(0xFFb8b5ff)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isPrimary ? null : (isDark ? Colors.white10 : Colors.white24),
          border: isPrimary ? null : Border.all(color: Colors.white38),
          boxShadow: isPrimary
              ? [
                  BoxShadow(
                    color: const Color(0xFFa8d8ea).withValues(alpha: 0.3),
                    blurRadius: 16,
                    offset: const Offset(0, 8),
                  ),
                ]
              : null,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Platform.isAndroid
              ? Container(
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (icon != null) ...[
                        Icon(icon, color: Colors.white, size: 20),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        label,
                        style: const TextStyle(
                          color: Colors
                              .white, // Always white for contrast on gradients
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                )
              : BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                  child: Container(
                    alignment: Alignment.center,
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (icon != null) ...[
                          Icon(icon, color: Colors.white, size: 20),
                          const SizedBox(width: 8),
                        ],
                        Text(
                          label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
        ),
      ),
    );
  }
}
