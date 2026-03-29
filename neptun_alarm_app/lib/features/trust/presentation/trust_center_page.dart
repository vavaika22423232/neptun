import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import '../../../config/api_config.dart';
import '../../../core/widgets/neptun_card.dart';
import '../../../core/widgets/neptun_badge.dart';
import '../../../core/widgets/neptun_shimmer.dart';

class TrustCenterPage extends StatefulWidget {
  const TrustCenterPage({super.key});

  @override
  State<TrustCenterPage> createState() => _TrustCenterPageState();
}

class _TrustCenterPageState extends State<TrustCenterPage> {
  bool _isLoading = true;
  Map<String, dynamic>? _statusData;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    setState(() => _isLoading = true);
    try {
      final resp = await http
          .get(Uri.parse('${ApiConfig.baseUrl}/api/health'))
          .timeout(const Duration(seconds: 5));

      if (resp.statusCode == 200) {
        final data = json.decode(resp.body) as Map<String, dynamic>;
        if (mounted) {
          setState(() {
            _isLoading = false;
            _statusData = {
              'api': 'operational',
              'sse': data['sse'] == true ? 'operational' : 'degraded',
              'worker': data['worker'] == true ? 'operational' : 'degraded',
              'fcm': 'operational',
            };
          });
        }
      } else {
        throw Exception('Status ${resp.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _statusData = {
            'api': 'degraded',
            'sse': 'unknown',
            'worker': 'unknown',
            'fcm': 'unknown',
          };
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Надійність',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
      ),
      body: RefreshIndicator(
        onRefresh: _loadStatus,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Server Status
            NeptunCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.dns_rounded, size: 20, color: cs.primary),
                      const SizedBox(width: 8),
                      Text(
                        'Статус серверів',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface,
                        ),
                      ),
                      const Spacer(),
                      if (!_isLoading)
                        const NeptunBadge.success(label: 'Працює'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (_isLoading)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Column(
                        children: [
                          const NeptunShimmer(width: double.infinity, height: 40, borderRadius: 10),
                          const SizedBox(height: 16),
                          const NeptunShimmer(width: double.infinity, height: 40, borderRadius: 10),
                          const SizedBox(height: 16),
                          const NeptunShimmer(width: double.infinity, height: 40, borderRadius: 10),
                          const SizedBox(height: 16),
                          const NeptunShimmer(width: double.infinity, height: 40, borderRadius: 10),
                        ],
                      ),
                    )
                  else ...[
                    _StatusRow(
                      label: 'API',
                      status: _statusData?['api'] ?? 'unknown',
                    ),
                    _StatusRow(
                      label: 'SSE (реал-тайм)',
                      status: _statusData?['sse'] ?? 'unknown',
                    ),
                    _StatusRow(
                      label: 'Worker (обробка загроз)',
                      status: _statusData?['worker'] ?? 'unknown',
                    ),
                    _StatusRow(
                      label: 'FCM (push-повідомлення)',
                      status: _statusData?['fcm'] ?? 'unknown',
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Data Sources
            NeptunCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.source_rounded, size: 20, color: cs.primary),
                      const SizedBox(width: 8),
                      Text(
                        'Джерела даних',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Дані про загрози збираються з 12+ верифікованих '
                    'Telegram-каналів у реальному часі. Кожне повідомлення '
                    'обробляється AI для витягування типу загрози, '
                    'геолокації та траєкторії.',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: cs.onSurface.withValues(alpha: 0.6),
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Pipeline
            NeptunCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.timeline_rounded, size: 20, color: cs.primary),
                      const SizedBox(width: 8),
                      Text(
                        'Як це працює',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _PipelineStep(
                    step: '1',
                    title: 'Моніторинг каналів',
                    subtitle: 'Автоматичний збір даних з Telegram',
                  ),
                  _PipelineStep(
                    step: '2',
                    title: 'AI-аналіз',
                    subtitle: 'GPT-4o-mini витягує тип загрози та локацію',
                  ),
                  _PipelineStep(
                    step: '3',
                    title: 'Геокодування',
                    subtitle: 'Визначення точних координат (4 рівня)',
                  ),
                  _PipelineStep(
                    step: '4',
                    title: 'Push-повідомлення',
                    subtitle: 'Миттєва доставка через FCM',
                    isLast: true,
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

class _StatusRow extends StatelessWidget {
  final String label;
  final String status;

  const _StatusRow({required this.label, required this.status});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isOperational = status == 'operational';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: isOperational ? cs.secondary : cs.error,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: cs.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }
}

class _PipelineStep extends StatelessWidget {
  final String step;
  final String title;
  final String subtitle;
  final bool isLast;

  const _PipelineStep({
    required this.step,
    required this.title,
    required this.subtitle,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: cs.primary.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Text(
                  step,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: cs.primary,
                  ),
                ),
              ),
              if (!isLast)
                Container(
                  width: 1,
                  height: 24,
                  color: cs.outline.withValues(alpha: 0.3),
                ),
            ],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: cs.onSurface.withValues(alpha: 0.5),
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
