import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/di/service_locator.dart';
import '../services/chat_service.dart' show ChatService, BanEntry;
import '../core/widgets/neptun_shell_modal.dart';

/// Адмін панель чату: блокування, розблокування, список заблокованих.
class ChatAdminPage extends StatefulWidget {
  const ChatAdminPage({super.key});

  @override
  State<ChatAdminPage> createState() => _ChatAdminPageState();
}

class _ChatAdminPageState extends State<ChatAdminPage> {
  final _chat = sl<ChatService>();
  final _banController = TextEditingController();
  List<BanEntry> _blockedList = [];
  bool _loadingBlocked = false;
  bool _banning = false;
  String? _banError;

  Future<void> _loadBlocked() async {
    setState(() => _loadingBlocked = true);
    final list = await _chat.getBanListDetails();
    if (mounted) {
      setState(() {
        _blockedList = list;
        _loadingBlocked = false;
      });
    }
  }

  Future<void> _unblock(String nickname) async {
    final ok = await _chat.unbanUser(nickname);
    if (mounted) {
      if (ok) {
        setState(() => _blockedList.removeWhere((b) => b.nickname == nickname));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Розблоковано: $nickname')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Помилка розблокування'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  void initState() {
    super.initState();
    _loadBlocked();
  }

  @override
  void dispose() {
    _banController.dispose();
    super.dispose();
  }

  Future<void> _banByNickname() async {
    final nick = _banController.text.trim();
    if (nick.isEmpty) return;
    setState(() {
      _banning = true;
      _banError = null;
    });
    final ok = await _chat.banUserByNickname(nick);
    if (mounted) {
      setState(() => _banning = false);
      if (ok) {
        _banController.clear();
        _loadBlocked();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Заблоковано: $nick')),
        );
      } else {
        setState(() => _banError = 'Не вдалося заблокувати');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Адмін панель чату',
          style: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
        centerTitle: false,
        leading: IconButton(
          tooltip: 'Назад',
          icon: const Icon(Icons.arrow_back_ios_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
        physics: const BouncingScrollPhysics(
          parent: AlwaysScrollableScrollPhysics(),
        ),
        padding: const EdgeInsets.all(16),
        children: [
          _buildSection(
            cs,
            title: 'Швидке блокування',
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _banController,
                    decoration: InputDecoration(
                      hintText: 'Нікнейм для блокування',
                      hintStyle: GoogleFonts.plusJakartaSans(
                        color: cs.onSurfaceVariant,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                      filled: true,
                      fillColor: cs.surfaceContainerLow,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(color: cs.outlineVariant),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(color: cs.outlineVariant),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide(color: cs.primary, width: 2),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                    ),
                    style: GoogleFonts.plusJakartaSans(
                      color: cs.onSurface,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                    onSubmitted: (_) => _banByNickname(),
                  ),
                  if (_banError != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        _banError!,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          color: cs.error,
                        ),
                      ),
                    ),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: _banning ? null : _banByNickname,
                    icon: _banning
                        ? SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: cs.onPrimary,
                            ),
                          )
                        : const Icon(Icons.block_rounded, size: 18),
                    label: Text(
                      _banning ? 'Блокування…' : 'Заблокувати',
                      style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700),
                    ),
                    style: FilledButton.styleFrom(
                      backgroundColor: cs.error,
                      foregroundColor: cs.onError,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          _buildSection(
            cs,
            title: 'Заблоковані користувачі',
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Список заблокованих (${_blockedList.length})',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        color: cs.onSurface,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Оновити список',
                      icon: _loadingBlocked
                          ? SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: cs.primary,
                              ),
                            )
                          : const Icon(Icons.refresh_rounded),
                      onPressed: _loadingBlocked ? null : _loadBlocked,
                    ),
                  ],
                ),
                if (_blockedList.isEmpty && !_loadingBlocked)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 24),
                    child: Text(
                      'Немає заблокованих',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  )
                else
                  ..._blockedList.map(
                    (ban) => Dismissible(
                      key: ValueKey(ban.nickname),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 16),
                        color: cs.tertiary.withValues(alpha: 0.2),
                        child: Text(
                          'Розблокувати',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: cs.tertiary,
                          ),
                        ),
                      ),
                      onDismissed: (_) => _unblock(ban.nickname),
                      child: ListTile(
                        leading: Icon(
                          Icons.block_rounded,
                          color: cs.error.withValues(alpha: 0.8),
                          size: 22,
                        ),
                        title: Text(
                          ban.nickname,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 15,
                            color: cs.onSurface,
                          ),
                        ),
                        subtitle: () {
                          final parts = <String>[
                            if (ban.reason.isNotEmpty) ban.reason,
                            if (ban.bannedAt != null) _formatDate(ban.bannedAt),
                          ];
                          if (parts.isEmpty) return null;
                          return Text(
                            parts.join(' · '),
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              color: cs.onSurfaceVariant,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          );
                        }(),
                        trailing: TextButton(
                          onPressed: () => _confirmUnblock(ban.nickname),
                          child: const Text('Розблокувати'),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final d = DateTime.parse(iso);
      return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
    } catch (_) {
      return iso;
    }
  }

  void _confirmUnblock(String nickname) {
    NeptunShellModal.showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Розблокувати',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700),
        ),
        content: Text(
          'Розблокувати користувача $nickname?',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 15,
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'Скасувати',
              style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
            ),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _unblock(nickname);
            },
            child: Text(
              'Розблокувати',
              style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSection(
    ColorScheme cs, {
    required String title,
    required Widget child,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            title,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: cs.onSurfaceVariant,
              letterSpacing: 0.5,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: cs.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: cs.outlineVariant.withValues(alpha: 0.45),
            ),
          ),
          child: child,
        ),
      ],
    );
  }
}
