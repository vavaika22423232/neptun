import 'package:flutter/material.dart';

/// Wraps a message item with slide-up + fade-in animation on first appearance.
class ChatAnimatedMessageItem extends StatefulWidget {
  final Widget child;
  final String messageId;
  final bool animate;

  const ChatAnimatedMessageItem({
    super.key,
    required this.child,
    required this.messageId,
    this.animate = true,
  });

  @override
  State<ChatAnimatedMessageItem> createState() =>
      _ChatAnimatedMessageItemState();
}

class _ChatAnimatedMessageItemState extends State<ChatAnimatedMessageItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fade;
  late Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 250),
      vsync: this,
    );
    _fade = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
    _slide = Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
    if (widget.animate) {
      _controller.forward();
    } else {
      _controller.value = 1.0;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fade,
      child: SlideTransition(position: _slide, child: widget.child),
    );
  }
}
