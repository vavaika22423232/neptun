import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:async';
import 'dart:io' show Platform;
import '../core/widgets/neptun_card.dart';
import '../core/widgets/neptun_shimmer.dart';
import '../services/window_manager.dart';

// Головна сторінка безпеки
class SafetyPage extends StatefulWidget {
  const SafetyPage({super.key});

  @override
  State<SafetyPage> createState() => _SafetyPageState();
}

class _SafetyPageState extends State<SafetyPage> {
  @override
  Widget build(BuildContext context) {
    // No Scaffold, No Gradient (handled by MainPage)
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          child: Row(
            children: [
              NeptunCard(
                variant: NeptunCardVariant.elevated,
                padding: const EdgeInsets.all(12),
                child: Icon(
                  Icons.shield_rounded,
                  color: colorScheme.primary,
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Центр безпеки',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(
                            color: colorScheme.onSurface,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    Text(
                      'Інструменти та поради',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Content
        const Expanded(child: ToolsTab()),
      ],
    );
  }
}

// ==================== TOOLS TAB ====================
class ToolsTab extends StatefulWidget {
  const ToolsTab({super.key});

  @override
  State<ToolsTab> createState() => _ToolsTabState();
}

class _ToolsTabState extends State<ToolsTab> {
  final bool _isLoading = false;

  // Медична картка
  String _bloodType = '';
  String _allergies = '';
  String _medications = '';
  String _emergencyContact1 = '';
  String _emergencyContact2 = '';

  // Чекліст тривожної валізи
  Map<String, bool> _emergencyBagItems = {};

  final List<Map<String, dynamic>> _emergencyBagChecklist = [
    {'key': 'documents', 'name': 'Документи', 'icon': Icons.badge_rounded},
    {
      'key': 'water',
      'name': 'Вода (2л на особу)',
      'icon': Icons.water_drop_rounded,
    },
    {
      'key': 'food',
      'name': 'Консерви/їжа (3 дні)',
      'icon': Icons.restaurant_rounded,
    },
    {
      'key': 'flashlight',
      'name': 'Ліхтарик + батарейки',
      'icon': Icons.flashlight_on_rounded,
    },
    {
      'key': 'powerbank',
      'name': 'Powerbank',
      'icon': Icons.battery_charging_full_rounded,
    },
    {
      'key': 'firstaid',
      'name': 'Аптечка',
      'icon': Icons.medical_services_rounded,
    },
    {'key': 'cash', 'name': 'Готівка', 'icon': Icons.payments_rounded},
    {'key': 'clothes', 'name': 'Змінний одяг', 'icon': Icons.checkroom_rounded},
    {'key': 'blanket', 'name': 'Ковдра/плед', 'icon': Icons.bed_rounded},
    {
      'key': 'radio',
      'name': 'Радіо на батарейках',
      'icon': Icons.radio_rounded,
    },
    {
      'key': 'charger',
      'name': 'Зарядки для телефону',
      'icon': Icons.cable_rounded,
    },
    {'key': 'hygiene', 'name': 'Засоби гігієни', 'icon': Icons.soap_rounded},
  ];

  @override
  void initState() {
    super.initState();
    _loadMedicalCard();
    _loadEmergencyBagChecklist();
  }

  Future<void> _loadEmergencyBagChecklist() async {
    final prefs = await SharedPreferences.getInstance();
    final savedItems = prefs.getString('emergency_bag_items');
    if (savedItems != null) {
      final decoded = json.decode(savedItems) as Map<String, dynamic>;
      setState(() {
        _emergencyBagItems = decoded.map((k, v) => MapEntry(k, v as bool));
      });
    }
  }

  Future<void> _saveEmergencyBagChecklist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'emergency_bag_items',
      json.encode(_emergencyBagItems),
    );
  }

  Future<void> _loadMedicalCard() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _bloodType = prefs.getString('medical_blood_type') ?? '';
      _allergies = prefs.getString('medical_allergies') ?? '';
      _medications = prefs.getString('medical_medications') ?? '';
      _emergencyContact1 = prefs.getString('emergency_contact_1') ?? '';
      _emergencyContact2 = prefs.getString('emergency_contact_2') ?? '';
    });
  }

  Future<void> _saveMedicalCard() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('medical_blood_type', _bloodType);
    await prefs.setString('medical_allergies', _allergies);
    await prefs.setString('medical_medications', _medications);
    await prefs.setString('emergency_contact_1', _emergencyContact1);
    await prefs.setString('emergency_contact_2', _emergencyContact2);
  }

  void _showMedicalCardDialog() {
    final bloodController = TextEditingController(text: _bloodType);
    final allergiesController = TextEditingController(text: _allergies);
    final medicationsController = TextEditingController(text: _medications);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        title: Row(
          children: [
            Icon(Icons.medical_information_rounded, color: Theme.of(context).colorScheme.error),
            const SizedBox(width: 8),
            const Text('Медична картка'),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: bloodController,
                decoration: const InputDecoration(
                  labelText: 'Група крові',
                  hintText: 'Напр.: A+ (II+)',
                  prefixIcon: Icon(Icons.bloodtype_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: allergiesController,
                decoration: const InputDecoration(
                  labelText: 'Алергії',
                  hintText: 'Напр.: Пеніцилін, горіхи',
                  prefixIcon: Icon(Icons.warning_amber_rounded),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: medicationsController,
                decoration: const InputDecoration(
                  labelText: 'Ліки які приймаю',
                  hintText: 'Напр.: Інсулін, аспірин',
                  prefixIcon: Icon(Icons.medication_rounded),
                ),
                maxLines: 2,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Скасувати'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _bloodType = bloodController.text;
                _allergies = allergiesController.text;
                _medications = medicationsController.text;
              });
              _saveMedicalCard();
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('✅ Медичну картку збережено')),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Colors.white,
            ),
            child: const Text('Зберегти'),
          ),
        ],
      ),
    );
  }

  void _showEmergencyContactsDialog() {
    final contact1Controller = TextEditingController(text: _emergencyContact1);
    final contact2Controller = TextEditingController(text: _emergencyContact2);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        title: Row(
          children: [
            Icon(Icons.contact_phone_rounded, color: Theme.of(context).colorScheme.error),
            const SizedBox(width: 8),
            const Text('Екстрені контакти'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: contact1Controller,
              decoration: const InputDecoration(
                labelText: 'Контакт 1 (ім\'я та телефон)',
                hintText: 'Напр.: Мама +380501234567',
                prefixIcon: Icon(Icons.person_rounded),
              ),
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: contact2Controller,
              decoration: const InputDecoration(
                labelText: 'Контакт 2 (ім\'я та телефон)',
                hintText: 'Напр.: Брат +380671234567',
                prefixIcon: Icon(Icons.person_rounded),
              ),
              keyboardType: TextInputType.phone,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Скасувати'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _emergencyContact1 = contact1Controller.text;
                _emergencyContact2 = contact2Controller.text;
              });
              _saveMedicalCard();
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('✅ Контакти збережено')),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Colors.white,
            ),
            child: const Text('Зберегти'),
          ),
        ],
      ),
    );
  }

  void _showEmergencyBagDialog() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          final checkedCount = _emergencyBagItems.values.where((v) => v).length;
          final totalCount = _emergencyBagChecklist.length;
          final progress = totalCount > 0 ? checkedCount / totalCount : 0.0;

          return AlertDialog(
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
            title: Row(
              children: [
                const Icon(Icons.backpack_rounded, color: Colors.grey),
                const SizedBox(width: 8),
                const Expanded(child: Text('Тривожна валіза')),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: progress == 1.0
                        ? Theme.of(context).colorScheme.secondary
                        : Theme.of(context).colorScheme.tertiary,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '$checkedCount/$totalCount',
                    style: TextStyle(
                      color: progress == 1.0 ? Colors.black : Colors.black,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            content: SizedBox(
              width: double.maxFinite,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Прогрес-бар
                  LinearProgressIndicator(
                    value: progress,
                    backgroundColor: Colors.grey[300],
                    valueColor: AlwaysStoppedAnimation(
                      progress == 1.0 ? Theme.of(context).colorScheme.secondary : Colors.grey,
                    ),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    progress == 1.0
                        ? '✅ Валіза зібрана!'
                        : 'Зберіть всі необхідні речі',
                    style: TextStyle(
                      fontSize: 12,
                      color: progress == 1.0
                          ? Theme.of(context).colorScheme.secondary
                          : Colors.grey[600],
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Список
                  Flexible(
                    child: SingleChildScrollView(
                      child: Column(
                        children: _emergencyBagChecklist.map((item) {
                          final key = item['key'] as String;
                          final isChecked = _emergencyBagItems[key] ?? false;
                          return CheckboxListTile(
                            value: isChecked,
                            onChanged: (value) {
                              setDialogState(() {
                                _emergencyBagItems[key] = value ?? false;
                              });
                              setState(() {});
                              _saveEmergencyBagChecklist();
                            },
                            title: Text(
                              item['name'] as String,
                              style: TextStyle(
                                decoration: isChecked
                                    ? TextDecoration.lineThrough
                                    : null,
                                color: isChecked ? Colors.grey : null,
                              ),
                            ),
                            secondary: Icon(
                              item['icon'] as IconData,
                              color: isChecked
                                  ? Theme.of(context).colorScheme.secondary
                                  : Colors.grey,
                            ),
                            dense: true,
                            controlAffinity: ListTileControlAffinity.trailing,
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  setDialogState(() {
                    _emergencyBagItems.clear();
                  });
                  setState(() {});
                  _saveEmergencyBagChecklist();
                },
                child: const Text('Очистити'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.error,
                  foregroundColor: Colors.white,
                ),
                child: const Text('Готово'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colorScheme = Theme.of(context).colorScheme;

    // Glass style colors
    final glassColor = colorScheme.surfaceContainer;
    final glassBorderColor = colorScheme.outlineVariant;
    final textColor = colorScheme.onSurface;

    if (_isLoading) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          children: const [
            SizedBox(height: 16),
            NeptunShimmer(height: 80, borderRadius: 16),
            SizedBox(height: 12),
            NeptunShimmer(height: 80, borderRadius: 16),
            SizedBox(height: 12),
            NeptunShimmer(height: 80, borderRadius: 16),
            SizedBox(height: 12),
            NeptunShimmer(height: 80, borderRadius: 16),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 🏠 Карта укриттів - головна кнопка
          if (!Platform.isIOS) ...[
            GestureDetector(
              onTap: () {
                WindowManager().openPanel(PanelType.shelters);
              },
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainer,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: colorScheme.outlineVariant),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: colorScheme.primary.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Icon(
                        Icons.location_on_rounded,
                        color: colorScheme.primary,
                        size: 32,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Укриття поруч',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: textColor,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Знайти найближчі укриття та метро',
                            style: TextStyle(
                              fontSize: 14,
                              color: textColor.withValues(alpha: 0.8),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: textColor,
                      size: 20,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],

          // 💡 Поради
          Text(
            'Поради безпеки',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),

          const SizedBox(height: 12),

          _buildGlassTipCard(
            icon: Icons.timer_rounded,
            title: 'Правило двох стін',
            description:
                'При тривозі знаходьтесь мінімум за двома капітальними стінами від вулиці',
            color: colorScheme.tertiary,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
          ),

          const SizedBox(height: 12),

          _buildGlassTipCard(
            icon: Icons.phone_android_rounded,
            title: 'Зарядіть телефон',
            description:
                'Тримайте телефон зарядженим мінімум на 50% для отримання сповіщень',
            color: colorScheme.secondary,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
          ),

          const SizedBox(height: 12),

          _buildGlassTipCard(
            icon: Icons.backpack_rounded,
            title: 'Тривожна валіза',
            description:
                'Підготуйте сумку з документами, водою, ліхтариком та аптечкою',
            color: Colors.grey,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
          ),

          const SizedBox(height: 24),

          // 🛠 Інструменти
          Text(
            'Інструменти',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),
          const SizedBox(height: 12),

          _buildToolButton(
            icon: Icons.medical_information_rounded,
            title: 'Медична картка',
            description: _bloodType.isNotEmpty
                ? 'Група крові: $_bloodType'
                : 'Заповніть дані для екстрених ситуацій',
            color: colorScheme.error,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
            onTap: _showMedicalCardDialog,
          ),
          const SizedBox(height: 12),

          _buildToolButton(
            icon: Icons.contact_phone_rounded,
            title: 'Екстрені контакти',
            description: _emergencyContact1.isNotEmpty
                ? _emergencyContact1
                : 'Додайте контакти близьких',
            color: colorScheme.error,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
            onTap: _showEmergencyContactsDialog,
          ),
          const SizedBox(height: 12),

          _buildToolButton(
            icon: Icons.backpack_rounded,
            title: 'Чекліст тривожної валізи',
            description: () {
              final checked = _emergencyBagItems.values.where((v) => v).length;
              final total = _emergencyBagChecklist.length;
              return checked == 0
                  ? 'Перевірте готовність'
                  : '$checked з $total зібрано';
            }(),
            color: Colors.grey,
            glassColor: glassColor,
            glassBorderColor: glassBorderColor,
            isDark: isDark,
            onTap: _showEmergencyBagDialog,
          ),

          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildToolButton({
    required IconData icon,
    required String title,
    required String description,
    required Color color,
    required Color glassColor,
    required Color glassBorderColor,
    required bool isDark,
    required VoidCallback onTap,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textColor = colorScheme.onSurface;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                      color: textColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(
                      fontSize: 13,
                      color: textColor.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: textColor.withValues(alpha: 0.5),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGlassTipCard({
    required IconData icon,
    required String title,
    required String description,
    required Color color,
    required Color glassColor,
    required Color glassBorderColor,
    required bool isDark,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textColor = colorScheme.onSurface;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 13,
                    color: textColor.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ==================== ACHIEVEMENTS TAB ====================
class AchievementsTab extends StatefulWidget {
  const AchievementsTab({super.key});

  @override
  State<AchievementsTab> createState() => _AchievementsTabState();
}

class _AchievementsTabState extends State<AchievementsTab> {
  final Map<String, int> _achievements = {};
  bool _isLoading = true;

  final List<Achievement> _allAchievements = [
    Achievement(
      id: 'shelter_visits',
      title: 'Обережність',
      description: 'Відвідайте укриття',
      icon: Icons.shield_rounded,
      tiers: [1, 5, 10, 25, 50, 100],
      tierNames: [
        'Новачок',
        'Обережний',
        'Досвідчений',
        'Ветеран',
        'Експерт',
        'Легенда',
      ],
    ),
    Achievement(
      id: 'family_added',
      title: 'Сімейні узи',
      description: 'Додайте членів родини',
      icon: Icons.family_restroom_rounded,
      tiers: [1, 3, 5, 10],
      tierNames: ['Пара', 'Родина', 'Велика сім\'я', 'Клан'],
    ),
    Achievement(
      id: 'app_opens',
      title: 'Пильність',
      description: 'Відкрийте додаток',
      icon: Icons.visibility_rounded,
      tiers: [1, 7, 30, 100, 365],
      tierNames: ['Перший раз', 'Тиждень', 'Місяць', 'Сто разів', 'Рік'],
    ),
    Achievement(
      id: 'sos_sent',
      title: 'Рятівник',
      description: 'Надішліть SOS',
      icon: Icons.sos_rounded,
      tiers: [1, 5, 10],
      tierNames: ['Перший виклик', 'На зв\'язку', 'Завжди готовий'],
    ),
    Achievement(
      id: 'night_alerts',
      title: 'Нічний вартовий',
      description: 'Отримайте нічну тривогу',
      icon: Icons.nightlight_rounded,
      tiers: [1, 10, 50],
      tierNames: ['Пробудження', 'Нічна зміна', 'Сова'],
    ),
    Achievement(
      id: 'streak_days',
      title: 'Серія',
      description: 'Днів поспіль в додатку',
      icon: Icons.local_fire_department_rounded,
      tiers: [3, 7, 14, 30, 100],
      tierNames: ['3 дні', 'Тиждень', '2 тижні', 'Місяць', '100 днів'],
    ),
  ];

  @override
  void initState() {
    super.initState();
    _loadAchievements();
  }

  Future<void> _loadAchievements() async {
    final prefs = await SharedPreferences.getInstance();

    for (var achievement in _allAchievements) {
      _achievements[achievement.id] =
          prefs.getInt('achievement_${achievement.id}') ?? 0;
    }

    // Збільшити лічильник відкриттів додатку
    final appOpens = (_achievements['app_opens'] ?? 0) + 1;
    await prefs.setInt('achievement_app_opens', appOpens);
    _achievements['app_opens'] = appOpens;

    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colorScheme = Theme.of(context).colorScheme;

    if (_isLoading) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: const [
            NeptunShimmer(height: 60, borderRadius: 16),
            SizedBox(height: 16),
            NeptunShimmer(height: 100, borderRadius: 16),
            SizedBox(height: 12),
            NeptunShimmer(height: 100, borderRadius: 16),
            SizedBox(height: 12),
            NeptunShimmer(height: 100, borderRadius: 16),
          ],
        ),
      );
    }

    // Підрахувати загальну кількість відкритих досягнень
    int totalUnlocked = 0;
    int totalPossible = 0;
    for (var achievement in _allAchievements) {
      final progress = _achievements[achievement.id] ?? 0;
      for (var tier in achievement.tiers) {
        totalPossible++;
        if (progress >= tier) totalUnlocked++;
      }
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Загальний прогрес
          // Загальний прогрес
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.grey.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.grey.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(
                    Icons.emoji_events_rounded,
                    color: Colors.white,
                    size: 40,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Мої досягнення',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: colorScheme.onSurface,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '$totalUnlocked з $totalPossible відкрито',
                        style: TextStyle(
                          fontSize: 14,
                          color: colorScheme.onSurface,
                        ),
                      ),
                      const SizedBox(height: 8),
                      LinearProgressIndicator(
                        value: totalPossible > 0
                            ? totalUnlocked / totalPossible
                            : 0,
                        backgroundColor: Colors.white.withValues(alpha: 0.1),
                        valueColor: AlwaysStoppedAnimation(
                          colorScheme.error,
                        ),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Список досягнень
          ..._allAchievements.map(
            (achievement) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _AchievementCard(
                achievement: achievement,
                progress: _achievements[achievement.id] ?? 0,
                isDark: isDark,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ==================== HELPER WIDGETS ====================

// ignore: unused_element
class _PremiumHintCard extends StatelessWidget {
  final bool isDark;

  const _PremiumHintCard({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.tertiary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: colorScheme.tertiary.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.workspace_premium_rounded,
            color: colorScheme.tertiary,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Premium дозволяє додати необмежену кількість членів родини',
              style: TextStyle(
                color: colorScheme.onSurface,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AchievementCard extends StatelessWidget {
  final Achievement achievement;
  final int progress;
  final bool isDark;

  const _AchievementCard({
    required this.achievement,
    required this.progress,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    // Визначити поточний рівень
    final colorScheme = Theme.of(context).colorScheme;
    int currentTier = 0;
    int nextTierValue = achievement.tiers.first;

    for (int i = 0; i < achievement.tiers.length; i++) {
      if (progress >= achievement.tiers[i]) {
        currentTier = i + 1;
        if (i + 1 < achievement.tiers.length) {
          nextTierValue = achievement.tiers[i + 1];
        } else {
          nextTierValue = achievement.tiers.last;
        }
      } else {
        nextTierValue = achievement.tiers[i];
        break;
      }
    }

    final isMaxed = currentTier >= achievement.tiers.length;
    final progressPercent = isMaxed ? 1.0 : progress / nextTierValue;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isMaxed
                    ? [const Color(0xFFFFD700), const Color(0xFFFF8C00)]
                    : currentTier > 0
                    ? [
                        colorScheme.error,
                        colorScheme.error.withValues(alpha: 0.7),
                      ]
                    : [
                        Colors.grey.shade800,
                        Colors.grey.shade900,
                      ], // Darker grey for locked
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(achievement.icon, color: Colors.white, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        achievement.title,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: colorScheme.onSurface,
                        ),
                      ),
                    ),
                    if (currentTier > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: isMaxed
                              ? const Color(0xFFFFD700)
                              : colorScheme.error,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          achievement.tierNames[currentTier - 1],
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  achievement.description,
                  style: TextStyle(
                    fontSize: 13,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: progressPercent,
                          backgroundColor: isDark
                              ? Colors.grey[700]
                              : Colors.grey[200],
                          valueColor: AlwaysStoppedAnimation(
                            isMaxed
                                ? const Color(0xFFFFD700)
                                : colorScheme.error,
                          ),
                          minHeight: 6,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      isMaxed ? 'MAX' : '$progress/$nextTierValue',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: isMaxed
                            ? const Color(0xFFFFD700)
                            : colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ignore: unused_element
class _AddFamilyMemberDialog extends StatelessWidget {
  final TextEditingController codeController;
  final TextEditingController nameController;

  const _AddFamilyMemberDialog({
    required this.codeController,
    required this.nameController,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Додати члена родини'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: nameController,
            decoration: const InputDecoration(
              labelText: 'Ім\'я',
              hintText: 'Мама, Тато, Брат...',
              prefixIcon: Icon(Icons.person_rounded),
            ),
            textCapitalization: TextCapitalization.words,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: codeController,
            decoration: const InputDecoration(
              labelText: 'Код',
              hintText: 'ABC123',
              prefixIcon: Icon(Icons.qr_code_rounded),
            ),
            textCapitalization: TextCapitalization.characters,
            maxLength: 6,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Скасувати'),
        ),
        ElevatedButton(
          onPressed: () {
            Navigator.pop(context, {
              'code': codeController.text,
              'name': nameController.text,
            });
          },
          child: const Text('Додати'),
        ),
      ],
    );
  }
}

// ==================== DATA MODELS ====================

class FamilyMember {
  final String code;
  final String name;
  bool isSafe;
  DateTime? lastUpdate;
  String location;
  int? batteryLevel;
  bool isOnline;
  bool hasToken; // Чи зареєстрований FCM токен для SOS

  FamilyMember({
    required this.code,
    required this.name,
    this.isSafe = false,
    this.lastUpdate,
    this.location = '',
    this.batteryLevel,
    this.isOnline = false,
    this.hasToken = false,
  });

  factory FamilyMember.fromJson(Map<String, dynamic> json) {
    return FamilyMember(
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      isSafe: json['is_safe'] ?? false,
      lastUpdate: json['last_update'] != null
          ? DateTime.tryParse(json['last_update'])
          : null,
      location: json['location'] ?? '',
      batteryLevel: json['battery_level'],
      isOnline: json['is_online'] ?? false,
      hasToken: json['has_token'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'code': code,
    'name': name,
    'is_safe': isSafe,
    'last_update': lastUpdate?.toIso8601String(),
    'location': location,
    'battery_level': batteryLevel,
    'is_online': isOnline,
    'has_token': hasToken,
  };
}

class Achievement {
  final String id;
  final String title;
  final String description;
  final IconData icon;
  final List<int> tiers;
  final List<String> tierNames;

  Achievement({
    required this.id,
    required this.title,
    required this.description,
    required this.icon,
    required this.tiers,
    required this.tierNames,
  });
}

// ==================== ENHANCED WIDGETS ====================

// ignore: unused_element
class _EnhancedSafeStatusCard extends StatelessWidget {
  final bool isSafe;
  final String myCode;
  final String myName;
  final String myLocation;
  final DateTime? lastUpdate;
  final VoidCallback onToggle;
  final VoidCallback onSOS;
  final VoidCallback onEditProfile;
  final VoidCallback onShareCode;
  final bool isDark;

  const _EnhancedSafeStatusCard({
    required this.isSafe,
    required this.myCode,
    required this.myName,
    required this.myLocation,
    // ignore: unused_element_parameter
    this.lastUpdate,
    required this.onToggle,
    required this.onSOS,
    required this.onEditProfile,
    required this.onShareCode,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final statusColor = isSafe ? colorScheme.secondary : Colors.grey;

    final borderColor = isSafe
        ? colorScheme.secondary.withValues(alpha: 0.3)
        : colorScheme.outlineVariant;

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        children: [
          // Верхня частина - статус
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Row(
                  children: [
                    // Іконка статусу
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: statusColor.withValues(alpha: 0.5),
                        ),
                      ),
                      child: Icon(
                        isSafe
                            ? Icons.shield_rounded
                            : Icons.warning_amber_rounded,
                        color: statusColor,
                        size: 32,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                isSafe ? 'Я В УКРИТТІ' : 'Я НЕ В УКРИТТІ',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: isSafe
                                      ? colorScheme.secondary
                                      : colorScheme.onSurface,
                                  letterSpacing: 0.5,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: statusColor,
                                  shape: BoxShape.circle,
                                  boxShadow: [
                                    BoxShadow(
                                      color: statusColor.withValues(alpha: 0.5),
                                      blurRadius: 4,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            myName.isNotEmpty ? myName : 'Налаштуйте профіль',
                            style: TextStyle(
                              fontSize: 14,
                              color: colorScheme.onSurface.withValues(
                                alpha: 0.7,
                              ),
                            ),
                          ),
                          if (myLocation.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Row(
                              children: [
                                Icon(
                                  Icons.location_on_rounded,
                                  size: 14,
                                  color: colorScheme.onSurface.withValues(
                                    alpha: 0.6,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  myLocation,
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: colorScheme.onSurface.withValues(
                                      alpha: 0.6,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: onEditProfile,
                      icon: Icon(
                        Icons.edit_rounded,
                        color: colorScheme.onSurface,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 20),

                // Мій код
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: colorScheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.qr_code_rounded,
                        color: colorScheme.onSurface,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Мій код: ',
                        style: TextStyle(
                          fontSize: 14,
                          color: colorScheme.onSurface.withValues(alpha: 0.7),
                        ),
                      ),
                      Text(
                        myCode,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: colorScheme.onSurface,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.share_rounded,
                        color: colorScheme.onSurface.withValues(alpha: 0.6),
                        size: 18,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Кнопки дій
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.black.withValues(alpha: 0.2)
                  : Colors.white.withValues(alpha: 0.5),
              border: Border(top: BorderSide(color: borderColor)),
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(24),
                bottomRight: Radius.circular(24),
              ),
            ),
            child: Row(
              children: [
                // Кнопка статусу
                Expanded(
                  flex: 3,
                  child: GestureDetector(
                    onTap: onToggle,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      decoration: BoxDecoration(
                        color: isSafe
                            ? colorScheme.error.withValues(alpha: 0.1)
                            : colorScheme.secondary.withValues(alpha: 0.1),
                        border: Border.all(
                          color: isSafe
                              ? colorScheme.error.withValues(alpha: 0.3)
                              : colorScheme.secondary.withValues(alpha: 0.3),
                        ),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            isSafe
                                ? Icons.exit_to_app_rounded
                                : Icons.home_rounded,
                            color: isSafe
                                ? colorScheme.error
                                : colorScheme.secondary,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            isSafe ? 'Вийшов з укриття' : 'Я в укритті!',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                              color: isSafe
                                  ? colorScheme.error
                                  : colorScheme.secondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // SOS кнопка
                GestureDetector(
                  onTap: onSOS,
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: colorScheme.error.withValues(alpha: 0.2),
                      border: Border.all(
                        color: colorScheme.error.withValues(alpha: 0.5),
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      Icons.sos_rounded,
                      color: colorScheme.error,
                      size: 28,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ignore: unused_element
class _EnhancedFamilyMemberCard extends StatelessWidget {
  final FamilyMember member;
  final int index;
  final bool isDark;
  final VoidCallback onDelete;
  final VoidCallback onPing;

  const _EnhancedFamilyMemberCard({
    required this.member,
    required this.index,
    required this.isDark,
    required this.onDelete,
    required this.onPing,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final lastUpdateText = member.lastUpdate != null
        ? _formatLastUpdate(member.lastUpdate!)
        : 'Невідомо';

    final colors = [
      colorScheme.error,
      Colors.grey,
      colorScheme.tertiary,
      colorScheme.secondary,
      colorScheme.error,
      Colors.white,
    ];
    final avatarColor = colors[index % colors.length];

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: member.isSafe
              ? colorScheme.secondary.withValues(alpha: 0.3)
              : colorScheme.error.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Аватар
                Stack(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            avatarColor,
                            avatarColor.withValues(alpha: 0.7),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Center(
                        child: Text(
                          member.name.isNotEmpty
                              ? member.name[0].toUpperCase()
                              : '?',
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                    // Індикатор онлайн
                    Positioned(
                      right: 0,
                      bottom: 0,
                      child: Container(
                        width: 16,
                        height: 16,
                        decoration: BoxDecoration(
                          color: member.isOnline
                              ? colorScheme.secondary
                              : Colors.grey,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: colorScheme.surfaceContainerHighest,
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              member.name,
                              style: TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.bold,
                                color: colorScheme.onSurface,
                              ),
                            ),
                          ),
                          // Статус іконка
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: member.isSafe
                                  ? colorScheme.secondary.withValues(alpha: 0.15)
                                  : colorScheme.error.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  member.isSafe
                                      ? Icons.shield_rounded
                                      : Icons.warning_amber_rounded,
                                  size: 14,
                                  color: member.isSafe
                                      ? colorScheme.secondary
                                      : colorScheme.error,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  member.isSafe ? 'В безпеці' : 'Тривога',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: member.isSafe
                                        ? colorScheme.secondary
                                        : colorScheme.error,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      // Локація
                      if (member.location.isNotEmpty) ...[
                        Row(
                          children: [
                            Icon(
                              Icons.location_on_rounded,
                              size: 14,
                              color: colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                member.location,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: colorScheme.onSurfaceVariant,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                      ],
                      // Останнє оновлення
                      Row(
                        children: [
                          Icon(
                            Icons.access_time_rounded,
                            size: 14,
                            color: colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            lastUpdateText,
                            style: TextStyle(
                              fontSize: 12,
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                          if (member.batteryLevel != null) ...[
                            const SizedBox(width: 12),
                            Icon(
                              _getBatteryIcon(member.batteryLevel!),
                              size: 14,
                              color: _getBatteryColor(member.batteryLevel!, colorScheme),
                            ),
                            const SizedBox(width: 2),
                            Text(
                              '${member.batteryLevel}%',
                              style: TextStyle(
                                fontSize: 12,
                                color: _getBatteryColor(member.batteryLevel!, colorScheme),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Попередження якщо людина не може отримати SOS
          if (!member.hasToken) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: colorScheme.tertiary.withValues(alpha: 0.15),
                border: Border(
                  top: BorderSide(
                    color: colorScheme.tertiary.withValues(alpha: 0.3),
                    width: 1,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: Colors.orange[700],
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Ця людина ще не відкривала вкладку Родина',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.orange[700],
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          // Кнопки дій
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.black.withValues(alpha: 0.2)
                  : Colors.grey.withValues(alpha: 0.1),
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(18),
                bottomRight: Radius.circular(18),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    onTap: onPing,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: colorScheme.error.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.notifications_active_rounded,
                            size: 16,
                            color: colorScheme.error,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Надіслати сигнал',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: colorScheme.error,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: onDelete,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: colorScheme.error.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      Icons.person_remove_rounded,
                      size: 18,
                      color: colorScheme.error,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatLastUpdate(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 1) return 'щойно';
    if (diff.inMinutes < 60) return '${diff.inMinutes} хв тому';
    if (diff.inHours < 24) return '${diff.inHours} год тому';
    return '${diff.inDays} дн. тому';
  }

  IconData _getBatteryIcon(int level) {
    if (level > 80) return Icons.battery_full_rounded;
    if (level > 60) return Icons.battery_5_bar_rounded;
    if (level > 40) return Icons.battery_4_bar_rounded;
    if (level > 20) return Icons.battery_2_bar_rounded;
    return Icons.battery_alert_rounded;
  }

  Color _getBatteryColor(int level, ColorScheme colorScheme) {
    if (level > 50) return colorScheme.secondary;
    if (level > 20) return colorScheme.tertiary;
    return colorScheme.error;
  }
}

// ignore: unused_element
class _EnhancedEmptyFamilyCard extends StatelessWidget {
  final bool isDark;
  final String myCode;
  final VoidCallback onShareCode;
  final VoidCallback onAddMember;

  const _EnhancedEmptyFamilyCard({
    required this.isDark,
    required this.myCode,
    required this.onShareCode,
    required this.onAddMember,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return NeptunCard(
      variant: NeptunCardVariant.elevated,
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: colorScheme.error.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.family_restroom_rounded,
              size: 48,
              color: colorScheme.error,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Додайте рідних',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Слідкуйте за безпекою близьких та отримуйте сповіщення про тривоги в їх регіоні',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: onShareCode,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(
                      color: colorScheme.error.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: colorScheme.error.withValues(alpha: 0.3),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.share_rounded,
                          color: colorScheme.error,
                          size: 20,
                        ),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            'Поділитися',
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: colorScheme.error,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: GestureDetector(
                  onTap: onAddMember,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [colorScheme.error, colorScheme.primary],
                      ),
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: colorScheme.error.withValues(alpha: 0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.person_add_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                        SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            'Додати',
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ignore: unused_element
class _HowToUseCard extends StatelessWidget {
  final bool isDark;

  const _HowToUseCard({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return NeptunCard(
      variant: NeptunCardVariant.elevated,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.help_outline_rounded,
                color: colorScheme.error,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Як це працює?',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: colorScheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildStep('1', 'Поділіться своїм кодом з рідними', colorScheme),
          _buildStep('2', 'Вони додають вас у свій додаток', colorScheme),
          _buildStep(
            '3',
            'Натисніть "Я в укритті" коли ви в безпеці',
            colorScheme,
          ),
          _buildStep(
            '4',
            'Родина бачить ваш статус в реальному часі',
            colorScheme,
          ),
        ],
      ),
    );
  }

  Widget _buildStep(String number, String text, ColorScheme colorScheme) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: colorScheme.error.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                number,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: colorScheme.primary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 13,
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
