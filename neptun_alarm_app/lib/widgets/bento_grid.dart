import 'package:flutter/material.dart';

import '../design/neptun_breakpoints.dart';
import '../design/neptun_design.dart';

/// Bento-сітка: адаптивна кількість колонок, відступи з токенів теми.
class BentoGrid extends StatelessWidget {
  final List<Widget> children;
  final int? crossAxisCount;
  final double? spacing;
  final EdgeInsetsGeometry? padding;
  final bool shrinkWrap;
  final ScrollPhysics? physics;
  final double childAspectRatio;

  const BentoGrid({
    super.key,
    required this.children,
    this.crossAxisCount,
    this.spacing,
    this.padding,
    this.shrinkWrap = true,
    this.physics = const NeverScrollableScrollPhysics(),
    this.childAspectRatio = 1.0,
  });

  @override
  Widget build(BuildContext context) {
    final gap = spacing ?? NeptunSpacing.bentoGap;
    final count = crossAxisCount ?? NeptunBreakpoints.bentoCrossAxisCount(context);

    return Padding(
      padding: padding ?? const EdgeInsets.symmetric(horizontal: NeptunSpacing.screenHorizontal),
      child: GridView.builder(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: count,
          crossAxisSpacing: gap,
          mainAxisSpacing: gap,
          childAspectRatio: childAspectRatio,
        ),
        itemCount: children.length,
        shrinkWrap: shrinkWrap,
        physics: physics,
        itemBuilder: (context, index) => children[index],
      ),
    );
  }
}

/// Плитка з заявленим span (для майбутнього staggered; зараз делегує дитині).
class BentoTile extends StatelessWidget {
  final Widget child;
  final int crossAxisCellCount;
  final int mainAxisCellCount;

  const BentoTile({
    super.key,
    required this.child,
    this.crossAxisCellCount = 1,
    this.mainAxisCellCount = 1,
  });

  @override
  Widget build(BuildContext context) => child;
}
