import 'package:flutter/material.dart';

/// Shimmer-эффект загрузки — замена скучных спиннеров
class ShimmerLoading extends StatefulWidget {
  final double width;
  final double height;
  final double borderRadius;

  const ShimmerLoading({
    super.key,
    this.width = double.infinity,
    this.height = 20,
    this.borderRadius = 8,
  });

  @override
  State<ShimmerLoading> createState() => _ShimmerLoadingState();
}

class _ShimmerLoadingState extends State<ShimmerLoading>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = isDark
        ? const Color(0xFF1F2937)
        : const Color(0xFFE2E8F0);
    final highlightColor = isDark
        ? const Color(0xFF374151)
        : const Color(0xFFF1F5F9);

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            gradient: LinearGradient(
              begin: Alignment(-1.0 + 2.0 * _controller.value, 0),
              end: Alignment(1.0 + 2.0 * _controller.value, 0),
              colors: [baseColor, highlightColor, baseColor],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
        );
      },
    );
  }
}

/// Скелетон-карточка для списков
class ShimmerCard extends StatelessWidget {
  const ShimmerCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          const ShimmerLoading(width: 48, height: 48, borderRadius: 12),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ShimmerLoading(
                  width: MediaQuery.of(context).size.width * 0.4,
                  height: 14,
                ),
                const SizedBox(height: 8),
                const ShimmerLoading(height: 10),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Полный скелетон для списков
class ShimmerListSkeleton extends StatelessWidget {
  final int itemCount;
  const ShimmerListSkeleton({super.key, this.itemCount = 8});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      physics: const NeverScrollableScrollPhysics(),
      itemCount: itemCount,
      itemBuilder: (context, index) => const Padding(
        padding: EdgeInsets.only(bottom: 4),
        child: ShimmerCard(),
      ),
    );
  }
}

/// Скелетон для карты/больших блоков
class ShimmerBlock extends StatelessWidget {
  final double height;
  const ShimmerBlock({super.key, this.height = 200});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          ShimmerLoading(height: height, borderRadius: 16),
          const SizedBox(height: 12),
          const ShimmerLoading(height: 14, width: 180),
          const SizedBox(height: 8),
          const ShimmerLoading(height: 10),
        ],
      ),
    );
  }
}
