/// Централізована конфігурація API
class ApiConfig {
  ApiConfig._();

  /// Базовий URL API (compile-time: --dart-define=API_BASE_URL=https://...)
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://neptun.in.ua',
  );

  /// API endpoints
  static const String alarmsEndpoint = '/api/alarms';
  static const String alarmsFullEndpoint = '/api/alarms/full';
  static const String alarmsAllEndpoint = '/api/alarms/all';
  static const String alarmStatusEndpoint = '/api/alarm-status';
  static const String messagesEndpoint = '/api/messages';
  static const String chatMessagesEndpoint = '/api/chat/messages';
  static const String chatSendEndpoint = '/api/chat/send';
  static const String chatUnbanEndpoint = '/api/chat/unban';
  static const String chatStreamEndpoint = '/api/chat/stream';
  static const String chatTypingEndpoint = '/api/chat/typing';
  static const String chatReactEndpoint = '/api/chat/react';
  static const String chatCheckBanEndpoint = '/api/chat/check-ban';
  static const String chatCheckNicknameEndpoint = '/api/chat/check-nickname';
  static const String chatRegisterNicknameEndpoint =
      '/api/chat/register-nickname';
  static const String chatBanUserEndpoint = '/api/chat/ban-user';
  static const String chatBanListEndpoint = '/api/chat/ban-list';
  static const String chatAddModeratorEndpoint = '/api/chat/add-moderator';
  static const String chatRemoveModeratorEndpoint =
      '/api/chat/remove-moderator';
  static const String chatUploadAudioEndpoint = '/api/chat/upload-audio';
  static const String chatUploadImageEndpoint = '/api/chat/upload-image';
  static const String chatReportEndpoint = '/api/chat/report';
  static const String dataEndpoint = '/data';
  static const String registerEndpoint = '/api/register-device';
  static const String testNotificationEndpoint = '/api/test-notification';
  static const String threatsEndpoint = '/api/threats';
  static const String feedbackEndpoint = '/api/feedback';
  static const String verifyPurchaseEndpoint = '/api/verify-purchase';
  static const String premiumEntitlementEndpoint = '/api/premium/entitlement';
  static const String authTokenEndpoint = '/api/auth/token';
  static const String authRefreshEndpoint = '/api/auth/refresh';
  static const String authRevokeEndpoint = '/api/auth/revoke';
  /// Мінімальна версія нативного клієнта (JSON з сервера).
  static const String appRequirementsEndpoint = '/api/app-requirements';
  static const String presenceEndpoint = '/api/presence';
  static const String adminMarkersDeleteEndpoint = '/api/admin/markers/delete';
  static const String adminHiddenHideEndpoint = '/api/admin/hidden/hide';
  static const String adminChatReportsEndpoint = '/api/admin/chat/reports';
  static const String adminChatReportsResolveEndpoint =
      '/api/admin/chat/reports/resolve';
  static const String adminChatBanUserEndpoint = '/api/admin/chat/ban-user';
  static const String adminChatBanListEndpoint = '/api/admin/chat/ban-list';
  static const String adminChatUnbanEndpoint = '/api/admin/chat/unban';
  static const String adminChatDeleteUserMessagesEndpoint =
      '/api/admin/chat/delete-user-messages';

  /// Повні URLs
  static String get alarms => '$baseUrl$alarmsEndpoint';
  static String get alarmsFull => '$baseUrl$alarmsFullEndpoint';
  static String get alarmsAll => '$baseUrl$alarmsAllEndpoint';
  static String get alarmStatus => '$baseUrl$alarmStatusEndpoint';
  static String get messages => '$baseUrl$messagesEndpoint';
  static String get chatMessages => '$baseUrl$chatMessagesEndpoint';
  static String get chatSend => '$baseUrl$chatSendEndpoint';
  static String get chatUnban => '$baseUrl$chatUnbanEndpoint';
  static String get chatStream => '$baseUrl$chatStreamEndpoint';
  static String get chatTyping => '$baseUrl$chatTypingEndpoint';
  static String get chatReact => '$baseUrl$chatReactEndpoint';
  static String get chatCheckBan => '$baseUrl$chatCheckBanEndpoint';
  static String get chatCheckNickname => '$baseUrl$chatCheckNicknameEndpoint';
  static String get chatRegisterNickname =>
      '$baseUrl$chatRegisterNicknameEndpoint';
  static String get chatBanUser => '$baseUrl$chatBanUserEndpoint';
  static String get chatBanList => '$baseUrl$chatBanListEndpoint';
  static String get chatAddModerator => '$baseUrl$chatAddModeratorEndpoint';
  static String get chatRemoveModerator =>
      '$baseUrl$chatRemoveModeratorEndpoint';
  static String get chatUploadAudio => '$baseUrl$chatUploadAudioEndpoint';
  static String get chatUploadImage => '$baseUrl$chatUploadImageEndpoint';
  static String get chatReport => '$baseUrl$chatReportEndpoint';
  static String get data => '$baseUrl$dataEndpoint';
  static String get register => '$baseUrl$registerEndpoint';
  static String get testNotification => '$baseUrl$testNotificationEndpoint';
  static String get threats => '$baseUrl$threatsEndpoint';
  static String get feedback => '$baseUrl$feedbackEndpoint';
  static String get verifyPurchase => '$baseUrl$verifyPurchaseEndpoint';
  static String get premiumEntitlement => '$baseUrl$premiumEntitlementEndpoint';
  static String get authToken => '$baseUrl$authTokenEndpoint';
  static String get authRefresh => '$baseUrl$authRefreshEndpoint';
  static String get authRevoke => '$baseUrl$authRevokeEndpoint';
  static String get appRequirements => '$baseUrl$appRequirementsEndpoint';
  static String get presence => '$baseUrl$presenceEndpoint';
  static String get adminMarkersDelete => '$baseUrl$adminMarkersDeleteEndpoint';
  static String get adminHiddenHide => '$baseUrl$adminHiddenHideEndpoint';
  static String get adminChatReports => '$baseUrl$adminChatReportsEndpoint';
  static String get adminChatReportsResolve =>
      '$baseUrl$adminChatReportsResolveEndpoint';
  static String get adminChatBanUser => '$baseUrl$adminChatBanUserEndpoint';
  static String get adminChatBanList => '$baseUrl$adminChatBanListEndpoint';
  static String get adminChatUnban => '$baseUrl$adminChatUnbanEndpoint';
  static String get adminChatDeleteUserMessages =>
      '$baseUrl$adminChatDeleteUserMessagesEndpoint';

  /// Chat message by ID (for DELETE)
  static String chatMessageById(String id) => '$baseUrl/api/chat/message/$id';

  /// API often returns relative paths (e.g. `/data/images/...`). HTTP clients
  /// and [CachedNetworkImage] require a full URI with scheme and host.
  static String resolveAbsoluteUrl(String url) {
    final t = url.trim();
    if (t.isEmpty) return t;
    if (t.startsWith('https://') || t.startsWith('http://')) return t;
    if (t.startsWith('/')) return '$baseUrl$t';
    return '$baseUrl/$t';
  }

  /// Timeout для HTTP запитів
  static const Duration httpTimeout = Duration(seconds: 15);
  static const Duration longHttpTimeout = Duration(seconds: 30);
  /// Короткий timeout для політики мінімальної версії (не блокувати cold start надто довго).
  static const Duration appRequirementsHttpTimeout = Duration(seconds: 8);
}
