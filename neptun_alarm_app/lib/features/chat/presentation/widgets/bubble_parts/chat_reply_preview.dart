import 'package:flutter/material.dart';
import '../../../../../models/chat_message.dart';
import 'package:google_fonts/google_fonts.dart';

class ChatReplyPreview extends StatelessWidget {
  final ReplyInfo reply;
  final ColorScheme colorScheme;

  const ChatReplyPreview({
    super.key,
    required this.reply,
    required this.colorScheme,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(8, 8, 8, 0),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(10),
        border: Border(
          left: BorderSide(color: colorScheme.primary, width: 3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            reply.nickname ?? 'Користувач',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: colorScheme.primary,
            ),
          ),
          Text(
            reply.text ?? '',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}
