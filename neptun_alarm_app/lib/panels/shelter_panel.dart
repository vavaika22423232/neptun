import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'dart:math';
import '../core/error/error_handler.dart';
import '../core/widgets/neptun_card.dart';

class ShelterPanel extends StatefulWidget {
  const ShelterPanel({super.key});

  @override
  State<ShelterPanel> createState() => _ShelterPanelState();
}

class _ShelterPanelState extends State<ShelterPanel> {
  List<Shelter> _shelters = [];
  bool _isLoading = true;
  String? _error;
  Position? _currentPosition;

  @override
  void initState() {
    super.initState();
    _initLocation();
  }

  Future<void> _initLocation() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      LocationPermission permission = await Geolocator.checkPermission();

      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        setState(() {
          _isLoading = false;
          _error = 'Потрібен доступ до геолокації для пошуку укриттів';
        });
        return;
      }

      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() {
          _isLoading = false;
          _error = 'Будь ласка, увімкніть служби геолокації';
        });
        return;
      }

      _currentPosition = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );

      await _loadShelters();
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = userFriendlyErrorMessage(e);
      });
    }
  }

  Future<void> _loadShelters() async {
    if (_currentPosition == null) return;

    try {
      final query =
          '''
      [out:json][timeout:25];
      (
        node["amenity"="shelter"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["bunker_type"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["building"="bunker"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        way["amenity"="shelter"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        way["bunker_type"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        way["building"="bunker"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["shelter_type"="public_transport"](around:1000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["railway"="subway_entrance"](around:1500,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["public_transport"="station"]["subway"="yes"](around:1500,${_currentPosition!.latitude},${_currentPosition!.longitude});
      );
      out body center;
      ''';

      final response = await http
          .post(
            Uri.parse('https://overpass-api.de/api/interpreter'),
            body: query,
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final elements = data['elements'] as List;

        final shelters = elements
            .map((e) {
              double lat =
                  e['lat']?.toDouble() ?? e['center']?['lat']?.toDouble() ?? 0;
              double lon =
                  e['lon']?.toDouble() ?? e['center']?['lon']?.toDouble() ?? 0;

              final tags = e['tags'] as Map<String, dynamic>? ?? {};
              String name = tags['name'] ?? _getShelterTypeName(tags);
              String type = _getShelterType(tags);

              final distance = _calculateDistance(
                _currentPosition!.latitude,
                _currentPosition!.longitude,
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
            })
            .where((s) => s.latitude != 0 && s.longitude != 0)
            .toList();

        shelters.sort((a, b) => a.distance.compareTo(b.distance));

        await _addMetroStations(shelters);

        if (mounted) {
          setState(() {
            _shelters = shelters.take(20).toList();
            _isLoading = false;
          });
        }
      } else {
        setState(() {
          _isLoading = false;
          _error = 'Не вдалося завантажити укриття';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = userFriendlyErrorMessage(e);
        });
      }
    }
  }

  Future<void> _addMetroStations(List<Shelter> shelters) async {
    if (_currentPosition == null) return;

    try {
      final query =
          '''
      [out:json][timeout:15];
      (
        node["railway"="station"]["station"="subway"](around:3000,${_currentPosition!.latitude},${_currentPosition!.longitude});
        node["railway"="subway_entrance"](around:2000,${_currentPosition!.latitude},${_currentPosition!.longitude});
      );
      out body;
      ''';

      final response = await http
          .post(
            Uri.parse('https://overpass-api.de/api/interpreter'),
            body: query,
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final elements = data['elements'] as List;

        for (var e in elements) {
          final tags = e['tags'] as Map<String, dynamic>? ?? {};
          final lat = e['lat']?.toDouble() ?? 0.0;
          final lon = e['lon']?.toDouble() ?? 0.0;

          if (lat == 0 || lon == 0) continue;

          final distance = _calculateDistance(
            _currentPosition!.latitude,
            _currentPosition!.longitude,
            lat,
            lon,
          );

          shelters.add(
            Shelter(
              name: tags['name'] ?? 'Станція метро',
              type: 'metro',
              latitude: lat,
              longitude: lon,
              distance: distance,
              tags: tags,
            ),
          );
        }
      }
    } catch (e) {
      debugPrint('Error loading metro: $e');
    }
  }

  String _getShelterTypeName(Map<String, dynamic> tags) {
    if (tags['railway'] == 'subway_entrance') return 'Вхід у метро';
    if (tags['bunker_type'] != null) return 'Бомбосховище';
    if (tags['building'] == 'bunker') return 'Укриття';
    if (tags['shelter_type'] == 'public_transport') return 'Зупинка-укриття';
    return 'Укриття';
  }

  String _getShelterType(Map<String, dynamic> tags) {
    if (tags['railway'] == 'subway_entrance' || tags['station'] == 'subway') {
      return 'metro';
    }
    if (tags['bunker_type'] != null || tags['building'] == 'bunker') {
      return 'bunker';
    }
    if (tags['shelter_type'] == 'public_transport') return 'transit';
    return 'shelter';
  }

  double _calculateDistance(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const earthRadius = 6371000;
    final dLat = _toRadians(lat2 - lat1);
    final dLon = _toRadians(lon2 - lon1);

    final a =
        sin(dLat / 2) * sin(dLat / 2) +
        cos(_toRadians(lat1)) *
            cos(_toRadians(lat2)) *
            sin(dLon / 2) *
            sin(dLon / 2);

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

    final url = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&origin=${_currentPosition!.latitude},${_currentPosition!.longitude}'
      '&destination=${shelter.latitude},${shelter.longitude}'
      '&travelmode=walking',
    );

    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final colorScheme = Theme.of(context).colorScheme;

    return NeptunCard(
      variant: NeptunCardVariant.elevated,
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            child: Row(
              children: [
                Icon(
                  Icons.shield_rounded,
                  color: colorScheme.primary,
                  size: 18,
                ),
                const SizedBox(width: 8),
                Text(
                  'Укриття',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: colorScheme.onSurface,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: Icon(
                    Icons.refresh,
                    size: 20,
                    color: colorScheme.onSurfaceVariant,
                  ),
                  onPressed: _initLocation,
                ),
              ],
            ),
          ),

          Divider(
            height: 1,
            color: colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),

          // Content
          Expanded(
            child: _isLoading
                ? _buildLoadingState()
                : _error != null
                ? _buildErrorState()
                : _shelters.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
                    itemCount: _shelters.length,
                    itemBuilder: (context, index) {
                      return _buildShelterCard(_shelters[index], isDark);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: CircularProgressIndicator(color: Theme.of(context).colorScheme.primary),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 40,
              color: Theme.of(context).colorScheme.tertiary.withValues(alpha: 0.8),
            ),
            const SizedBox(height: 12),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white60),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return const Center(
      child: Text(
        'Укриттів поблизу не знайдено',
        style: TextStyle(color: Colors.white54),
      ),
    );
  }

  Widget _buildShelterCard(Shelter shelter, bool isDark) {
    final typeInfo = _getShelterTypeInfo(shelter.type);
    final color = typeInfo['color'] as Color;

    return GestureDetector(
      onTap: () => _openInMaps(shelter),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          border: Border.all(color: color.withValues(alpha: 0.2)),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(typeInfo['icon'], color: color, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    shelter.name,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          typeInfo['label'].toUpperCase(),
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: color,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Text(
                        _formatDistance(shelter.distance),
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white70 : Colors.black54,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
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
          'icon': Icons.subway,
          'label': 'Метро',
          'color': const Color(0xFFa8d8ea),
        };
      case 'bunker':
        return {
          'icon': Icons.security,
          'label': 'Укриття',
          'color': Colors.green,
        };
      case 'transit':
        return {
          'icon': Icons.directions_bus,
          'label': 'Зупинка',
          'color': const Color(0xFFFFA726),
        };
      default:
        return {
          'icon': Icons.shield,
          'label': 'Сховище',
          'color': const Color(0xFFb8b5ff),
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
