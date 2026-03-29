import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/models/notification_event.dart';
import 'package:neptun_alarm_app/models/user_region_selection.dart';
import 'package:neptun_alarm_app/services/notification_filter_service.dart';
import 'package:neptun_alarm_app/services/region_database.dart';

void main() {
  late RegionDatabase db;
  late NotificationFilterService filterService;

  setUp(() {
    db = RegionDatabase();
    db.initialize();
    filterService = NotificationFilterService();
  });

  group('RegionDatabase', () {
    test('should have all oblasts loaded', () {
      final oblasts = db.getAllOblasts();
      expect(oblasts.length, 27); // 24 області + Київ + Крим + Севастополь
    });

    test('Дніпропетровська область should have 7 raions', () {
      final raions = db.getRaionIdsForOblast('UA-12');
      expect(raions.length, 7);
    });

    test('Синельниківський район should belong to Дніпропетровська область', () {
      final oblastId = db.getOblastIdForRaion('UA-12-06');
      expect(oblastId, 'UA-12');
    });

    test('Нікопольський район should belong to Дніпропетровська область', () {
      final oblastId = db.getOblastIdForRaion('UA-12-04');
      expect(oblastId, 'UA-12');
    });

    test('Синельниківський район ID should NOT equal Нікопольський район ID', () {
      const synelnykyvskyiId = 'UA-12-06';
      const nikopolskyiId = 'UA-12-04';
      expect(synelnykyvskyiId, isNot(equals(nikopolskyiId)));
    });
  });

  group('NotificationFilterService - Синельниківський район tests', () {
    const synelnykyvskyiRaionId = 'UA-12-06';
    const nikopolskyiRaionId = 'UA-12-04';
    const dnipropetrovskaOblastId = 'UA-12';

    test('КРИТИЧНИЙ: Синельниківський район НЕ повинен отримувати Марганець (Нікопольський район)', () {
      // Користувач обрав Синельниківський район
      final userSelection = UserRegionSelection(
        raionIds: {synelnykyvskyiRaionId},
      );

      // Подія з Марганця (Нікопольський район)
      final event = NotificationEvent(
        oblastId: dnipropetrovskaOblastId,
        raionId: nikopolskyiRaionId, // Нікопольський, НЕ Синельниківський
        title: 'Тривога: Марганець',
        body: 'БПЛА',
        timestamp: DateTime.now(),
      );

      final shouldShow = filterService.shouldShowNotification(event, userSelection);
      
      // MUST BE FALSE!
      expect(shouldShow, false, 
        reason: 'Синельниківський район НЕ повинен отримувати повідомлення з Нікопольського району');
    });

    test('КРИТИЧНИЙ: Синельниківський район НЕ повинен отримувати Нікополь', () {
      final userSelection = UserRegionSelection(
        raionIds: {synelnykyvskyiRaionId},
      );

      final event = NotificationEvent(
        oblastId: dnipropetrovskaOblastId,
        raionId: nikopolskyiRaionId,
        title: 'Тривога: Нікополь',
        body: 'Ракетна небезпека',
        timestamp: DateTime.now(),
      );

      final shouldShow = filterService.shouldShowNotification(event, userSelection);
      expect(shouldShow, false,
        reason: 'Синельниківський район НЕ повинен отримувати повідомлення з Нікополя');
    });

    test('Синельниківський район ПОВИНЕН отримувати події з Синельникового', () {
      final userSelection = UserRegionSelection(
        raionIds: {synelnykyvskyiRaionId},
      );

      final event = NotificationEvent(
        oblastId: dnipropetrovskaOblastId,
        raionId: synelnykyvskyiRaionId, // Той самий район
        title: 'Тривога: Синельникове',
        body: 'БПЛА',
        timestamp: DateTime.now(),
      );

      final shouldShow = filterService.shouldShowNotification(event, userSelection);
      expect(shouldShow, true);
    });

    test('Подія без raionId НЕ повинна показуватись якщо обрано конкретний район', () {
      final userSelection = UserRegionSelection(
        raionIds: {synelnykyvskyiRaionId},
      );

      // Подія тільки з oblastId (загальна для області)
      final event = NotificationEvent(
        oblastId: dnipropetrovskaOblastId,
        raionId: null, // Немає конкретного району
        title: 'Тривога: Дніпропетровська область',
        body: 'Повітряна тривога',
        timestamp: DateTime.now(),
      );

      final shouldShow = filterService.shouldShowNotification(event, userSelection);
      expect(shouldShow, false,
        reason: 'Без raionId не можемо визначити чи це наш район');
    });

    test('Якщо обрана вся область - показувати всі події з неї', () {
      final userSelection = UserRegionSelection(
        oblastIds: {dnipropetrovskaOblastId},
      );

      // Подія з Нікополя
      final event = NotificationEvent(
        oblastId: dnipropetrovskaOblastId,
        raionId: nikopolskyiRaionId,
        title: 'Тривога: Нікополь',
        body: 'Ракетна небезпека',
        timestamp: DateTime.now(),
      );

      final shouldShow = filterService.shouldShowNotification(event, userSelection);
      expect(shouldShow, true,
        reason: 'Обрана вся область - показувати всі події');
    });
  });

  group('NotificationFilterService - edge cases', () {
    test('Порожній вибір користувача - НЕ показувати', () {
      const userSelection = UserRegionSelection();

      final event = NotificationEvent(
        oblastId: 'UA-12',
        title: 'Test',
        body: 'Test',
        timestamp: DateTime.now(),
      );

      expect(filterService.shouldShowNotification(event, userSelection), false);
    });

    test('Подія без oblastId - НЕ показувати', () {
      final userSelection = UserRegionSelection(
        oblastIds: {'UA-12'},
      );

      final event = NotificationEvent(
        oblastId: null, // Невалідна подія
        title: 'Test',
        body: 'Test',
        timestamp: DateTime.now(),
      );

      expect(filterService.shouldShowNotification(event, userSelection), false);
    });

    test('Подія з іншої області - НЕ показувати', () {
      final userSelection = UserRegionSelection(
        oblastIds: {'UA-12'}, // Дніпропетровська
      );

      final event = NotificationEvent(
        oblastId: 'UA-63', // Харківська
        title: 'Test',
        body: 'Test',
        timestamp: DateTime.now(),
      );

      expect(filterService.shouldShowNotification(event, userSelection), false);
    });
  });

  group('ID-based matching - NO string operations', () {
    test('Фільтрація працює ТІЛЬКИ по ID, не по назвах', () {
      // Цей тест перевіряє що ми НЕ використовуємо string matching
      
      final userSelection = UserRegionSelection(
        raionIds: {'UA-12-06'}, // Синельниківський за ID
      );

      // Подія з правильним ID але неправильною назвою
      final eventCorrectId = NotificationEvent(
        oblastId: 'UA-12',
        raionId: 'UA-12-06', // Правильний ID
        title: 'Тривога: НЕПРАВИЛЬНА_НАЗВА',
        body: 'Текст з Марганець Нікополь', // Слова з інших районів
        timestamp: DateTime.now(),
      );

      // Повинно показати бо ID співпадає
      expect(filterService.shouldShowNotification(eventCorrectId, userSelection), true);

      // Подія з неправильним ID але правильною назвою
      final eventWrongId = NotificationEvent(
        oblastId: 'UA-12',
        raionId: 'UA-12-04', // Нікопольський ID
        title: 'Тривога: Синельникове', // Назва Синельникового
        body: 'Синельниківський район',
        timestamp: DateTime.now(),
      );

      // НЕ повинно показати бо ID не співпадає
      expect(filterService.shouldShowNotification(eventWrongId, userSelection), false);
    });
  });
}
