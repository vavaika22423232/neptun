import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'dart:math';
import '../core/error/error_handler.dart';

/// Координати центрів міст для пошуку укриттів без GPS
const Map<String, ({double lat, double lon})> _cityCoordinates = {
  'Київ': (lat: 50.4501, lon: 30.5234),
  'Харків': (lat: 49.9935, lon: 36.2304),
  'Одеса': (lat: 46.4825, lon: 30.7233),
  'Дніпро': (lat: 48.4647, lon: 35.0462),
  'Львів': (lat: 49.8397, lon: 24.0297),
  'Запоріжжя': (lat: 47.8388, lon: 35.1396),
  'Вінниця': (lat: 49.2328, lon: 28.4681),
  'Чернігів': (lat: 51.4982, lon: 31.2893),
  'Суми': (lat: 50.9077, lon: 34.7981),
  'Полтава': (lat: 49.5883, lon: 34.5514),
  'Черкаси': (lat: 49.4444, lon: 32.0598),
  'Кропивницький': (lat: 48.5132, lon: 32.2597),
  'Житомир': (lat: 50.2547, lon: 28.6587),
  'Чернівці': (lat: 48.2917, lon: 25.9352),
  'Рівне': (lat: 50.6199, lon: 26.2516),
  'Івано-Франківськ': (lat: 48.9226, lon: 24.7111),
  'Тернопіль': (lat: 49.5535, lon: 25.5948),
  'Ужгород': (lat: 48.6208, lon: 22.2879),
  'Луцьк': (lat: 50.7472, lon: 25.3254),
  'Миколаїв': (lat: 46.9750, lon: 31.9946),
  'Херсон': (lat: 46.6354, lon: 32.6169),
  'Маріуполь': (lat: 47.0962, lon: 37.5400),
};

/// Сторінка пошуку укриттів поруч
class SheltersPage extends StatefulWidget {
  const SheltersPage({super.key});

  @override
  State<SheltersPage> createState() => _SheltersPageState();
}

class _SheltersPageState extends State<SheltersPage> {
  List<Shelter> _shelters = [];
  bool _isLoading = true;
  String? _error;
  Position? _currentPosition;
  double? _searchLat;
  double? _searchLon;
  String? _selectedCityName;
  bool _locationPermissionGranted = false;

  @override
  void initState() {
    super.initState();
    _initLocation();
  }

  void _searchByCity(String cityName) {
    final coords = _cityCoordinates[cityName];
    if (coords == null) return;
    HapticFeedback.lightImpact();
    setState(() {
      _error = null;
      _searchLat = coords.lat;
      _searchLon = coords.lon;
      _selectedCityName = cityName;
      _currentPosition = null;
      _isLoading = true;
    });
    _loadShelters();
  }

  void _showCityPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: BoxDecoration(
          color: Theme.of(ctx).colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Оберіть місто для пошуку укриттів',
                  style: Theme.of(ctx).textTheme.titleMedium,
                ),
              ),
              const Divider(height: 1),
              ..._cityCoordinates.keys.map((name) => ListTile(
                title: Text(name),
                leading: const Icon(Icons.location_city_rounded),
                onTap: () {
                  Navigator.pop(ctx);
                  _searchByCity(name);
                },
              )),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _initLocation() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Перевірка дозволу на геолокацію
      LocationPermission permission = await Geolocator.checkPermission();
      
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        setState(() {
          _isLoading = false;
          _error = 'Для пошуку укриттів потрібен доступ до геолокації';
          _locationPermissionGranted = false;
        });
        return;
      }

      // Перевірка чи увімкнена геолокація
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() {
          _isLoading = false;
          _error = 'Увімкніть геолокацію для пошуку укриттів';
        });
        return;
      }

      _locationPermissionGranted = true;

      // Отримання позиції
      _currentPosition = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
      _searchLat = _currentPosition!.latitude;
      _searchLon = _currentPosition!.longitude;
      _selectedCityName = null;

      await _loadShelters();
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = userFriendlyErrorMessage(e);
      });
    }
  }

  Future<void> _loadShelters() async {
    if (_searchLat == null || _searchLon == null) return;

    final lat = _searchLat!;
    final lon = _searchLon!;

    try {
      // Запит до Overpass API для пошуку укриттів поруч
      final query = '''
      [out:json][timeout:25];
      (
        node["amenity"="shelter"](around:2000,$lat,$lon);
        node["bunker_type"](around:2000,$lat,$lon);
        node["building"="bunker"](around:2000,$lat,$lon);
        way["amenity"="shelter"](around:2000,$lat,$lon);
        way["bunker_type"](around:2000,$lat,$lon);
        way["building"="bunker"](around:2000,$lat,$lon);
        node["shelter_type"="public_transport"](around:1000,$lat,$lon);
        node["railway"="subway_entrance"](around:1500,$lat,$lon);
        node["public_transport"="station"]["subway"="yes"](around:1500,$lat,$lon);
      );
      out body center;
      ''';

      final response = await http.post(
        Uri.parse('https://overpass-api.de/api/interpreter'),
        body: query,
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final elements = data['elements'] as List;

        final shelters = elements.map((e) {
          double lat = e['lat']?.toDouble() ?? e['center']?['lat']?.toDouble() ?? 0;
          double lon = e['lon']?.toDouble() ?? e['center']?['lon']?.toDouble() ?? 0;
          
          final tags = e['tags'] as Map<String, dynamic>? ?? {};
          String name = tags['name'] ?? _getShelterTypeName(tags);
          String type = _getShelterType(tags);
          
          final distance = _calculateDistance(
            _searchLat!,
            _searchLon!,
            lat,
            lon,
          );

          return Shelter(
            name: name,
            type: type,
            latitude: lat,
            longitude: lon,
            distance: distance,
            tags: tags,
          );
        }).where((s) => s.latitude != 0 && s.longitude != 0).toList();

        // Сортування по відстані
        shelters.sort((a, b) => a.distance.compareTo(b.distance));

        // Додаємо підземні паркінги та станції метро як потенційні укриття
        await _addMetroStations(shelters);

        setState(() {
          _shelters = shelters.take(20).toList();
          _isLoading = false;
        });
      } else {
        setState(() {
          _isLoading = false;
          _error = 'Помилка завантаження укриттів';
        });
      }
    } catch (e) {
        setState(() {
          _isLoading = false;
          _error = userFriendlyErrorMessage(e);
        });
    }
  }

  Future<void> _addMetroStations(List<Shelter> shelters) async {
    if (_searchLat == null || _searchLon == null) return;

    final centerLat = _searchLat!;
    final centerLon = _searchLon!;

    try {
      final query = '''
      [out:json][timeout:15];
      (
        node["railway"="station"]["station"="subway"](around:3000,$centerLat,$centerLon);
        node["railway"="subway_entrance"](around:2000,$centerLat,$centerLon);
      );
      out body;
      ''';

      final response = await http.post(
        Uri.parse('https://overpass-api.de/api/interpreter'),
        body: query,
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final elements = data['elements'] as List;

        for (var e in elements) {
          final tags = e['tags'] as Map<String, dynamic>? ?? {};
          final lat = e['lat']?.toDouble() ?? 0.0;
          final lon = e['lon']?.toDouble() ?? 0.0;
          
          if (lat == 0 || lon == 0) continue;

          final distance = _calculateDistance(
            centerLat,
            centerLon,
            lat,
            lon,
          );

          shelters.add(Shelter(
            name: tags['name'] ?? 'Станція метро',
            type: 'metro',
            latitude: lat,
            longitude: lon,
            distance: distance,
            tags: tags,
          ));
        }
      }
    } catch (e) {
      debugPrint('Error loading metro: $e');
    }
  }

  String _getShelterTypeName(Map<String, dynamic> tags) {
    if (tags['railway'] == 'subway_entrance') return 'Вхід в метро';
    if (tags['bunker_type'] != null) return 'Бомбосховище';
    if (tags['building'] == 'bunker') return 'Бункер';
    if (tags['shelter_type'] == 'public_transport') return 'Зупинка';
    return 'Укриття';
  }

  String _getShelterType(Map<String, dynamic> tags) {
    if (tags['railway'] == 'subway_entrance' || tags['station'] == 'subway') return 'metro';
    if (tags['bunker_type'] != null || tags['building'] == 'bunker') return 'bunker';
    if (tags['shelter_type'] == 'public_transport') return 'transit';
    return 'shelter';
  }

  double _calculateDistance(double lat1, double lon1, double lat2, double lon2) {
    const earthRadius = 6371000; // в метрах
    final dLat = _toRadians(lat2 - lat1);
    final dLon = _toRadians(lon2 - lon1);
    
    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_toRadians(lat1)) * cos(_toRadians(lat2)) *
        sin(dLon / 2) * sin(dLon / 2);
    
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    
    return earthRadius * c;
  }

  double _toRadians(double degree) => degree * pi / 180;

  String _formatDistance(double meters) {
    if (meters < 1000) {
      return '${meters.round()} м';
    }
    return '${(meters / 1000).toStringAsFixed(1)} км';
  }

  Future<void> _openInMaps(Shelter shelter) async {
    HapticFeedback.mediumImpact();
    final origLat = _searchLat ?? _currentPosition?.latitude ?? shelter.latitude;
    final origLon = _searchLon ?? _currentPosition?.longitude ?? shelter.longitude;
    final url = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&origin=$origLat,$origLon'
      '&destination=${shelter.latitude},${shelter.longitude}'
      '&travelmode=walking'
    );

    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final glassColor = Colors.white.withValues(alpha: isDark ? 0.15 : 0.25);
    final glassBorderColor = Colors.white.withValues(alpha: isDark ? 0.2 : 0.4);

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [const Color(0xFF000000), const Color(0xFF0A0A0A), const Color(0xFF000000)]
                : [Theme.of(context).colorScheme.primary, Theme.of(context).colorScheme.primary.withValues(alpha: 0.7), Theme.of(context).colorScheme.primary.withValues(alpha: 0.9)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Custom AppBar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_rounded, color: Colors.white),
                      onPressed: () => Navigator.pop(context),
                    ),
                    Expanded(
                      child: Text(
                        _selectedCityName != null
                            ? 'Укриття: $_selectedCityName'
                            : 'Укриття поруч',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    if (_selectedCityName != null)
                      IconButton(
                        icon: const Icon(Icons.location_city_rounded, color: Colors.white),
                        onPressed: _showCityPicker,
                        tooltip: 'Змінити місто',
                      ),
                    IconButton(
                      icon: const Icon(Icons.refresh_rounded, color: Colors.white),
                      onPressed: _initLocation,
                      tooltip: 'Оновити (спробувати GPS)',
                    ),
                  ],
                ),
              ),
              
              // Content
              Expanded(
                child: _isLoading
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const CircularProgressIndicator(color: Colors.white),
                            const SizedBox(height: 16),
                            Text(
                              'Шукаємо укриття поруч...',
                              style: TextStyle(color: Colors.white.withValues(alpha: 0.8)),
                            ),
                          ],
                        ),
                      )
                    : _error != null
                        ? _buildGlassErrorWidget(glassColor, glassBorderColor)
                        : _shelters.isEmpty
                            ? _buildGlassEmptyWidget(glassColor, glassBorderColor)
                            : _buildGlassSheltersList(glassColor, glassBorderColor),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGlassErrorWidget(Color glassColor, Color glassBorderColor) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: glassColor,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: glassBorderColor),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.3),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.location_off_rounded,
                  size: 64,
                  color: Colors.orange,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 16,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 24),
              GestureDetector(
                onTap: _initLocation,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: glassBorderColor),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.refresh_rounded, color: Colors.white),
                      const SizedBox(width: 8),
                      const Text(
                        'Спробувати ще',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              GestureDetector(
                onTap: _showCityPicker,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: glassBorderColor),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.location_city_rounded, color: Colors.white),
                      const SizedBox(width: 8),
                      Text(
                        'Оберіть місто для пошуку',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.95), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              if (!_locationPermissionGranted) ...[
                const SizedBox(height: 12),
                GestureDetector(
                  onTap: () => Geolocator.openAppSettings(),
                  child: Text(
                    'Відкрити налаштування',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.7),
                      decoration: TextDecoration.underline,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGlassEmptyWidget(Color glassColor, Color glassBorderColor) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: glassColor,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: glassBorderColor),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.search_off_rounded,
                  size: 64,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Укриттів не знайдено',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Спробуйте пошукати в іншому місці',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.8),
                ),
              ),
              const SizedBox(height: 24),
              GestureDetector(
                onTap: _showCityPicker,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: glassBorderColor),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.location_city_rounded, color: Colors.white, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Оберіть інше місто',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.95), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGlassSheltersList(Color glassColor, Color glassBorderColor) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _shelters.length,
      itemBuilder: (context, index) {
        final shelter = _shelters[index];
        return _buildGlassShelterCard(shelter, glassColor, glassBorderColor);
      },
    );
  }

  Widget _buildGlassShelterCard(Shelter shelter, Color glassColor, Color glassBorderColor) {
    final typeInfo = _getShelterTypeInfo(shelter.type);
    
    return GestureDetector(
      onTap: () => _openInMaps(shelter),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: glassColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: glassBorderColor),
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: typeInfo['color'].withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                typeInfo['icon'],
                color: typeInfo['color'],
                size: 28,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    shelter.name,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Colors.white,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: typeInfo['color'].withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          typeInfo['label'],
                          style: TextStyle(
                            fontSize: 11,
                            color: typeInfo['color'],
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.directions_walk_rounded,
                        size: 14,
                        color: Colors.white.withValues(alpha: 0.7),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _formatDistance(shelter.distance),
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.white.withValues(alpha: 0.8),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.directions_rounded,
                color: Colors.white,
                size: 22,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Map<String, dynamic> _getShelterTypeInfo(String type) {
    switch (type) {
      case 'metro':
        return {
          'icon': Icons.subway_rounded,
          'label': 'Метро',
          'color': Colors.blue,
        };
      case 'bunker':
        return {
          'icon': Icons.security_rounded,
          'label': 'Бомбосховище',
          'color': Colors.green,
        };
      case 'transit':
        return {
          'icon': Icons.directions_bus_rounded,
          'label': 'Зупинка',
          'color': Colors.orange,
        };
      default:
        return {
          'icon': Icons.shield_rounded,
          'label': 'Укриття',
          'color': const Color(0xFF4A90E2),
        };
    }
  }
}

class Shelter {
  final String name;
  final String type;
  final double latitude;
  final double longitude;
  final double distance;
  final Map<String, dynamic> tags;

  Shelter({
    required this.name,
    required this.type,
    required this.latitude,
    required this.longitude,
    required this.distance,
    required this.tags,
  });
}
