import 'package:get_it/get_it.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../services/notification_service.dart';
import '../../services/chat_service.dart';
import '../../services/ad_service.dart';
import '../../services/purchase_service.dart';
import '../../services/tts_service.dart';
import '../../services/review_service.dart';
import '../../services/alarm_tracking_service.dart';
import '../../services/data_stream_service.dart';
import '../../services/presence_service.dart';
import '../../services/pro_customization_service.dart';
import '../../services/moderator_service.dart';
import '../../services/widget_service.dart';
import '../../services/ballistic_alert_service.dart';
import '../../services/map_data_service.dart';
import '../../services/chat_moderation_service.dart';
import '../../services/sleep_mode_service.dart';
import '../../services/notification_filter_service.dart';
import '../network/api_client.dart';
import '../network/sse_client.dart';

final sl = GetIt.instance;

Future<void> initServiceLocator() async {
  // Async singletons
  final prefs = await SharedPreferences.getInstance();
  sl.registerSingleton<SharedPreferences>(prefs);

  // Network
  sl.registerLazySingleton<ApiClient>(() => ApiClient());
  sl.registerLazySingleton<SSEClient>(() => SSEClient());

  // Services (re-register existing singletons for DI access)
  sl.registerLazySingleton<DataStreamService>(
    () => DataStreamService.instance,
  );
  sl.registerLazySingleton<PresenceService>(() => PresenceService.instance);
  sl.registerLazySingleton<ProCustomizationService>(
    () => ProCustomizationService(),
  );
  sl.registerLazySingleton<ChatService>(() => ChatService.instance);
  sl.registerLazySingleton<ModeratorService>(() => ModeratorService.instance);
  sl.registerLazySingleton<PurchaseService>(() => PurchaseService());
  sl.registerLazySingleton<AdService>(() => AdService());
  sl.registerLazySingleton<NotificationService>(() => NotificationService());
  sl.registerLazySingleton<TtsService>(() => TtsService());
  sl.registerLazySingleton<ReviewService>(() => ReviewService());
  sl.registerLazySingleton<AlarmTrackingService>(() => AlarmTrackingService());
  sl.registerLazySingleton<WidgetService>(() => WidgetService());
  sl.registerLazySingleton<BallisticAlertService>(
    () => BallisticAlertService(),
  );
  sl.registerLazySingleton<MapDataService>(() => MapDataService());
  sl.registerLazySingleton<ChatModerationService>(
    () => ChatModerationService.instance,
  );
  sl.registerLazySingleton<SleepModeService>(() => SleepModeService());
  sl.registerLazySingleton<NotificationFilterService>(
    () => NotificationFilterService(),
  );
}
