import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';

import '../config/app_constants.dart';
import '../core/widgets/neptun_shell_modal.dart';

/// Swipeable картка тривоги з швидкими діями
class SwipeableAlarmCard extends StatefulWidget {
  final Widget child;
  final String alarmText;
  final String location;
  final String timestamp;
  final VoidCallback? onDismiss;
  final VoidCallback? onSave;
  final bool isSaved;
  
  const SwipeableAlarmCard({
    super.key,
    required this.child,
    required this.alarmText,
    required this.location,
    required this.timestamp,
    this.onDismiss,
    this.onSave,
    this.isSaved = false,
  });

  @override
  State<SwipeableAlarmCard> createState() => _SwipeableAlarmCardState();
}

class _SwipeableAlarmCardState extends State<SwipeableAlarmCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  double _dragOffset = 0;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _share() {
    HapticFeedback.mediumImpact();
    final shareText = '''
🚨 ${widget.alarmText}

📍 ${widget.location}
⏰ ${widget.timestamp}

Завантажуй ${AppConstants.appName} для оповіщень про тривоги!
''';
    Share.share(shareText);
  }

  void _save() {
    HapticFeedback.mediumImpact();
    widget.onSave?.call();
  }

  void _dismiss() {
    HapticFeedback.lightImpact();
    widget.onDismiss?.call();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final shareColor = cs.primary;
    final saveColor = cs.secondary;
    final deleteColor = cs.error;
    return GestureDetector(
      onHorizontalDragStart: (_) {
        _controller.forward();
      },
      onHorizontalDragUpdate: (details) {
        setState(() {
          _dragOffset += details.delta.dx;
          _dragOffset = _dragOffset.clamp(-120.0, 120.0);
        });
      },
      onHorizontalDragEnd: (_) {
        _controller.reverse();
        
        if (_dragOffset > 80) {
          // Swipe right - share
          _share();
        } else if (_dragOffset < -80) {
          // Swipe left - dismiss/save
          if (widget.isSaved) {
            _dismiss();
          } else {
            _save();
          }
        }
        
        setState(() {
          _dragOffset = 0;
        });
      },
      onLongPress: () {
        HapticFeedback.mediumImpact();
        _showQuickActions(context);
      },
      child: Stack(
        children: [
          // Background actions
          Positioned.fill(
            child: Row(
              children: [
                // Left action (share)
                Expanded(
                  child: Container(
                    alignment: Alignment.centerLeft,
                    padding: const EdgeInsets.only(left: 20),
                    decoration: BoxDecoration(
                      color: shareColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: AnimatedOpacity(
                      opacity: _dragOffset > 30 ? 1.0 : 0.0,
                      duration: const Duration(milliseconds: 150),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: cs.onPrimary.withValues(alpha: 0.2),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              Icons.share_rounded,
                              color: cs.onPrimary,
                              size: 22,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Поділитись',
                            style: GoogleFonts.plusJakartaSans(
                              color: cs.onPrimary,
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                // Right action (save/dismiss)
                Expanded(
                  child: Container(
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 20),
                    decoration: BoxDecoration(
                      color: widget.isSaved ? deleteColor : saveColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: AnimatedOpacity(
                      opacity: _dragOffset < -30 ? 1.0 : 0.0,
                      duration: const Duration(milliseconds: 150),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            widget.isSaved ? 'Видалити' : 'Зберегти',
                            style: GoogleFonts.plusJakartaSans(
                              color: widget.isSaved ? cs.onError : cs.onSecondary,
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: (widget.isSaved ? cs.onError : cs.onSecondary).withValues(alpha: 0.2),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              widget.isSaved
                                  ? Icons.delete_rounded
                                  : Icons.bookmark_add_rounded,
                              color: widget.isSaved ? cs.onError : cs.onSecondary,
                              size: 22,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Main card
          AnimatedBuilder(
            animation: _scaleAnimation,
            builder: (context, child) {
              return Transform.translate(
                offset: Offset(_dragOffset, 0),
                child: Transform.scale(
                  scale: _scaleAnimation.value,
                  child: widget.child,
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  void _showQuickActions(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    
    NeptunShellModal.showBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        margin: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: cs.surfaceContainer,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: cs.outline.withValues(alpha: 0.2),
            width: 0.5,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: cs.outline.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            
            const SizedBox(height: 20),
            
            // Title
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                widget.location,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            
            const SizedBox(height: 8),
            
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                widget.timestamp,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  color: cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Actions
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Expanded(
                    child: _buildActionButton(
                      context: context,
                      icon: Icons.share_rounded,
                      label: 'Поділитись',
                      color: cs.primary,
                      onTap: () {
                        Navigator.pop(context);
                        _share();
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildActionButton(
                      context: context,
                      icon: widget.isSaved
                          ? Icons.bookmark_remove_rounded
                          : Icons.bookmark_add_rounded,
                      label: widget.isSaved ? 'Видалити' : 'Зберегти',
                      color: widget.isSaved ? cs.error : cs.secondary,
                      onTap: () {
                        Navigator.pop(context);
                        widget.isSaved ? _dismiss() : _save();
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildActionButton(
                      context: context,
                      icon: Icons.copy_rounded,
                      label: 'Копіювати',
                      color: cs.tertiary,
                      onTap: () {
                        Navigator.pop(context);
                        HapticFeedback.mediumImpact();
                        Clipboard.setData(ClipboardData(
                          text: '${widget.alarmText}\n${widget.location}\n${widget.timestamp}',
                        ));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Скопійовано!'),
                            duration: Duration(seconds: 1),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required BuildContext context,
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: color.withValues(alpha: 0.35),
            width: 1,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              label,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
