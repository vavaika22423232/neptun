import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../radar_tokens.dart';

class RadarNewUpdatesPill extends StatelessWidget {
  const RadarNewUpdatesPill({
    super.key,
    required this.count,
    required this.onTap,
  });

  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (count <= 0) return const SizedBox.shrink();
    return SafeArea(
      child: Align(
        alignment: Alignment.topCenter,
        child: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(RadarTokens.chipRadius),
              child: Ink(
                decoration: BoxDecoration(
                  color: RadarTokens.accentStrong,
                  borderRadius: BorderRadius.circular(RadarTokens.chipRadius),
                  boxShadow: [
                    BoxShadow(
                      color: RadarTokens.accentStrong.withValues(alpha: 0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                child: Text(
                  'Нові оновлення · $count',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: RadarTokens.bg,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
