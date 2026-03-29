import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/widgets/neptun_glass.dart';
import '../models/map_models.dart';
import '../features/map/presentation/threat_detail_sheet.dart';

/// Horizontal scrollable timeline of today's threat events.
/// Event chips colored by threat type; tap to expand details.
class ThreatTimeline extends StatefulWidget {
  final List<Map<String, dynamic>> markers;
  final VoidCallback? onRefresh;

  const ThreatTimeline({
    super.key,
    required this.markers,
    this.onRefresh,
  });

  @override
  State<ThreatTimeline> createState() => _ThreatTimelineState();
}

class _ThreatTimelineState extends State<ThreatTimeline> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToNow());
  }

  void _scrollToNow() {
    if (!_scrollController.hasClients) return;
    final events = _buildEvents();
    if (events.isEmpty) return;
    final now = DateTime.now();
    int closestIdx = 0;
    int minDiff = 86400;
    for (var i = 0; i < events.length; i++) {
      final diff = events[i].timestamp.difference(now).inSeconds.abs();
      if (diff < minDiff) {
        minDiff = diff;
        closestIdx = i;
      }
    }
    final itemWidth = 140.0;
    final offset = (closestIdx * (itemWidth + 8)) - 80;
    _scrollController.animateTo(
      offset.clamp(0.0, _scrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  List<_TimelineEvent> _buildEvents() {
    final now = DateTime.now();
    final todayStart = DateTime(now.year, now.month, now.day);
    final events = <_TimelineEvent>[];

    for (final m in widget.markers) {
      final dateStr = m['date'] ?? m['timestamp'] ?? '';
      final timestamp = DateTime.tryParse(dateStr);
      if (timestamp == null || timestamp.isBefore(todayStart)) continue;

      final type = (m['threatType'] ?? m['threat_type'] ?? m['type'] ?? 'unknown')
          .toString()
          .toLowerCase();
      final place = (m['place'] ?? m['location'] ?? '').toString();
      events.add(_TimelineEvent(
        timestamp: timestamp,
        threatType: type,
        place: place,
        raw: m,
      ));
    }
    events.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return events;
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final events = _buildEvents();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Text(
              'Події сьогодні',
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: cs.onSurface,
              ),
            ),
            const Spacer(),
            if (events.isNotEmpty)
              TextButton.icon(
                onPressed: () {
                  HapticFeedback.lightImpact();
                  _scrollToNow();
                },
                icon: Icon(Icons.schedule_rounded, size: 16, color: cs.primary),
                label: Text(
                  'Зараз',
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: cs.primary,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 44,
          child: events.isEmpty
              ? Center(
                  child: Text(
                    'Подій сьогодні немає',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                )
              : ListView.separated(
                  controller: _scrollController,
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  itemCount: events.length,
                  separatorBuilder: (context, index) => const SizedBox(width: 8),
                  itemBuilder: (context, i) {
                    final ev = events[i];
                    return _EventChip(
                      event: ev,
                      onTap: () => _onEventTap(ev),
                    );
                  },
                ),
        ),
      ],
    );
  }

  void _onEventTap(_TimelineEvent ev) {
    HapticFeedback.lightImpact();
    final marker = _rawToThreatMarker(ev.raw);
    if (context.mounted) {
      ThreatDetailSheet.show(context, marker);
    }
  }

  ThreatMarker _rawToThreatMarker(Map<String, dynamic> raw) {
    final normalized = Map<String, dynamic>.from(raw);
    if (normalized['threat_type'] == null && normalized['threatType'] != null) {
      normalized['threat_type'] = normalized['threatType'];
    }
    if (normalized['place'] == null && normalized['location'] != null) {
      normalized['place'] = normalized['location'];
    }
    return ThreatMarker.fromJson(normalized);
  }
}

class _TimelineEvent {
  final DateTime timestamp;
  final String threatType;
  final String place;
  final Map<String, dynamic> raw;

  _TimelineEvent({
    required this.timestamp,
    required this.threatType,
    required this.place,
    required this.raw,
  });
}

class _EventChip extends StatefulWidget {
  final _TimelineEvent event;
  final VoidCallback onTap;

  const _EventChip({required this.event, required this.onTap});

  @override
  State<_EventChip> createState() => _EventChipState();
}

class _EventChipState extends State<_EventChip>
    with SingleTickerProviderStateMixin {
  late AnimationController _anim;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _scale = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _anim, curve: Curves.elasticOut),
    );
    _anim.forward();
  }

  @override
  void dispose() {
    _anim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final color = _threatColor(widget.event.threatType, cs);
    final timeStr =
        '${widget.event.timestamp.hour.toString().padLeft(2, '0')}:${widget.event.timestamp.minute.toString().padLeft(2, '0')}';

    return ScaleTransition(
      scale: _scale,
      child: GestureDetector(
        onTap: widget.onTap,
        child: NeptunGlass(
          borderRadius: 10,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                timeStr,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface,
                ),
              ),
              if (widget.event.place.isNotEmpty) ...[
                const SizedBox(width: 4),
                SizedBox(
                  width: 80,
                  child: Text(
                    widget.event.place,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: cs.onSurface.withValues(alpha: 0.7),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _threatColor(String type, ColorScheme cs) {
    switch (type) {
      case 'shahed':
      case 'drone':
        return Colors.orange;
      case 'raketa':
      case 'missile':
        return cs.error;
      case 'ballistic':
        return Colors.red.shade700;
      case 'kab':
        return Colors.blue;
      case 'avia':
        return Colors.purple;
      default:
        return cs.error;
    }
  }
}
