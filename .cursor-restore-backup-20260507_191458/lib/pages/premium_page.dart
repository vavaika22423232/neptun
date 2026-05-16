import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:io';
import '../core/pro/pro_features.dart';
import '../design/design_exports.dart';
import '../services/purchase_service.dart';

/// Features shown on Premium page — implemented + new PRO features.
final List<ProFeature> _premiumFeaturesList = [
  ProFeature.noAds,
  ProFeature.alarmHistory,
  ProFeature.personalAnalytics,
  ProFeature.chatBadge,
  ProFeature.extendedRadar,
  ProFeature.heatmap,
  ProFeature.customAlarmSounds,
];

IconData _featureIcon(ProFeature f) {
  switch (f) {
    case ProFeature.noAds:
      return Icons.block;
    case ProFeature.alarmHistory:
      return Icons.history_rounded;
    case ProFeature.personalAnalytics:
      return Icons.analytics_rounded;
    case ProFeature.chatBadge:
      return Icons.star_rounded;
    case ProFeature.extendedRadar:
      return Icons.radar_rounded;
    case ProFeature.heatmap:
      return Icons.whatshot_rounded;
    case ProFeature.customAlarmSounds:
      return Icons.volume_up_rounded;
    default:
      return Icons.star_rounded;
  }
}

Color _featureColor(ProFeature f) {
  switch (f) {
    case ProFeature.noAds:
      return const Color(0xFFFF6B6B);
    case ProFeature.alarmHistory:
      return const Color(0xFF4ECDC4);
    case ProFeature.personalAnalytics:
      return const Color(0xFF6C5CE7);
    case ProFeature.chatBadge:
      return const Color(0xFFFFE66D);
    case ProFeature.extendedRadar:
      return const Color(0xFF00B894);
    case ProFeature.heatmap:
      return const Color(0xFFE17055);
    case ProFeature.customAlarmSounds:
      return const Color(0xFF0984E3);
    default:
      return const Color(0xFFFFB800);
  }
}

class PremiumPage extends StatefulWidget {
  const PremiumPage({super.key});

  @override
  State<PremiumPage> createState() => _PremiumPageState();
}

class _PremiumPageState extends State<PremiumPage>
    with TickerProviderStateMixin {
  bool _isPremium = false;
  bool _isLoading = true;
  bool _isPurchasing = false;
  final PurchaseService _purchaseService = PurchaseService();

  late AnimationController _shimmerController;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    // Shimmer animation for premium badge
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();

    // Pulse animation for CTA button
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _initializePurchases();
    _loadPremiumStatus();
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _initializePurchases() async {
    await _purchaseService.initialize();

    _purchaseService.onPurchaseSuccess = () {
      setState(() {
        _isPremium = true;
        _isPurchasing = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('🎉 Дякуємо за підтримку! Premium активовано!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    };

    _purchaseService.onPurchaseError = (error) {
      setState(() => _isPurchasing = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Помилка: $error')));
      }
    };
  }

  Future<void> _loadPremiumStatus() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _isPremium = prefs.getBool('is_premium') ?? false;
      _isLoading = false;
    });
  }

  Future<void> _buyPremium(String productId) async {
    setState(() => _isPurchasing = true);
    try {
      final success = await _purchaseService.buyPremium();
      if (!success) {
        setState(() => _isPurchasing = false);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Товар недоступний. Спробуйте пізніше.'),
            ),
          );
        }
      }
      // Якщо успішно - callback onPurchaseSuccess поверне результат
    } catch (e) {
      setState(() => _isPurchasing = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Помилка покупки: $e')));
      }
    }
  }

  Future<void> _restorePurchases() async {
    setState(() => _isPurchasing = true);
    try {
      final restored = await _purchaseService.restorePurchases();
      await _loadPremiumStatus();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              restored
                  ? '✅ Покупки відновлено!'
                  : 'Покупок не знайдено. Переконайтесь, що ви ввійшли з тим самим обліковим записом.',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Помилка відновлення: $e')));
      }
    } finally {
      if (mounted) setState(() => _isPurchasing = false);
    }
  }

  Future<void> _launchDonateUrl(String url) async {
    try {
      final uri = Uri.parse(url);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Помилка: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    const gold = Color(0xFFDDBB5B);

    if (_isLoading) {
      return Scaffold(
        backgroundColor: isDark ? NeptunSurfaces.s0 : cs.surface,
        body: Center(
          child: CircularProgressIndicator(color: isDark ? gold : cs.primary),
        ),
      );
    }

    return Scaffold(
      backgroundColor: isDark ? NeptunSurfaces.s0 : cs.surface,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
          children: [
            Row(
              children: [
                _RoundIconButton(
                  icon: Icons.close_rounded,
                  onTap: () => Navigator.pop(context),
                ),
                const Spacer(),
                TextButton(
                  onPressed: _isPurchasing ? null : _restorePurchases,
                  child: Text(
                    'Відновити',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Center(
              child: Container(
                width: 86,
                height: 86,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: gold.withValues(alpha: 0.45)),
                  color: isDark ? const Color(0xFF111621) : cs.surface,
                ),
                child: Icon(Icons.auto_awesome_rounded, color: gold, size: 38),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              _isPremium ? 'Ви з PRO' : 'NEPTUN PRO',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 34,
                fontWeight: FontWeight.w900,
                height: 1.05,
                color: cs.onSurface,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              _isPremium
                  ? 'Дякуємо за довіру — налаштуйте оформлення нижче.'
                  : 'Більше можливостей без шуму: карти, історія, аналітика та чистий застосунок без реклами.',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                height: 1.35,
                color: cs.onSurface.withValues(alpha: 0.58),
              ),
            ),
            const SizedBox(height: 28),
            TacticalSurface(
              style: TacticalSurfaceStyle.glow,
              accentGlow: gold,
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Можливості',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 3,
                      color: cs.onSurface.withValues(alpha: 0.45),
                    ),
                  ),
                  const SizedBox(height: 14),
                  ..._premiumFeaturesList.map(
                    (f) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _buildGlassBenefitCard(
                        icon: _featureIcon(f),
                        title: ProGate.featureNames[f] ?? '',
                        description: ProGate.featureDescriptions[f] ?? '',
                        color: _featureColor(f),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (!_isPremium) ...[
              const SizedBox(height: 18),
              ScaleTransition(
                scale: _pulseAnimation,
                child: FilledButton(
                  onPressed: _isPurchasing
                      ? null
                      : () => _buyPremium('premium_150_uah'),
                  style: FilledButton.styleFrom(
                    backgroundColor: gold,
                    foregroundColor: const Color(0xFF121317),
                    minimumSize: const Size.fromHeight(54),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(18),
                    ),
                  ),
                  child: _isPurchasing
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2.5),
                        )
                      : Text(
                          'Отримати PRO · 150 ₴',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                ),
              ),
            ],
            if (!Platform.isIOS) ...[
              const SizedBox(height: 14),
              _SupportTile(
                onTap: () {
                  HapticFeedback.mediumImpact();
                  _launchDonateUrl('https://send.monobank.ua/jar/6Vi9TVzJZQ');
                },
              ),
            ],
            const SizedBox(height: 14),
            _buildGlassExpenseCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildGlassBenefitCard({
    required IconData icon,
    required String title,
    required String description,
    required Color color,
  }) {
    final cs = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.fromLTRB(0, 0, 0, 10),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: cs.outline.withValues(alpha: 0.12)),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    color: cs.onSurface,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: GoogleFonts.plusJakartaSans(
                    color: cs.onSurface.withValues(alpha: 0.52),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // Картка витрат у Glass стилі
  Widget _buildGlassExpenseCard() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;
    final expenses = [
      {'label': 'Сервери', 'percent': 40, 'color': Colors.blue},
      {'label': 'Apple Dev', 'percent': 20, 'color': Colors.grey},
      {'label': 'Розробка', 'percent': 15, 'color': Colors.purple},
      {'label': 'Підтримка', 'percent': 15, 'color': Colors.brown},
      {'label': 'ЗСУ', 'percent': 10, 'color': Colors.yellow.shade700},
    ];

    return TacticalSurface(
      style: TacticalSurfaceStyle.flat,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title
          Row(
            children: [
              Icon(
                Icons.pie_chart_rounded,
                color: cs.onSurface.withValues(alpha: 0.8),
                size: 20,
              ),
              const SizedBox(width: 10),
              Text(
                'Куди йдуть кошти',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: cs.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Progress bars
          ...expenses.map(
            (e) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        e['label'] as String,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: cs.onSurface.withValues(alpha: 0.72),
                        ),
                      ),
                      Text(
                        '${e['percent']}%',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: (e['percent'] as int) / 100,
                      backgroundColor: isDark
                          ? Colors.white.withValues(alpha: 0.1)
                          : Colors.grey.withValues(alpha: 0.2),
                      valueColor: AlwaysStoppedAnimation(e['color'] as Color),
                      minHeight: 6,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 8),

          // Footer
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: isDark ? 0.16 : 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                const Icon(Icons.verified, color: Colors.green, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '100% прозорість • Всі кошти на розвиток',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      color: Colors.green.shade700,
                      fontWeight: FontWeight.w700,
                    ),
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

class _RoundIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _RoundIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: cs.surfaceContainerHighest.withValues(alpha: 0.6),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: 24, color: cs.onSurface.withValues(alpha: 0.7)),
      ),
    );
  }
}

class _SupportTile extends StatelessWidget {
  final VoidCallback onTap;

  const _SupportTile({required this.onTap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return TacticalSurface(
      style: TacticalSurfaceStyle.flat,
      padding: const EdgeInsets.all(14),
      onTap: onTap,
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(0xFFDDBB5B).withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.favorite_rounded, color: Color(0xFFDDBB5B)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Підтримати',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                    color: cs.onSurface,
                  ),
                ),
                Text(
                  'Довільна сума на розвиток',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface.withValues(alpha: 0.52),
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right_rounded,
            color: cs.onSurface.withValues(alpha: 0.45),
          ),
        ],
      ),
    );
  }
}
