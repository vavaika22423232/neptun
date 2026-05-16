import 'dart:convert';

import 'package:audioplayers/audioplayers.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../core/error/error_handler.dart';
import '../core/widgets/neptun_card.dart';
import '../core/widgets/neptun_error_state.dart';
import '../services/moderator_service.dart';
import '../core/widgets/neptun_shell_modal.dart';

/// Moderator page: view and act on chat reports (скарги).
class ComplaintsPage extends StatefulWidget {
  const ComplaintsPage({super.key});

  @override
  State<ComplaintsPage> createState() => _ComplaintsPageState();
}

class _ComplaintsPageState extends State<ComplaintsPage> {
  List<_ChatReport> _reports = [];
  bool _loading = true;
  String? _error;
  String _filter = 'PENDING';

  final AudioPlayer _audioPlayer = AudioPlayer();
  String? _playingVoiceMessageId;
  bool _isPlayingVoice = false;

  Future<void> _loadReports() async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Спочатку увійдіть як модератор';
        });
      }
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final resp = await http
          .get(
            Uri.parse(ApiConfig.adminChatReports),
            headers: {'X-Auth-Secret': secret},
          )
          .timeout(ApiConfig.httpTimeout);

      if (!mounted) return;

      if (resp.statusCode == 200) {
        final data = _safeJsonDecode<Map<String, dynamic>>(resp.body);
        if (data == null) {
          setState(() {
            _error = 'Сервер повернув некоректну відповідь';
            _loading = false;
          });
          return;
        }
        final list = data['reports'] as List? ?? [];
        setState(() {
          _reports = (list)
              .map((e) => _ChatReport.fromJson(e as Map<String, dynamic>))
              .toList();
          _loading = false;
        });
      } else {
        String errMsg = resp.statusCode == 401
            ? 'Невірний доступ. Увійдіть як модератор.'
            : 'Помилка ${resp.statusCode}';
        final errData = _safeJsonDecode<Map<String, dynamic>>(resp.body);
        if (errData != null && errData['error'] != null) {
          errMsg = errData['error'].toString();
        }
        setState(() {
          _error = errMsg;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = userFriendlyErrorMessage(e);
          _loading = false;
        });
      }
    }
  }

  Future<void> _deleteAndResolve(_ChatReport report) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) _showSnack('Увійдіть як модератор', isError: true);
      return;
    }

    try {
      final deleteResp = await http.delete(
        Uri.parse(ApiConfig.chatMessageById(report.messageId)),
        headers: {'X-Auth-Secret': secret},
      ).timeout(ApiConfig.httpTimeout);

      if (deleteResp.statusCode != 200 && deleteResp.statusCode != 404) {
        final errMsg = _parseErrorBody(deleteResp.body) ??
            'Помилка видалення (${deleteResp.statusCode})';
        if (mounted) _showSnack(errMsg, isError: true);
        return;
      }
      // 404 = message already deleted by another mod — still resolve the complaint

      final resolveResp = await http.post(
        Uri.parse(ApiConfig.adminChatReportsResolve),
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Secret': secret,
        },
        body: json.encode({'reportId': report.id, 'action': 'RESOLVED'}),
      ).timeout(ApiConfig.httpTimeout);

      if (resolveResp.statusCode == 200) {
        if (mounted) {
          _showSnack(deleteResp.statusCode == 404
              ? 'Повідомлення вже видалено, скаргу закрито'
              : 'Повідомлення видалено, скарга закрита');
        }
        _loadReports();
      } else {
        final errMsg = _parseErrorBody(resolveResp.body) ??
            'Помилка закриття скарги (${resolveResp.statusCode})';
        if (mounted) _showSnack(errMsg, isError: true);
      }
    } catch (e) {
      if (mounted) _showSnack(userFriendlyErrorMessage(e), isError: true);
    }
  }

  Future<void> _rejectReport(_ChatReport report) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) _showSnack('Увійдіть як модератор', isError: true);
      return;
    }

    try {
      final resp = await http.post(
        Uri.parse(ApiConfig.adminChatReportsResolve),
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Secret': secret,
        },
        body: json.encode({'reportId': report.id, 'action': 'REJECTED'}),
      ).timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200) {
        if (mounted) _showSnack('Скаргу відхилено');
        _loadReports();
      } else {
        final errMsg = _parseErrorBody(resp.body) ??
            'Помилка відхилення (${resp.statusCode})';
        if (mounted) _showSnack(errMsg, isError: true);
      }
    } catch (e) {
      if (mounted) _showSnack(userFriendlyErrorMessage(e), isError: true);
    }
  }

  Future<void> _blockUser(_ChatReport report) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) _showSnack('Увійдіть як модератор', isError: true);
      return;
    }

    final hasNickname = report.reportedNickname.isNotEmpty &&
        report.reportedNickname.toLowerCase() != 'анонім';
    final hasDeviceId = report.reportedDeviceId.isNotEmpty;
    if (!hasNickname && !hasDeviceId) {
      if (mounted) _showSnack('Немає даних про користувача для блокування', isError: true);
      return;
    }

    try {
      final resp = await http.post(
        Uri.parse(ApiConfig.adminChatBanUser),
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Secret': secret,
        },
        body: json.encode({
          'nickname': hasNickname ? report.reportedNickname : null,
          'deviceId': hasDeviceId ? report.reportedDeviceId : null,
          'reason': 'Скарга: ${report.reason}',
        }),
      ).timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200) {
        if (mounted) _showSnack('Користувача заблоковано');
        _loadReports();
      } else {
        final errMsg = _parseErrorBody(resp.body) ??
            'Помилка блокування (${resp.statusCode})';
        if (mounted) _showSnack(errMsg, isError: true);
      }
    } catch (e) {
      if (mounted) _showSnack(userFriendlyErrorMessage(e), isError: true);
    }
  }

  Future<void> _deleteAllMessagesFromUser(_ChatReport report) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) _showSnack('Увійдіть як модератор', isError: true);
      return;
    }

    final hasNickname = report.reportedNickname.isNotEmpty &&
        report.reportedNickname.toLowerCase() != 'анонім';
    final hasDeviceId = report.reportedDeviceId.isNotEmpty;
    if (!hasNickname && !hasDeviceId) {
      if (mounted) _showSnack('Немає даних про користувача для видалення', isError: true);
      return;
    }

    try {
      final resp = await http.post(
        Uri.parse(ApiConfig.adminChatDeleteUserMessages),
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Secret': secret,
        },
        body: json.encode({
          'nickname': hasNickname ? report.reportedNickname : null,
          'deviceId': hasDeviceId ? report.reportedDeviceId : null,
        }),
      ).timeout(ApiConfig.httpTimeout);

      if (resp.statusCode == 200) {
        final data = _safeJsonDecode<Map<String, dynamic>>(resp.body);
        final deleted = data?['deleted'] as int? ?? 0;
        if (mounted) _showSnack('Видалено повідомлень: $deleted');
        _loadReports();
      } else {
        final errMsg = _parseErrorBody(resp.body) ??
            'Помилка видалення (${resp.statusCode})';
        if (mounted) _showSnack(errMsg, isError: true);
      }
    } catch (e) {
      if (mounted) _showSnack(userFriendlyErrorMessage(e), isError: true);
    }
  }

  T? _safeJsonDecode<T>(String body) {
    if (body.isEmpty) return null;
    final trimmed = body.trimLeft();
    // Reject HTML and other non-JSON responses
    if (trimmed.startsWith('<') || trimmed.startsWith('<!')) return null;
    try {
      return json.decode(body) as T?;
    } catch (_) {
      return null;
    }
  }

  String? _parseErrorBody(String body) {
    final data = _safeJsonDecode<Map<String, dynamic>>(body);
    final err = data?['error'];
    return err?.toString();
  }

  void _showSnack(String text, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: isError ? Theme.of(context).colorScheme.error : null,
      ),
    );
  }

  String _formatTime(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final d = DateTime.parse(iso);
      return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }

  @override
  void initState() {
    super.initState();
    _loadReports();
    _audioPlayer.onPlayerComplete.listen((_) {
      if (mounted) setState(() => _isPlayingVoice = false);
    });
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _toggleVoicePlayback(String messageId, String url) async {
    if (_playingVoiceMessageId == messageId && _isPlayingVoice) {
      await _audioPlayer.pause();
      if (mounted) setState(() => _isPlayingVoice = false);
      return;
    }
    final fullUrl = url.startsWith('http') ? url : '${ApiConfig.baseUrl}$url';
    try {
      if (_playingVoiceMessageId != messageId) {
        await _audioPlayer.stop();
        await _audioPlayer.play(UrlSource(fullUrl));
      } else {
        await _audioPlayer.resume();
      }
      if (mounted) {
        setState(() {
          _playingVoiceMessageId = messageId;
          _isPlayingVoice = true;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isPlayingVoice = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Скарги',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _loading ? null : _loadReports,
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'PENDING', label: Text('Нові')),
                      ButtonSegment(value: 'ALL', label: Text('Всі')),
                    ],
                    selected: {_filter},
                    onSelectionChanged: (s) => setState(() => _filter = s.first),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _buildBody(cs),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(ColorScheme cs) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return NeptunErrorState(
        message: 'Помилка завантаження',
        detail: _error,
        onRetry: _loadReports,
      );
    }

    final filtered = _filter == 'ALL'
        ? _reports
        : _reports.where((r) => r.status == 'PENDING').toList();

    if (filtered.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.inbox_rounded, size: 56, color: cs.onSurface.withValues(alpha: 0.3)),
              const SizedBox(height: 16),
              Text(
                'Немає скарг',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadReports,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: filtered.length,
        itemBuilder: (context, i) {
          final r = filtered[i];
          return KeyedSubtree(
            key: ValueKey('report_${r.id}'),
            child: _ReportCard(
              report: r,
              formatTime: _formatTime,
              isPlayingVoice:
                  _playingVoiceMessageId == r.messageId && _isPlayingVoice,
              onPlayVoice: r.hasVoice
                  ? () => _toggleVoicePlayback(r.messageId, r.audioUrl!)
                  : null,
              onDelete: () async {
              final confirmed = await NeptunShellModal.showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Підтвердження'),
                  content: const Text(
                    'Видалити повідомлення та закрити скаргу?',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text('Скасувати'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      child: const Text('Видалити'),
                    ),
                  ],
                ),
              );
              if (confirmed == true) _deleteAndResolve(r);
            },
            onReject: () => _rejectReport(r),
            onBlock: () async {
              final confirmed = await NeptunShellModal.showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Заблокувати'),
                  content: Text(
                    'Заблокувати ${r.reportedNickname.isNotEmpty ? r.reportedNickname : "користувача"}? Він не зможе писати в чат.',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text('Скасувати'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      style: FilledButton.styleFrom(
                        backgroundColor: cs.error,
                        foregroundColor: cs.onError,
                      ),
                      child: const Text('Заблокувати'),
                    ),
                  ],
                ),
              );
              if (confirmed == true) _blockUser(r);
            },
            onDeleteAll: () async {
              final confirmed = await NeptunShellModal.showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Видалити всі повідомлення'),
                  content: Text(
                    'Видалити всі повідомлення від ${r.reportedNickname.isNotEmpty ? r.reportedNickname : "цього користувача"}?',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text('Скасувати'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      style: FilledButton.styleFrom(
                        backgroundColor: cs.error,
                        foregroundColor: cs.onError,
                      ),
                      child: const Text('Видалити всі'),
                    ),
                  ],
                ),
              );
              if (confirmed == true) _deleteAllMessagesFromUser(r);
            },
            cs: cs,
            ),
          );
        },
      ),
    );
  }
}

class _ChatReport {
  final String id;
  final String messageId;
  final String reason;
  final String reporterNickname;
  final String reportedNickname;
  final String reportedDeviceId;
  final String originalText;
  final String status;
  final String createdAt;
  final String? imageUrl;
  final String? audioUrl;
  final String messageType;
  final int? audioDuration;

  _ChatReport({
    required this.id,
    required this.messageId,
    required this.reason,
    required this.reporterNickname,
    required this.reportedNickname,
    required this.reportedDeviceId,
    required this.originalText,
    required this.status,
    required this.createdAt,
    this.imageUrl,
    this.audioUrl,
    this.messageType = 'text',
    this.audioDuration,
  });

  bool get hasImage => imageUrl != null && imageUrl!.isNotEmpty;
  bool get hasVoice => audioUrl != null && audioUrl!.isNotEmpty;

  static _ChatReport fromJson(Map<String, dynamic> json) {
    final dur = json['audioDuration'];
    return _ChatReport(
      id: json['id']?.toString() ?? '',
      messageId: json['messageId']?.toString() ?? '',
      reason: json['reason']?.toString() ?? '',
      reporterNickname: json['reporterNickname']?.toString() ?? 'Анонім',
      reportedNickname: json['reportedNickname']?.toString() ?? 'Анонім',
      reportedDeviceId: json['reportedDeviceId']?.toString() ?? '',
      originalText: json['originalText']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      createdAt: json['createdAt']?.toString() ?? '',
      imageUrl: json['imageUrl']?.toString(),
      audioUrl: json['audioUrl']?.toString(),
      messageType: json['messageType']?.toString() ?? 'text',
      audioDuration: dur is int ? dur : dur is String ? int.tryParse(dur) : null,
    );
  }
}

class _ReportCard extends StatelessWidget {
  final _ChatReport report;
  final String Function(String?) formatTime;
  final VoidCallback onDelete;
  final VoidCallback onReject;
  final VoidCallback? onBlock;
  final VoidCallback? onDeleteAll;
  final VoidCallback? onPlayVoice;
  final bool isPlayingVoice;
  final ColorScheme cs;

  const _ReportCard({
    required this.report,
    required this.formatTime,
    required this.onDelete,
    required this.onReject,
    this.onBlock,
    this.onDeleteAll,
    this.onPlayVoice,
    this.isPlayingVoice = false,
    required this.cs,
  });

  bool get _hasValidUserData {
    final hasNickname = report.reportedNickname.isNotEmpty &&
        report.reportedNickname.toLowerCase() != 'анонім';
    final hasDeviceId = report.reportedDeviceId.isNotEmpty;
    return hasNickname || hasDeviceId;
  }

  Widget _buildReportImage(BuildContext context, String url) {
    final fullUrl = url.startsWith('http') ? url : '${ApiConfig.baseUrl}$url';
    return GestureDetector(
      onTap: () => _showFullScreenImage(context, fullUrl),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: CachedNetworkImage(
          imageUrl: fullUrl,
          fit: BoxFit.cover,
          maxWidthDiskCache: 400,
          maxHeightDiskCache: 400,
          placeholder: (_, _) => Container(
            width: double.infinity,
            height: 160,
            color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
            child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
          ),
          errorWidget: (_, _, _) => Container(
            width: double.infinity,
            height: 120,
            color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
            child: Icon(Icons.broken_image_rounded, color: cs.onSurfaceVariant),
          ),
        ),
      ),
    );
  }

  void _showFullScreenImage(BuildContext context, String url) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            iconTheme: const IconThemeData(color: Colors.white),
          ),
          body: Center(
            child: InteractiveViewer(
              minScale: 0.5,
              maxScale: 4,
              child: CachedNetworkImage(imageUrl: url, fit: BoxFit.contain),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildReportVoice(_ChatReport r) {
    final duration = r.audioDuration ?? 0;
    final m = duration ~/ 60;
    final s = duration % 60;
    final durationText = '$m:${s.toString().padLeft(2, '0')}';
    return GestureDetector(
      onTap: onPlayVoice != null ? () => onPlayVoice!() : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: cs.primary.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(
                isPlayingVoice ? Icons.pause_rounded : Icons.play_arrow_rounded,
                color: cs.primary,
                size: 24,
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Голосове повідомлення',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: cs.onSurface,
                  ),
                ),
                Text(
                  durationText,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    color: cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isPending = report.status == 'PENDING';

    return NeptunCard(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: report.status == 'PENDING'
                      ? cs.tertiary.withValues(alpha: 0.2)
                      : report.status == 'RESOLVED'
                          ? cs.secondary.withValues(alpha: 0.2)
                          : cs.outline.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  report.status,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: report.status == 'PENDING' ? cs.tertiary : cs.onSurface.withValues(alpha: 0.7),
                  ),
                ),
              ),
              Text(
                formatTime(report.createdAt),
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  color: cs.onSurface.withValues(alpha: 0.4),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Причина: ${report.reason}',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: cs.onSurface.withValues(alpha: 0.8),
            ),
          ),
          const SizedBox(height: 6),
          if (report.hasImage) _buildReportImage(context, report.imageUrl!),
          if (report.hasImage) const SizedBox(height: 6),
          if (report.hasVoice) _buildReportVoice(report),
          if (report.hasVoice) const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              report.originalText.isEmpty
                  ? (report.hasImage || report.hasVoice ? '(медіа)' : '<без тексту>')
                  : report.originalText,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 14,
                color: cs.onSurface,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Скаржник: ${report.reporterNickname}',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  color: cs.primary,
                ),
              ),
              if (report.reportedNickname.isNotEmpty) ...[
                const SizedBox(width: 16),
                Text(
                  'Автор: ${report.reportedNickname}',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    color: cs.error,
                  ),
                ),
              ],
            ],
          ),
          if (isPending) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: onDelete,
                    icon: const Icon(Icons.delete_forever_rounded, size: 18),
                    label: const Text('Видалити'),
                    style: FilledButton.styleFrom(
                      backgroundColor: cs.error,
                      foregroundColor: cs.onError,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onReject,
                    icon: const Icon(Icons.close_rounded, size: 18),
                    label: const Text('Відхилити'),
                  ),
                ),
              ],
            ),
            if ((onBlock != null || onDeleteAll != null) && _hasValidUserData) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  if (onBlock != null)
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onBlock,
                        icon: const Icon(Icons.block_rounded, size: 18),
                        label: const Text('Заблокувати'),
                      ),
                    ),
                  if (onBlock != null && onDeleteAll != null) const SizedBox(width: 12),
                  if (onDeleteAll != null)
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onDeleteAll,
                        icon: const Icon(Icons.delete_sweep_rounded, size: 18),
                        label: const Text('Видалити всі'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: cs.error,
                          side: BorderSide(color: cs.error.withValues(alpha: 0.7)),
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }
}
