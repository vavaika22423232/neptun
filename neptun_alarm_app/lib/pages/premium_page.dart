import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:math' as math;
import 'dart:io';
import '../core/pro/pro_features.dart';
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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Помилка відновлення: $e')),
        );
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (_isLoading) {
      return Scaffold(
        body: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: isDark
                  ? [
                      const Color(0xFF000000),
                      const Color(0xFF0A0A0A),
                      const Color(0xFF000000),
                    ]
                  : [
                      const Color(0xFFa8d8ea),
                      const Color(0xFFb8b5ff),
                      const Color(0xFFf8b4c8),
                    ],
            ),
          ),
          child: const Center(
            child: CircularProgressIndicator(color: Colors.white),
          ),
        ),
      );
    }

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: _isPremium
                ? (isDark
                      ? [
                          const Color(0xFF1a1a2e),
                          const Color(0xFF16213e),
                          const Color(0xFF0f0f23),
                        ]
                      : [
                          const Color(0xFFFFD700),
                          const Color(0xFFFF8C00),
                          const Color(0xFFFF6347),
                        ])
                : (isDark
                      ? [
                          const Color(0xFF000000),
                          const Color(0xFF0A0A0A),
                          const Color(0xFF000000),
                        ]
                      : [
                          const Color(0xFFa8d8ea),
                          const Color(0xFFb8b5ff),
                          const Color(0xFFf8b4c8),
                        ]),
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // AppBar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(
                        Icons.arrow_back_ios_rounded,
                        color: Colors.white,
                      ),
                      onPressed: () => Navigator.pop(context),
                    ),
                    const Expanded(
                      child: Text(
                        'Premium',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),

              // Content
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      // Animated Icon
                      AnimatedBuilder(
                        animation: _shimmerController,
                        builder: (context, child) {
                          return Transform.rotate(
                            angle: _isPremium
                                ? math.sin(
                                        _shimmerController.value * 2 * math.pi,
                                      ) *
                                      0.1
                                : 0,
                            child: Container(
                              width: 120,
                              height: 120,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.white.withValues(alpha: 0.2),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.white.withValues(alpha: 0.3),
                                    blurRadius: 30,
                                    spreadRadius: 5,
                                  ),
                                ],
                              ),
                              child: Icon(
                                _isPremium
                                    ? Icons.workspace_premium
                                    : Icons.diamond_rounded,
                                size: 60,
                                color: Colors.white,
                              ),
                            ),
                          );
                        },
                      ),

                      const SizedBox(height: 24),

                      // Status text
                      Text(
                        _isPremium
                            ? '🎉 Premium Активовано!'
                            : 'Отримай Premium',
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                        textAlign: TextAlign.center,
                      ),

                      const SizedBox(height: 8),

                      Text(
                        _isPremium
                            ? 'Дякуємо за підтримку!'
                            : 'Без реклами • Історія • Аналітика • PRO бейдж • І ще...',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.white.withValues(alpha: 0.9),
                        ),
                        textAlign: TextAlign.center,
                      ),

                      const SizedBox(height: 32),

                      // Premium benefits — dynamic list from ProFeature
                      if (!_isPremium) ...[
                        ..._premiumFeaturesList.map((f) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _buildGlassBenefitCard(
                            icon: _featureIcon(f),
                            title: ProGate.featureNames[f] ?? '',
                            description: ProGate.featureDescriptions[f] ?? '',
                            color: _featureColor(f),
                          ),
                        )),
                        const SizedBox(height: 32),

                        // Purchase button
                        ScaleTransition(
                          scale: _pulseAnimation,
                          child: GestureDetector(
                            onTap: _isPurchasing
                                ? null
                                : () => _buyPremium('premium_150_uah'),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [
                                    Color(0xFF00C853),
                                    Color(0xFF009624),
                                  ],
                                ),
                                borderRadius: BorderRadius.circular(20),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(
                                      0xFF00C853,
                                    ).withValues(alpha: 0.5),
                                    blurRadius: 20,
                                    offset: const Offset(0, 8),
                                  ),
                                ],
                              ),
                              child: _isPurchasing
                                  ? const Center(
                                      child: SizedBox(
                                        width: 28,
                                        height: 28,
                                        child: CircularProgressIndicator(
                                          color: Colors.white,
                                          strokeWidth: 3,
                                        ),
                                      ),
                                    )
                                  : Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        const Icon(
                                          Icons.shopping_cart_rounded,
                                          color: Colors.white,
                                          size: 28,
                                        ),
                                        const SizedBox(width: 12),
                                        Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            const Text(
                                              'Отримати Premium',
                                              style: TextStyle(
                                                color: Colors.white,
                                                fontSize: 18,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                            Text(
                                              Platform.isIOS
                                                  ? '150 ₴ • Назавжди'
                                                  : '150 ₴ • Назавжди',
                                              style: const TextStyle(
                                                color: Colors.white70,
                                                fontSize: 13,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 16),

                        // Restore purchases
                        GestureDetector(
                          onTap: _isPurchasing ? null : _restorePurchases,
                          child: Text(
                            'Відновити покупки',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.7),
                              fontSize: 14,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                      ],

                      // Donate section (Android only)
                      if (!Platform.isIOS) ...[
                        const SizedBox(height: 32),

                        Container(
                          padding: const EdgeInsets.all(4),
                          child: Text(
                            '💙 Підтримати',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.9),
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),

                        const SizedBox(height: 16),

                        // Monobank card
                        GestureDetector(
                          onTap: () {
                            HapticFeedback.mediumImpact();
                            _launchDonateUrl(
                              'https://send.monobank.ua/jar/6Vi9TVzJZQ',
                            );
                          },
                          child: Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  Colors.pink.shade400,
                                  Colors.pink.shade600,
                                ],
                              ),
                              borderRadius: BorderRadius.circular(20),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.pink.withValues(alpha: 0.4),
                                  blurRadius: 15,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: const Text(
                                    '🐷',
                                    style: TextStyle(fontSize: 32),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                const Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Монобанка',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      Text(
                                        'Довільна сума на розвиток',
                                        style: TextStyle(
                                          color: Colors.white70,
                                          fontSize: 13,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(alpha: 0.2),
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(
                                    Icons.arrow_forward_rounded,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],

                      const SizedBox(height: 32),

                      // Expense card - куди йдуть кошти
                      _buildGlassExpenseCard(),

                      const SizedBox(height: 32),

                      // Footer
                      const Text(
                        '💙💛',
                        style: TextStyle(fontSize: 32),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Дякуємо, що обрали NEPTUN!',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                          color: Colors.white.withValues(alpha: 0.9),
                        ),
                        textAlign: TextAlign.center,
                      ),

                      const SizedBox(height: 40),
                    ],
                  ),
                ),
              ),
            ],
          ),
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final glassAlpha = isDark ? 0.15 : 0.25;
    final borderAlpha = isDark ? 0.2 : 0.4;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: glassAlpha),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: borderAlpha)),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: color, size: 26),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.8),
                    fontSize: 13,
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
    final expenses = [
      {'label': '🖥️ Сервери', 'percent': 40, 'color': Colors.blue},
      {'label': '📱 Apple Dev', 'percent': 20, 'color': Colors.grey},
      {'label': '🔧 Розробка', 'percent': 15, 'color': Colors.purple},
      {'label': '☕ Кава', 'percent': 15, 'color': Colors.brown},
      {'label': '🇺🇦 ЗСУ', 'percent': 10, 'color': Colors.yellow.shade700},
    ];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.9),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withValues(alpha: isDark ? 0.2 : 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title
          Row(
            children: [
              Icon(
                Icons.pie_chart_rounded,
                color: Theme.of(context).colorScheme.onSurface,
                size: 22,
              ),
              const SizedBox(width: 10),
              Text(
                'Куди йдуть кошти',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

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
                        style: TextStyle(
                          fontSize: 13,
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.9)
                              : Colors.grey[800],
                        ),
                      ),
                      Text(
                        '${e['percent']}%',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Theme.of(context).colorScheme.onSurface,
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
              color: Colors.green.withValues(alpha: isDark ? 0.2 : 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                const Icon(Icons.verified, color: Colors.green, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '100% прозорість • Всі кошти на розвиток',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.green.shade700,
                      fontWeight: FontWeight.w500,
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
