import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/di/service_locator.dart';
import '../../../../services/data_stream_service.dart';
import '../../../map/domain/map_realtime_link_status.dart';
import '../radar_tokens.dart';

/// Compact live status under app chrome: connection, last fetch, counters.
class RadarLiveStatusBar extends StatelessWidget {
  const RadarLiveStatusBar({
    super.key,
    required this.eventCount,
    required this.activeOblasts,
    required this.lastFetchedAt,
    required this.isStale,
  });

  final int eventCount;
  final int activeOblasts;
  final DateTime? lastFetchedAt;
  final bool isStale;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: sl<DataStreamService>().mapRealtimeLink,
      builder: (context, _) {
        final phase = sl<DataStreamService>().mapRealtimeLink.value.phase;
        final live = phase == MapRealtimeLinkPhase.live;
        return Row(
          children: [
            _LiveDot(live: live),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Радар · ${live ? 'Live' : _phaseLabel(phase)}',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: RadarTokens.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$eventCount подій · $activeOblasts тривог'
                    '${lastFetchedAt != null ? ' · ${_rel(lastFetchedAt!)}' : ''}'
                    '${isStale ? ' · кеш' : ''}',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: RadarTokens.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  String _phaseLabel(MapRealtimeLinkPhase phase) => switch (phase) {
        MapRealtimeLinkPhase.idle => 'Очікування',
        MapRealtimeLinkPhase.connecting => 'Зʼєднання…',
        MapRealtimeLinkPhase.reconnecting => 'Повтор…',
        MapRealtimeLinkPhase.live => 'Live',
      };

  String _rel(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inSeconds < 45) return 'щойно';
    if (d.inMinutes < 60) return '${d.inMinutes} хв';
    return '${d.inHours} год';
  }
}

class _LiveDot extends StatefulWidget {
  const _LiveDot({required this.live});
  final bool live;

  @override
  State<_LiveDot> createState() => _LiveDotState();
}

class _LiveDotState extends State<_LiveDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.live ? RadarTokens.live : RadarTokens.warning;
    return AnimatedBuilder(
      animation: _c,
      builder: (context, child) {
        final scale = widget.live ? 1 + _c.value * 0.25 : 1.0;
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color,
              boxShadow: widget.live
                  ? [
                      BoxShadow(
                        color: color.withValues(alpha: 0.45),
                        blurRadius: 8,
                      ),
                    ]
                  : null,
            ),
          ),
        );
      },
    );
  }
}
