import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../services/chat_service.dart';
import '../../../../services/moderator_service.dart';

/// Bottom sheet for chat settings: nickname, moderator, ban list.
class ChatSettingsSheet extends StatefulWidget {
  final ChatService chat;
  final VoidCallback onNicknameChanged;

  const ChatSettingsSheet({
    super.key,
    required this.chat,
    required this.onNicknameChanged,
  });

  @override
  State<ChatSettingsSheet> createState() => _ChatSettingsSheetState();
}

class _ChatSettingsSheetState extends State<ChatSettingsSheet> {
  final _secretController = TextEditingController();
  final _newNickController = TextEditingController();
  List<String>? _banList;
  bool _showModSection = false;
  bool _loadingBans = false;
  String? _modError;
  String? _modSuccess;
  String? _nickError;
  bool _nickChanging = false;

  @override
  void dispose() {
    _secretController.dispose();
    _newNickController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.75,
      ),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12),
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: cs.onSurface.withValues(alpha: 0.35),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Налаштування',
            style: GoogleFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: cs.onSurface,
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              children: [
                if (widget.chat.isModerator) ...[
                  _moderatorAdminTile(cs),
                  const SizedBox(height: 20),
                ],
                _sectionTitle('Ваш нікнейм'),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: _cardDecoration(),
                  child: Row(
                    children: [
                      Icon(Icons.person_rounded, color: cs.primary, size: 20),
                      const SizedBox(width: 10),
                      Text(
                        widget.chat.nickname ?? '—',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _sectionTitle('Змінити нікнейм'),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _newNickController,
                        maxLength: 20,
                        style: GoogleFonts.inter(
                          color: cs.onSurface,
                          fontSize: 14,
                        ),
                        decoration: InputDecoration(
                          hintText: 'Новий нікнейм',
                          hintStyle: GoogleFonts.inter(
                            color: cs.onSurface.withValues(alpha: 0.35),
                            fontSize: 14,
                          ),
                          errorText: _nickError,
                          counterText: '',
                          filled: true,
                          fillColor: cs.surfaceContainerHighest,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      height: 46,
                      child: ElevatedButton(
                        onPressed: _nickChanging ? null : _changeNickname,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: cs.primary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                        ),
                        child: _nickChanging
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Text('Зберегти'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                _sectionTitle('Модерація'),
                Container(
                  decoration: _cardDecoration(),
                  child: Column(
                    children: [
                      ListTile(
                        leading: Icon(
                          widget.chat.isModerator
                              ? Icons.shield_rounded
                              : Icons.shield_outlined,
                          color: widget.chat.isModerator
                              ? cs.tertiary
                              : cs.onSurface.withValues(alpha: 0.35),
                        ),
                        title: Text(
                          widget.chat.isModerator
                              ? 'Ви модератор'
                              : 'Стати модератором',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            color: cs.onSurface,
                          ),
                        ),
                        trailing: Icon(
                          _showModSection
                              ? Icons.expand_less
                              : Icons.expand_more,
                          color: cs.onSurface.withValues(alpha: 0.35),
                        ),
                        onTap: () =>
                            setState(() => _showModSection = !_showModSection),
                      ),
                      if (_showModSection) ...[
                        Divider(height: 0.5, color: cs.outline),
                        Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            children: [
                              TextField(
                                controller: _secretController,
                                obscureText: true,
                                style: GoogleFonts.inter(
                                  color: cs.onSurface,
                                  fontSize: 14,
                                ),
                                decoration: InputDecoration(
                                  hintText: 'Пароль модератора',
                                  hintStyle: GoogleFonts.inter(
                                    color: cs.onSurface.withValues(alpha: 0.35),
                                    fontSize: 14,
                                  ),
                                  filled: true,
                                  fillColor: cs.surface,
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: BorderSide.none,
                                  ),
                                  contentPadding: const EdgeInsets.symmetric(
                                    horizontal: 14,
                                    vertical: 12,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton(
                                  onPressed: _activateModerator,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: cs.tertiary.withValues(
                                      alpha: 0.15,
                                    ),
                                    foregroundColor: cs.tertiary,
                                    elevation: 0,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                  ),
                                  child: Text(
                                    widget.chat.isModerator
                                        ? 'Оновити'
                                        : 'Активувати',
                                  ),
                                ),
                              ),
                              if (_modError != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 6),
                                  child: Text(
                                    _modError!,
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: cs.error,
                                    ),
                                  ),
                                ),
                              if (_modSuccess != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 6),
                                  child: Text(
                                    _modSuccess!,
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: cs.secondary,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                if (widget.chat.isModerator) ...[
                  _sectionTitle('Заблоковані'),
                  Container(
                    decoration: _cardDecoration(),
                    child: Column(
                      children: [
                        ListTile(
                          leading: Icon(
                            Icons.block_rounded,
                            color: cs.error,
                            size: 20,
                          ),
                          title: Text(
                            'Список заблокованих',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              color: cs.onSurface,
                            ),
                          ),
                          trailing: _loadingBans
                              ? SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: cs.onSurface.withValues(alpha: 0.35),
                                  ),
                                )
                              : Icon(
                                  Icons.refresh_rounded,
                                  color: cs.onSurface.withValues(alpha: 0.35),
                                  size: 20,
                                ),
                          onTap: _loadBanList,
                        ),
                        if (_banList != null && _banList!.isNotEmpty) ...[
                          Divider(height: 0.5, color: cs.outline),
                          ..._banList!.map(
                            (nick) => Dismissible(
                              key: ValueKey(nick),
                              direction: DismissDirection.endToStart,
                              background: Container(
                                alignment: Alignment.centerRight,
                                padding: const EdgeInsets.only(right: 16),
                                color: cs.secondary.withValues(alpha: 0.15),
                                child: Text(
                                  'Розблокувати',
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    color: cs.secondary,
                                  ),
                                ),
                              ),
                              onDismissed: (_) async {
                                await widget.chat.unbanUser(nick);
                                setState(() => _banList?.remove(nick));
                              },
                              child: ListTile(
                                dense: true,
                                title: Text(
                                  nick,
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    color: cs.onSurfaceVariant,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                        if (_banList != null && _banList!.isEmpty)
                          Padding(
                            padding: const EdgeInsets.all(14),
                            child: Text(
                              'Список порожній',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: cs.onSurface.withValues(alpha: 0.35),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
                const SizedBox(height: 32),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _moderatorAdminTile(ColorScheme cs) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          Navigator.of(context).pop();
          context.push('/chat-admin');
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: _cardDecoration(),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: cs.tertiary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.admin_panel_settings_rounded,
                  color: cs.tertiary,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Адмін панель чату',
                      style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                    Text(
                      'Заблоковані, розблокування',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: cs.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String title) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 4),
      child: Text(
        title,
        style: GoogleFonts.inter(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: cs.onSurface.withValues(alpha: 0.35),
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration() {
    final cs = Theme.of(context).colorScheme;
    return BoxDecoration(
      color: cs.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: cs.outline, width: 0.5),
    );
  }

  Future<void> _changeNickname() async {
    final nick = _newNickController.text.trim();
    if (nick.length < 2 || nick.length > 20) {
      setState(() => _nickError = 'Від 2 до 20 символів');
      return;
    }
    setState(() {
      _nickChanging = true;
      _nickError = null;
    });
    final check = await widget.chat.checkNickname(nick);
    if (!check.available) {
      if (mounted) {
        setState(() {
          _nickChanging = false;
          _nickError = check.error;
        });
      }
      return;
    }
    final result = await widget.chat.registerNickname(nick);
    if (mounted) {
      setState(() => _nickChanging = false);
      if (result.success) {
        _newNickController.clear();
        widget.onNicknameChanged();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Нікнейм змінено'),
              behavior: SnackBarBehavior.floating,
              duration: Duration(seconds: 2),
            ),
          );
        }
        setState(() {});
      } else {
        setState(() => _nickError = result.error);
      }
    }
  }

  Future<void> _activateModerator() async {
    final secret = _secretController.text.trim();
    if (secret.isEmpty) {
      setState(() => _modError = 'Введіть пароль');
      return;
    }
    setState(() {
      _modError = null;
      _modSuccess = null;
    });
    final result = await ModeratorService.instance.login(secret);
    if (mounted) {
      if (result == null) {
        setState(() => _modSuccess = 'Модератор активовано ✓');
        widget.chat.syncModeratorState();
      } else {
        setState(() => _modError = result);
      }
    }
  }

  Future<void> _loadBanList() async {
    setState(() => _loadingBans = true);
    final list = await widget.chat.getBanList();
    if (mounted) {
      setState(() {
        _banList = list;
        _loadingBans = false;
      });
    }
  }
}
