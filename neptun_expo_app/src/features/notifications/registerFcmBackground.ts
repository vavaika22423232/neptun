import { fcmMessagingService } from './services/fcmMessagingService';
import { fcmTopicService } from './services/fcmTopicService';

/** Must run before `expo-router/entry` (Flutter `main()` background registration). */
export function registerFcmBackgroundHandler(): void {
  fcmTopicService.configureBackgroundHandler((message) =>
    fcmMessagingService.handleBackgroundMessage(message),
  );
}
