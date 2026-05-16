import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/api_config.dart';
import '../core/utils/open_neptun_telegram.dart';
import '../services/auth_service.dart';
import '../core/widgets/neptun_shimmer.dart';
import '../config/app_constants.dart';
import '../design/neptun_design.dart';

/// Bidirectional feedback page — submit, view history, reply, see admin responses
class FeedbackPage extends StatefulWidget {
  const FeedbackPage({super.key});

  @override
  State<FeedbackPage> createState() => _FeedbackPageState();
}

class _FeedbackPageState extends State<FeedbackPage> {
  // Form
  final _controller = TextEditingController();
  String _selectedType = 'general';
  bool _sending = false;
  String? _error;
  bool _showFallback = false;
  int _retryCount = 0;

  // Tickets
  List<Map<String, dynamic>> _tickets = [];
  bool _loadingTickets = true;
  String? _deviceId;
  String? _expandedTicketId;
  final Map<String, TextEditingController> _replyControllers = {};
  final Set<String> _replyingSending = {};

  static const _types = [
    ('general', 'Загальне', Icons.chat_bubble_outline_rounded),
    ('bug', 'Помилка', Icons.bug_report_outlined),
    ('suggestion', 'Пропозиція', Icons.lightbulb_outline_rounded),
  ];

  @override
  void initState() {
    super.initState();
    _loadTickets();
  }

  @override
  void dispose() {
    _controller.dispose();
    for (final c in _replyControllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<String> _getDeviceId() async {
    if (_deviceId != null) return _deviceId!;
    _deviceId = await AuthService.getDeviceId();
    return _deviceId!;
  }

  Future<void> _loadTickets() async {
    try {
      final deviceId = await _getDeviceId();
      if (deviceId.isEmpty) {
        setState(() => _loadingTickets = false);
        return;
      }

      final resp = await http
          .get(Uri.parse('${ApiConfig.feedback}?device_id=$deviceId&limit=30'))
          .timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200 && mounted) {
        final data = json.decode(resp.body);
        setState(() {
          _tickets = List<Map<String, dynamic>>.from(data['feedback'] ?? []);
          _loadingTickets = false;
        });
      } else {
        setState(() => _loadingTickets = false);
      }
    } catch (_) {
      if (mounted) setState(() => _loadingTickets = false);
    }
  }

  Future<void> _markRead(String ticketId) async {
    try {
      final deviceId = await _getDeviceId();
      await http
          .post(
            Uri.parse('${ApiConfig.feedback}/$ticketId/read'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'device_id': deviceId}),
          )
          .timeout(ApiConfig.httpTimeout);
    } catch (_) {}
  }

  Future<void> _sendReply(String ticketId) async {
    final controller = _replyControllers[ticketId];
    final text = controller?.text.trim();
    if (text == null || text.isEmpty) return;

    setState(() => _replyingSending.add(ticketId));
    try {
      final deviceId = await _getDeviceId();
      final resp = await http
          .post(
            Uri.parse('${ApiConfig.feedback}/$ticketId/respond'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'message': text,
              'author': 'user',
              'device_id': deviceId,
            }),
          )
          .timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200 && mounted) {
        controller?.clear();
        _loadTickets();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Помилка. Спробуйте пізніше.')),
        );
      }
    }
    if (mounted) setState(() => _replyingSending.remove(ticketId));
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) {
      setState(() => _error = 'Введіть повідомлення');
      return;
    }
    if (text.length < 5) {
      setState(() => _error = 'Мінімум 5 символів');
      return;
    }

    setState(() {
      _sending = true;
      _error = null;
      _showFallback = false;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final packageInfo = await PackageInfo.fromPlatform();
      final deviceId = await _getDeviceId();

      final body = {
        'message': text,
        'type': _selectedType,
        'device_id': deviceId,
        'device': Platform.isIOS
            ? 'iOS'
            : (Platform.isAndroid ? 'Android' : 'unknown'),
        'app_version': '${packageInfo.version}+${packageInfo.buildNumber}',
        'regions': prefs.getStringList('subscribed_topics') ?? [],
      };

      final resp = await http
          .post(
            Uri.parse(ApiConfig.feedback),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);

      if (mounted) {
        if (resp.statusCode >= 200 && resp.statusCode < 300) {
          _controller.clear();
          setState(() {
            _sending = false;
            _error = null;
            _retryCount = 0;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Row(
                children: [
                  Icon(Icons.check_circle_rounded, color: Colors.white),
                  SizedBox(width: 12),
                  Expanded(child: Text('Дякуємо! Ваш відгук надіслано.')),
                ],
              ),
              backgroundColor: NeptunStatus.safe,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          );
          _loadTickets();
        } else {
          _retryCount++;
          setState(() {
            _sending = false;
            _error = 'Помилка сервера (${resp.statusCode}). Спробуйте пізніше.';
            _showFallback = _retryCount >= 2;
          });
        }
      }
    } catch (e) {
      _retryCount++;
      if (mounted) {
        setState(() {
          _sending = false;
          _error = 'Немає з\'єднання. Перевірте інтернет.';
          _showFallback = _retryCount >= 2;
        });
      }
    }
  }

  void _sendViaEmail() {
    final text = _controller.text.trim();
    final subject = Uri.encodeComponent(
      '${AppConstants.appName} Feedback [$_selectedType]',
    );
    final body = Uri.encodeComponent(text);
    launchUrl(
      Uri.parse('mailto:neptun.alerts@gmail.com?subject=$subject&body=$body'),
      mode: LaunchMode.externalApplication,
    );
  }

  void _sendViaTelegram() {
    openNeptunTelegramChannel('feedback');
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Зворотній зв\'язок'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadTickets,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // ── Existing tickets ──
            if (_loadingTickets) ...[
              Text(
                'Мої звернення',
                style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              ...List.generate(3, (_) => const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: NeptunShimmer(
                  width: double.infinity,
                  height: 80,
                  borderRadius: 14,
                ),
              )),
              const Divider(height: 32),
            ],
            if (!_loadingTickets && _tickets.isNotEmpty) ...[
              Text(
                'Мої звернення',
                style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              ..._tickets.map(_buildTicketCard),
              const Divider(height: 32),
            ],

            // ── New ticket form ──
            Text(
              'Нове звернення',
              style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              'Напишіть нам — ми читаємо кожне повідомлення.',
              style: tt.bodyMedium?.copyWith(color: cs.onSurfaceVariant),
            ),
            const SizedBox(height: 20),

            // Type selector
            Text(
              'Тип',
              style: tt.labelMedium?.copyWith(
                color: cs.onSurface.withValues(alpha: 0.6),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _types.map((t) {
                final selected = _selectedType == t.$1;
                return GestureDetector(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    setState(() => _selectedType = t.$1);
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: selected
                          ? cs.primary.withValues(alpha: 0.15)
                          : cs.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected ? cs.primary : cs.outline,
                        width: selected ? 1.5 : 0.5,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          t.$3,
                          size: 18,
                          color: selected ? cs.primary : cs.onSurfaceVariant,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          t.$2,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: selected
                                ? FontWeight.w600
                                : FontWeight.w500,
                            color: selected ? cs.primary : cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Message field
            Text(
              'Повідомлення',
              style: tt.labelMedium?.copyWith(
                color: cs.onSurface.withValues(alpha: 0.6),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _controller,
              maxLines: 5,
              minLines: 4,
              maxLength: 1000,
              enabled: !_sending,
              style: GoogleFonts.plusJakartaSans(color: cs.onSurface, fontSize: 15),
              decoration: InputDecoration(
                hintText: 'Опишіть питання, пропозицію або помилку...',
                hintStyle: GoogleFonts.plusJakartaSans(
                  color: cs.onSurface.withValues(alpha: 0.35),
                  fontSize: 15,
                ),
                errorText: _error,
                filled: true,
                fillColor: cs.surfaceContainerHighest,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(color: cs.outline),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(color: cs.outline),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(color: cs.primary, width: 1.5),
                ),
                contentPadding: const EdgeInsets.all(16),
              ),
            ),
            const SizedBox(height: 24),

            // Send button
            SizedBox(
              height: 52,
              child: ElevatedButton(
                onPressed: _sending ? null : _send,
                style: ElevatedButton.styleFrom(
                  backgroundColor: cs.primary,
                  // У dark theme primary майже білий — потрібен onPrimary (темний), не Colors.white.
                  foregroundColor: cs.onPrimary,
                  disabledBackgroundColor:
                      cs.primary.withValues(alpha: 0.45),
                  disabledForegroundColor:
                      cs.onPrimary.withValues(alpha: 0.55),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 0,
                ),
                child: _sending
                    ? SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.5,
                          color: cs.onPrimary,
                        ),
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.send_rounded, size: 20, color: cs.onPrimary),
                          const SizedBox(width: 10),
                          Text(
                            'Надіслати',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: cs.onPrimary,
                            ),
                          ),
                        ],
                      ),
              ),
            ),

            // Fallback options
            if (_showFallback) ...[
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: cs.outline, width: 0.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Альтернативні способи зв\'язку:',
                      style: tt.titleSmall?.copyWith(
                        color: cs.onSurface,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _sendViaTelegram,
                            icon: const Icon(Icons.send_rounded, size: 18),
                            label: Text(
                              'Telegram',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: const Color(0xFF2AABEE),
                              side: const BorderSide(
                                color: Color(0xFF2AABEE),
                                width: 1,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _sendViaEmail,
                            icon: const Icon(Icons.email_outlined, size: 18),
                            label: Text(
                              'Email',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: cs.primary,
                              side: BorderSide(color: cs.primary, width: 1),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTicketCard(Map<String, dynamic> ticket) {
    final cs = Theme.of(context).colorScheme;
    final isExpanded = _expandedTicketId == ticket['id'];
    final responses = List<Map<String, dynamic>>.from(
      ticket['responses'] ?? [],
    );
    final hasUnread = ticket['has_unread_response'] == true;
    final status = ticket['status'] ?? 'open';
    final type = ticket['type'] ?? 'general';

    final statusLabel =
        {
          'open': 'Відкрито',
          'in_progress': 'В роботі',
          'resolved': 'Вирішено',
          'closed': 'Закрито',
        }[status] ??
        status;

    final statusColor =
        {
          'open': cs.primary,
          'in_progress': Colors.orange,
          'resolved': Colors.green,
          'closed': Colors.grey,
        }[status] ??
        cs.primary;

    final typeIcon =
        {
          'bug': Icons.bug_report_outlined,
          'suggestion': Icons.lightbulb_outline_rounded,
          'general': Icons.chat_bubble_outline_rounded,
        }[type] ??
        Icons.chat_bubble_outline_rounded;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            setState(() {
              _expandedTicketId = isExpanded ? null : ticket['id'];
            });
            if (!isExpanded && hasUnread) {
              _markRead(ticket['id']);
            }
          },
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    Icon(typeIcon, size: 20, color: cs.onSurfaceVariant),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        (ticket['message'] as String? ?? '').length > 60
                            ? '${(ticket['message'] as String).substring(0, (ticket['message'] as String).length < 60 ? (ticket['message'] as String).length : 60)}...'
                            : ticket['message'] ?? '',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          fontWeight: hasUnread
                              ? FontWeight.w600
                              : FontWeight.w400,
                          color: cs.onSurface,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        statusLabel,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: statusColor,
                        ),
                      ),
                    ),
                    if (hasUnread) ...[
                      const SizedBox(width: 6),
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: cs.primary,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ],
                    if (responses.isNotEmpty) ...[
                      const SizedBox(width: 6),
                      Text(
                        '${responses.length}',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                      Icon(
                        Icons.forum_outlined,
                        size: 14,
                        color: cs.onSurfaceVariant,
                      ),
                    ],
                  ],
                ),
              ),

              // Expanded: responses + reply
              if (isExpanded) ...[
                Divider(height: 1, color: cs.outline.withValues(alpha: 0.3)),
                Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Full message
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: cs.surface,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          ticket['message'] ?? '',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            color: cs.onSurface,
                            height: 1.5,
                          ),
                        ),
                      ),
                      // Date
                      Padding(
                        padding: const EdgeInsets.only(top: 6, bottom: 12),
                        child: Text(
                          _formatDate(ticket['created_at'] ?? ''),
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 11,
                            color: cs.onSurfaceVariant.withValues(alpha: 0.6),
                          ),
                        ),
                      ),
                      // Responses
                      if (responses.isNotEmpty) ...[
                        Text(
                          'Відповіді',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ...responses.map((r) => _buildResponseBubble(r)),
                      ],
                      // Reply field (only for open/in_progress)
                      if (status == 'open' || status == 'in_progress') ...[
                        const SizedBox(height: 12),
                        _buildReplyField(ticket['id']),
                      ],
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResponseBubble(Map<String, dynamic> resp) {
    final cs = Theme.of(context).colorScheme;
    final isAdmin = resp['author'] == 'admin';

    return Align(
      alignment: isAdmin ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: EdgeInsets.only(
          bottom: 8,
          left: isAdmin ? 0 : 40,
          right: isAdmin ? 40 : 0,
        ),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isAdmin
              ? cs.primary.withValues(alpha: 0.08)
              : cs.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(14),
          border: isAdmin
              ? Border.all(color: cs.primary.withValues(alpha: 0.2))
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isAdmin ? Icons.support_agent_rounded : Icons.person_rounded,
                  size: 14,
                  color: isAdmin ? cs.primary : cs.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  isAdmin ? 'Команда ${AppConstants.appName}' : 'Ви',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isAdmin ? cs.primary : cs.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                Text(
                  _formatDate(resp['created_at'] ?? ''),
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 10,
                    color: cs.onSurfaceVariant.withValues(alpha: 0.5),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              resp['message'] ?? '',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 14,
                color: cs.onSurface,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReplyField(String ticketId) {
    final cs = Theme.of(context).colorScheme;
    _replyControllers.putIfAbsent(ticketId, () => TextEditingController());
    final controller = _replyControllers[ticketId]!;
    final isSending = _replyingSending.contains(ticketId);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: TextField(
            controller: controller,
            maxLines: 3,
            minLines: 1,
            maxLength: 1000,
            enabled: !isSending,
            style: GoogleFonts.plusJakartaSans(fontSize: 14, color: cs.onSurface),
            decoration: InputDecoration(
              hintText: 'Ваша відповідь...',
              hintStyle: GoogleFonts.plusJakartaSans(
                color: cs.onSurface.withValues(alpha: 0.35),
                fontSize: 14,
              ),
              filled: true,
              fillColor: cs.surface,
              counterText: '',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: cs.outline),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: cs.outline),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: cs.primary, width: 1.5),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 10,
              ),
              isDense: true,
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 44,
          height: 44,
          child: IconButton.filled(
            onPressed: isSending ? null : () => _sendReply(ticketId),
            icon: isSending
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send_rounded, size: 20),
            style: IconButton.styleFrom(
              backgroundColor: cs.primary,
              foregroundColor: Colors.white,
              disabledBackgroundColor: cs.primary.withValues(alpha: 0.3),
            ),
          ),
        ),
      ],
    );
  }

  String _formatDate(String iso) {
    try {
      final d = DateTime.parse(iso);
      final now = DateTime.now();
      final diff = now.difference(d);
      if (diff.inMinutes < 60) return '${diff.inMinutes} хв тому';
      if (diff.inHours < 24) return '${diff.inHours} год тому';
      if (diff.inDays < 7) return '${diff.inDays} д тому';
      return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
    } catch (_) {
      return iso;
    }
  }
}
