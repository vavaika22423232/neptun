import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:neptun_alarm_app/config/api_config.dart';

/// Віджет таймера поточної тривоги з прогнозом
class AlarmTimerWidget extends StatefulWidget {
  final String? region;

  const AlarmTimerWidget({super.key, this.region});

  @override
  State<AlarmTimerWidget> createState() => _AlarmTimerWidgetState();
}

class _AlarmTimerWidgetState extends State<AlarmTimerWidget> {
  bool _isAlarmActive = false;
  DateTime? _alarmStartTime;
  Duration _currentDuration = Duration.zero;
  Duration? _averageDuration;
  Timer? _timer;
  String _alarmType = '';
  String _region = '';

  @override
  void initState() {
    super.initState();
    _loadAlarmState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_isAlarmActive && _alarmStartTime != null) {
        setState(() {
          _currentDuration = DateTime.now().difference(_alarmStartTime!);
        });
      }
    });
  }

  Future<void> _loadAlarmState() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final selectedRegions = prefs.getStringList('selected_regions') ?? [];

      if (selectedRegions.isNotEmpty) {
        _region = selectedRegions.first;
      }

      // Спочатку пробуємо API alarm-status
      bool statusLoaded = false;
      try {
        final response = await http
            .get(Uri.parse(ApiConfig.alarmStatus))
            .timeout(const Duration(seconds: 8));

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final alerts = data['alerts'] as Map<String, dynamic>? ?? {};

          // Перевіряємо чи є тривога в обраному регіоні
          for (var key in alerts.keys) {
            if (_region.isNotEmpty &&
                key.toLowerCase().contains(_region.toLowerCase())) {
              final alertData = alerts[key];
              if (alertData['active'] == true) {
                setState(() {
                  _isAlarmActive = true;
                  if (alertData['start_time'] != null) {
                    _alarmStartTime = DateTime.tryParse(
                      alertData['start_time'],
                    );
                  }
                  _alarmType = alertData['type'] ?? 'Повітряна тривога';
                });
                statusLoaded = true;
                break;
              }
            }
          }
        }
      } catch (e) {
        debugPrint('alarm-status API failed: $e');
      }

      // Якщо не вдалося - перевіряємо через messages API
      if (!statusLoaded) {
        try {
          final messagesResponse = await http
              .get(Uri.parse(ApiConfig.messages))
              .timeout(const Duration(seconds: 8));

          if (messagesResponse.statusCode == 200) {
            final data = json.decode(utf8.decode(messagesResponse.bodyBytes));
            final messages = data['messages'] as List? ?? [];

            // Шукаємо останнє повідомлення для нашого регіону
            for (var msg in messages.take(30)) {
              final location = (msg['location'] ?? '').toString().toLowerCase();
              final text = (msg['text'] ?? '').toString().toLowerCase();

              if (_region.isNotEmpty &&
                  location.contains(_region.toLowerCase())) {
                // Перевіряємо чи це тривога чи відбій
                if (text.contains('відбій')) {
                  setState(() {
                    _isAlarmActive = false;
                    _alarmStartTime = null;
                  });
                  break;
                } else if (text.contains('тривога') ||
                    text.contains('бпла') ||
                    text.contains('дрон') ||
                    text.contains('ракет')) {
                  setState(() {
                    _isAlarmActive = true;
                    _alarmStartTime = DateTime.tryParse(msg['timestamp'] ?? '');
                    _alarmType = msg['type'] ?? 'Повітряна тривога';
                  });
                  break;
                }
              }
            }
          }
        } catch (e) {
          debugPrint('Error checking messages for alarm state: $e');
        }
      }

      // Завантажуємо середній час тривоги
      await _loadAverageDuration();
    } catch (e) {
      debugPrint('Error loading alarm state: $e');
    }
  }

  Future<void> _loadAverageDuration() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final avgMinutes = prefs.getInt('avg_alarm_duration_$_region');
      if (avgMinutes != null) {
        setState(() {
          _averageDuration = Duration(minutes: avgMinutes);
        });
      } else {
        // Дефолтне значення - 45 хвилин
        setState(() {
          _averageDuration = const Duration(minutes: 45);
        });
      }
    } catch (e) {
      debugPrint('Error loading average duration: $e');
    }
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '$hoursгод ${minutes.toString().padLeft(2, '0')}хв';
    }
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  double _getProgress() {
    if (_averageDuration == null || _averageDuration!.inSeconds == 0) {
      return 0.0;
    }
    final progress = _currentDuration.inSeconds / _averageDuration!.inSeconds;
    return progress.clamp(0.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (!_isAlarmActive) {
      return _buildNoAlarmState(isDark);
    }

    return _buildAlarmActiveState(isDark);
  }

  Widget _buildNoAlarmState(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF30D158).withValues(alpha: 0.1),
            const Color(0xFF28A745).withValues(alpha: 0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFF30D158).withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF30D158).withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.check_circle_rounded,
              color: Color(0xFF30D158),
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Тривоги немає',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF2D3748),
                  ),
                ),
                Text(
                  _region.isNotEmpty
                      ? _region
                      : 'Оберіть регіон у налаштуваннях',
                  style: TextStyle(
                    fontSize: 13,
                    color: isDark ? Colors.grey[400] : const Color(0xFF718096),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlarmActiveState(bool isDark) {
    final progress = _getProgress();
    final remainingTime = _averageDuration != null
        ? _averageDuration! - _currentDuration
        : null;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFFE63946).withValues(alpha: 0.15),
            const Color(0xFFBE2A35).withValues(alpha: 0.15),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFFE63946).withValues(alpha: 0.5),
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFE63946).withValues(alpha: 0.2),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              // Пульсуюча іконка
              _PulsingIcon(),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          'ТРИВОГА',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: const Color(0xFFE63946),
                            letterSpacing: 1.5,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFE63946),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'LIVE',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _region,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: isDark ? Colors.white : const Color(0xFF2D3748),
                      ),
                    ),
                  ],
                ),
              ),
              // Великий таймер
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    _formatDuration(_currentDuration),
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFFE63946),
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  if (_alarmType.isNotEmpty)
                    Text(
                      _alarmType,
                      style: TextStyle(
                        fontSize: 11,
                        color: isDark
                            ? Colors.grey[400]
                            : const Color(0xFF718096),
                      ),
                    ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Прогрес-бар з прогнозом
          Column(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress,
                  backgroundColor: isDark ? Colors.grey[800] : Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation(
                    progress > 0.8
                        ? const Color(0xFF30D158)
                        : const Color(0xFFE63946),
                  ),
                  minHeight: 8,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Прогноз на основі історії',
                    style: TextStyle(
                      fontSize: 11,
                      color: isDark
                          ? Colors.grey[500]
                          : const Color(0xFF718096),
                    ),
                  ),
                  if (remainingTime != null && remainingTime.inSeconds > 0)
                    Text(
                      '~${_formatDuration(remainingTime)} до відбою',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: progress > 0.8
                            ? const Color(0xFF30D158)
                            : (isDark
                                  ? Colors.grey[400]
                                  : const Color(0xFF718096)),
                      ),
                    )
                  else
                    Text(
                      'Відбій очікується скоро',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: const Color(0xFF30D158),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Пульсуюча іконка тривоги
class _PulsingIcon extends StatefulWidget {
  @override
  State<_PulsingIcon> createState() => _PulsingIconState();
}

class _PulsingIconState extends State<_PulsingIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 1.15,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _scaleAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFE63946),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFFE63946).withValues(alpha: 0.5),
                  blurRadius: 15,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: const Icon(
              Icons.warning_rounded,
              color: Colors.white,
              size: 28,
            ),
          ),
        );
      },
    );
  }
}

/// Компактний віджет для показу в хедері
class CompactAlarmTimer extends StatefulWidget {
  const CompactAlarmTimer({super.key});

  @override
  State<CompactAlarmTimer> createState() => _CompactAlarmTimerState();
}

class _CompactAlarmTimerState extends State<CompactAlarmTimer> {
  final bool _isActive = false;
  Duration _duration = Duration.zero;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _checkAlarmState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_isActive) {
        setState(() {
          _duration += const Duration(seconds: 1);
        });
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _checkAlarmState() async {
    // Тут буде логіка перевірки стану тривоги
    // Поки що просто демо
  }

  @override
  Widget build(BuildContext context) {
    if (!_isActive) return const SizedBox.shrink();

    final minutes = _duration.inMinutes;
    final seconds = _duration.inSeconds.remainder(60);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFE63946),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.timer_rounded, color: Colors.white, size: 14),
          const SizedBox(width: 4),
          Text(
            '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
              fontFeatures: [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}
