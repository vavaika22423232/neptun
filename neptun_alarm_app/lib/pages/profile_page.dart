import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  // Medical Data
  String _userName = 'Користувач';
  String _bloodType = '';
  String _allergies = '';
  String _medications = '';
  String _emergencyContact1 = '';
  String _emergencyContact2 = '';

  // Emergency Bag Data
  Map<String, bool> _emergencyBagItems = {};
  final List<Map<String, dynamic>> _emergencyBagChecklist = [
    {'key': 'documents', 'name': 'Документи', 'icon': Icons.badge_rounded},
    {'key': 'water', 'name': 'Вода (2л)', 'icon': Icons.water_drop_rounded},
    {'key': 'food', 'name': 'Їжа (3 дні)', 'icon': Icons.restaurant_rounded},
    {
      'key': 'flashlight',
      'name': 'Ліхтарик',
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
    {'key': 'clothes', 'name': 'Одяг', 'icon': Icons.checkroom_rounded},
    {'key': 'blanket', 'name': 'Ковдра', 'icon': Icons.bed_rounded},
    {'key': 'radio', 'name': 'Радіо', 'icon': Icons.radio_rounded},
    {'key': 'charger', 'name': 'Зарядка', 'icon': Icons.cable_rounded},
    {'key': 'hygiene', 'name': 'Гігієна', 'icon': Icons.soap_rounded},
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _bloodType = prefs.getString('medical_blood_type') ?? '';
      _allergies = prefs.getString('medical_allergies') ?? '';
      _medications = prefs.getString('medical_medications') ?? '';
      _emergencyContact1 = prefs.getString('emergency_contact_1') ?? '';
      _emergencyContact2 = prefs.getString('emergency_contact_2') ?? '';
      _userName = prefs.getString('anonymous_user_id') ?? 'Користувач';

      final savedItems = prefs.getString('emergency_bag_items');
      if (savedItems != null) {
        final decoded = json.decode(savedItems) as Map<String, dynamic>;
        _emergencyBagItems = decoded.map((k, v) => MapEntry(k, v as bool));
      }
    });
  }

  Future<void> _saveMedicalData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('medical_blood_type', _bloodType);
    await prefs.setString('medical_allergies', _allergies);
    await prefs.setString('medical_medications', _medications);
    await prefs.setString('emergency_contact_1', _emergencyContact1);
    await prefs.setString('emergency_contact_2', _emergencyContact2);
  }

  Future<void> _saveBagData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'emergency_bag_items',
      json.encode(_emergencyBagItems),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        SafeArea(
          child: Column(
            children: [
              // Avatar & Name
              const SizedBox(height: 20),
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: colorScheme.primary,
                ),
                child: const Icon(Icons.person, size: 50, color: Colors.white),
              ),
              const SizedBox(height: 16),
              Text(
                _userName,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: colorScheme.onSurface,
                ),
              ),
              Text(
                'Kyiv, Ukraine',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 32),

              // Stats Grid
              Row(
                children: [
                  Expanded(
                    child: _buildStatCard('Рівень', '5', Theme.of(context).colorScheme.tertiary),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _buildStatCard('Друзі', '12', Theme.of(context).colorScheme.secondary),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _buildStatCard(
                      'Валіза',
                      '${_calculateBagProgress()}%',
                      Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // Safety Tools Section
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "Центр Безпеки",
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onSurface,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              _buildSettingsItem(
                Icons.medical_information_rounded,
                'Медична Картка',
                onTap: _showMedicalCardDialog,
              ),
              _buildSettingsItem(
                Icons.backpack_rounded,
                'Тривожна Валіза',
                onTap: _showEmergencyBagDialog,
              ),
              _buildSettingsItem(
                Icons.contact_phone_rounded,
                'Екстрені Контакти',
                onTap: _showEmergencyContactsDialog,
              ),

              const SizedBox(height: 32),

              // Link to full settings (replaces duplicate non-functional items)
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  "Налаштування",
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onSurface,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              _buildSettingsItem(
                Icons.settings_rounded,
                'Налаштування додатку',
                subtitle: 'Сповіщення, регіони, тема, звук',
                onTap: () => context.go('/profile'),
              ),

              const SizedBox(height: 100),
            ],
          ),
        ),
      ],
    );
  }

  int _calculateBagProgress() {
    if (_emergencyBagChecklist.isEmpty) return 0;
    final checked = _emergencyBagItems.values.where((v) => v).length;
    return ((checked / _emergencyBagChecklist.length) * 100).round();
  }

  Widget _buildStatCard(String label, String value, Color color) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsItem(
    IconData icon,
    String label, {
    String? subtitle,
    bool isDestructive = false,
    VoidCallback? onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainer,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          child: Row(
            children: [
              Icon(
                icon,
                color: isDestructive
                    ? Theme.of(context).colorScheme.error
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: isDestructive
                            ? Theme.of(context).colorScheme.error
                            : Theme.of(context).colorScheme.onSurface,
                      ),
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context)
                              .colorScheme
                              .onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.3),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- Dialogs ---

  void _showMedicalCardDialog() {
    final bloodController = TextEditingController(text: _bloodType);
    final allergiesController = TextEditingController(text: _allergies);
    final medicationsController = TextEditingController(text: _medications);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor:
            Colors.white, // Simply using white for now to match theme
        title: const Text('Медична картка'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: bloodController,
                decoration: const InputDecoration(labelText: 'Група крові'),
              ),
              TextField(
                controller: allergiesController,
                decoration: const InputDecoration(labelText: 'Алергії'),
              ),
              TextField(
                controller: medicationsController,
                decoration: const InputDecoration(labelText: 'Ліки'),
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
              _saveMedicalData();
              Navigator.pop(context);
            },
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
        backgroundColor: Colors.white,
        title: const Text('Екстрені контакти'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: contact1Controller,
              decoration: const InputDecoration(labelText: 'Контакт 1'),
            ),
            TextField(
              controller: contact2Controller,
              decoration: const InputDecoration(labelText: 'Контакт 2'),
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
              _saveMedicalData();
              Navigator.pop(context);
            },
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
          return AlertDialog(
            backgroundColor: Colors.white,
            title: const Text('Тривожна валіза'),
            content: SizedBox(
              width: double.maxFinite,
              child: ListView(
                shrinkWrap: true,
                children: _emergencyBagChecklist.map((item) {
                  final key = item['key'] as String;
                  final isChecked = _emergencyBagItems[key] ?? false;
                  return CheckboxListTile(
                    value: isChecked,
                    onChanged: (value) {
                      setDialogState(() {
                        _emergencyBagItems[key] = value ?? false;
                      });
                      setState(() {}); // Update parent for progress
                      _saveBagData();
                    },
                    title: Text(item['name']),
                    secondary: Icon(item['icon']),
                  );
                }).toList(),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Закрити'),
              ),
            ],
          );
        },
      ),
    );
  }
}
