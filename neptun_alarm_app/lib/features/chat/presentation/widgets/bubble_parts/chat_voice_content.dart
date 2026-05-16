import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ChatVoiceContent extends StatelessWidget {
  final int duration;
  final bool isPlaying;
  final ColorScheme colorScheme;
  final VoidCallback onTap;
  final Color? textColor;

  const ChatVoiceContent({
    super.key,
    required this.duration,
    required this.isPlaying,
    required this.colorScheme,
    required this.onTap,
    this.textColor,
  });

  Color get _labelColor => textColor ?? colorScheme.onSurface;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Голосове повідомлення $duration секунд',
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: colorScheme.primary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: Icon(
                    isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    key: ValueKey<bool>(isPlaying),
                    color: colorScheme.primary,
                    size: 20,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildWaveform(),
                  const SizedBox(height: 4),
                  Text(
                    'Голосове • $durationс',
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                      color: _labelColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: 8),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWaveform() {
    return Row(
      children: List.generate(15, (index) {
        // Aesthetic static waveform
        final height = (index % 3 + 1) * 4.0 + (index % 5) * 2.0;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 1),
          width: 2.5,
          height: isPlaying ? height : (height / 2 + 2),
          decoration: BoxDecoration(
            color: isPlaying
                ? colorScheme.primary
                : _labelColor.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(2),
          ),
        );
      }),
    );
  }
}
