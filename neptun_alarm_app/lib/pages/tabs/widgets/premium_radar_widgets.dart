import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../design/neptun_design.dart';
import 'dart:ui';

/// Soft ambient background with radial gradients for depth.
class AmbientBackground extends StatelessWidget {
  const AmbientBackground({super.key});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          top: -100,
          left: -50,
          child: Container(
            width: 400,
            height: 400,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  NeptunStatus.alarm.withValues(alpha: 0.1),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.7],
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 100,
          right: -50,
          child: Container(
            width: 350,
            height: 350,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  const Color(0xFFA78BFA).withValues(alpha: 0.08),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.7],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Premium counter card with rotating radar and pulsing glow.
class PremiumRadarCounterCard extends StatefulWidget {
  final int activeCount;

  const PremiumRadarCounterCard({super.key, required this.activeCount});

  @override
  State<PremiumRadarCounterCard> createState() =>
      _PremiumRadarCounterCardState();
}

class _PremiumRadarCounterCardState extends State<PremiumRadarCounterCard>
    with TickerProviderStateMixin {
  late AnimationController _rotationController;
  late AnimationController _pulseController;
  late AnimationController _glowController;

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: NeptunSpacing.lg),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            NeptunStatus.alarm.withValues(alpha: 0.12),
            const Color(0xFF1F2937).withValues(alpha: 0.9),
          ],
        ),
        border: Border.all(
          color: NeptunStatus.alarm.withValues(alpha: 0.25),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: NeptunStatus.alarm.withValues(alpha: 0.15),
            blurRadius: 60,
            offset: const Offset(0, 20),
          ),
          BoxShadow(
            color: Colors.white.withValues(alpha: 0.05),
            offset: const Offset(0, -1),
            blurRadius: 0,
            spreadRadius: 1,
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Animated Glow Background
          AnimatedBuilder(
            animation: _glowController,
            builder: (context, child) {
              return Positioned(
                top: -80,
                right: -80,
                child: Container(
                  width: 200,
                  height: 200,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        NeptunStatus.alarm.withValues(
                          alpha: 0.3 * (0.5 + 0.5 * _glowController.value),
                        ),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          Padding(
            padding: const EdgeInsets.all(28),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          LucideIcons.activity,
                          size: 16,
                          color: NeptunStatus.alarm,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Активні загрози',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFFD1D5DB),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TweenAnimationBuilder<int>(
                      tween: IntTween(begin: 0, end: widget.activeCount),
                      duration: const Duration(milliseconds: 1000),
                      curve: Curves.easeOutQuart,
                      builder: (context, value, child) {
                        return Text(
                          '$value',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 48,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        );
                      },
                    ),
                  ],
                ),
                // Radar Icon Container
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        NeptunStatus.alarm.withValues(alpha: 0.2),
                        NeptunStatus.alarm.withValues(alpha: 0.1),
                      ],
                    ),
                    border: Border.all(
                      color: NeptunStatus.alarm.withValues(alpha: 0.3),
                      width: 1,
                    ),
                  ),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // Pulsing Ripple
                      AnimatedBuilder(
                        animation: _pulseController,
                        builder: (context, child) {
                          return Container(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(24),
                              boxShadow: [
                                BoxShadow(
                                  color: NeptunStatus.alarm.withValues(
                                    alpha: 0.4 * (1 - _pulseController.value),
                                  ),
                                  blurRadius: 0,
                                  spreadRadius: 12 * _pulseController.value,
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                      RotationTransition(
                        turns: _rotationController,
                        child: Icon(
                          LucideIcons.radio,
                          size: 32,
                          color: NeptunStatus.alarm,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Glassmorphic threat tile with staggered appearance.
class PremiumThreatTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final String time;
  final bool isActive;
  final String type;

  const PremiumThreatTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.time,
    required this.isActive,
    required this.type,
  });

  IconData _getIcon() {
    switch (type.toLowerCase()) {
      case 'missile':
      case 'raketa':
        return LucideIcons.triangleAlert;
      case 'drone':
      case 'shahed':
        return LucideIcons.radio;
      case 'aircraft':
      case 'avia':
        return LucideIcons.plane;
      default:
        return LucideIcons.circleAlert;
    }
  }

  String _getTypeLabel() {
    switch (type.toLowerCase()) {
      case 'missile':
      case 'raketa':
        return 'Ракета';
      case 'drone':
      case 'shahed':
        return 'БПЛА';
      case 'aircraft':
      case 'avia':
        return 'Авіація';
      default:
        return 'Загроза';
    }
  }

  @override
  Widget build(BuildContext context) {
    final bgColor = isActive
        ? LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              NeptunStatus.alarm.withValues(alpha: 0.08),
              const Color(0xFF1F2937).withValues(alpha: 0.8),
            ],
          )
        : null;

    final solidColor = isActive
        ? null
        : const Color(0xFF1F2937).withValues(alpha: 0.4);
    final borderColor = isActive
        ? NeptunStatus.alarm.withValues(alpha: 0.2)
        : Colors.white.withValues(alpha: 0.05);

    final iconColor = isActive ? NeptunStatus.alarm : const Color(0xFF6B7280);
    final textColor = isActive ? Colors.white : const Color(0xFF9CA3AF);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: bgColor,
        color: solidColor,
        border: Border.all(color: borderColor, width: 1),
        boxShadow: isActive
            ? [
                BoxShadow(
                  color: NeptunStatus.alarm.withValues(alpha: 0.1),
                  blurRadius: 32,
                  offset: const Offset(0, 8),
                ),
              ]
            : null,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Icon Container
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(20),
                    gradient: isActive
                        ? LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              NeptunStatus.alarm.withValues(alpha: 0.2),
                              NeptunStatus.alarm.withValues(alpha: 0.1),
                            ],
                          )
                        : null,
                    color: isActive
                        ? null
                        : const Color(0xFF9CA3AF).withValues(alpha: 0.1),
                    border: Border.all(color: borderColor, width: 1),
                  ),
                  child: Icon(_getIcon(), size: 24, color: iconColor),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            _getTypeLabel().toUpperCase(),
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1,
                              color: iconColor,
                            ),
                          ),
                          if (isActive) ...[
                            const SizedBox(width: 8),
                            const StatusPulse(),
                          ],
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        title,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: textColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(
                            LucideIcons.clock,
                            size: 13,
                            color: const Color(0xFF9CA3AF),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            time,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              color: const Color(0xFF9CA3AF),
                            ),
                          ),
                          if (!isActive) ...[
                            const SizedBox(width: 8),
                            const Text(
                              '•',
                              style: TextStyle(color: Color(0xFF9CA3AF)),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Відбій',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: const Color(0xFF34D399),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class StatusPulse extends StatefulWidget {
  const StatusPulse({super.key});

  @override
  State<StatusPulse> createState() => _StatusPulseState();
}

class _StatusPulseState extends State<StatusPulse>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: NeptunStatus.alarm.withValues(
              alpha: 0.3 + 0.7 * _controller.value,
            ),
          ),
        );
      },
    );
  }
}
