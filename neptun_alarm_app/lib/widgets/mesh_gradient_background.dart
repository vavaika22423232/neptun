import 'dart:ui';
import 'dart:io';
import 'package:flutter/material.dart';

class MeshGradientBackground extends StatelessWidget {
  final Widget child;

  const MeshGradientBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Dark Base
        Container(color: const Color(0xFF050505)),

        // Mesh Blobs (Vibrant & Airy)
        Positioned(
          top: -100,
          right: -50,
          child: _buildBlob(const Color(0xFF4B7BFF), 400), // Vibrant Blue
        ),
        Positioned(
          bottom: -100,
          left: -50,
          child: _buildBlob(const Color(0xFFFF3B30), 400), // Primary Red
        ),
        Positioned(
          top: 300,
          left: -100,
          child: _buildBlob(const Color(0xFFD4C4FC), 300), // Soft Purple
        ),
        Positioned(
          bottom: 200,
          right: -50,
          child: _buildBlob(const Color(0xFFFFC6E6), 250), // Soft Pink
        ),

        // Heavy Blur to fuse blobs (skip on Android — too expensive)
        if (!Platform.isAndroid)
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 100, sigmaY: 100),
              child: Container(color: Colors.transparent),
            ),
          ),

        // Subtle Overlay to darken for contrast if needed
        Positioned.fill(
          child: Container(color: Colors.black.withValues(alpha: 0.3)),
        ),

        // Content
        Positioned.fill(child: child),
      ],
    );
  }

  Widget _buildBlob(Color color, double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withValues(alpha: 0.5),
      ),
    );
  }
}
