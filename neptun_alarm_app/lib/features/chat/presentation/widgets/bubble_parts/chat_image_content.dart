import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import '../../../../../config/api_config.dart';

class ChatImageContent extends StatelessWidget {
  final String imageUrl;

  /// Must match [ChatImageGallery.heroTag] for this message (never use raw URL — duplicate URLs → duplicate heroes).
  final String heroTag;
  final ColorScheme colorScheme;
  final VoidCallback onTap;

  const ChatImageContent({
    super.key,
    required this.imageUrl,
    required this.heroTag,
    required this.colorScheme,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final resolved = ApiConfig.resolveAbsoluteUrl(imageUrl);

    return Semantics(
      label: 'Зображення в чаті',
      child: GestureDetector(
        onTap: onTap,
        child: Hero(
          tag: heroTag,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: CachedNetworkImage(
              imageUrl: resolved,
              fit: BoxFit.cover,
              placeholder: (context, url) => Container(
                height: 200,
                width: 200,
                color: colorScheme.surfaceContainerHighest,
                child: Center(
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: colorScheme.primary,
                  ),
                ),
              ),
              errorWidget: (context, url, error) => Container(
                height: 200,
                width: 200,
                color: colorScheme.error.withValues(alpha: 0.1),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.broken_image_rounded, color: colorScheme.error),
                    const SizedBox(height: 8),
                    Text(
                      'Помилка завантаження',
                      style: TextStyle(fontSize: 10, color: colorScheme.error),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
