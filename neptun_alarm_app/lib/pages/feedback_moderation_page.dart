import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../services/moderator_service.dart';

/// In-app feedback moderation page for moderators.
/// Shows all feedback tickets with status filters, detail view, and reply.
class FeedbackModerationPage extends StatefulWidget {
  const FeedbackModerationPage({super.key});

  @override
  State<FeedbackModerationPage> createState() => _FeedbackModerationPageState();
}

class _FeedbackModerationPageState extends State<FeedbackModerationPage> {
  List<Map<String, dynamic>> _tickets = [];
  bool _loading = true;
  String _filterStatus = 'all';
  String? _expandedId;
  final Map<String, TextEditingController> _replyControllers = {};
  final Set<String> _sendingReply = {};
  final Set<String> _updatingStatus = {};

  static const _statusFilters = [
    ('all', 'Все'),
    ('open', 'Відкриті'),
    ('in_progress', 'В роботі'),
    ('resolved', 'Вирішені'),
    ('closed', 'Закриті'),
  ];

  @override
  void initState() {
    super.initState();
    _loadTickets();
  }

  @override
  void dispose() {
    for (final c in _replyControllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<Map<String, String>> _authHeaders() async {
    final secret = await ModeratorService.instance.getSecret();
    return {
      'Content-Type': 'application/json',
      'x-auth-secret': ?secret,
    };
  }

  Future<void> _loadTickets() async {
    setState(() => _loading = true);
    try {
      final headers = await _authHeaders();
      final status = _filterStatus == 'all' ? '' : '&status=$_filterStatus';
      final resp = await http
          .get(
            Uri.parse('${ApiConfig.feedback}?limit=100$status'),
            headers: headers,
          )
          .timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200 && mounted) {
        final data = json.decode(resp.body);
        setState(() {
          _tickets = List<Map<String, dynamic>>.from(data['feedback'] ?? []);
          _loading = false;
        });
      } else {
        setState(() => _loading = false);
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _updateStatus(String ticketId, String newStatus) async {
    setState(() => _updatingStatus.add(ticketId));
    try {
      final headers = await _authHeaders();
      final resp = await http
          .patch(
            Uri.parse('${ApiConfig.feedback}/$ticketId'),
            headers: headers,
            body: json.encode({'status': newStatus}),
          )
          .timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200) {
        _loadTickets();
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Помилка: ${resp.statusCode}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Помилка з\'єднання')));
      }
    }
    if (mounted) setState(() => _updatingStatus.remove(ticketId));
  }

  Future<void> _sendReply(String ticketId) async {
    final controller = _replyControllers[ticketId];
    if (controller == null || controller.text.trim().isEmpty) return;

    setState(() => _sendingReply.add(ticketId));
    try {
      final headers = await _authHeaders();
      final resp = await http
          .post(
            Uri.parse('${ApiConfig.feedback}/$ticketId/respond'),
            headers: headers,
            body: json.encode({
              'message': controller.text.trim(),
              'author': 'admin',
            }),
          )
          .timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200) {
        controller.clear();
        _loadTickets();
      }
    } catch (_) {}
    if (mounted) setState(() => _sendingReply.remove(ticketId));
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Модерація відгуків'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadTickets),
        ],
      ),
      body: Column(
        children: [
          // ── Status filter chips ──
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: _statusFilters.map((f) {
                final isActive = _filterStatus == f.$1;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    selected: isActive,
                    label: Text(f.$2),
                    onSelected: (_) {
                      _filterStatus = f.$1;
                      _loadTickets();
                    },
                  ),
                );
              }).toList(),
            ),
          ),

          // ── Ticket list ──
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _tickets.isEmpty
                ? Center(
                    child: Text(
                      'Немає відгуків',
                      style: TextStyle(
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _loadTickets,
                    child: ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 20),
                      itemCount: _tickets.length,
                      itemBuilder: (_, i) =>
                          _buildTicketCard(_tickets[i], cs, isDark),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildTicketCard(
    Map<String, dynamic> ticket,
    ColorScheme cs,
    bool isDark,
  ) {
    final id = ticket['id']?.toString() ?? '';
    final message = ticket['message']?.toString() ?? '';
    final type = ticket['type']?.toString() ?? 'general';
    final status = ticket['status']?.toString() ?? 'open';
    final deviceId = ticket['device_id']?.toString() ?? '';
    final device = ticket['device']?.toString() ?? '';
    final appVersion = ticket['app_version']?.toString() ?? '';
    final createdAt = ticket['created_at']?.toString() ?? '';
    final responses = List<Map<String, dynamic>>.from(
      ticket['responses'] ?? [],
    );
    final isExpanded = _expandedId == id;

    _replyControllers.putIfAbsent(id, () => TextEditingController());

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: InkWell(
        onTap: () => setState(() => _expandedId = isExpanded ? null : id),
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header row ──
              Row(
                children: [
                  _statusBadge(status, cs),
                  const SizedBox(width: 8),
                  _typeBadge(type, cs),
                  const Spacer(),
                  if (responses.isNotEmpty)
                    Text(
                      '💬 ${responses.length}',
                      style: TextStyle(
                        fontSize: 12,
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Icon(
                    isExpanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    size: 20,
                    color: cs.onSurface.withValues(alpha: 0.4),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // ── Message preview ──
              Text(
                message,
                maxLines: isExpanded ? null : 2,
                overflow: isExpanded ? null : TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14,
                  color: cs.onSurface.withValues(alpha: 0.85),
                ),
              ),

              // ── Meta info ──
              if (!isExpanded) ...[
                const SizedBox(height: 6),
                Text(
                  _formatDate(createdAt),
                  style: TextStyle(
                    fontSize: 11,
                    color: cs.onSurface.withValues(alpha: 0.35),
                  ),
                ),
              ],

              // ── Expanded details ──
              if (isExpanded) ...[
                const Divider(height: 20),

                // Device info
                _metaRow('Пристрій', device.isNotEmpty ? device : '—'),
                _metaRow(
                  'Device ID',
                  deviceId.isNotEmpty
                      ? '${deviceId.substring(0, deviceId.length < 8 ? deviceId.length : 8)}…'
                      : '—',
                ),
                _metaRow('Версія', appVersion.isNotEmpty ? appVersion : '—'),
                _metaRow('Дата', _formatDate(createdAt)),
                const SizedBox(height: 12),

                // ── Status actions ──
                Wrap(
                  spacing: 8,
                  children: [
                    if (status != 'in_progress')
                      _statusButton(
                        id,
                        'in_progress',
                        'В роботу',
                        Icons.play_arrow_rounded,
                        Colors.blue,
                      ),
                    if (status != 'resolved')
                      _statusButton(
                        id,
                        'resolved',
                        'Вирішено',
                        Icons.check_circle_outline,
                        Colors.green,
                      ),
                    if (status != 'closed')
                      _statusButton(
                        id,
                        'closed',
                        'Закрити',
                        Icons.close_rounded,
                        Colors.red,
                      ),
                    if (status != 'open')
                      _statusButton(
                        id,
                        'open',
                        'Відкрити',
                        Icons.refresh_rounded,
                        Colors.orange,
                      ),
                  ],
                ),

                // ── Responses timeline ──
                if (responses.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text(
                    'Відповіді',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...responses.map((r) => _buildResponse(r, cs, isDark)),
                ],

                // ── Reply input ──
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _replyControllers[id],
                        decoration: InputDecoration(
                          hintText: 'Відповідь модератора…',
                          filled: true,
                          fillColor: isDark
                              ? Colors.grey[850]
                              : Colors.grey[100],
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 10,
                          ),
                          isDense: true,
                        ),
                        maxLines: 3,
                        minLines: 1,
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      onPressed: _sendingReply.contains(id)
                          ? null
                          : () => _sendReply(id),
                      icon: _sendingReply.contains(id)
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.send_rounded, size: 20),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResponse(Map<String, dynamic> r, ColorScheme cs, bool isDark) {
    final isAdmin = r['author'] == 'admin';
    final message = r['message']?.toString() ?? '';
    final date = r['created_at']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: isAdmin
            ? cs.primary.withValues(alpha: 0.08)
            : cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isAdmin ? Icons.admin_panel_settings : Icons.person,
                size: 14,
                color: isAdmin
                    ? cs.primary
                    : cs.onSurface.withValues(alpha: 0.5),
              ),
              const SizedBox(width: 4),
              Text(
                isAdmin ? 'Модератор' : 'Користувач',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isAdmin
                      ? cs.primary
                      : cs.onSurface.withValues(alpha: 0.5),
                ),
              ),
              const Spacer(),
              Text(
                _formatDate(date),
                style: TextStyle(
                  fontSize: 10,
                  color: cs.onSurface.withValues(alpha: 0.3),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(message, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }

  Widget _statusBadge(String status, ColorScheme cs) {
    final (label, color) = switch (status) {
      'open' => ('Відкритий', Colors.orange),
      'in_progress' => ('В роботі', Colors.blue),
      'resolved' => ('Вирішений', Colors.green),
      'closed' => ('Закритий', Colors.grey),
      _ => (status, Colors.grey),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  Widget _typeBadge(String type, ColorScheme cs) {
    final (label, icon) = switch (type) {
      'bug' => ('Помилка', Icons.bug_report_outlined),
      'suggestion' => ('Пропозиція', Icons.lightbulb_outline),
      _ => ('Загальне', Icons.chat_bubble_outline),
    };

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: cs.onSurface.withValues(alpha: 0.4)),
        const SizedBox(width: 3),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: cs.onSurface.withValues(alpha: 0.4),
          ),
        ),
      ],
    );
  }

  Widget _statusButton(
    String ticketId,
    String status,
    String label,
    IconData icon,
    Color color,
  ) {
    final isUpdating = _updatingStatus.contains(ticketId);
    return ActionChip(
      avatar: isUpdating
          ? SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2, color: color),
            )
          : Icon(icon, size: 16, color: color),
      label: Text(label, style: TextStyle(fontSize: 12, color: color)),
      onPressed: isUpdating ? null : () => _updateStatus(ticketId, status),
      side: BorderSide(color: color.withValues(alpha: 0.3)),
    );
  }

  Widget _metaRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 3),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.4),
              ),
            ),
          ),
          Text(value, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  String _formatDate(String isoDate) {
    if (isoDate.isEmpty) return '';
    try {
      final dt = DateTime.parse(isoDate);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 60) return '${diff.inMinutes} хв тому';
      if (diff.inHours < 24) return '${diff.inHours} год тому';
      if (diff.inDays < 7) return '${diff.inDays} дн тому';
      return '${dt.day}.${dt.month.toString().padLeft(2, '0')}.${dt.year}';
    } catch (_) {
      return isoDate;
    }
  }
}
