import 'package:flutter/material.dart';
import 'dart:math' as math;

import '../theme/diary_design.dart';

/// Красивий віджет статистики тривог
class AlarmStatsWidget extends StatefulWidget {
  final int totalAlarms;
  final int dronesCount;
  final int rocketsCount;
  final int clearedCount;
  final Map<String, int> regionStats;
  
  const AlarmStatsWidget({
    super.key,
    required this.totalAlarms,
    required this.dronesCount,
    required this.rocketsCount,
    required this.clearedCount,
    required this.regionStats,
  });

  @override
  State<AlarmStatsWidget> createState() => _AlarmStatsWidgetState();
}

class _AlarmStatsWidgetState extends State<AlarmStatsWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _progressAnimation;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    
    _progressAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
    
    _controller.forward();
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    // Знаходимо топ-3 небезпечних регіони
    final sortedRegions = widget.regionStats.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final topRegions = sortedRegions.take(3).toList();
    
    return AnimatedBuilder(
      animation: _progressAnimation,
      builder: (context, child) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isDark
                  ? [
                      DiaryColors.darkSurfaceElevated,
                      DiaryColors.darkSurface,
                    ]
                  : [
                      DiaryColors.background,
                      DiaryColors.surface,
                    ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.1),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            children: [
              // Заголовок
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [
                      Color(0xFF1E3A5F),
                      Color(0xFF0F172A),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: DiaryColors.onPrimary.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.analytics_rounded,
                        color: DiaryColors.onPrimary,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Статистика тривог',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: DiaryColors.onPrimary,
                            ),
                          ),
                          Text(
                            'За останню годину',
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xB3FFFFFF),
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Анимований індикатор
                    _buildPulsingIndicator(),
                  ],
                ),
              ),
              
              // Статистика по типам
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    // Основні показники
                    Row(
                      children: [
                        Expanded(
                          child: _buildStatCard(
                            icon: Icons.warning_rounded,
                            label: 'Всього',
                            value: (widget.totalAlarms * _progressAnimation.value).round(),
                            color: const Color(0xFFFF9500),
                            isDark: isDark,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _buildStatCard(
                            icon: Icons.airplanemode_active_rounded,
                            label: 'Дрони',
                            value: (widget.dronesCount * _progressAnimation.value).round(),
                            color: const Color(0xFFFF9500),
                            isDark: isDark,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _buildStatCard(
                            icon: Icons.rocket_launch_rounded,
                            label: 'Ракети',
                            value: (widget.rocketsCount * _progressAnimation.value).round(),
                            color: const Color(0xFFE63946),
                            isDark: isDark,
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 20),
                    
                    // Прогрес-бар розподілу загроз
                    _buildThreatDistribution(isDark),
                    
                    const SizedBox(height: 20),
                    
                    // Топ небезпечних регіонів
                    if (topRegions.isNotEmpty) ...[
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          '🔥 Найактивніші регіони',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: isDark
                                ? DiaryColors.darkPrimary
                                : DiaryColors.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...topRegions.asMap().entries.map((entry) {
                        final index = entry.key;
                        final region = entry.value;
                        return _buildRegionBar(
                          region.key,
                          region.value,
                          topRegions.first.value,
                          index,
                          isDark,
                        );
                      }),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPulsingIndicator() {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.8, end: 1.2),
      duration: const Duration(milliseconds: 800),
      curve: Curves.easeInOut,
      builder: (context, scale, child) {
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: const Color(0xFF38BDF8),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.45),
                  blurRadius: 8,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
        );
      },
      onEnd: () {
        if (mounted) {
          setState(() {}); // Trigger rebuild to restart animation
        }
      },
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String label,
    required int value,
    required Color color,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            '$value',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: isDark
                  ? DiaryColors.darkPrimary
                  : DiaryColors.primary,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: isDark ? DiaryColors.darkMuted : DiaryColors.muted,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildThreatDistribution(bool isDark) {
    final total = widget.dronesCount + widget.rocketsCount + widget.clearedCount;
    if (total == 0) return const SizedBox.shrink();
    
    final dronePercent = widget.dronesCount / total;
    final rocketPercent = widget.rocketsCount / total;
    final clearedPercent = widget.clearedCount / total;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Розподіл загроз',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: isDark
                    ? DiaryColors.darkPrimary
                    : DiaryColors.primary,
              ),
            ),
            Text(
              '${(dronePercent * 100).toInt()}% / ${(rocketPercent * 100).toInt()}% / ${(clearedPercent * 100).toInt()}%',
              style: TextStyle(
                fontSize: 12,
                color: isDark ? DiaryColors.darkMuted : DiaryColors.muted,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: SizedBox(
            height: 12,
            child: Row(
              children: [
                // Дрони
                Expanded(
                  flex: (dronePercent * 100 * _progressAnimation.value).round().clamp(0, 100),
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color(0xFFFF9500), Color(0xFFFF6B00)],
                      ),
                    ),
                  ),
                ),
                // Ракети
                Expanded(
                  flex: (rocketPercent * 100 * _progressAnimation.value).round().clamp(0, 100),
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color(0xFFE63946), Color(0xFFBE2A35)],
                      ),
                    ),
                  ),
                ),
                // Відбій
                Expanded(
                  flex: (clearedPercent * 100 * _progressAnimation.value).round().clamp(0, 100),
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color(0xFF30D158), Color(0xFF28A745)],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildLegendItem('Дрони', const Color(0xFFFF9500)),
            _buildLegendItem('Ракети', const Color(0xFFE63946)),
            _buildLegendItem('Відбій', const Color(0xFF30D158)),
          ],
        ),
      ],
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
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
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: Theme.of(context).brightness == Brightness.dark
                ? DiaryColors.darkMuted
                : DiaryColors.muted,
          ),
        ),
      ],
    );
  }

  Widget _buildRegionBar(
    String region,
    int count,
    int maxCount,
    int index,
    bool isDark,
  ) {
    final progress = maxCount > 0 ? count / maxCount : 0.0;
    final colors = [
      [const Color(0xFFE63946), const Color(0xFFBE2A35)], // Найнебезпечніший
      [const Color(0xFFFF9500), const Color(0xFFFF6B00)],
      [const Color(0xFFFFCC00), const Color(0xFFFF9500)],
    ];
    final gradientColors = colors[index.clamp(0, 2)];
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  region.replaceAll(' область', '').replaceAll('м. ', ''),
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: isDark
                        ? DiaryColors.darkPrimary.withValues(alpha: 0.72)
                        : DiaryColors.muted,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: gradientColors[0].withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '$count',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: gradientColors[0],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              height: 6,
              child: Stack(
                children: [
                  Container(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.grey.withValues(alpha: 0.2),
                  ),
                  FractionallySizedBox(
                    widthFactor: progress * _progressAnimation.value,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(colors: gradientColors),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Міні круговий графік для статистики
class MiniPieChart extends StatelessWidget {
  final double dronePercent;
  final double rocketPercent;
  final double clearedPercent;
  
  const MiniPieChart({
    super.key,
    required this.dronePercent,
    required this.rocketPercent,
    required this.clearedPercent,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(60, 60),
      painter: _PieChartPainter(
        dronePercent: dronePercent,
        rocketPercent: rocketPercent,
        clearedPercent: clearedPercent,
      ),
    );
  }
}

class _PieChartPainter extends CustomPainter {
  final double dronePercent;
  final double rocketPercent;
  final double clearedPercent;

  _PieChartPainter({
    required this.dronePercent,
    required this.rocketPercent,
    required this.clearedPercent,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;
    
    final dronePaint = Paint()
      ..color = const Color(0xFFFF9500)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;
    
    final rocketPaint = Paint()
      ..color = const Color(0xFFE63946)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;
    
    final clearedPaint = Paint()
      ..color = const Color(0xFF30D158)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    double startAngle = -math.pi / 2;
    
    // Дрони
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      dronePercent * 2 * math.pi,
      false,
      dronePaint,
    );
    startAngle += dronePercent * 2 * math.pi;
    
    // Ракети
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      rocketPercent * 2 * math.pi,
      false,
      rocketPaint,
    );
    startAngle += rocketPercent * 2 * math.pi;
    
    // Відбій
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      clearedPercent * 2 * math.pi,
      false,
      clearedPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
