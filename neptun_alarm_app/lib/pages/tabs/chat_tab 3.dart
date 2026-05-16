import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';

import '../../design/neptun_design.dart';
import '../../core/providers/chat_provider.dart';
import '../../features/chat/presentation/providers/chat_controller.dart';
import '../../features/chat/presentation/widgets/chat_input_bar.dart';
import '../../features/chat/presentation/widgets/chat_message_list.dart';
import '../../features/chat/presentation/widgets/chat_auth_views.dart';
import '../../features/chat/presentation/widgets/typing_indicator.dart';
import '../../features/chat/presentation/widgets/chat_dialog_helpers.dart';
import '../../models/chat_message.dart';
import '../../core/widgets/neptun_overlay_insets.dart';
import '../../core/widgets/neptun_shell_modal.dart';
import '../../services/purchase_service.dart';

import '../../features/chat/presentation/widgets/chat_background.dart';
import '../../features/chat/presentation/widgets/chat_status_views.dart';

class ChatTab extends ConsumerStatefulWidget {
  const ChatTab({super.key});

  @override
  ConsumerState<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends ConsumerState<ChatTab>
    with AutomaticKeepAliveClientMixin {
  /// Смуга пошуку під глобальним HUD (без другої «капсули» над чатом).
  static const double _searchStripH = 48;

  /// Повітря між останніми повідомленнями і полем вводу (і чипом «друкує», якщо є).
  static const double _gapAboveInputStack = NeptunSpacing.lg;

  /// Низ таба вже закінчується над смугою реклами; [neptunContentBottomPadding] — відступ для
  /// кінця скролу, не для позиції поля вводу. Інакше між вводом і банером зʼявляється ~48px пустоти.
  static double _chatInputDockBottomInset(BuildContext context) {
    if (NeptunOverlayInsets.maybeOf(context) != null) {
      return NeptunSpacing.sm;
    }
    return neptunContentBottomPadding(context);
  }

  final _scrollController = ScrollController();
  final _textController = TextEditingController();
  final _searchController = TextEditingController();
  final _focusNode = FocusNode();
  final _searchFocusNode = FocusNode();
  final _listKey = GlobalKey<ChatMessageListState>();

  bool _showScrollFab = false;

  ProviderSubscription<bool>? _searchModeSub;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _searchModeSub = ref.listenManual<bool>(
      chatControllerProvider.select((s) => s.searchMode),
      (prev, next) {
        if (next && prev != true) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _searchFocusNode.requestFocus();
          });
        }
      },
    );
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final isAtBottom = _scrollController.offset < 100;
    if (_showScrollFab == isAtBottom) {
      setState(() => _showScrollFab = !isAtBottom);
    }
  }

  void _scrollToMessage(String messageId) {
    if (!_scrollController.hasClients) return;
    _listKey.currentState?.scrollToMessageId(messageId);
  }

  @override
  void dispose() {
    _searchModeSub?.close();
    _scrollController.dispose();
    _textController.dispose();
    _searchController.dispose();
    _focusNode.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final gate = ref.watch(
      chatControllerProvider.select(
        (s) => (
          s.isLoading,
          s.ageConfirmed,
          s.needsRegistration,
          s.rulesAgreed,
          s.isBanned,
          s.banReason,
        ),
      ),
    );
    final notifier = ref.read(chatControllerProvider.notifier);

    if (gate.$1) return const ChatLoadingView();
    if (!gate.$2) return ChatAgeGateView(background: const ChatBackground());
    if (gate.$3) {
      return ChatRegistrationView(background: const ChatBackground());
    }
    if (!gate.$4) {
      return ChatRulesView(
        onAgree: notifier.agreeToRules,
        background: const ChatBackground(),
      );
    }
    if (gate.$5) {
      return ChatBannedView(
        reason: gate.$6,
        onCheck: () => ref.read(chatServiceProvider).checkBanStatus(),
      );
    }

    final searchMode = ref.watch(
      chatControllerProvider.select((s) => s.searchMode),
    );
    final headerSearch = ref.watch(
      chatControllerProvider.select(
        (s) => (s.searchResults, s.searchCurrentIndex),
      ),
    );
    final inputBar = ref.watch(
      chatControllerProvider.select(
        (s) => (
          s.replyTo,
          s.editingMessage,
          s.isSending,
          s.isRecording,
          s.recordingSeconds,
        ),
      ),
    );
    final typingUsers = ref.watch(
      chatControllerProvider.select((s) => s.typingUsers),
    );

    final dockBottom = _chatInputDockBottomInset(context);
    final underHud = neptunTightTopUnderHud(context);
    final listTopPad = underHud + (searchMode ? _searchStripH + 6 : 8);
    final listBottomPad =
        dockBottom +
        _estimateInputStackHeight(
          isRecording: inputBar.$4,
          replyTo: inputBar.$1,
          editingMessage: inputBar.$2,
          typingNotEmpty: typingUsers.isNotEmpty,
        ) +
        _gapAboveInputStack;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: Stack(
        clipBehavior: Clip.none,
        children: [
          const ChatBackground(),
          Positioned.fill(
            child: Padding(
              padding: EdgeInsets.only(
                top: listTopPad,
                left: NeptunSpacing.lg,
                right: NeptunSpacing.lg,
                bottom: listBottomPad,
              ),
              child: ChatMessageList(
                key: _listKey,
                scrollController: _scrollController,
                myDeviceId: ref.read(chatServiceProvider).deviceId ?? '',
                onReply: notifier.setReply,
                onEdit: (m) {
                  _textController.text = m.message;
                  notifier.setEdit(m);
                  _focusNode.requestFocus();
                },
                onReport: _reportMessage,
                onBlock: _blockUser,
                onDeleteAll: _deleteAllMessagesFromUser,
              ),
            ),
          ),
          if (searchMode)
            Positioned(
              top: underHud,
              left: NeptunSpacing.lg,
              right: NeptunSpacing.lg,
              child: _buildSearchStrip(
                notifier,
                searchResults: headerSearch.$1,
                searchCurrentIndex: headerSearch.$2,
              ),
            ),
          Positioned(
            left: NeptunSpacing.lg,
            right: NeptunSpacing.lg,
            bottom: dockBottom,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (typingUsers.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: ChatTypingStatusBar(users: typingUsers),
                  ),
                ChatInputBar(
                  textController: _textController,
                  focusNode: _focusNode,
                  replyTo: inputBar.$1,
                  editTo: inputBar.$2,
                  isSending: inputBar.$3,
                  isRecording: inputBar.$4,
                  recordingSeconds: inputBar.$5,
                  onReplyDismiss: () => notifier.setReply(null),
                  onEditDismiss: () {
                    _textController.clear();
                    notifier.setEdit(null);
                  },
                  onTypingChanged: (typing) {
                    ref.read(chatServiceProvider).sendTyping(typing);
                  },
                  onSend: () {
                    notifier.sendMessage(_textController.text);
                    _textController.clear();
                    _focusNode.requestFocus();
                  },
                  onStartRecording: () {
                    if (!_ensureProForChatMedia('Голосові повідомлення')) {
                      return;
                    }
                    notifier.startRecording();
                  },
                  onCancelRecording: notifier.cancelRecording,
                  onStopAndSendRecording: notifier.stopAndSendRecording,
                  onAttach: () => _onAttach(notifier),
                ),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: _showScrollFab
          ? Padding(
              padding: EdgeInsets.only(bottom: dockBottom),
              child: _buildScrollFab(),
            )
          : null,
    );
  }

  /// Оцінка місця під ввід + превʼю відповіді + рядок «друкує» (щоб список не ховався під капсулою).
  double _estimateInputStackHeight({
    required bool isRecording,
    required ChatMessage? replyTo,
    required ChatMessage? editingMessage,
    required bool typingNotEmpty,
  }) {
    if (isRecording) return 80;
    var h = 54.0;
    if (replyTo != null || editingMessage != null) h += 44;
    if (typingNotEmpty) h += 36;
    return h;
  }

  Widget _buildSearchStrip(
    ChatNotifier notifier, {
    required List<int> searchResults,
    required int searchCurrentIndex,
  }) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Material(
      elevation: isDark ? 3 : 1,
      shadowColor: Colors.black.withValues(alpha: isDark ? 0.42 : 0.1),
      surfaceTintColor: Colors.transparent,
      color: cs.surfaceContainerHigh,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: cs.outlineVariant.withValues(alpha: 0.32),
          width: 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: _searchStripH,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: _buildSearchBar(
            notifier,
            searchResults: searchResults,
            searchCurrentIndex: searchCurrentIndex,
          ),
        ),
      ),
    );
  }

  Widget _buildSearchBar(
    ChatNotifier notifier, {
    required List<int> searchResults,
    required int searchCurrentIndex,
  }) {
    final cs = Theme.of(context).colorScheme;
    final iconC = cs.onSurfaceVariant;
    // Один зовнішній Expanded: усередині Row(Expanded(TextField) + trailing), щоб не було
    // двох сусідніх flex-дітей з від'ємним залишком ширини на вузьких екранах.
    return Row(
      children: [
        IconButton(
          onPressed: () {
            HapticFeedback.lightImpact();
            FocusScope.of(context).unfocus();
            notifier.setSearchMode(false);
            _searchController.clear();
          },
          style: IconButton.styleFrom(
            foregroundColor: iconC,
            minimumSize: const Size(36, 36),
            maximumSize: const Size(40, 40),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
          ),
          icon: const Icon(Icons.close_rounded, size: 20),
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  focusNode: _searchFocusNode,
                  decoration: InputDecoration(
                    hintText: 'Пошук…',
                    isDense: true,
                    filled: false,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                    errorBorder: InputBorder.none,
                    focusedErrorBorder: InputBorder.none,
                    contentPadding: EdgeInsets.zero,
                    hintStyle: GoogleFonts.plusJakartaSans(
                      fontSize: 14,
                      color: cs.onSurfaceVariant.withValues(alpha: 0.65),
                    ),
                  ),
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    color: cs.onSurface,
                  ),
                  onChanged: notifier.updateSearch,
                ),
              ),
              if (searchResults.isNotEmpty)
                Flexible(
                  flex: 0,
                  fit: FlexFit.loose,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    reverse: true,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${searchCurrentIndex + 1}/${searchResults.length}',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 10,
                            color: iconC,
                          ),
                        ),
                        IconButton(
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(
                            minWidth: 24,
                            minHeight: 24,
                            maxWidth: 40,
                            maxHeight: 40,
                          ),
                          style: IconButton.styleFrom(
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                          ),
                          onPressed: () {
                            notifier.nextSearchResult(-1);
                            final results = ref
                                .read(chatControllerProvider)
                                .searchResults;
                            final curIdx = ref
                                .read(chatControllerProvider)
                                .searchCurrentIndex;
                            final msg = ref
                                .read(chatControllerProvider)
                                .messages[results[curIdx]];
                            _scrollToMessage(msg.id);
                          },
                          icon: const Icon(
                            Icons.keyboard_arrow_up_rounded,
                            size: 20,
                          ),
                        ),
                        IconButton(
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(
                            minWidth: 24,
                            minHeight: 24,
                            maxWidth: 40,
                            maxHeight: 40,
                          ),
                          style: IconButton.styleFrom(
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                          ),
                          onPressed: () {
                            notifier.nextSearchResult(1);
                            final results = ref
                                .read(chatControllerProvider)
                                .searchResults;
                            final curIdx = ref
                                .read(chatControllerProvider)
                                .searchCurrentIndex;
                            final msg = ref
                                .read(chatControllerProvider)
                                .messages[results[curIdx]];
                            _scrollToMessage(msg.id);
                          },
                          icon: const Icon(
                            Icons.keyboard_arrow_down_rounded,
                            size: 20,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildScrollFab() {
    final cs = Theme.of(context).colorScheme;
    return FloatingActionButton.small(
      elevation: 3,
      backgroundColor: cs.primary,
      foregroundColor: cs.onPrimary,
      tooltip: 'До останніх повідомлень',
      onPressed: () {
        HapticFeedback.lightImpact();
        _scrollController.animateTo(
          0,
          duration: const Duration(milliseconds: 320),
          curve: Curves.easeOutCubic,
        );
      },
      child: const Icon(Icons.keyboard_arrow_down_rounded, size: 22),
    );
  }

  Future<void> _onAttach(ChatNotifier notifier) async {
    if (!_ensureProForChatMedia('Медіа в чаті')) return;
    HapticFeedback.lightImpact();
    final cs = Theme.of(context).colorScheme;
    final source = await NeptunShellModal.showBottomSheet<ImageSource>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          child: Material(
            color: cs.surfaceContainerHigh,
            elevation: 4,
            shadowColor: Colors.black.withValues(alpha: 0.2),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
              side: BorderSide(color: cs.outlineVariant.withValues(alpha: 0.5)),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
                  child: Text(
                    'Вкласти фото',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: cs.onSurfaceVariant,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
                ListTile(
                  leading: Icon(Icons.photo_library_rounded, color: cs.primary),
                  title: Text(
                    'Галерея',
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w600,
                      color: cs.onSurface,
                    ),
                  ),
                  onTap: () => Navigator.pop(ctx, ImageSource.gallery),
                ),
                ListTile(
                  leading: Icon(Icons.camera_alt_rounded, color: cs.primary),
                  title: Text(
                    'Камера',
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w600,
                      color: cs.onSurface,
                    ),
                  ),
                  onTap: () => Navigator.pop(ctx, ImageSource.camera),
                ),
                const SizedBox(height: 4),
              ],
            ),
          ),
        ),
      ),
    );
    if (source == null) return;
    await notifier.pickAndSendImage(
      source,
      caption: _textController.text.trim(),
    );
    _textController.clear();
  }

  bool _ensureProForChatMedia(String featureName) {
    if (PurchaseService().isPremium) return true;
    HapticFeedback.lightImpact();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$featureName доступні тільки з PRO'),
        behavior: SnackBarBehavior.floating,
        action: SnackBarAction(
          label: 'PRO',
          onPressed: () => context.push('/premium'),
        ),
      ),
    );
    return false;
  }

  void _reportMessage(ChatMessage msg) {
    ChatDialogHelpers.reportMessage(
      context,
      ref.read(chatServiceProvider),
      msg,
    );
  }

  void _deleteAllMessagesFromUser(ChatMessage msg) {
    ChatDialogHelpers.deleteAllMessagesFromUser(
      context,
      ref.read(chatServiceProvider),
      msg,
      () {},
    );
  }

  void _blockUser(ChatMessage msg) {
    ChatDialogHelpers.blockUser(
      context,
      ref.read(chatServiceProvider),
      msg,
      () {},
    );
  }
}
