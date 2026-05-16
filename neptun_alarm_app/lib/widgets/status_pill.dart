import 'dart:async';
import 'package:flutter/material.dart';
import '../core/widgets/neptun_card.dart';
import '../design/neptun_design.dart';

class StatusPill extends StatefulWidget {
  const StatusPill({super.key});

  @override
  State<StatusPill> createState() => _StatusPillState();
}

class _StatusPillState extends State<StatusPill> {
  late Timer _timer;
  late DateTime _now;

  @override
  void initState() {
    super.initState();
    _now = DateTime.now();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() => _now = DateTime.now());
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final timeString =
        "${_now.hour.toString().padLeft(2, '0')}:${_now.minute.toString().padLeft(2, '0')}";

    return NeptunCard(
      borderRadius: 30,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Time
          Text(
            timeString,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.bold,
              letterSpacing: 1.0,
            ),
          ),

          Container(
            height: 12,
            width: 1,
            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.5),
            margin: const EdgeInsets.symmetric(horizontal: 12),
          ),

          // Network Status (Mock)
          Icon(Icons.wifi, size: 14, color: NeptunStatus.safe),
          const SizedBox(width: 6),
          Text(
            'ONLINE',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              fontSize: 10,
              color: NeptunStatus.safe,
            ),
          ),
        ],
      ),
    );
  }
}
