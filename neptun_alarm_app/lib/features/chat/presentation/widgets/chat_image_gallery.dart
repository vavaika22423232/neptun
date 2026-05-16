import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher_string.dart';

/// Full-screen image viewer. [imageUrl] must already be absolute (use [ApiConfig.resolveAbsoluteUrl]).
/// [heroTag] must match the bubble [Hero] tag (unique per message, not per URL — avoids duplicate-hero crashes).
class ChatImageGallery extends StatefulWidget {
  final String imageUrl;
  final String heroTag;

  const ChatImageGallery({
    super.key,
    required this.imageUrl,
    required this.heroTag,
  });

  @override
  State<ChatImageGallery> createState() => _ChatImageGalleryState();
}

class _ChatImageGalleryState extends State<ChatImageGallery> {
  double _dragOffset = 0;
  bool _isDragging = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final bgAlpha = (1 - (_dragOffset.abs() / 400)).clamp(0.0, 1.0);
    return Scaffold(
      backgroundColor: cs.scrim.withValues(alpha: 0.94 * bgAlpha),
      body: Stack(
        fit: StackFit.expand,
        children: [
          Positioned.fill(
            child: GestureDetector(
              onVerticalDragUpdate: (details) {
                final d = details.primaryDelta;
                if (d == null) return;
                setState(() {
                  _dragOffset += d;
                  _isDragging = true;
                });
              },
              onVerticalDragEnd: (details) {
                if (_dragOffset.abs() > 150) {
                  Navigator.pop(context);
                } else {
                  setState(() {
                    _dragOffset = 0;
                    _isDragging = false;
                  });
                }
              },
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final w = constraints.maxWidth;
                  final h = constraints.maxHeight;
                  final dpr = MediaQuery.devicePixelRatioOf(context);
                  final memW = (w * dpr).round().clamp(64, 2048);
                  final memH = (h * dpr).round().clamp(64, 2048);
                  return Center(
                    child: AnimatedContainer(
                      duration: _isDragging
                          ? Duration.zero
                          : const Duration(milliseconds: 300),
                      curve: Curves.easeOutCubic,
                      transform: Matrix4.translationValues(0, _dragOffset, 0),
                      width: w,
                      height: h,
                      child: InteractiveViewer(
                        minScale: 0.5,
                        maxScale: 4.0,
                        boundaryMargin: const EdgeInsets.all(80),
                        child: Hero(
                          tag: widget.heroTag,
                          child: CachedNetworkImage(
                            imageUrl: widget.imageUrl,
                            width: w,
                            height: h,
                            fit: BoxFit.contain,
                            memCacheWidth: memW,
                            memCacheHeight: memH,
                            placeholder: (context, url) => Center(
                              child: CircularProgressIndicator(
                                color: cs.onInverseSurface.withValues(alpha: 0.7),
                              ),
                            ),
                            errorWidget: (context, url, error) => Center(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.broken_image_outlined,
                                      color: cs.error,
                                      size: 52,
                                    ),
                                    const SizedBox(height: 12),
                                    Text(
                                      'Не вдалося завантажити зображення',
                                      textAlign: TextAlign.center,
                                      style: GoogleFonts.plusJakartaSans(
                                        color: cs.onSurface,
                                        fontSize: 15,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          _buildAppBar(),
          _buildBottomActions(),
          _buildDismissHint(),
        ],
      ),
    );
  }

  Widget _buildDismissHint() {
    final cs = Theme.of(context).colorScheme;
    // Над FAB справа та safe area
    final bottomPad = MediaQuery.viewPaddingOf(context).bottom + 88;
    return Positioned(
      left: 24,
      right: 88,
      bottom: bottomPad,
      child: IgnorePointer(
        child: AnimatedOpacity(
          opacity: (1 - (_dragOffset.abs() / 120).clamp(0.0, 1.0)) * 0.85,
          duration: const Duration(milliseconds: 200),
          child: Text(
            'Потягніть вниз, щоб закрити',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: cs.onSurface.withValues(alpha: 0.55),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    final cs = Theme.of(context).colorScheme;
    final topInset = MediaQuery.viewPaddingOf(context).top + 8;
    return Positioned(
      top: topInset,
      left: 20,
      right: 20,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton.filledTonal(
            style: IconButton.styleFrom(
              backgroundColor: cs.inverseSurface.withValues(alpha: 0.55),
              foregroundColor: cs.onInverseSurface,
            ),
            tooltip: 'Закрити',
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.close_rounded, size: 28),
          ),
          IconButton.filledTonal(
            style: IconButton.styleFrom(
              backgroundColor: cs.inverseSurface.withValues(alpha: 0.55),
              foregroundColor: cs.onInverseSurface,
            ),
            tooltip: 'Поділитися',
            onPressed: () => Share.share(widget.imageUrl),
            icon: const Icon(Icons.share_rounded, size: 24),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomActions() {
    final cs = Theme.of(context).colorScheme;
    final bottomInset = MediaQuery.viewPaddingOf(context).bottom + 16;
    return Positioned(
      bottom: bottomInset,
      right: 20,
      child: Column(
        children: [
          FloatingActionButton.small(
            heroTag: 'chat_gallery_dl_${widget.heroTag.hashCode}',
            backgroundColor: cs.inverseSurface.withValues(alpha: 0.72),
            foregroundColor: cs.onInverseSurface,
            elevation: 0,
            tooltip: 'Відкрити в браузері',
            onPressed: () => launchUrlString(widget.imageUrl),
            child: const Icon(Icons.open_in_browser_rounded),
          ),
        ],
      ),
    );
  }
}
