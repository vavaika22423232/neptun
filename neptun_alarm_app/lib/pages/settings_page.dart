import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/notification_service.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final List<String> _allRegions = [
    'Вінницька область',
    'Волинська область',
    'Дніпропетровська область',
    'Донецька область',
    'Житомирська область',
    'Закарпатська область',
    'Запорізька область',
    'Івано-Франківська область',
    'Київська область',
    'Київ',
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
  ];

  Set<String> _selectedRegions = {};
  bool _notificationsEnabled = true;
  bool _isLoading = true;
  String? _fcmToken;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final savedRegions = prefs.getStringList('selected_regions') ?? [];
    final enabled = prefs.getBool('notifications_enabled') ?? true;
    final token = NotificationService().fcmToken;

    setState(() {
      _selectedRegions = savedRegions.toSet();
      _notificationsEnabled = enabled;
      _fcmToken = token;
      _isLoading = false;
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('selected_regions', _selectedRegions.toList());
    await prefs.setBool('notifications_enabled', _notificationsEnabled);
    
    await NotificationService().updateRegions(_selectedRegions.toList());
  }

  void _toggleRegion(String region) {
    setState(() {
      if (_selectedRegions.contains(region)) {
        _selectedRegions.remove(region);
      } else {
        _selectedRegions.add(region);
      }
    });
    _saveSettings();
  }

  void _selectAll() {
    setState(() {
      _selectedRegions = _allRegions.toSet();
    });
    _saveSettings();
  }

  void _deselectAll() {
    setState(() {
      _selectedRegions.clear();
    });
    _saveSettings();
  }

  Future<void> _sendTestNotification() async {
    await NotificationService().sendTestNotification();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Тестове сповіщення надіслано')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Налаштування'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Notifications toggle
          Card(
            child: SwitchListTile(
              title: const Text('Увімкнути сповіщення'),
              subtitle: Text(
                _notificationsEnabled 
                    ? 'Ви отримуватимете сповіщення про загрози'
                    : 'Сповіщення вимкнено',
              ),
              value: _notificationsEnabled,
              onChanged: (value) {
                setState(() {
                  _notificationsEnabled = value;
                });
                NotificationService().setNotificationsEnabled(value);
                _saveSettings();
              },
            ),
          ),
          
          const SizedBox(height: 16),

          // FCM Token status
          if (_fcmToken != null)
            Card(
              child: ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: const Text('Підключено'),
                subtitle: Text('Token: ${_fcmToken!.substring(0, 20)}...'),
              ),
            ),

          const SizedBox(height: 8),

          // Test notification button
          Card(
            child: ListTile(
              leading: const Icon(Icons.notifications_active),
              title: const Text('Надіслати тестове сповіщення'),
              onTap: _sendTestNotification,
            ),
          ),

          const SizedBox(height: 24),

          // Region selection header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Оберіть області (${_selectedRegions.length}/${_allRegions.length})',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Row(
                children: [
                  TextButton(
                    onPressed: _selectAll,
                    child: const Text('Усі'),
                  ),
                  TextButton(
                    onPressed: _deselectAll,
                    child: const Text('Скасувати'),
                  ),
                ],
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Regions list
          Card(
            child: Column(
              children: _allRegions.map((region) {
                final isSelected = _selectedRegions.contains(region);
                return CheckboxListTile(
                  title: Text(region),
                  value: isSelected,
                  onChanged: (_) => _toggleRegion(region),
                  activeColor: Theme.of(context).colorScheme.primary,
                );
              }).toList(),
            ),
          ),

          const SizedBox(height: 24),

          // Info card
          Card(
            color: Colors.blue.shade50,
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue),
                      SizedBox(width: 8),
                      Text(
                        'Як це працює',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.blue,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Оберіть області, про які ви хочете отримувати сповіщення. '
                    'Коли з\'явиться загроза в обраній області, ви миттєво '
                    'отримаєте push-сповіщення на телефон, навіть якщо додаток закритий.',
                    style: TextStyle(fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
