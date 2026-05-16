import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/widgets/neptun_shimmer.dart';
import '../services/notification_service.dart';
import '../data/ukraine_regions.dart';
import '../design/design_exports.dart';
import 'app_shell.dart';

/// "Сповіщення" tab — region selection with auto-save.
class AlertsPage extends StatefulWidget {
  const AlertsPage({super.key});

  @override
  State<AlertsPage> createState() => _AlertsPageState();
}

class _AlertsPageState extends State<AlertsPage> {
  bool _isLoading = true;
  Set<String> _selectedRegions = {};
  String? _expandedOblast;
  String _searchQuery = '';
  final _searchController = TextEditingController();
  Timer? _debounce;
  bool _saving = false;

  List<Map<String, dynamic>> get _allOblasts => UkraineRegions.allOblasts;
  Map<String, List<String>> get _districtsByOblast =>
      UkraineRegions.districtsByOblast;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadSettings());
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // DATA
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final selected = prefs.getStringList('selected_regions') ?? [];
    if (mounted) {
      setState(() {
        _selectedRegions = selected.toSet();
        _isLoading = false;
      });
    }
  }

  void _scheduleAutoSave() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 800), _saveAndUpdate);
  }

  Future<void> _saveAndUpdate() async {
    if (_saving) return;
    _saving = true;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('selected_regions', _selectedRegions.toList());
      await NotificationService().updateRegions(_selectedRegions.toList());
    } catch (_) {
      // silent
    } finally {
      _saving = false;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════════════════

  void _toggleOblast(String oblast) {
    HapticFeedback.selectionClick();
    setState(() {
      if (_selectedRegions.contains(oblast)) {
        _selectedRegions.remove(oblast);
        final districts = _districtsByOblast[oblast] ?? [];
        for (var d in districts) {
          _selectedRegions.remove(d);
        }
      } else {
        _selectedRegions.add(oblast);
      }
    });
    _scheduleAutoSave();
  }

  void _toggleDistrict(String district, String oblast) {
    HapticFeedback.selectionClick();
    setState(() {
      if (_selectedRegions.contains(district)) {
        _selectedRegions.remove(district);
        final oblastDistricts = _districtsByOblast[oblast] ?? [];
        final hasAny = oblastDistricts.any((d) => _selectedRegions.contains(d));
        if (!hasAny) _selectedRegions.remove(oblast);
      } else {
        // Тільки район — без області. Сповіщення будуть лише для району.
        _selectedRegions.add(district);
      }
    });
    _scheduleAutoSave();
  }

  void _selectAll() {
    HapticFeedback.mediumImpact();
    setState(() {
      for (var o in _allOblasts) {
        _selectedRegions.add(o['name']);
      }
      for (var districts in _districtsByOblast.values) {
        _selectedRegions.addAll(districts);
      }
    });
    _scheduleAutoSave();
  }

  void _clearAll() {
    HapticFeedback.mediumImpact();
    setState(() => _selectedRegions.clear());
    _scheduleAutoSave();
  }

  List<Map<String, dynamic>> get _filteredOblasts {
    if (_searchQuery.isEmpty) return _allOblasts;
    final q = _searchQuery.toLowerCase();
    return _allOblasts.where((o) {
      final name = o['name'].toString().toLowerCase();
      if (name.contains(q)) return true;
      final districts = _districtsByOblast[o['name']] ?? [];
      return districts.any((d) => d.toLowerCase().contains(q));
    }).toList();
  }

  int get _selectedOblastCount {
    return _allOblasts
        .where((o) => _selectedRegions.contains(o['name']))
        .length;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final topInset =
        MediaQuery.of(context).padding.top +
        AppShellState.chromeHeight +
        AppShellState.contentTopGap;

    if (_isLoading) {
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          NeptunSpacing.lg,
          topInset,
          NeptunSpacing.lg,
          NeptunSpacing.xxxl,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const NeptunShimmer(
              width: double.infinity,
              height: 44,
              borderRadius: 12,
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: NeptunShimmer(
                    width: double.infinity,
                    height: 56,
                    borderRadius: 12,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: NeptunShimmer(
                    width: double.infinity,
                    height: 56,
                    borderRadius: 12,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...List.generate(
              5,
              (_) => const Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: NeptunShimmer(
                  width: double.infinity,
                  height: 72,
                  borderRadius: 14,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(
            NeptunSpacing.lg,
            topInset,
            NeptunSpacing.lg,
            0,
          ),
          child: TacticalSurface(
            style: TacticalSurfaceStyle.flat,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Регіони сповіщень',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                          color: cs.onSurface,
                        ),
                      ),
                    ),
                    StatusPill(
                      label: '${_selectedRegions.length}',
                      variant: _selectedRegions.isNotEmpty
                          ? StatusPillVariant.safe
                          : StatusPillVariant.neutral,
                      icon: Icons.notifications_active_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Обрано областей: $_selectedOblastCount · Усього позицій у списку: ${_selectedRegions.length}',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface.withValues(alpha: 0.54),
                  ),
                ),
              ],
            ),
          ),
        ),
        // Search + quick actions
        Padding(
          padding: const EdgeInsets.fromLTRB(
            NeptunSpacing.lg,
            NeptunSpacing.lg,
            NeptunSpacing.lg,
            0,
          ),
          child: _buildSearchBar(cs),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            NeptunSpacing.lg,
            NeptunSpacing.sm,
            NeptunSpacing.lg,
            NeptunSpacing.md,
          ),
          child: Row(
            children: [
              Expanded(
                child: _quickButton(
                  label: 'Обрати всі',
                  icon: Icons.select_all_rounded,
                  cs: cs,
                  onTap: _selectAll,
                ),
              ),
              const SizedBox(width: NeptunSpacing.sm),
              Expanded(
                child: _quickButton(
                  label: 'Скинути',
                  icon: Icons.deselect_rounded,
                  cs: cs,
                  onTap: _clearAll,
                ),
              ),
            ],
          ),
        ),
        SectionHeader(title: 'Області України', icon: Icons.map_rounded),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _loadSettings,
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(
                NeptunSpacing.lg,
                0,
                NeptunSpacing.lg,
                NeptunSpacing.xxxl,
              ),
              itemCount: _filteredOblasts.length,
              itemBuilder: (ctx, i) =>
                  _buildOblastCard(_filteredOblasts[i], cs),
            ),
          ),
        ),
      ],
    );
  }

  // ─── Search bar ────────────────────────────────────────────────────────

  Widget _buildSearchBar(ColorScheme cs) {
    return Container(
      height: 50,
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? NeptunSurfaces.s1
            : cs.surfaceContainer,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: Theme.of(context).brightness == Brightness.dark
              ? NeptunSurfaces.border
              : cs.outline.withValues(alpha: 0.3),
          width: 0.5,
        ),
      ),
      child: TextField(
        controller: _searchController,
        onChanged: (v) => setState(() => _searchQuery = v),
        style: GoogleFonts.plusJakartaSans(color: cs.onSurface, fontSize: 14),
        decoration: InputDecoration(
          hintText: 'Пошук області чи району...',
          hintStyle: GoogleFonts.plusJakartaSans(
            color: cs.onSurface.withValues(alpha: 0.35),
            fontSize: 14,
          ),
          prefixIcon: Icon(
            Icons.search_rounded,
            color: cs.onSurface.withValues(alpha: 0.4),
            size: 21,
          ),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: Icon(
                    Icons.close_rounded,
                    color: cs.onSurfaceVariant,
                    size: 18,
                  ),
                  onPressed: () {
                    _searchController.clear();
                    setState(() => _searchQuery = '');
                  },
                )
              : null,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 10,
          ),
        ),
      ),
    );
  }

  // ─── Quick button ──────────────────────────────────────────────────────

  Widget _quickButton({
    required String label,
    required IconData icon,
    required ColorScheme cs,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: isDark ? NeptunSurfaces.s1 : cs.surfaceContainer,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isDark
                ? NeptunSurfaces.border
                : cs.outline.withValues(alpha: 0.3),
            width: 0.5,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 18, color: cs.primary),
            const SizedBox(width: NeptunSpacing.sm),
            Text(
              label,
              style: GoogleFonts.plusJakartaSans(
                color: cs.onSurface,
                fontSize: NeptunTypography.caption,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Oblast card ────────────────────────────────────────────────────────

  Widget _buildOblastCard(Map<String, dynamic> oblast, ColorScheme cs) {
    final name = oblast['name'] as String;
    final emoji = (oblast['emoji'] ?? oblast['icon']) as String?;
    final isSelected = _selectedRegions.contains(name);
    final isExpanded = _expandedOblast == name;
    final districts = _districtsByOblast[name];
    final selectedDistricts = districts != null
        ? _selectedRegions.intersection(districts.toSet())
        : <String>{};

    return RegionTile(
      name: name,
      emoji: emoji,
      isSelected: isSelected,
      isExpanded: isExpanded,
      districts: districts,
      selectedDistricts: selectedDistricts,
      onOblastTap: () => setState(() {
        if (_expandedOblast == name) {
          _toggleOblast(name);
        } else {
          _expandedOblast = name;
        }
      }),
      onDistrictTap: (d) => _toggleDistrict(d, name),
      onExpandTap: (districts != null && districts.isNotEmpty)
          ? () {
              HapticFeedback.selectionClick();
              setState(() {
                _expandedOblast = isExpanded ? null : name;
              });
            }
          : null,
    );
  }
}
