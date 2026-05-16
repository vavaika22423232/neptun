import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/di/service_locator.dart';
import '../services/chat_service.dart' show ChatService, BanEntry;

/// Адмін панель чату: блокування, розблокування, список заблокованих.
class ChatAdminPage extends StatefulWidget {
  const ChatAdminPage({super.key});

  @override
  State<ChatAdminPage> createState() => _ChatAdminPageState();
}

class _ChatAdminPageState extends State<ChatAdminPage> {
  final _chat = sl<ChatService>();
  final _banController = TextEditingController();
  final _searchController = TextEditingController();
  List<BanEntry> _blockedList = [];
  bool _loadingBlocked = false;
  bool _banning = false;
  String? _banError;
  Timer? _searchDebounce;

  Future<void> _loadBlocked() async {
    setState(() => _loadingBlocked = true);
    final list = await _chat.getBanListDetails(
      query: _searchController.text.trim(),
    );
    if (mounted) {
      setState(() {
        _blockedList = list;
        _loadingBlocked = false;
      });
    }
  }

  Future<void> _unblock(BanEntry ban) async {
    final ok = await _chat.unbanEntry(ban);
    if (mounted) {
      if (ok) {
        setState(() {
          _blockedList.removeWhere((b) => b.stableKey == ban.stableKey);
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Розблоковано: ${_banTitle(ban)}')),
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
    _searchDebounce?.cancel();
    _banController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _scheduleSearch() {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 300), _loadBlocked);
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Заблоковано: $nick')));
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
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
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
                      hintStyle: GoogleFonts.inter(
                        color: cs.onSurfaceVariant,
                        fontSize: 14,
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 12,
                      ),
                    ),
                    style: GoogleFonts.inter(color: cs.onSurface, fontSize: 14),
                    onSubmitted: (_) => _banByNickname(),
                  ),
                  if (_banError != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        _banError!,
                        style: GoogleFonts.inter(fontSize: 12, color: cs.error),
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
                    label: Text(_banning ? 'Блокування…' : 'Заблокувати'),
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
                      _searchController.text.trim().isEmpty
                          ? 'Список заблокованих (${_blockedList.length})'
                          : 'Знайдено (${_blockedList.length})',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: cs.onSurface,
                      ),
                    ),
                    IconButton(
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
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Пошук: нік, device ID, причина',
                      prefixIcon: const Icon(Icons.search_rounded, size: 20),
                      suffixIcon: _searchController.text.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.close_rounded, size: 18),
                              onPressed: () {
                                _searchController.clear();
                                _loadBlocked();
                              },
                            ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                    ),
                    style: GoogleFonts.inter(color: cs.onSurface, fontSize: 14),
                    onChanged: (_) {
                      setState(() {});
                      _scheduleSearch();
                    },
                    onSubmitted: (_) => _loadBlocked(),
                  ),
                ),
                if (_blockedList.isEmpty && !_loadingBlocked)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 24),
                    child: Text(
                      'Немає заблокованих',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  )
                else
                  ..._blockedList.map(
                    (ban) => Dismissible(
                      key: ValueKey(ban.stableKey),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 16),
                        color: cs.tertiary.withValues(alpha: 0.2),
                        child: Text(
                          'Розблокувати',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: cs.tertiary,
                          ),
                        ),
                      ),
                      onDismissed: (_) => _unblock(ban),
                      child: ListTile(
                        leading: Icon(
                          Icons.block_rounded,
                          color: cs.error.withValues(alpha: 0.8),
                          size: 22,
                        ),
                        title: Text(
                          _banTitle(ban),
                          style: GoogleFonts.inter(
                            fontSize: 15,
                            color: cs.onSurface,
                          ),
                        ),
                        subtitle: () {
                          final parts = <String>[
                            if (ban.deviceId.isNotEmpty)
                              'ID ${_shortId(ban.deviceId)}',
                            if ((ban.hardwareId ?? '').isNotEmpty)
                              'HW ${_shortId(ban.hardwareId!)}',
                            if (ban.reason.isNotEmpty) ban.reason,
                            if (ban.bannedAt != null) _formatDate(ban.bannedAt),
                          ];
                          if (parts.isEmpty) return null;
                          return Text(
                            parts.join(' · '),
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: cs.onSurfaceVariant,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          );
                        }(),
                        trailing: TextButton(
                          onPressed: () => _confirmUnblock(ban),
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

  String _banTitle(BanEntry ban) {
    final nick = ban.nickname.trim();
    if (nick.isNotEmpty) return nick;
    if (ban.deviceId.isNotEmpty) return _shortId(ban.deviceId);
    return ban.hardwareId != null ? _shortId(ban.hardwareId!) : 'Без імені';
  }

  String _shortId(String id) {
    if (id.length <= 10) return id;
    return '${id.substring(0, 6)}…${id.substring(id.length - 4)}';
  }

  void _confirmUnblock(BanEntry ban) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Розблокувати'),
        content: Text('Розблокувати користувача ${_banTitle(ban)}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _unblock(ban);
            },
            child: const Text('Розблокувати'),
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
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: cs.onSurfaceVariant,
              letterSpacing: 0.5,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: cs.outline.withValues(alpha: 0.2),
              width: 0.5,
            ),
          ),
          child: child,
        ),
      ],
    );
  }
}
