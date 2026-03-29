import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/neptun_shimmer.dart';
import '../../../services/briefing_service.dart';

/// Full-screen briefing in 5-card story format.
/// Auto-advance 5s per card, manual swipe, gradient backgrounds.
class BriefingPage extends StatefulWidget {
  const BriefingPage({super.key});

  @override
  State<BriefingPage> createState() => _BriefingPageState();
}

class _BriefingPageState extends State<BriefingPage> {
  final PageController _pageController = PageController();
  BriefingData? _data;
  bool _isLoading = true;
  int _currentPage = 0;
  Timer? _autoAdvanceTimer;

  static const _safetyTips = [
    'Тримайте документи та аптечку поруч',
    'Знайте найближче укриття',
    'У тривогу — негайно в укриття',
    'Не використовуйте ліфт під час тривоги',
    'Майте заряджений телефон та powerbank',
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _autoAdvanceTimer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final data = await BriefingService().fetchBriefing();
    if (mounted) {
      setState(() {
        _data = data;
        _isLoading = false;
      });
      _startAutoAdvance();
    }
  }

  void _startAutoAdvance() {
    _autoAdvanceTimer?.cancel();
    _autoAdvanceTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted) return;
      if (_currentPage < 4) {
        _pageController.nextPage(
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOutCubic,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      final cs = Theme.of(context).colorScheme;
      return Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 40),
                NeptunShimmer(
                  width: 200,
                  height: 32,
                  borderRadius: 8,
                ),
                const SizedBox(height: 32),
                NeptunShimmer(
                  width: double.infinity,
                  height: 160,
                  borderRadius: 20,
                ),
                const SizedBox(height: 24),
                NeptunShimmer(
                  width: double.infinity,
                  height: 24,
                  borderRadius: 6,
                ),
                const SizedBox(height: 12),
                NeptunShimmer(
                  width: double.infinity,
                  height: 24,
                  borderRadius: 6,
                ),
                const Spacer(),
                Center(
                  child: Text(
                    'Завантаження брифінгу...',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 14,
                      color: cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: SafeArea(
        child: Column(
          children: [
            if (_data!.fromCache)
              GestureDetector(
                onTap: () {
                  HapticFeedback.lightImpact();
                  _loadData();
                },
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  color: cs.tertiary.withValues(alpha: 0.15),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Офлайн. Показуємо останні дані — тап для оновлення',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          color: cs.tertiary,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Icon(Icons.refresh_rounded, size: 16, color: cs.tertiary),
                    ],
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (i) {
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    curve: Curves.easeInOut,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _currentPage ? 24 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: i <= _currentPage
                          ? cs.primary
                          : cs.onSurface.withValues(alpha: 0.25),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  );
                }),
              ),
            ),
            Expanded(
              child: PageView(
                controller: _pageController,
                onPageChanged: (i) {
                  setState(() => _currentPage = i);
                  HapticFeedback.selectionClick();
                },
                children: [
                  _Card1(data: _data!),
                  _Card2(data: _data!),
                  _Card3(data: _data!),
                  _Card4(data: _data!),
                  _Card5(tip: _safetyTips[math.Random().nextInt(_safetyTips.length)]),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: () {
                      HapticFeedback.lightImpact();
                      _loadData();
                    },
                    icon: Icon(Icons.refresh_rounded, size: 18, color: cs.onSurface.withValues(alpha: 0.7)),
                    label: Text(
                      'Оновити',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  TextButton(
                    onPressed: () {
                      HapticFeedback.lightImpact();
                      context.pop();
                    },
                    child: Text(
                      'Закрити',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface.withValues(alpha: 0.85),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Card1 extends StatelessWidget {
  final BriefingData data;

  const _Card1({required this.data});

  @override
  Widget build(BuildContext context) {
    return _GradientCard(
      gradient: const [
        Color(0xFF1A237E),
        Color(0xFF0D47A1),
      ],
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            data.isMorning ? 'Доброго ранку' : 'Доброго вечора',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 32,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 24),
          _AnimatedCounter(
            value: data.totalAlarmsToday,
            suffix: data.totalAlarmsToday == 0
                ? ' — все спокійно'
                : ' тривог сьогодні',
          ),
        ],
      ),
    );
  }
}

class _Card2 extends StatelessWidget {
  final BriefingData data;

  const _Card2({required this.data});

  @override
  Widget build(BuildContext context) {
    return _GradientCard(
      gradient: const [
        Color(0xFF1B5E20),
        Color(0xFF2E7D32),
      ],
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'Карта тривог',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 16),
          if (data.alarmRegions.isEmpty)
            Text(
              'Жодного регіону з тривогою',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 18,
                color: Colors.white.withValues(alpha: 0.9),
              ),
            )
          else
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: data.alarmRegions.take(8).map((r) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    r.replaceAll(' область', ''),
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 14,
                      color: Colors.white,
                    ),
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
}

class _Card3 extends StatelessWidget {
  final BriefingData data;

  const _Card3({required this.data});

  @override
  Widget build(BuildContext context) {
    return _GradientCard(
      gradient: const [
        Color(0xFFB71C1C),
        Color(0xFFC62828),
      ],
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'Загрози сьогодні',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _ThreatCountItem(label: 'Шахеди', count: data.drones, icon: Icons.flight_rounded),
              _ThreatCountItem(label: 'Ракети', count: data.missiles, icon: Icons.rocket_launch_rounded),
              _ThreatCountItem(label: 'КАБ', count: data.kab, icon: Icons.gps_fixed_rounded),
              _ThreatCountItem(label: 'Балістика', count: data.ballistic, icon: Icons.warning_rounded),
            ],
          ),
        ],
      ),
    );
  }
}

class _ThreatCountItem extends StatelessWidget {
  final String label;
  final int count;
  final IconData icon;

  const _ThreatCountItem({
    required this.label,
    required this.count,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _AnimatedCounter(value: count),
        const SizedBox(height: 4),
        Icon(icon, color: Colors.white70, size: 20),
        const SizedBox(height: 4),
        Text(
          label,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 12,
            color: Colors.white70,
          ),
        ),
      ],
    );
  }
}

class _Card4 extends StatelessWidget {
  final BriefingData data;

  const _Card4({required this.data});

  @override
  Widget build(BuildContext context) {
    return _GradientCard(
      gradient: const [
        Color(0xFF4A148C),
        Color(0xFF6A1B9A),
      ],
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            data.hasMultipleRegions ? 'Ваші регіони' : 'Ваш регіон',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 24),
          if (data.userRegionName != null || data.userRegionsTotal > 0) ...[
            if (!data.hasMultipleRegions && data.userRegionName != null)
              Text(
                data.userRegionName!,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 18,
                  color: Colors.white.withValues(alpha: 0.9),
                ),
                textAlign: TextAlign.center,
              )
            else if (data.hasMultipleRegions)
              Text(
                '${data.userRegionsTotal} обраних',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 16,
                  color: Colors.white.withValues(alpha: 0.85),
                ),
              ),
            if (data.userRegionName != null || data.hasMultipleRegions)
              const SizedBox(height: 16),
            _AnimatedCounter(
              value: data.userRegionAlarmCount,
              suffix: data.hasMultipleRegions
                  ? ' з тривогою'
                  : ' тривог',
            ),
          ] else
            Text(
              'Оберіть регіон у налаштуваннях',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                color: Colors.white70,
              ),
            ),
        ],
      ),
    );
  }
}

class _Card5 extends StatelessWidget {
  final String tip;

  const _Card5({required this.tip});

  @override
  Widget build(BuildContext context) {
    return _GradientCard(
      gradient: const [
        Color(0xFFE65100),
        Color(0xFFEF6C00),
      ],
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.lightbulb_rounded, size: 48, color: Colors.white.withValues(alpha: 0.9)),
          const SizedBox(height: 16),
          Text(
            'Порада дня',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 24),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              tip,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 18,
                height: 1.5,
                color: Colors.white.withValues(alpha: 0.95),
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class _GradientCard extends StatelessWidget {
  final List<Color> gradient;
  final Widget child;

  const _GradientCard({
    required this.gradient,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: gradient,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: gradient.first.withValues(alpha: 0.4),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _AnimatedCounter extends StatefulWidget {
  final int value;
  final String? suffix;

  const _AnimatedCounter({required this.value, this.suffix});

  @override
  State<_AnimatedCounter> createState() => _AnimatedCounterState();
}

class _AnimatedCounterState extends State<_AnimatedCounter>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<int> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _anim = IntTween(begin: 0, end: widget.value).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic),
    );
    _ctrl.forward();
  }

  @override
  void didUpdateWidget(_AnimatedCounter oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) {
      _anim = IntTween(begin: oldWidget.value, end: widget.value).animate(
        CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic),
      );
      _ctrl.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (context, _) {
        return Text(
          '${_anim.value}${widget.suffix ?? ''}',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        );
      },
    );
  }
}
