import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../data/ukraine_oblast_geo_loader.dart';

/// Heatmap without filled polygons: geographic [CircleLayer] + boundary [PolylineLayer].
/// Avoids Earcut / heavy translucent fills that crash or hang on pinch-zoom (iOS).
class AlarmHeatmapMapView extends StatefulWidget {
  const AlarmHeatmapMapView({
    super.key,
    required this.geo,
    required this.countsByOblastStateId,
    required this.isDark,
    required this.tileUrl,
  });

  final UkraineOblastGeoData geo;
  final Map<String, int> countsByOblastStateId;
  final bool isDark;
  final String tileUrl;

  @override
  State<AlarmHeatmapMapView> createState() => _AlarmHeatmapMapViewState();
}

class _AlarmHeatmapMapViewState extends State<AlarmHeatmapMapView> {
  List<Polyline<Object>>? _polylines;
  List<CircleMarker<Object>>? _circles;

  @override
  void initState() {
    super.initState();
    _rebuildLayers();
  }

  @override
  void didUpdateWidget(covariant AlarmHeatmapMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.geo != widget.geo ||
        oldWidget.isDark != widget.isDark ||
        !mapEquals(
            oldWidget.countsByOblastStateId, widget.countsByOblastStateId)) {
      _rebuildLayers();
    }
  }

  void _rebuildLayers() {
    final borderColor = widget.isDark
        ? const Color(0xFFFFFFFF).withValues(alpha: 0.24)
        : const Color(0xFF000000).withValues(alpha: 0.3);

    _polylines = widget.geo.oblastBoundaryPolylines(
      color: borderColor,
      strokeWidth: 1.1,
    );

    final maxC = heatmapMaxCount(widget.countsByOblastStateId);
    final circles = <CircleMarker<Object>>[];
    if (maxC > 0) {
      for (final e in widget.geo.centroidByOblastStateId.entries) {
        final id = e.key;
        final n = widget.countsByOblastStateId[id] ?? 0;
        if (n <= 0) continue;
        final t = math.sqrt(n / maxC).clamp(0.0, 1.0);
        // Oblast-scale glow in meters (grows with intensity).
        final radiusM = 28000 + 125000 * t;
        circles.add(
          CircleMarker<Object>(
            point: e.value,
            radius: radiusM,
            useRadiusInMeter: true,
            color: heatmapOblastFillColor(
              id,
              widget.countsByOblastStateId,
              widget.isDark,
            ),
            borderStrokeWidth: 0,
          ),
        );
      }
    }
    _circles = circles;
  }

  @override
  Widget build(BuildContext context) {
    final polylines = _polylines;
    final circles = _circles;
    if (polylines == null || circles == null) {
      return const SizedBox.expand();
    }

    return FlutterMap(
      options: MapOptions(
        initialCenter: const LatLng(48.5, 31.5),
        initialZoom: 6.0,
        initialRotation: 0.0,
        minZoom: 4.0,
        maxZoom: 11.0,
        backgroundColor:
            widget.isDark ? const Color(0xFF141414) : const Color(0xFFF3F4F6),
        interactionOptions: const InteractionOptions(
          flags: InteractiveFlag.drag |
              InteractiveFlag.pinchZoom |
              InteractiveFlag.doubleTapZoom,
        ),
        cameraConstraint: CameraConstraint.containCenter(
          bounds: LatLngBounds(
            const LatLng(44.0, 20.0),
            const LatLng(53.0, 42.0),
          ),
        ),
      ),
      children: [
        TileLayer(
          urlTemplate: widget.tileUrl,
          subdomains: const ['a', 'b', 'c', 'd'],
          userAgentPackageName: 'com.neptunalarm.neptun_alarm_app',
          maxZoom: 18,
        ),
        CircleLayer<Object>(
          circles: circles,
          optimizeRadiusInMeters: true,
        ),
        PolylineLayer<Object>(
          polylines: polylines,
          simplificationTolerance: 4.5,
        ),
      ],
    );
  }
}
