import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../config/api_config.dart';
import '../../../../models/chat_message.dart';
import '../../../../design/neptun_design.dart';
import '../../../../theme/diary_design.dart';
import '../../../../services/pro_customization_service.dart';
import '../../../../core/di/service_locator.dart';
import '../../../../core/pro/pro_features.dart';
import '../../../../core/widgets/neptun_shell_modal.dart';
import 'chat_context_menu.dart';
import 'chat_image_gallery.dart';
import 'bubble_parts/chat_reply_preview.dart';
import 'bubble_parts/chat_image_content.dart';
import 'bubble_parts/chat_voice_content.dart';
import 'bubble_parts/chat_reaction_row.dart';

/// **Modern "Candy" Chat Bubble (2026)**
/// Features:
/// - Decomposed architecture (bubble_parts/)
/// - Smooth AnimationController-based swipe-to-reply
/// - Premium ChatImageGallery integration
/// - Enhanced accessibility & semantics
class ChatMessageBubble extends StatefulWidget {
  final ChatMessage message;
  final bool isMine;
  final bool isFirstInGroup;
  final bool isLastInGroup;
  final String myDeviceId;
  /// Used when API strips reaction [deviceId] — match own reactions by nickname.
  final String? myNickname;
  final bool isModerator;
  final VoidCallback onReply;
  final void Function(String emoji) onReact;
  final VoidCallback onDelete;
  final VoidCallback? onBan;
  final VoidCallback? onReport;
  final VoidCallback? onBlock;
  final VoidCallback onCopy;
  final void Function(String messageId, String url)? onPlayVoice;
  final bool isPlayingVoice;
  final String? searchHighlight;
  final VoidCallback? onEdit;
  final bool isPending;
  final VoidCallback? onDeleteAll;

  const ChatMessageBubble({
    super.key,
    required this.message,
    required this.isMine,
    this.isFirstInGroup = true,
    this.isLastInGroup = true,
    required this.myDeviceId,
    this.myNickname,
    required this.isModerator,
    required this.onReply,
    required this.onReact,
    required this.onDelete,
    this.onBan,
    this.onReport,
    this.onBlock,
    required this.onCopy,
    this.onPlayVoice,
    this.isPlayingVoice = false,
    this.searchHighlight,
    this.onEdit,
    this.isPending = false,
    this.onDeleteAll,
  });

  @override
  State<ChatMessageBubble> createState() => _ChatMessageBubbleState();
}

class _ChatMessageBubbleState extends State<ChatMessageBubble> with TickerProviderStateMixin {
  late AnimationController _dragController;
  late AnimationController _avatarPulseController;
  late CurvedAnimation _avatarPulseCurve;

  bool _hasTriggered = false;
  static const _swipeThreshold = 60.0;
  static const _maxDrag = 80.0;

  final ProCustomizationService _proService = sl<ProCustomizationService>();

  /// Server may still attach generic anonymous labels while JWT/registry lag;
  /// show local nick for own bubbles when we recognise the placeholder pattern.
  String get _authorLabelForMine {
    final uid = widget.message.userId.trim();
    final looksPlaceholder =
        uid.isEmpty || uid == 'Анонім' || _looksLikeAutoGuestNickname(uid);
    if (looksPlaceholder) {
      final mine = widget.myNickname?.trim();
      if (mine != null && mine.isNotEmpty) return mine;
    }
    return uid.isEmpty ? '?' : uid;
  }

  bool _looksLikeAutoGuestNickname(String uid) {
    final u = uid.trim().toLowerCase();
    return u.startsWith('анонім·') ||
        u.startsWith('анонім.') ||
        u.startsWith('anonymous·');
  }

  String get _myAvatarInitials {
    final label = _authorLabelForMine;
    if (label.length >= 2) return label.substring(0, 2).toUpperCase();
    if (label.isNotEmpty) return label[0].toUpperCase();
    return '?';
  }

  /// Per-message Hero tag — same URL in multiple bubbles must not share one tag.
  String get _imageHeroTag => 'chat_img_${widget.message.id}';

  void _openImageGallery() => _showFullScreenImage(widget.message.imageUrl!);

  @override
  void initState() {
    super.initState();
    _dragController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _avatarPulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );
    _avatarPulseCurve = CurvedAnimation(
      parent: _avatarPulseController,
      curve: Curves.easeInOut,
    );
  }

  @override
  void dispose() {
    _avatarPulseCurve.dispose();
    _dragController.dispose();
    _avatarPulseController.dispose();
    super.dispose();
  }

  void _syncMyAvatarPulse() {
    final pulse = widget.isMine &&
        widget.isFirstInGroup &&
        ProGate.isPro &&
        _proService.isAnimatedAvatarEnabled;
    if (pulse) {
      if (!_avatarPulseController.isAnimating) {
        _avatarPulseController.repeat(reverse: true);
      }
    } else {
      if (_avatarPulseController.isAnimating) {
        _avatarPulseController.stop();
      }
      _avatarPulseController.value = 0;
    }
  }

  void _onHorizontalDragUpdate(DragUpdateDetails details) {
    final delta = details.primaryDelta ?? 0;
    final newOffset = (_dragController.value * _maxDrag + delta);
    
    // Convert to normalized value (0.0 to 1.0)
    double normalized;
    if (widget.isMine) {
      normalized = (newOffset / -_maxDrag).clamp(0.0, 1.0);
    } else {
      normalized = (newOffset / _maxDrag).clamp(0.0, 1.0);
    }
    
    _dragController.value = normalized;

    if (!_hasTriggered && (_dragController.value * _maxDrag) >= _swipeThreshold) {
      _hasTriggered = true;
      HapticFeedback.lightImpact();
    }
  }

  void _onHorizontalDragEnd(DragEndDetails details) {
    if ((_dragController.value * _maxDrag) >= _swipeThreshold) {
      widget.onReply();
    }
    _dragController.reverse();
    _hasTriggered = false;
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    _syncMyAvatarPulse();

    return Padding(
      padding: EdgeInsets.only(
        top: widget.isFirstInGroup ? 10.0 : 3.0,
        bottom: widget.isLastInGroup ? 10.0 : 3.0,
      ),
      child: Semantics(
        container: true,
        label: widget.isMine
            ? 'Ваше повідомлення'
            : 'Повідомлення від ${widget.message.userId}',
        child: GestureDetector(
        onDoubleTap: () => widget.onReact('👍'),
        onLongPress: () => _showContextMenu(context),
        onHorizontalDragUpdate: _onHorizontalDragUpdate,
        onHorizontalDragEnd: _onHorizontalDragEnd,
        child: AnimatedBuilder(
          animation: _dragController,
          builder: (context, child) {
            final dragOffset = _dragController.value * (widget.isMine ? -_maxDrag : _maxDrag);
            final replyIconOpacity = (_dragController.value * _maxDrag / _swipeThreshold).clamp(0.0, 1.0);
            
            return Stack(
              alignment: widget.isMine ? Alignment.centerRight : Alignment.centerLeft,
              children: [
                if (_dragController.value > 0)
                  Positioned(
                    left: widget.isMine ? null : 16,
                    right: widget.isMine ? 16 : null,
                    child: Opacity(
                      opacity: replyIconOpacity,
                      child: Transform.scale(
                        scale: 0.8 + (replyIconOpacity * 0.4),
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: cs.primary,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(Icons.reply_rounded,
                              size: 20, color: cs.onPrimary),
                        ),
                      ),
                    ),
                  ),
                Transform.translate(
                  offset: Offset(dragOffset, 0),
                  child: _buildBubbleLayout(context),
                ),
              ],
            );
          },
        ),
        ),
      ),
    );
  }

  Widget _buildBubbleLayout(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: widget.isMine ? 64 : 12,
        right: widget.isMine ? 12 : 64,
      ),
      child: Row(
        mainAxisAlignment: widget.isMine ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!widget.isMine) ...[
            if (widget.isFirstInGroup)
              _buildPeerAvatar()
            else
              const SizedBox(width: 36),
            const SizedBox(width: 8),
          ],
          Flexible(child: _buildBubble(context)),
          if (widget.isMine) ...[
            const SizedBox(width: 8),
            if (widget.isFirstInGroup)
              _buildMyAvatar()
            else
              const SizedBox(width: 36),
          ],
        ],
      ),
    );
  }

  Widget _buildPeerAvatar() {
    final color = _colorForNick(widget.message.userId);

    return CircleAvatar(
      radius: 18,
      backgroundColor: color,
      child: Text(
        widget.message.avatarInitials,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          fontWeight: FontWeight.w800,
          color: Colors.white,
        ),
      ),
    );
  }

  Widget _buildMyAvatar() {
    final color = _colorForNick(_authorLabelForMine);
    final useProGradient = widget.message.isPro ||
        (ProGate.isPro && _proService.isAnimatedAvatarEnabled);

    if (!useProGradient) {
      return CircleAvatar(
        radius: 18,
        backgroundColor: color,
        child: Text(
          _myAvatarInitials,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 14,
            fontWeight: FontWeight.w800,
            color: Colors.white,
          ),
        ),
      );
    }

    final core = Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: color,
      ),
      alignment: Alignment.center,
      child: Text(
        _myAvatarInitials,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          fontWeight: FontWeight.w800,
          color: Colors.white,
        ),
      ),
    );

    if (ProGate.isPro && _proService.isAnimatedAvatarEnabled) {
      return AnimatedBuilder(
        animation: _avatarPulseController,
        builder: (context, child) {
          final scale = 1.0 + _avatarPulseCurve.value * 0.06;
          return Transform.scale(scale: scale, child: child);
        },
        child: core,
      );
    }
    return core;
  }

  Widget _buildBubble(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    final proTheme =
        widget.isMine && ProGate.isPro ? _proService.selectedChatTheme : ChatTheme.defaultTheme;

    final Color bubbleColor;
    final Color bodyTextColor;
    final Color borderColor;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (proTheme.id == 'default') {
      if (widget.isMine) {
        bubbleColor = cs.primary;
        bodyTextColor = cs.onPrimary;
        borderColor = cs.primary;
      } else {
        // Чіткіший шар над градієнтом чату (#1A1F2E ≈ як у макеті)
        bubbleColor =
            isDark ? DiaryColors.darkSurfaceElevated : cs.surface;
        bodyTextColor = cs.onSurface;
        borderColor = isDark
            ? DiaryColors.darkBorder.withValues(alpha: 0.75)
            : cs.outlineVariant.withValues(alpha: 0.85);
      }
    } else {
      bubbleColor = proTheme.bubbleColor.withValues(alpha: 0.25);
      bodyTextColor = cs.onSurface;
      borderColor = proTheme.bubbleColor.withValues(alpha: 0.3);
    }

    final r = NeptunRadius.lg;
    final small = 4.0;

    return Container(
      decoration: BoxDecoration(
        color: bubbleColor,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(widget.isFirstInGroup || widget.isMine ? r : small),
          topRight: Radius.circular(widget.isFirstInGroup || !widget.isMine ? r : small),
          bottomLeft: Radius.circular(!widget.isMine && widget.isLastInGroup ? small : r),
          bottomRight: Radius.circular(widget.isMine && widget.isLastInGroup ? small : r),
        ),
        border: Border.all(
          color: borderColor,
          width: 1,
        ),
        boxShadow: isDark
            ? [
                BoxShadow(
                  color: Colors.black.withValues(alpha: widget.isMine ? 0.18 : 0.28),
                  blurRadius: widget.isMine ? 8 : 12,
                  offset: const Offset(0, 3),
                ),
              ]
            : null,
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxW = constraints.maxWidth;
          if (maxW.isFinite && maxW <= 0) {
            return const SizedBox.shrink();
          }
          return ConstrainedBox(
            constraints: BoxConstraints(
              minWidth: 0,
              maxWidth: maxW.isFinite ? maxW : double.infinity,
            ),
            child: IntrinsicWidth(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (!widget.isMine && widget.isFirstInGroup) _buildSenderHeader(cs),
                  if (widget.message.replyTo != null)
                    ChatReplyPreview(
                      reply: widget.message.replyTo!,
                      colorScheme: cs,
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (widget.message.isVoice)
                          ChatVoiceContent(
                            duration: widget.message.audioDuration ?? 0,
                            isPlaying: widget.isPlayingVoice,
                            colorScheme: cs,
                            textColor: bodyTextColor,
                            onTap: () => widget.onPlayVoice?.call(
                              widget.message.id,
                              widget.message.audioUrl!,
                            ),
                          )
                        else if (widget.message.isImage)
                          ChatImageContent(
                            imageUrl: widget.message.imageUrl!,
                            heroTag: _imageHeroTag,
                            colorScheme: cs,
                            onTap: _openImageGallery,
                          )
                        else
                          _buildMessageText(
                            widget.message.message,
                            bodyTextColor,
                          ),
                        const SizedBox(height: 4),
                        _buildFooterInfo(cs, bodyTextColor: bodyTextColor),
                      ],
                    ),
                  ),
                  ChatReactionRow(
                    reactions: widget.message.reactions,
                    myDeviceId: widget.myDeviceId,
                    myNickname: widget.myNickname,
                    onReact: widget.onReact,
                    colorScheme: cs,
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSenderHeader(ColorScheme cs) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            widget.message.userId,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: _colorForNick(widget.message.userId),
            ),
          ),
          if (widget.message.isModerator) ...[
            const SizedBox(width: 4),
            Icon(Icons.verified_user_rounded, size: 12, color: cs.onSurface),
          ],
          if (widget.message.isPro) ...[
            const SizedBox(width: 4),
            Icon(Icons.stars_rounded, size: 12, color: cs.onSurfaceVariant),
          ],
        ],
      ),
    );
  }

  Widget _buildMessageText(String text, Color color) {
    return Text(
      text,
      style: GoogleFonts.plusJakartaSans(
        fontSize: 15,
        height: 1.45,
        letterSpacing: 0.1,
        color: color,
      ),
    );
  }

  Widget _buildFooterInfo(ColorScheme cs, {required Color bodyTextColor}) {
    final muted = bodyTextColor.withValues(alpha: 0.45);
    final veryMuted = bodyTextColor.withValues(alpha: 0.35);
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.message.isEdited)
          Text(
            'ред. ',
            style: TextStyle(fontSize: 10, color: veryMuted),
          ),
        Text(
          _formatTime(widget.message.dateTime),
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w600,
            color: muted,
          ),
        ),
        if (widget.isMine && (widget.message.isPro || ProGate.isPro)) ...[
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            decoration: BoxDecoration(
              color: cs.onPrimary.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              'PRO',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 8,
                fontWeight: FontWeight.w800,
                color: cs.onPrimary,
                height: 1,
              ),
            ),
          ),
        ],
        if (widget.isMine) ...[
          const SizedBox(width: 4),
          Icon(
            widget.isPending ? Icons.access_time_rounded : Icons.done_all_rounded,
            size: 12,
            color: widget.isPending ? veryMuted : cs.onPrimary,
          ),
        ],
      ],
    );
  }

  void _showFullScreenImage(String url) {
    final resolved = ApiConfig.resolveAbsoluteUrl(url);
    Navigator.of(context).push(
      PageRouteBuilder(
        opaque: false,
        pageBuilder: (ctx, _, _) => ChatImageGallery(
          imageUrl: resolved,
          heroTag: _imageHeroTag,
        ),
        transitionsBuilder: (ctx, anim, _, child) {
          return FadeTransition(opacity: anim, child: child);
        },
      ),
    );
  }

  void _showContextMenu(BuildContext context) {
    HapticFeedback.mediumImpact();
    NeptunShellModal.showDialog(
      context: context,
      barrierColor: Theme.of(context).colorScheme.scrim.withValues(alpha: 0.58),
      builder: (ctx) => ChatContextMenuOverlay(
        message: widget.message,
        isMine: widget.isMine,
        isModerator: widget.isModerator,
        myDeviceId: widget.myDeviceId,
        myNickname: widget.myNickname,
        onReact: (emoji) { Navigator.pop(ctx); widget.onReact(emoji); },
        onReply: () { Navigator.pop(ctx); widget.onReply(); },
        onCopy: () { Navigator.pop(ctx); widget.onCopy(); },
        onDelete: () { Navigator.pop(ctx); widget.onDelete(); },
        onBan: () { Navigator.pop(ctx); widget.onBan?.call(); },
        onReport: () { Navigator.pop(ctx); widget.onReport?.call(); },
        onBlock: () { Navigator.pop(ctx); widget.onBlock?.call(); },
        onEdit: () { Navigator.pop(ctx); widget.onEdit?.call(); },
        onDeleteAll: () { Navigator.pop(ctx); widget.onDeleteAll?.call(); },
      ),
    );
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }

  static Color _colorForNick(String nick) {
    const colors = [
      Color(0xFF334155),
      Color(0xFF475569),
      Color(0xFF0E7490),
      Color(0xFF0369A1),
      Color(0xFF4F46E5),
      Color(0xFF6D28D9),
      Color(0xFF0D9488),
      Color(0xFF1D4ED8),
    ];
    int hash = 0;
    for (var i = 0; i < nick.length; i++) {
      hash = nick.codeUnitAt(i) + ((hash << 5) - hash);
    }
    return colors[hash.abs() % colors.length];
  }
}
