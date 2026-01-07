import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/notification_service.dart';

class RegionsPage extends StatefulWidget {
  const RegionsPage({super.key});

  @override
  State<RegionsPage> createState() => _RegionsPageState();
}

class _RegionsPageState extends State<RegionsPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  
  final List<String> _allOblasts = [
    'Вінницька область',
    'Волинська область',
    'Дніпропетровська область',
    'Донецька область',
    'Житомирська область',
    'Закарпатська область',
    'Запорізька область',
    'Івано-Франківська область',
    'Київська область',
    'Кіровоградська область',
    'Луганська область',
    'Львівська область',
    'Миколаївська область',
    'Одеська область',
    'Полтавська область',
    'Рівненська область',
    'Сумська область',
    'Тернопільська область',
    'Харківська область',
    'Херсонська область',
    'Хмельницька область',
    'Черкаська область',
    'Чернівецька область',
    'Чернігівська область',
    'АР Крим',
    'м. Київ',
    'м. Севастополь',
  ];

  // Мапа районів по областях
  final Map<String, List<String>> _districtsByOblast = {
    'Дніпропетровська область': [
      'Синельниківський район',
      'Новомосковський район',
      'Дніпровський район',
      'Криворізький район',
      'Кам\'янський район',
      'Нікопольський район',
      'Павлоградський район',
    ],
    'Харківська область': [
      'Куп\'янський район',
      'Ізюмський район',
      'Чугуївський район',
      'Харківський район',
      'Богодухівський район',
      'Красноградський район',
      'Лозівський район',
    ],
    'Сумська область': [
      'Сумський район',
      'Конотопський район',
      'Шосткинський район',
      'Охтирський район',
      'Роменський район',
    ],
    'Чернігівська область': [
      'Новгород-Сіверський район',
      'Чернігівський район',
      'Ніжинський район',
      'Прилуцький район',
      'Корюківський район',
    ],
    'Донецька область': [
      'Краматорський район',
      'Бахмутський район',
      'Покровський район',
      'Волноваський район',
      'Кальміуський район',
      'Маріупольський район',
      'Донецький район',
      'Горлівський район',
    ],
    'Запорізька область': [
      'Запорізький район',
      'Мелітопольський район',
      'Бердянський район',
      'Пологівський район',
      'Василівський район',
    ],
    'Луганська область': [
      'Сєвєродонецький район',
      'Старобільський район',
      'Сватівський район',
      'Щастинський район',
    ],
    'Херсонська область': [
      'Херсонський район',
      'Бериславський район',
      'Генічеський район',
      'Каховський район',
      'Скадовський район',
    ],
    'Миколаївська область': [
      'Миколаївський район',
      'Баштанський район',
      'Вознесенський район',
      'Первомайський район',
    ],
    'Одеська область': [
      'Одеський район',
      'Білгород-Дністровський район',
      'Болградський район',
      'Ізмаїльський район',
      'Подільський район',
      'Березівський район',
      'Роздільнянський район',
    ],
    'Полтавська область': [
      'Полтавський район',
      'Кременчуцький район',
      'Лубенський район',
      'Миргородський район',
    ],
    'Київська область': [
      'Білоцерківський район',
      'Бориспільський район',
      'Броварський район',
      'Бучанський район',
      'Вишгородський район',
      'Обухівський район',
      'Фастівський район',
    ],
    'Черкаська область': [
      'Черкаський район',
      'Золотоніський район',
      'Уманський район',
      'Звенигородський район',
    ],
    'Кіровоградська область': [
      'Кропивницький район',
      'Олександрійський район',
      'Голованівський район',
      'Новоукраїнський район',
    ],
    'Вінницька область': [
      'Вінницький район',
      'Гайсинський район',
      'Жмеринський район',
      'Могилів-Подільський район',
      'Тульчинський район',
      'Хмільницький район',
    ],
    'Житомирська область': [
      'Житомирський район',
      'Бердичівський район',
      'Коростенський район',
      'Звягельський район',
    ],
    'Рівненська область': [
      'Рівненський район',
      'Дубенський район',
      'Вараський район',
      'Сарненський район',
    ],
    'Волинська область': [
      'Луцький район',
      'Володимирський район',
      'Ковельський район',
      'Камінь-Каширський район',
    ],
  };

  Set<String> _selectedRegions = {};
  bool _isLoading = true;
  bool _notificationsEnabled = true;
  String? _expandedOblast;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadSelectedRegions();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadSelectedRegions() async {
    final prefs = await SharedPreferences.getInstance();
    final selected = prefs.getStringList('selected_regions') ?? [];
    final enabled = prefs.getBool('notifications_enabled') ?? true;
    
    setState(() {
      _selectedRegions = selected.toSet();
      _notificationsEnabled = enabled;
      _isLoading = false;
    });
  }

  Future<void> _saveAndUpdate() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('selected_regions', _selectedRegions.toList());
    await prefs.setBool('notifications_enabled', _notificationsEnabled);
    
    // Update notification service
    await NotificationService().updateRegions(_selectedRegions.toList());
    await NotificationService().setNotificationsEnabled(_notificationsEnabled);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Налаштування збережено'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  int get _selectedOblastsCount {
    return _selectedRegions.where((r) => _allOblasts.contains(r)).length;
  }

  int get _selectedDistrictsCount {
    return _selectedRegions.where((r) => !_allOblasts.contains(r)).length;
  }

  List<String> get _allDistricts {
    return _districtsByOblast.values.expand((list) => list).toList()..sort();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F3460) : const Color(0xFFF5F7FA),
      appBar: AppBar(
        backgroundColor: isDark ? const Color(0xFF16213E) : Colors.white,
        elevation: 0,
        title: const Text(
          'Сповіщення про тривоги',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          TextButton(
            onPressed: _isLoading ? null : _saveAndUpdate,
            child: Text(
              'Зберегти',
              style: TextStyle(
                color: _isLoading ? Colors.grey : const Color(0xFF4A90E2),
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF4A90E2),
          labelColor: isDark ? Colors.white : Colors.black,
          unselectedLabelColor: Colors.grey,
          tabs: [
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.map, size: 18),
                  const SizedBox(width: 8),
                  Text('Області ($_selectedOblastsCount)'),
                ],
              ),
            ),
            Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.location_city, size: 18),
                  const SizedBox(width: 8),
                  Text('Райони ($_selectedDistrictsCount)'),
                ],
              ),
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Enable/Disable switch
                Container(
                  margin: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF16213E) : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.05),
                        blurRadius: 10,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: SwitchListTile(
                    value: _notificationsEnabled,
                    onChanged: (value) {
                      setState(() {
                        _notificationsEnabled = value;
                      });
                    },
                    title: const Text(
                      'Push-сповіщення',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    subtitle: Text(
                      _notificationsEnabled
                          ? 'Тривоги та загрози в обраних регіонах'
                          : 'Сповіщення вимкнено',
                      style: TextStyle(
                        fontSize: 13,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                    ),
                    activeColor: const Color(0xFF4A90E2),
                  ),
                ),
                
                // Description
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.blue.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700, size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Оберіть області або конкретні райони для сповіщень про тривоги та загрози',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.blue.shade700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // TabBarView
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildOblastsTab(isDark),
                      _buildDistrictsTab(isDark),
                    ],
                  ),
                ),
                
                // Test notification button
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      await NotificationService().sendTestNotification();
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('🔔 Тестове сповіщення відправлено'),
                            duration: Duration(seconds: 2),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    },
                    icon: const Icon(Icons.notifications_active),
                    label: const Text('Тестове сповіщення'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4A90E2),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      minimumSize: const Size(double.infinity, 50),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildOblastsTab(bool isDark) {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        // Quick select buttons
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _selectedRegions.addAll(_allOblasts);
                  });
                },
                icon: const Icon(Icons.select_all, size: 18),
                label: const Text('Всі'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF4A90E2),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _selectedRegions.removeAll(_allOblasts);
                  });
                },
                icon: const Icon(Icons.clear_all, size: 18),
                label: const Text('Скинути'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.grey,
                ),
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 16),
        
        // Oblasts list
        Container(
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF16213E) : Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            children: _allOblasts.map((oblast) {
              final isSelected = _selectedRegions.contains(oblast);
              final districts = _districtsByOblast[oblast] ?? [];
              final hasDistricts = districts.isNotEmpty;
              final selectedDistrictsCount = districts.where((d) => _selectedRegions.contains(d)).length;
              
              return Column(
                children: [
                  CheckboxListTile(
                    value: isSelected,
                    onChanged: (value) {
                      setState(() {
                        if (value == true) {
                          _selectedRegions.add(oblast);
                        } else {
                          _selectedRegions.remove(oblast);
                        }
                      });
                    },
                    title: Row(
                      children: [
                        Expanded(
                          child: Text(
                            oblast,
                            style: const TextStyle(fontSize: 15),
                          ),
                        ),
                        if (hasDistricts && selectedDistrictsCount > 0)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF4A90E2).withOpacity(0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '+$selectedDistrictsCount район${selectedDistrictsCount > 1 ? 'и' : ''}',
                              style: const TextStyle(
                                fontSize: 11,
                                color: Color(0xFF4A90E2),
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                    secondary: hasDistricts
                        ? IconButton(
                            icon: Icon(
                              _expandedOblast == oblast
                                  ? Icons.expand_less
                                  : Icons.expand_more,
                              color: Colors.grey,
                            ),
                            onPressed: () {
                              setState(() {
                                _expandedOblast = _expandedOblast == oblast ? null : oblast;
                              });
                            },
                          )
                        : null,
                    activeColor: const Color(0xFF4A90E2),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                  if (_expandedOblast == oblast && hasDistricts)
                    Container(
                      color: isDark ? const Color(0xFF0F3460) : Colors.grey[50],
                      padding: const EdgeInsets.only(left: 32, right: 16, bottom: 8),
                      child: Column(
                        children: districts.map((district) {
                          final isDistrictSelected = _selectedRegions.contains(district);
                          return CheckboxListTile(
                            value: isDistrictSelected,
                            onChanged: (value) {
                              setState(() {
                                if (value == true) {
                                  _selectedRegions.add(district);
                                } else {
                                  _selectedRegions.remove(district);
                                }
                              });
                            },
                            title: Text(
                              district,
                              style: const TextStyle(fontSize: 14),
                            ),
                            activeColor: const Color(0xFF4A90E2),
                            controlAffinity: ListTileControlAffinity.leading,
                            dense: true,
                          );
                        }).toList(),
                      ),
                    ),
                ],
              );
            }).toList(),
          ),
        ),
        
        const SizedBox(height: 80),
      ],
    );
  }

  Widget _buildDistrictsTab(bool isDark) {
    // Group districts by oblast
    final groupedDistricts = <String, List<String>>{};
    for (final entry in _districtsByOblast.entries) {
      if (entry.value.isNotEmpty) {
        groupedDistricts[entry.key] = entry.value;
      }
    }
    
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        // Quick select buttons
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _selectedRegions.addAll(_allDistricts);
                  });
                },
                icon: const Icon(Icons.select_all, size: 18),
                label: const Text('Всі'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF4A90E2),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _selectedRegions.removeWhere((r) => !_allOblasts.contains(r));
                  });
                },
                icon: const Icon(Icons.clear_all, size: 18),
                label: const Text('Скинути'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.grey,
                ),
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 16),
        
        // Districts grouped by oblast
        ...groupedDistricts.entries.map((entry) {
          final oblast = entry.key;
          final districts = entry.value;
          final selectedCount = districts.where((d) => _selectedRegions.contains(d)).length;
          final allSelected = selectedCount == districts.length;
          
          return Container(
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF16213E) : Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.location_on, color: Color(0xFF4A90E2)),
                  title: Text(
                    oblast,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  subtitle: Text(
                    '$selectedCount з ${districts.length} обрано',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.grey[400] : Colors.grey[600],
                    ),
                  ),
                  trailing: TextButton(
                    onPressed: () {
                      setState(() {
                        if (allSelected) {
                          _selectedRegions.removeAll(districts);
                        } else {
                          _selectedRegions.addAll(districts);
                        }
                      });
                    },
                    child: Text(
                      allSelected ? 'Скинути' : 'Всі',
                      style: const TextStyle(
                        color: Color(0xFF4A90E2),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const Divider(height: 1),
                ...districts.map((district) {
                  final isSelected = _selectedRegions.contains(district);
                  return CheckboxListTile(
                    value: isSelected,
                    onChanged: (value) {
                      setState(() {
                        if (value == true) {
                          _selectedRegions.add(district);
                        } else {
                          _selectedRegions.remove(district);
                        }
                      });
                    },
                    title: Text(
                      district,
                      style: const TextStyle(fontSize: 14),
                    ),
                    activeColor: const Color(0xFF4A90E2),
                    controlAffinity: ListTileControlAffinity.leading,
                    dense: true,
                  );
                }).toList(),
              ],
            ),
          );
        }).toList(),
        
        const SizedBox(height: 80),
      ],
    );
  }
}
