import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../services/ballistic_alert_service.dart';
import '../config/api_config.dart';
class RadarPanel extends StatefulWidget {
  const RadarPanel({super.key});

  @override
  State<RadarPanel> createState() => _RadarPanelState();
}

class _RadarPanelState extends State<RadarPanel>
    with SingleTickerProviderStateMixin {
  // Threat states
  bool _ballisticActive = false;
  bool _strategicAviationActive = false;
  bool _mig31kActive = false;
  bool _dronesActive = false;
  bool _kabActive = false;
  bool _cruiseMissilesActive = false;

  // Quantities
  int _ballisticCount = 0;
  int _dronesCount = 0;
  int _kabCount = 0;
  int _cruiseMissilesCount = 0;

  // State
  // bool _isLoading = true; // Unused
  // bool _hasError = false; // Unused
  DateTime? _lastUpdated;
  Timer? _refreshTimer;

  // Animation
  late AnimationController _pulseController;

  final _ballisticService = BallisticAlertService();

  @override
  void initState() {
    super.initState();

    // Pulse animation for active threats
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000), // Slower, calmer breathing
    )..repeat(reverse: true);

    _loadThreats();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 60),
      (_) => _loadThreats(),
    );

    _ballisticActive = _ballisticService.isBallisticThreatActive;
    _ballisticService.onBallisticThreat(_onBallisticThreat);
    _ballisticService.onBallisticAllClear(_onBallisticAllClear);
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _pulseController.dispose();
    _ballisticService.removeCallback(_onBallisticThreat);
    _ballisticService.removeCallback(_onBallisticAllClear);
    super.dispose();
  }

  void _onBallisticThreat(String? region) {
    if (mounted) setState(() => _ballisticActive = true);
  }

  void _onBallisticAllClear(String? region) {
    if (mounted) setState(() => _ballisticActive = false);
  }

  Future<void> _loadThreats() async {
    try {
      // setState(() { _hasError = false; });
      final response = await http
          .get(Uri.parse(ApiConfig.threats))
          .timeout(ApiConfig.httpTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final summary = data['summary'] as Map<String, dynamic>? ?? {};
        final threats = data['threats'] as List? ?? [];

        if (mounted) {
          setState(() {
            _dronesCount = (summary['drones'] as num?)?.toInt() ?? 0;
            _cruiseMissilesCount = (summary['missiles'] as num?)?.toInt() ?? 0;
            _kabCount = (summary['kab'] as num?)?.toInt() ?? 0;
            _ballisticCount = (summary['ballistic'] as num?)?.toInt() ?? 0;

            _dronesActive = _dronesCount > 0;
            _cruiseMissilesActive = _cruiseMissilesCount > 0;
            _kabActive = _kabCount > 0;
            if (_ballisticCount > 0) _ballisticActive = true;

            _strategicAviationActive = false;
            _mig31kActive = false;

            for (final threat in threats) {
              final text =
                  threat['description']?.toString().toLowerCase() ?? '';
              if (text.contains('ту-95') ||
                  text.contains('tu-95') ||
                  text.contains('ту-160') ||
                  text.contains('tu-160') ||
                  text.contains('стратегічн')) {
                _strategicAviationActive = true;
              }
              if (text.contains('міг-31') ||
                  text.contains('mig-31') ||
                  text.contains('кинджал') ||
                  text.contains('kinzhal')) {
                _mig31kActive = true;
              }
            }

            final updatedAt = data['updated_at'];
            if (updatedAt != null) {
              try {
                _lastUpdated = DateTime.parse(updatedAt.toString());
              } catch (_) {}
            }
            _lastUpdated ??= DateTime.now();
            // _isLoading = false;
          });
        }
      }
    } catch (e) {
      // if (mounted) setState(() { _isLoading = false; _hasError = true; });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Bento Grid Layout
    // We are inside the Sheet, so we have width constraints.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Total Threats Hero
        _buildTotalThreatsHero(),

        const SizedBox(height: 16),

        // Threat Matrix (Grid)
        LayoutBuilder(
          builder: (context, constraints) {
            final halfWidth = (constraints.maxWidth - 12) / 2; // 12 is gap
            return Column(
              children: [
                Row(
                  children: [
                    _buildBentoCell(
                      width: halfWidth,
                      title: 'БАЛІСТИКА',
                      count: _ballisticCount,
                      isActive: _ballisticActive,
                      isCritical: true,
                      color: Theme.of(context).colorScheme.error,
                      icon: Icons.bolt,
                    ),
                    const SizedBox(width: 12),
                    _buildBentoCell(
                      width: halfWidth,
                      title: 'АВІАЦІЯ',
                      count:
                          _cruiseMissilesCount, // Missiles count often correlated or separate
                      subtitle: _strategicAviationActive
                          ? 'Ту-95/160'
                          : (_mig31kActive ? 'МіГ-31К' : null),
                      isActive:
                          _strategicAviationActive ||
                          _mig31kActive ||
                          _cruiseMissilesActive,
                      isCritical: _strategicAviationActive || _mig31kActive,
                      color: Theme.of(context).colorScheme.tertiary,
                      icon: Icons.airplanemode_active,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _buildBentoCell(
                      width: halfWidth,
                      title: 'ШАХЕДИ',
                      count: _dronesCount,
                      isActive: _dronesActive,
                      color: Theme.of(context).colorScheme.tertiary,
                      icon: Icons.android, // Or explicit drone icon if avail
                    ),
                    const SizedBox(width: 12),
                    _buildBentoCell(
                      width: halfWidth,
                      title: 'КАБ / УМПК',
                      count: _kabCount,
                      isActive: _kabActive,
                      color: Theme.of(context).colorScheme.tertiary,
                      icon: Icons.gps_fixed,
                    ),
                  ],
                ),
              ],
            );
          },
        ),

        const SizedBox(height: 24),

        // Footer Data
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'STATUS: MONITORING',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                letterSpacing: 1.2,
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.4),
              ),
            ),
            if (_lastUpdated != null)
              Text(
                'UPDATED: ${_lastUpdated!.hour.toString().padLeft(2, '0')}:${_lastUpdated!.minute.toString().padLeft(2, '0')}:${_lastUpdated!.second.toString().padLeft(2, '0')}',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  fontFamily: 'JetBrains Mono', // Explicitly ensure mono
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.4),
                ),
              ),
          ],
        ),
        const SizedBox(height: 40), // Bottom padding for scroll
      ],
    );
  }

  Widget _buildTotalThreatsHero() {
    final total =
        _ballisticCount + _dronesCount + _kabCount + _cruiseMissilesCount;
    final hasThreats =
        total > 0 ||
        _ballisticActive ||
        _strategicAviationActive ||
        _mig31kActive;

    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        final pulse = hasThreats ? _pulseController.value : 0.0;
        final cs = Theme.of(context).colorScheme;
        final borderColor = hasThreats
            ? cs.error.withValues(alpha: 0.3 + (0.3 * pulse))
            : cs.outline.withValues(alpha: 0.1);

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 24),
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).colorScheme.surfaceContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: borderColor, width: 1),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TOTAL THREATS',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      letterSpacing: 1.5,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    hasThreats ? '$total' : '0',
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                      fontSize: 64,
                      fontWeight: FontWeight.w200,
                      color: hasThreats ? cs.error : cs.secondary,
                    ),
                  ),
                ],
              ),

              // Status Icon / Pulse
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: hasThreats
                      ? cs.error.withValues(alpha: 0.1 + (0.1 * pulse))
                      : cs.secondary.withValues(alpha: 0.1),
                  border: Border.all(
                    color: hasThreats
                        ? cs.error.withValues(alpha: 0.5)
                        : cs.secondary.withValues(alpha: 0.5),
                  ),
                ),
                child: Icon(
                  hasThreats
                      ? Icons.warning_amber_rounded
                      : Icons.shield_outlined,
                  color: hasThreats ? cs.error : cs.secondary,
                  size: 32,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildBentoCell({
    required double width,
    required String title,
    int? count,
    String? subtitle,
    required bool isActive,
    bool isCritical = false,
    required Color color,
    required IconData icon,
  }) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        final pulse = isActive ? _pulseController.value : 0.0;
        // Active cells breathe if critical or just active
        final bgOpacity = isActive ? (isCritical ? 0.15 : 0.1) : 0.03;
        final borderOpacity = isActive ? (0.3 + (0.2 * pulse)) : 0.05;

        return Container(
          width: width,
          height: 120,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: color.withValues(alpha: bgOpacity),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: color.withValues(alpha: borderOpacity),
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Icon(
                    icon,
                    color: isActive ? color : Theme.of(context).disabledColor,
                    size: 20,
                  ),
                  if (count != null && count > 0)
                    Text(
                      'x$count',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: color,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      letterSpacing: 0.5,
                      fontWeight: FontWeight.bold,
                      color: isActive ? color : Theme.of(context).disabledColor,
                    ),
                  ),
                  if (subtitle != null && isActive)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          fontSize: 9,
                          color: color.withValues(alpha: 0.8),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}
