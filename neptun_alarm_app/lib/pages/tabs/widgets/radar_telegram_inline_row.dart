import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/utils/open_neptun_telegram.dart';

/// Компактний рядок під шапкою Радару (не окрема картка в середині скролу).
class RadarTelegramInlineRow extends StatelessWidget {
  const RadarTelegramInlineRow({
    super.key,
    required this.onDismiss,
  });

  final VoidCallback onDismiss;

  Future<void> _open() => openNeptunTelegramChannel('radar_banner');

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    const accent = Color(0xFF3A9EFD);

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: cs.outline.withValues(alpha: 0.12)),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: _open,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    children: [
                      Icon(Icons.telegram, size: 18, color: accent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Канал у Telegram — швидкі оновлення',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: cs.primary,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: onDismiss,
              icon: Icon(
                Icons.close_rounded,
                size: 20,
                color: cs.onSurface.withValues(alpha: 0.4),
              ),
              tooltip: 'Приховати',
            ),
          ],
        ),
      ),
    );
  }
}
