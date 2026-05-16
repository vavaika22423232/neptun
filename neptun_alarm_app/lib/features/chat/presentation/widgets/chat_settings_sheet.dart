import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../design/neptun_design.dart';
import '../../../../services/chat_service.dart';
import '../../../../services/moderator_service.dart';

/// Chat settings: nickname; moderator blocks only when logged in as moderator.
/// Відкривати через [Navigator.push] (повноекранно) — bottom sheet з `isScrollControlled`
/// ламав вертикальні обмеження й зсував контент під статус-бар.
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
    final tt = Theme.of(context).textTheme;
    return Scaffold(
        backgroundColor: cs.surface,
        resizeToAvoidBottomInset: true,
        appBar: AppBar(
          backgroundColor: cs.surfaceContainerHigh,
          surfaceTintColor: cs.surfaceTint,
          elevation: 0,
          leading: Semantics(
            label: 'Повернутися до чату',
            button: true,
            child: IconButton(
              style: IconButton.styleFrom(
                minimumSize: const Size(48, 48),
                tapTargetSize: MaterialTapTargetSize.padded,
              ),
              icon: Icon(Icons.arrow_back_rounded, color: cs.onSurface),
              tooltip: 'До чату',
              onPressed: () => context.pop(),
            ),
          ),
          title: Text(
            'Налаштування чату',
            style: tt.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              fontSize: 17,
              color: cs.onSurface,
            ),
          ),
          centerTitle: true,
        ),
        body: ListView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          padding: EdgeInsets.fromLTRB(
            NeptunSpacing.screenHorizontal,
            NeptunSpacing.lg,
            NeptunSpacing.screenHorizontal,
            NeptunSpacing.xxl + MediaQuery.paddingOf(context).bottom,
          ),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          children: _settingsSections(cs, tt),
        ),
    );
  }

  List<Widget> _settingsSections(ColorScheme cs, TextTheme tt) {
    return [
      if (widget.chat.isModerator) ...[
        _moderatorAdminTile(cs, tt),
        const SizedBox(height: 20),
      ],
      _sectionTitle('Ваш нікнейм', cs, tt),
      Container(
        padding: const EdgeInsets.all(14),
        decoration: _cardDecoration(),
        child: Row(
          children: [
            Icon(Icons.person_rounded, color: cs.primary, size: 20),
            const SizedBox(width: 10),
            Text(
              widget.chat.nickname ?? '—',
              style: tt.titleSmall?.copyWith(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: cs.onSurface,
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      _sectionTitle('Змінити нікнейм', cs, tt),
      // Не Row(Expanded + FilledButton) — на вузькій ширині flex дає від'ємні обмеження → assert у кнопки.
      Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _newNickController,
            maxLength: 20,
            style: tt.bodyMedium?.copyWith(
              color: cs.onSurface,
              fontSize: 14,
            ),
            decoration: InputDecoration(
              hintText: 'Новий нікнейм',
              hintStyle: tt.bodyMedium?.copyWith(
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
          const SizedBox(height: 10),
          SizedBox(
            height: 46,
            child: FilledButton(
              onPressed: _nickChanging ? null : _changeNickname,
              style: FilledButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16),
              ),
              child: _nickChanging
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: cs.onPrimary,
                      ),
                    )
                  : const Text('Зберегти'),
            ),
          ),
        ],
      ),
      if (widget.chat.isModerator) ...[
        const SizedBox(height: 20),
        _sectionTitle('Модерація', cs, tt),
        Container(
          decoration: _cardDecoration(),
          child: Column(
            children: [
              ListTile(
                leading: Icon(
                  Icons.shield_rounded,
                  color: cs.tertiary,
                ),
                title: Text(
                  'Ви модератор',
                  style: tt.bodyMedium?.copyWith(
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
                Divider(height: 0.5, color: cs.outlineVariant),
                Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      TextField(
                        controller: _secretController,
                        obscureText: true,
                        maxLength: ModeratorService.maxModeratorSecretLength,
                        style: tt.bodyMedium?.copyWith(
                          color: cs.onSurface,
                          fontSize: 14,
                        ),
                        decoration: InputDecoration(
                          hintText: 'Пароль модератора',
                          hintStyle: tt.bodyMedium?.copyWith(
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
                          counterText: '',
                        ),
                      ),
                      const SizedBox(height: 8),
                                           SizedBox(
                        width: double.infinity,
                        child: FilledButton.tonal(
                          onPressed: _activateModerator,
                          style: FilledButton.styleFrom(
                            foregroundColor: cs.tertiary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: const Text('Оновити'),
                        ),
                      ),
                      if (_modError != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            _modError!,
                            style: tt.bodySmall?.copyWith(
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
                            style: tt.bodySmall?.copyWith(
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
      ],
      if (widget.chat.isModerator) ...[
        const SizedBox(height: 20),
        _sectionTitle('Заблоковані', cs, tt),
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
                  style: tt.bodyMedium?.copyWith(
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
                Divider(height: 0.5, color: cs.outlineVariant),
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
                        style: tt.bodySmall?.copyWith(
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
                        style: tt.bodySmall?.copyWith(
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
                    style: tt.bodySmall?.copyWith(
                      fontSize: 13,
                      color: cs.onSurface.withValues(alpha: 0.35),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    ];
  }

  Widget _moderatorAdminTile(ColorScheme cs, TextTheme tt) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          final router = GoRouter.of(context);
          context.pop();
          WidgetsBinding.instance.addPostFrameCallback((_) {
            router.push('/chat-admin');
          });
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
                      style: tt.titleSmall?.copyWith(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: cs.onSurface,
                      ),
                    ),
                    Text(
                      'Заблоковані, розблокування',
                      style: tt.bodySmall?.copyWith(
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

  Widget _sectionTitle(String title, ColorScheme cs, TextTheme tt) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 4),
      child: Text(
        title,
        style: tt.labelSmall?.copyWith(
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
      color: cs.surfaceContainerHigh,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: cs.outlineVariant),
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
    final formatErr =
        ModeratorService.validateModeratorSecretInput(_secretController.text);
    if (formatErr != null) {
      setState(() {
        _modError = formatErr;
        _modSuccess = null;
      });
      return;
    }
    setState(() {
      _modError = null;
      _modSuccess = null;
    });
    final result =
        await ModeratorService.instance.login(_secretController.text);
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
