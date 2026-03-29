import '../models/region_node.dart';

/// База даних регіонів України
/// Ієрархія: область → район → населений пункт
/// Всі ID стабільні та незмінні
class RegionDatabase {
  static final RegionDatabase _instance = RegionDatabase._internal();
  factory RegionDatabase() => _instance;
  RegionDatabase._internal();

  /// Всі регіони по ID
  final Map<String, RegionNode> _regionsById = {};
  
  /// Райони для кожної області: `oblastId` → `Set<raionId>`
  final Map<String, Set<String>> _raionsByOblast = {};
  
  /// Oblast ID по назві (для міграції зі старого формату)
  final Map<String, String> _oblastIdByName = {};
  
  /// Raion ID по назві (для міграції)
  final Map<String, String> _raionIdByName = {};

  bool _isInitialized = false;
  bool get isInitialized => _isInitialized;

  /// Ініціалізація бази
  void initialize() {
    if (_isInitialized) return;
    
    _loadOblasts();
    _loadRaions();
    _buildIndexes();
    
    _isInitialized = true;
  }

  void _loadOblasts() {
    const oblasts = [
      RegionNode(id: 'UA-05', type: RegionType.oblast, nameUk: 'Вінницька область'),
      RegionNode(id: 'UA-07', type: RegionType.oblast, nameUk: 'Волинська область'),
      RegionNode(id: 'UA-12', type: RegionType.oblast, nameUk: 'Дніпропетровська область'),
      RegionNode(id: 'UA-14', type: RegionType.oblast, nameUk: 'Донецька область'),
      RegionNode(id: 'UA-18', type: RegionType.oblast, nameUk: 'Житомирська область'),
      RegionNode(id: 'UA-21', type: RegionType.oblast, nameUk: 'Закарпатська область'),
      RegionNode(id: 'UA-23', type: RegionType.oblast, nameUk: 'Запорізька область'),
      RegionNode(id: 'UA-26', type: RegionType.oblast, nameUk: 'Івано-Франківська область'),
      RegionNode(id: 'UA-32', type: RegionType.oblast, nameUk: 'Київська область'),
      RegionNode(id: 'UA-35', type: RegionType.oblast, nameUk: 'Кіровоградська область'),
      RegionNode(id: 'UA-44', type: RegionType.oblast, nameUk: 'Луганська область'),
      RegionNode(id: 'UA-46', type: RegionType.oblast, nameUk: 'Львівська область'),
      RegionNode(id: 'UA-48', type: RegionType.oblast, nameUk: 'Миколаївська область'),
      RegionNode(id: 'UA-51', type: RegionType.oblast, nameUk: 'Одеська область'),
      RegionNode(id: 'UA-53', type: RegionType.oblast, nameUk: 'Полтавська область'),
      RegionNode(id: 'UA-56', type: RegionType.oblast, nameUk: 'Рівненська область'),
      RegionNode(id: 'UA-59', type: RegionType.oblast, nameUk: 'Сумська область'),
      RegionNode(id: 'UA-61', type: RegionType.oblast, nameUk: 'Тернопільська область'),
      RegionNode(id: 'UA-63', type: RegionType.oblast, nameUk: 'Харківська область'),
      RegionNode(id: 'UA-65', type: RegionType.oblast, nameUk: 'Херсонська область'),
      RegionNode(id: 'UA-68', type: RegionType.oblast, nameUk: 'Хмельницька область'),
      RegionNode(id: 'UA-71', type: RegionType.oblast, nameUk: 'Черкаська область'),
      RegionNode(id: 'UA-77', type: RegionType.oblast, nameUk: 'Чернівецька область'),
      RegionNode(id: 'UA-74', type: RegionType.oblast, nameUk: 'Чернігівська область'),
      RegionNode(id: 'UA-30', type: RegionType.oblast, nameUk: 'м. Київ'),
      RegionNode(id: 'UA-43', type: RegionType.oblast, nameUk: 'АР Крим'),
      RegionNode(id: 'UA-40', type: RegionType.oblast, nameUk: 'м. Севастополь'),
    ];
    
    for (final oblast in oblasts) {
      _regionsById[oblast.id] = oblast;
    }
  }

  void _loadRaions() {
    // Дніпропетровська область (UA-12)
    _addRaion('UA-12-01', 'Дніпровський район', 'UA-12');
    _addRaion('UA-12-02', 'Криворізький район', 'UA-12');
    _addRaion('UA-12-03', 'Кам\'янський район', 'UA-12');
    _addRaion('UA-12-04', 'Нікопольський район', 'UA-12');
    _addRaion('UA-12-05', 'Павлоградський район', 'UA-12');
    _addRaion('UA-12-06', 'Синельниківський район', 'UA-12');
    _addRaion('UA-12-07', 'Новомосковський район', 'UA-12');
    
    // Харківська область (UA-63)
    _addRaion('UA-63-01', 'Харківський район', 'UA-63');
    _addRaion('UA-63-02', 'Куп\'янський район', 'UA-63');
    _addRaion('UA-63-03', 'Ізюмський район', 'UA-63');
    _addRaion('UA-63-04', 'Чугуївський район', 'UA-63');
    _addRaion('UA-63-05', 'Богодухівський район', 'UA-63');
    _addRaion('UA-63-06', 'Красноградський район', 'UA-63');
    _addRaion('UA-63-07', 'Лозівський район', 'UA-63');
    
    // Запорізька область (UA-23)
    _addRaion('UA-23-01', 'Запорізький район', 'UA-23');
    _addRaion('UA-23-02', 'Мелітопольський район', 'UA-23');
    _addRaion('UA-23-03', 'Бердянський район', 'UA-23');
    _addRaion('UA-23-04', 'Пологівський район', 'UA-23');
    _addRaion('UA-23-05', 'Василівський район', 'UA-23');
    
    // Херсонська область (UA-65)
    _addRaion('UA-65-01', 'Херсонський район', 'UA-65');
    _addRaion('UA-65-02', 'Бериславський район', 'UA-65');
    _addRaion('UA-65-03', 'Генічеський район', 'UA-65');
    _addRaion('UA-65-04', 'Каховський район', 'UA-65');
    _addRaion('UA-65-05', 'Скадовський район', 'UA-65');
    
    // Київська область (UA-32)
    _addRaion('UA-32-01', 'Білоцерківський район', 'UA-32');
    _addRaion('UA-32-02', 'Бориспільський район', 'UA-32');
    _addRaion('UA-32-03', 'Броварський район', 'UA-32');
    _addRaion('UA-32-04', 'Бучанський район', 'UA-32');
    _addRaion('UA-32-05', 'Вишгородський район', 'UA-32');
    _addRaion('UA-32-06', 'Обухівський район', 'UA-32');
    _addRaion('UA-32-07', 'Фастівський район', 'UA-32');
    
    // Одеська область (UA-51)
    _addRaion('UA-51-01', 'Одеський район', 'UA-51');
    _addRaion('UA-51-02', 'Білгород-Дністровський район', 'UA-51');
    _addRaion('UA-51-03', 'Болградський район', 'UA-51');
    _addRaion('UA-51-04', 'Ізмаїльський район', 'UA-51');
    _addRaion('UA-51-05', 'Подільський район', 'UA-51');
    _addRaion('UA-51-06', 'Березівський район', 'UA-51');
    _addRaion('UA-51-07', 'Роздільнянський район', 'UA-51');
    
    // Миколаївська область (UA-48)
    _addRaion('UA-48-01', 'Миколаївський район', 'UA-48');
    _addRaion('UA-48-02', 'Баштанський район', 'UA-48');
    _addRaion('UA-48-03', 'Вознесенський район', 'UA-48');
    _addRaion('UA-48-04', 'Первомайський район', 'UA-48');
    
    // Сумська область (UA-59)
    _addRaion('UA-59-01', 'Сумський район', 'UA-59');
    _addRaion('UA-59-02', 'Конотопський район', 'UA-59');
    _addRaion('UA-59-03', 'Шосткинський район', 'UA-59');
    _addRaion('UA-59-04', 'Охтирський район', 'UA-59');
    _addRaion('UA-59-05', 'Роменський район', 'UA-59');
    
    // Донецька область (UA-14)
    _addRaion('UA-14-01', 'Краматорський район', 'UA-14');
    _addRaion('UA-14-02', 'Бахмутський район', 'UA-14');
    _addRaion('UA-14-03', 'Покровський район', 'UA-14');
    _addRaion('UA-14-04', 'Волноваський район', 'UA-14');
    _addRaion('UA-14-05', 'Кальміуський район', 'UA-14');
    _addRaion('UA-14-06', 'Маріупольський район', 'UA-14');
    _addRaion('UA-14-07', 'Донецький район', 'UA-14');
    _addRaion('UA-14-08', 'Горлівський район', 'UA-14');
    
    // Луганська область (UA-44)
    _addRaion('UA-44-01', 'Луганський район', 'UA-44');
    _addRaion('UA-44-02', 'Сєвєродонецький район', 'UA-44');
    _addRaion('UA-44-03', 'Алчевський район', 'UA-44');
    _addRaion('UA-44-04', 'Довжанський район', 'UA-44');
    _addRaion('UA-44-05', 'Ровеньківський район', 'UA-44');
    _addRaion('UA-44-06', 'Щастинський район', 'UA-44');
    _addRaion('UA-44-07', 'Старобільський район', 'UA-44');
    _addRaion('UA-44-08', 'Сватівський район', 'UA-44');
    
    // Полтавська область (UA-53)
    _addRaion('UA-53-01', 'Полтавський район', 'UA-53');
    _addRaion('UA-53-02', 'Кременчуцький район', 'UA-53');
    _addRaion('UA-53-03', 'Лубенський район', 'UA-53');
    _addRaion('UA-53-04', 'Миргородський район', 'UA-53');
    
    // Чернігівська область (UA-74)
    _addRaion('UA-74-01', 'Чернігівський район', 'UA-74');
    _addRaion('UA-74-02', 'Новгород-Сіверський район', 'UA-74');
    _addRaion('UA-74-03', 'Ніжинський район', 'UA-74');
    _addRaion('UA-74-04', 'Прилуцький район', 'UA-74');
    _addRaion('UA-74-05', 'Корюківський район', 'UA-74');
    
    // Черкаська область (UA-71)
    _addRaion('UA-71-01', 'Черкаський район', 'UA-71');
    _addRaion('UA-71-02', 'Золотоніський район', 'UA-71');
    _addRaion('UA-71-03', 'Уманський район', 'UA-71');
    _addRaion('UA-71-04', 'Звенигородський район', 'UA-71');
    
    // Кіровоградська область (UA-35)
    _addRaion('UA-35-01', 'Кропивницький район', 'UA-35');
    _addRaion('UA-35-02', 'Олександрійський район', 'UA-35');
    _addRaion('UA-35-03', 'Голованівський район', 'UA-35');
    _addRaion('UA-35-04', 'Новоукраїнський район', 'UA-35');
    
    // Вінницька область (UA-05)
    _addRaion('UA-05-01', 'Вінницький район', 'UA-05');
    _addRaion('UA-05-02', 'Гайсинський район', 'UA-05');
    _addRaion('UA-05-03', 'Жмеринський район', 'UA-05');
    _addRaion('UA-05-04', 'Могилів-Подільський район', 'UA-05');
    _addRaion('UA-05-05', 'Тульчинський район', 'UA-05');
    _addRaion('UA-05-06', 'Хмільницький район', 'UA-05');
    
    // Житомирська область (UA-18)
    _addRaion('UA-18-01', 'Житомирський район', 'UA-18');
    _addRaion('UA-18-02', 'Бердичівський район', 'UA-18');
    _addRaion('UA-18-03', 'Коростенський район', 'UA-18');
    _addRaion('UA-18-04', 'Звягельський район', 'UA-18');
    
    // Рівненська область (UA-56)
    _addRaion('UA-56-01', 'Рівненський район', 'UA-56');
    _addRaion('UA-56-02', 'Дубенський район', 'UA-56');
    _addRaion('UA-56-03', 'Вараський район', 'UA-56');
    _addRaion('UA-56-04', 'Сарненський район', 'UA-56');
    
    // Волинська область (UA-07)
    _addRaion('UA-07-01', 'Луцький район', 'UA-07');
    _addRaion('UA-07-02', 'Володимирський район', 'UA-07');
    _addRaion('UA-07-03', 'Ковельський район', 'UA-07');
    _addRaion('UA-07-04', 'Камінь-Каширський район', 'UA-07');
    
    // Тернопільська область (UA-61)
    _addRaion('UA-61-01', 'Тернопільський район', 'UA-61');
    _addRaion('UA-61-02', 'Чортківський район', 'UA-61');
    _addRaion('UA-61-03', 'Кременецький район', 'UA-61');
    
    // Хмельницька область (UA-68)
    _addRaion('UA-68-01', 'Хмельницький район', 'UA-68');
    _addRaion('UA-68-02', 'Шепетівський район', 'UA-68');
    _addRaion('UA-68-03', 'Кам\'янець-Подільський район', 'UA-68');
    
    // Львівська область (UA-46)
    _addRaion('UA-46-01', 'Львівський район', 'UA-46');
    _addRaion('UA-46-02', 'Стрийський район', 'UA-46');
    _addRaion('UA-46-03', 'Самбірський район', 'UA-46');
    _addRaion('UA-46-04', 'Дрогобицький район', 'UA-46');
    _addRaion('UA-46-05', 'Червоноградський район', 'UA-46');
    _addRaion('UA-46-06', 'Яворівський район', 'UA-46');
    _addRaion('UA-46-07', 'Золочівський район', 'UA-46');
    
    // Івано-Франківська область (UA-26)
    _addRaion('UA-26-01', 'Івано-Франківський район', 'UA-26');
    _addRaion('UA-26-02', 'Калуський район', 'UA-26');
    _addRaion('UA-26-03', 'Коломийський район', 'UA-26');
    _addRaion('UA-26-04', 'Косівський район', 'UA-26');
    _addRaion('UA-26-05', 'Надвірнянський район', 'UA-26');
    _addRaion('UA-26-06', 'Верховинський район', 'UA-26');
    
    // Закарпатська область (UA-21)
    _addRaion('UA-21-01', 'Ужгородський район', 'UA-21');
    _addRaion('UA-21-02', 'Мукачівський район', 'UA-21');
    _addRaion('UA-21-03', 'Берегівський район', 'UA-21');
    _addRaion('UA-21-04', 'Хустський район', 'UA-21');
    _addRaion('UA-21-05', 'Рахівський район', 'UA-21');
    _addRaion('UA-21-06', 'Тячівський район', 'UA-21');
    
    // Чернівецька область (UA-77)
    _addRaion('UA-77-01', 'Чернівецький район', 'UA-77');
    _addRaion('UA-77-02', 'Вижницький район', 'UA-77');
    _addRaion('UA-77-03', 'Дністровський район', 'UA-77');
  }

  void _addRaion(String id, String name, String oblastId) {
    final raion = RegionNode(
      id: id,
      type: RegionType.raion,
      nameUk: name,
      parentId: oblastId,
    );
    _regionsById[id] = raion;
  }

  void _buildIndexes() {
    // Будуємо індекси по назві для міграції
    for (final region in _regionsById.values) {
      if (region.type == RegionType.oblast) {
        _oblastIdByName[region.nameUk] = region.id;
        // Також додаємо без "область"
        final shortName = region.nameUk.replaceAll(' область', '');
        _oblastIdByName[shortName] = region.id;
      } else if (region.type == RegionType.raion) {
        _raionIdByName[region.nameUk] = region.id;
        // Також зберігаємо зв'язок район → область
        final oblastId = region.parentId;
        if (oblastId != null) {
          _raionsByOblast.putIfAbsent(oblastId, () => {});
          _raionsByOblast[oblastId]!.add(region.id);
        }
      }
    }
    // Київ = м. Київ (НІКОЛИ Київська область!)
    _oblastIdByName['Київ'] = 'UA-30';
  }

  // === PUBLIC API ===

  /// Отримати регіон по ID
  RegionNode? getById(String id) => _regionsById[id];

  /// Отримати область по ID
  RegionNode? getOblastById(String id) {
    final region = _regionsById[id];
    return region?.type == RegionType.oblast ? region : null;
  }

  /// Отримати район по ID
  RegionNode? getRaionById(String id) {
    final region = _regionsById[id];
    return region?.type == RegionType.raion ? region : null;
  }

  /// Отримати всі райони області
  Set<String> getRaionIdsForOblast(String oblastId) {
    return _raionsByOblast[oblastId] ?? {};
  }

  /// Отримати ID області для району
  String? getOblastIdForRaion(String raionId) {
    return _regionsById[raionId]?.parentId;
  }

  /// Отримати всі області
  List<RegionNode> getAllOblasts() {
    return _regionsById.values
        .where((r) => r.type == RegionType.oblast)
        .toList()
      ..sort((a, b) => a.nameUk.compareTo(b.nameUk));
  }

  /// Отримати всі райони
  List<RegionNode> getAllRaions() {
    return _regionsById.values
        .where((r) => r.type == RegionType.raion)
        .toList()
      ..sort((a, b) => a.nameUk.compareTo(b.nameUk));
  }

  /// Отримати райони для області
  List<RegionNode> getRaionsForOblast(String oblastId) {
    final raionIds = _raionsByOblast[oblastId] ?? {};
    return raionIds
        .map((id) => _regionsById[id])
        .whereType<RegionNode>()
        .toList()
      ..sort((a, b) => a.nameUk.compareTo(b.nameUk));
  }

  // === MIGRATION HELPERS ===

  /// Отримати ID області по назві (для міграції зі старого формату)
  String? getOblastIdByName(String name) {
    // Прямий пошук
    if (_oblastIdByName.containsKey(name)) {
      return _oblastIdByName[name];
    }
    // Пошук без "область"
    final normalized = name.replaceAll(' область', '').trim();
    return _oblastIdByName[normalized];
  }

  /// Отримати ID району по назві (для міграції)
  String? getRaionIdByName(String name) {
    return _raionIdByName[name];
  }
  
  /// Перевірити чи raionId належить до oblastId
  bool isRaionInOblast(String raionId, String oblastId) {
    final raion = _regionsById[raionId];
    return raion?.parentId == oblastId;
  }

  /// Отримати регіон по ID
  RegionNode? getRegionById(String id) {
    return _regionsById[id];
  }

  /// Отримати назву регіону по ID
  String? getRegionNameById(String id) {
    return _regionsById[id]?.nameUk;
  }

  /// Отримати ID батьківської області для району
  String? getParentOblastId(String raionId) {
    return _regionsById[raionId]?.parentId;
  }
}
