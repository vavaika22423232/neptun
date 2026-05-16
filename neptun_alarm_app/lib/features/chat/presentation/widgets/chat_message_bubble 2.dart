import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../config/api_config.dart';
import '../../../../models/chat_message.dart';
import 'chat_context_menu.dart';

/// Message bubble with swipe-to-reply, reactions, voice playback.
/// [isFirstInGroup] — show avatar and nickname (for others)
/// [isLastInGroup] — rounded corner with "tail" at bottom
class ChatMessageBubble extends StatefulWidget {
  final ChatMessage message;
  final bool isMine;
  final bool isFirstInGroup;
  final bool isLastInGroup;
  final String myDeviceId;
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

class _ChatMessageBubbleState extends State<ChatMessageBubble> {
  double _dragOffset = 0;
  bool _hasTriggered = false;
  static const _swipeThreshold = 60.0;
  static const _maxDrag = 80.0;

  void _onHorizontalDragUpdate(DragUpdateDetails details) {
    final delta = details.primaryDelta ?? 0;
    setState(() {
      if (widget.isMine) {
        _dragOffset = (_dragOffset + delta).clamp(-_maxDrag, 0.0);
      } else {
        _dragOffset = (_dragOffset + delta).clamp(0.0, _maxDrag);
      }
    });
    if (!_hasTriggered && _dragOffset.abs() >= _swipeThreshold) {
      _hasTriggered = true;
      HapticFeedback.lightImpact();
    }
  }

  void _onHorizontalDragEnd(DragEndDetails details) {
    if (_dragOffset.abs() >= _swipeThreshold) {
      widget.onReply();
    }
    setState(() {
      _dragOffset = 0;
      _hasTriggered = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final replyIconOpacity = (_dragOffset.abs() / _swipeThreshold).clamp(
      0.0,
      1.0,
    );
    return GestureDetector(
      onDoubleTap: () => widget.onReact('👍'),
      onLongPress: () => _showContextMenu(context),
      onHorizontalDragUpdate: _onHorizontalDragUpdate,
      onHorizontalDragEnd: _onHorizontalDragEnd,
      child: Stack(
        alignment: widget.isMine ? Alignment.centerRight : Alignment.centerLeft,
        children: [
          if (_dragOffset.abs() > 0)
            Positioned(
              left: widget.isMine ? null : 8,
              right: widget.isMine ? 8 : null,
              child: Opacity(
                opacity: replyIconOpacity,
                child: Transform.scale(
                  scale: 0.6 + 0.4 * replyIconOpacity,
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: cs.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Icon(
                      Icons.reply_rounded,
                      size: 20,
                      color: cs.primary,
                    ),
                  ),
                ),
              ),
            ),
          AnimatedContainer(
            duration: _dragOffset == 0
                ? const Duration(milliseconds: 280)
                : Duration.zero,
            curve: Curves.easeOutCubic,
            transform: Matrix4.translationValues(_dragOffset, 0, 0),
            child: Padding(
              padding: EdgeInsets.only(
                left: widget.isMine ? 48 : 0,
                right: widget.isMine ? 0 : 48,
                bottom: 4,
              ),
              child: Row(
                mainAxisAlignment: widget.isMine
                    ? MainAxisAlignment.end
                    : MainAxisAlignment.start,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (!widget.isMine) ...[
                    if (widget.isFirstInGroup) _avatar(),
                    if (widget.isFirstInGroup) const SizedBox(width: 6),
                    if (!widget.isFirstInGroup) const SizedBox(width: 38),
                  ],
                  Flexible(child: _bubble(context)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _avatar() {
    final color = _colorForNick(widget.message.userId);
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [color, color.withValues(alpha: 0.7)],
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.3),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        widget.message.avatarInitials,
        style: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w700,
          color: Colors.white,
        ),
      ),
    );
  }

  Widget _bubble(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Telegram-style: own messages — accent, others — elevated so visible on dark bg
    // Dark theme: true black (#000) background — need clearly visible bubble (#4A4A50)
    final myBgColor = isDark
        ? cs.primary.withValues(alpha: 0.25)
        : const Color(0xFFB3D4FC);
    final othersColor = isDark
        ? const Color(0xFF1A2332) // Dark blue, visible on black
        : const Color(0xFFD4E4FC);
    final myBorderColor = isDark
        ? cs.primary.withValues(alpha: 0.3)
        : const Color(0xFF8BB8F0);
    final othersBorderColor = isDark
        ? const Color(0xFF2A3544) // Visible border for dark bubbles
        : const Color(0xFFA8C8F0);
    final borderWidth = isDark ? 0.5 : 1.0;

    // Grouping: tail at bottom corner (right for mine, left for others)
    const r = 18.0;
    const small = 4.0;
    final topL = widget.isFirstInGroup ? r : small;
    final topR = widget.isFirstInGroup ? r : small;
    // Mine: tail at bottom-right when last. Others: tail at bottom-left when last.
    // Middle messages: both bottom corners small to connect.
    final bottomL = widget.isMine
        ? (widget.isLastInGroup ? r : small)
        : (widget.isLastInGroup ? small : small);
    final bottomR = widget.isMine
        ? (widget.isLastInGroup ? small : small)
        : (widget.isLastInGroup ? r : small);

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
      decoration: BoxDecoration(
        color: widget.isMine ? myBgColor : othersColor,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(topL),
          topRight: Radius.circular(topR),
          bottomLeft: Radius.circular(bottomL),
          bottomRight: Radius.circular(bottomR),
        ),
        border: Border.all(
          color: widget.isMine ? myBorderColor : othersBorderColor,
          width: borderWidth,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.06),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!widget.isMine && widget.isFirstInGroup)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Flexible(
                    child: Text(
                      widget.message.userId,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _colorForNick(widget.message.userId),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (widget.message.isModerator) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.bolt_rounded, size: 12, color: cs.tertiary),
                  ],
                  if (widget.message.isPro) ...[
                    const SizedBox(width: 4),
                    Icon(
                      Icons.star_rounded,
                      size: 12,
                      color: const Color(0xFFFFB800),
                    ),
                  ],
                ],
              ),
            ),
          if (widget.message.replyTo != null) _replyPreview(),
          if (widget.message.isVoice && widget.message.audioUrl != null)
            _buildVoiceContent()
          else if (widget.message.isImage && widget.message.imageUrl != null)
            _buildImageContent()
          else
            _buildMessageText(widget.message.message),
          const SizedBox(height: 3),
          Align(
            alignment: Alignment.bottomRight,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (widget.message.isEdited)
                  Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Text(
                      'Відредаговано',
                      style: GoogleFonts.inter(
                        fontSize: 9,
                        fontStyle: FontStyle.italic,
                        color: cs.onSurface.withValues(
                          alpha: isDark ? 0.3 : 0.45,
                        ),
                      ),
                    ),
                  ),
                if (widget.isMine) ...[
                  if (widget.isPending)
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: Icon(
                        Icons.schedule_rounded,
                        size: 12,
                        color: cs.onSurface.withValues(
                          alpha: isDark ? 0.35 : 0.5,
                        ),
                      ),
                    )
                  else
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: Icon(
                        Icons.done_rounded,
                        size: 12,
                        color: cs.onSurface.withValues(
                          alpha: isDark ? 0.35 : 0.5,
                        ),
                      ),
                    ),
                ],
                Text(
                  _formatTime(widget.message.dateTime),
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    color: cs.onSurface.withValues(alpha: isDark ? 0.35 : 0.5),
                  ),
                ),
              ],
            ),
          ),
          if (widget.message.reactions.isNotEmpty) _reactionsRow(),
        ],
      ),
    );
  }

  Widget _buildVoiceContent() {
    final cs = Theme.of(context).colorScheme;
    final duration = widget.message.audioDuration ?? 0;
    final m = duration ~/ 60;
    final s = duration % 60;
    final durationText = '$m:${s.toString().padLeft(2, '0')}';

    return GestureDetector(
      onTap: () {
        final url = widget.message.audioUrl;
        if (url != null) widget.onPlayVoice?.call(widget.message.id, url);
      },
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: cs.primary.withValues(alpha: widget.isMine ? 0.2 : 0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(
              widget.isPlayingVoice
                  ? Icons.pause_rounded
                  : Icons.play_arrow_rounded,
              color: cs.primary,
              size: 22,
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Голосове повідомлення',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: cs.onSurface.withValues(alpha: 0.7),
                ),
              ),
              Text(
                durationText,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: cs.onSurface.withValues(alpha: 0.5),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildImageContent() {
    final url = widget.message.imageUrl;
    if (url == null) return const SizedBox.shrink();
    final fullUrl = url.startsWith('http') ? url : '${ApiConfig.baseUrl}$url';
    return GestureDetector(
      onTap: () => _showFullScreenImage(fullUrl),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: CachedNetworkImage(
          imageUrl: fullUrl,
          fit: BoxFit.cover,
          maxWidthDiskCache: 400,
          maxHeightDiskCache: 400,
          placeholder: (_, _) => Container(
            width: 200,
            height: 150,
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: const Center(
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
          errorWidget: (_, _, _) => Container(
            width: 200,
            height: 150,
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: Icon(
              Icons.broken_image_rounded,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }

  void _showFullScreenImage(String url) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            iconTheme: const IconThemeData(color: Colors.white),
          ),
          body: Center(
            child: InteractiveViewer(
              minScale: 0.5,
              maxScale: 4,
              child: CachedNetworkImage(imageUrl: url, fit: BoxFit.contain),
            ),
          ),
        ),
      ),
    );
  }

  static final _urlRegex = RegExp(
    r'(https?://[^\s\)\]\},;!?]+)',
    caseSensitive: false,
  );

  Widget _buildMessageText(String text) {
    final cs = Theme.of(context).colorScheme;
    final baseStyle = GoogleFonts.inter(
      fontSize: 14.5,
      color: cs.onSurface,
      height: 1.35,
    );
    final highlight = widget.searchHighlight;
    final hasHighlight = highlight != null && highlight.isNotEmpty;

    // Search highlight matches (case insensitive)
    List<RegExpMatch>? highlightMatches;
    if (hasHighlight) {
      try {
        highlightMatches = RegExp(
          RegExp.escape(highlight),
          caseSensitive: false,
        ).allMatches(text).toList();
      } catch (_) {
        highlightMatches = [];
      }
    }

    final urlMatches = _urlRegex.allMatches(text).toList();
    if (urlMatches.isEmpty &&
        (highlightMatches == null || highlightMatches.isEmpty)) {
      return Text(text, style: baseStyle);
    }

    // Build spans: merge URL and highlight ranges
    final spans = <TextSpan>[];
    int lastEnd = 0;
    final allRanges = <({int start, int end, bool isUrl})>[];
    for (final m in urlMatches) {
      allRanges.add((start: m.start, end: m.end, isUrl: true));
    }
    if (highlightMatches != null) {
      for (final m in highlightMatches) {
        allRanges.add((start: m.start, end: m.end, isUrl: false));
      }
    }
    allRanges.sort((a, b) => a.start.compareTo(b.start));

    for (final r in allRanges) {
      if (r.start > lastEnd) {
        spans.add(
          TextSpan(text: text.substring(lastEnd, r.start), style: baseStyle),
        );
      }
      final segment = text.substring(r.start, r.end);
      if (r.isUrl) {
        spans.add(
          TextSpan(
            text: segment,
            style: TextStyle(
              color: cs.primary,
              decoration: TextDecoration.underline,
              decorationColor: cs.primary,
            ),
            recognizer: TapGestureRecognizer()
              ..onTap = () => _launchUrl(segment),
          ),
        );
      } else {
        spans.add(
          TextSpan(
            text: segment,
            style: baseStyle.copyWith(
              backgroundColor: cs.primary.withValues(alpha: 0.3),
            ),
          ),
        );
      }
      lastEnd = r.end;
    }
    if (lastEnd < text.length) {
      spans.add(TextSpan(text: text.substring(lastEnd)));
    }

    return Text.rich(
      TextSpan(
        style: GoogleFonts.inter(
          fontSize: 14.5,
          color: cs.onSurface,
          height: 1.35,
        ),
        children: spans,
      ),
    );
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Widget _replyPreview() {
    final cs = Theme.of(context).colorScheme;
    final reply = widget.message.replyTo!;
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
      decoration: BoxDecoration(
        color: cs.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: cs.primary, width: 2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (reply.nickname != null)
            Text(
              reply.nickname!,
              style: GoogleFonts.inter(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: cs.primary,
              ),
            ),
          if (reply.text != null)
            Text(
              reply.text!,
              style: GoogleFonts.inter(
                fontSize: 11,
                color: cs.onSurfaceVariant,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
        ],
      ),
    );
  }

  Widget _reactionsRow() {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Wrap(
        spacing: 4,
        runSpacing: 2,
        children: widget.message.reactions.entries.map((e) {
          final hasReacted = widget.message.hasReacted(
            e.key,
            widget.myDeviceId,
          );
          return TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(milliseconds: 280),
            curve: Curves.elasticOut,
            builder: (context, value, child) =>
                Transform.scale(scale: value, child: child),
            child: GestureDetector(
              onTap: () => widget.onReact(e.key),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: hasReacted
                      ? cs.primary.withValues(alpha: 0.18)
                      : cs.surfaceContainer,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: hasReacted
                        ? cs.primary.withValues(alpha: 0.35)
                        : cs.outline.withValues(alpha: 0.5),
                    width: 0.5,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(e.key, style: const TextStyle(fontSize: 14)),
                    if (e.value.length > 1) ...[
                      const SizedBox(width: 4),
                      Text(
                        '${e.value.length}',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: hasReacted ? cs.primary : cs.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  void _showContextMenu(BuildContext context) {
    HapticFeedback.mediumImpact();
    showDialog(
      context: context,
      barrierColor: Colors.transparent,
      builder: (ctx) => ChatContextMenuOverlay(
        message: widget.message,
        isMine: widget.isMine,
        isModerator: widget.isModerator,
        myDeviceId: widget.myDeviceId,
        onReact: (emoji) {
          Navigator.pop(ctx);
          widget.onReact(emoji);
        },
        onReply: () {
          Navigator.pop(ctx);
          widget.onReply();
        },
        onCopy: () {
          Navigator.pop(ctx);
          widget.onCopy();
        },
        onDelete: () {
          Navigator.pop(ctx);
          widget.onDelete();
        },
        onBan: widget.onBan != null
            ? () {
                Navigator.pop(ctx);
                widget.onBan!();
              }
            : null,
        onReport: widget.onReport != null
            ? () {
                Navigator.pop(ctx);
                widget.onReport!();
              }
            : null,
        onBlock: widget.onBlock != null
            ? () {
                Navigator.pop(ctx);
                widget.onBlock!();
              }
            : null,
        onEdit: widget.onEdit != null
            ? () {
                Navigator.pop(ctx);
                widget.onEdit!();
              }
            : null,
        onDeleteAll: widget.onDeleteAll != null
            ? () {
                Navigator.pop(ctx);
                widget.onDeleteAll!();
              }
            : null,
      ),
    );
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }

  static Color _colorForNick(String nick) {
    const colors = [
      Color(0xFF4A9EFF),
      Color(0xFF32D74B),
      Color(0xFFFF375F),
      Color(0xFFBF5AF2),
      Color(0xFFFF9F0A),
      Color(0xFF64D2FF),
      Color(0xFFFFD60A),
      Color(0xFFAC8E68),
    ];
    int hash = 0;
    for (int i = 0; i < nick.length; i++) {
      hash = nick.codeUnitAt(i) + ((hash << 5) - hash);
    }
    return colors[hash.abs() % colors.length];
  }
}
