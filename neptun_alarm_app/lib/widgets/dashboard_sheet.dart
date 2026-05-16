import 'package:flutter/material.dart';
import '../core/widgets/neptun_card.dart';
import '../design/neptun_design.dart';
import '../panels/radar_panel.dart';

class DashboardSheet extends StatelessWidget {
  const DashboardSheet({super.key});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.15, // Collapsed state (approx 120px on most screens)
      minChildSize: 0.15,
      maxChildSize: 0.85,
      snap: true,
      builder: (context, scrollController) {
        return NeptunCard(
          borderRadius: 32,
          margin: const EdgeInsets.symmetric(horizontal: 0),
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              // Handle / Gripper
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Collapsed Header (Always visible)
              // This should eventually be the "Situation Summary"
              // For now, it's a placeholder header.
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 8,
                ),
                child: Row(
                  children: [
                    Text(
                      'Ситуація',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: NeptunStatus.safe.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: NeptunStatus.safe.withValues(alpha: 0.5),
                        ),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: NeptunStatus.safe,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'СПОКІЙНО',
                            style: Theme.of(context).textTheme.labelSmall
                                ?.copyWith(
                                  color: NeptunStatus.safe,
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // Expanded Content
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  physics: const ClampingScrollPhysics(),
                  child: const Padding(
                    padding: EdgeInsets.all(16.0),
                    // We temporarily embed the old RadarPanel content here
                    // Ideally we should refactor RadarPanel to not have its own glass/padding
                    child: RadarPanel(),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
