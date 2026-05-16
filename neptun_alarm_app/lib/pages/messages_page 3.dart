import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/widgets/neptun_shimmer.dart';
import '../data/ukraine_regions.dart';
import '../core/widgets/neptun_overlay_insets.dart';
import '../core/pro/pro_features.dart';
import '../design/design_exports.dart';
import '../widgets/ambient_background.dart';
import '../features/regions/presentation/regions_selection_provider.dart';
import 'tabs/widgets/regions_tab_header.dart';

/// Вибір областей/районів для сповіщень.
/// У головному shell вбудовується в [RadarTab] ([embedded]=true); повноекранний
/// каркас зі [Scaffold] лише для окремих маршрутів (наприклад `/alerts`).
/// Стан: [regionsSelectionProvider] (prefs + FCM).
class AlertsPage extends ConsumerStatefulWidget {
  const AlertsPage({super.key, this.embedded = false});

  /// Не дублювати [Scaffold]/[AmbientBackground] — батько вже дає фон (напр. [NeptunTabPageScaffold]).
  final bool embedded;

  @override
  ConsumerState<AlertsPage> createState() => _AlertsPageState();
}

class _AlertsPageState extends ConsumerState<AlertsPage>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  String? _expandedOblast;
  String _searchQuery = '';
  final _searchController = TextEditingController();

  List<Map<String, dynamic>> get _allOblasts => UkraineRegions.allOblasts;
  Map<String, List<String>> get _districtsByOblast =>
      UkraineRegions.districtsByOblast;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  int _selectedOblastCount(Set<String> selected) {
    return _allOblasts.where((o) => selected.contains(o['name'])).length;
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

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final regions = ref.watch(regionsSelectionProvider);
    final cs = Theme.of(context).colorScheme;
    final topInset = widget.embedded
        ? NeptunSpacing.sm
        : neptunContentTopPadding(context) + NeptunSpacing.lg;
    final bottomInset = neptunContentBottomPadding(context);
    final h = NeptunSpacing.screenHorizontal;

    if (regions.isLoading) {
      final loadingBody = SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(h, topInset, h, bottomInset),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const NeptunShimmer(
              width: double.infinity,
              height: 96,
              borderRadius: NeptunSpacing.bentoRadius,
            ),
            const SizedBox(height: NeptunSpacing.md),
            const NeptunShimmer(
              width: double.infinity,
              height: 132,
              borderRadius: NeptunSpacing.bentoRadius,
            ),
            const SizedBox(height: NeptunSpacing.lg),
            const NeptunShimmer(width: 120, height: 14, borderRadius: 6),
            const SizedBox(height: NeptunSpacing.md),
            ...List.generate(
              5,
              (_) => const Padding(
                padding: EdgeInsets.only(bottom: NeptunSpacing.md),
                child: NeptunShimmer(
                  width: double.infinity,
                  height: 76,
                  borderRadius: NeptunRadius.md,
                ),
              ),
            ),
          ],
        ),
      );
      if (widget.embedded) return loadingBody;
      return Scaffold(
        backgroundColor: cs.surface,
        body: Stack(
          children: [
            const AmbientBackground(),
            loadingBody,
          ],
        ),
      );
    }

    final selected = regions.selected;
    final notifier = ref.read(regionsSelectionProvider.notifier);

    final scrollBody = RefreshIndicator(
      onRefresh: notifier.reload,
      color: cs.primary,
      backgroundColor: cs.surfaceContainerHighest,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverPadding(
            padding: EdgeInsets.fromLTRB(h, topInset, h, 0),
            sliver: SliverToBoxAdapter(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  NeptunBentoSurface(
                    margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
                    padding: const EdgeInsets.fromLTRB(
                      NeptunSpacing.lg,
                      NeptunSpacing.lg,
                      NeptunSpacing.lg,
                      NeptunSpacing.sm,
                    ),
                    child: RegionsTabHeader(
                      selectedOblastCount: _selectedOblastCount(selected),
                      totalSelections: selected.length,
                    ),
                  ),
                  NeptunBentoSurface(
                    padding: const EdgeInsets.all(NeptunSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _buildSearchBar(cs),
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: NeptunSpacing.md,
                          ),
                          child: Divider(
                            height: 1,
                            color: Theme.of(context).brightness ==
                                    Brightness.dark
                                ? NeptunSurfaces.border
                                : cs.outline.withValues(alpha: 0.18),
                          ),
                        ),
                        Row(
                          children: [
                            Expanded(
                              child: _quickButton(
                                label: 'Обрати всі',
                                icon: Icons.select_all_rounded,
                                cs: cs,
                                onTap: () {
                                  HapticFeedback.mediumImpact();
                                  notifier.selectAllUkraine();
                                },
                              ),
                            ),
                            const SizedBox(width: NeptunSpacing.sm),
                            Expanded(
                              child: _quickButton(
                                label: 'Скинути',
                                icon: Icons.deselect_rounded,
                                cs: cs,
                                onTap: () {
                                  HapticFeedback.mediumImpact();
                                  notifier.clearAll();
                                },
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  SectionHeader(
                    title: 'Області України',
                    icon: Icons.map_rounded,
                    padding: const EdgeInsets.fromLTRB(
                      0,
                      NeptunSpacing.lg,
                      0,
                      NeptunSpacing.sectionTitleToContent,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_filteredOblasts.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: Padding(
                padding: EdgeInsets.fromLTRB(h, 0, h, bottomInset),
                child: _buildEmptySearchState(cs),
              ),
            )
          else
            SliverPadding(
              padding: EdgeInsets.fromLTRB(h, 0, h, bottomInset),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) {
                    final oblast = _filteredOblasts[i];
                    final name = oblast['name'] as String;
                    return KeyedSubtree(
                      key: ValueKey('oblast_$name'),
                      child: Padding(
                        padding: const EdgeInsets.only(
                          bottom: NeptunSpacing.md,
                        ),
                        child: _buildOblastCard(
                          oblast,
                          cs,
                          selected,
                          notifier,
                        ),
                      ),
                    );
                  },
                  childCount: _filteredOblasts.length,
                ),
              ),
            ),
        ],
      ),
    );

    if (widget.embedded) return scrollBody;
    return Scaffold(
      backgroundColor: cs.surface,
      body: Stack(
        children: [
          const AmbientBackground(),
          scrollBody,
        ],
      ),
    );
  }

  Widget _buildEmptySearchState(ColorScheme cs) {
    return Center(
      child: NeptunBentoSurface(
        padding: const EdgeInsets.symmetric(
          horizontal: NeptunSpacing.xl,
          vertical: NeptunSpacing.xxl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 40,
              color: cs.onSurface.withValues(alpha: 0.35),
            ),
            const SizedBox(height: NeptunSpacing.md),
            Text(
              'Нічого не знайдено',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: NeptunTypography.title,
                fontWeight: FontWeight.w700,
                color: cs.onSurface,
              ),
            ),
            const SizedBox(height: NeptunSpacing.sm),
            Text(
              'Спробуйте іншу назву області або району.',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: NeptunTypography.caption,
                color: cs.onSurface.withValues(alpha: 0.5),
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar(ColorScheme cs) {
    return Container(
      height: 48,
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? NeptunSurfaces.s1
            : cs.surfaceContainer,
        borderRadius: BorderRadius.circular(NeptunRadius.md),
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
            size: 20,
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

  Widget _quickButton({
    required String label,
    required IconData icon,
    required ColorScheme cs,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: NeptunSpacing.md),
        decoration: BoxDecoration(
          color: isDark ? NeptunSurfaces.s1 : cs.surfaceContainer,
          borderRadius: BorderRadius.circular(NeptunRadius.md),
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

  Widget _buildOblastCard(
    Map<String, dynamic> oblast,
    ColorScheme cs,
    Set<String> selected,
    RegionsSelectionNotifier notifier,
  ) {
    final name = oblast['name'] as String;
    final emoji = (oblast['emoji'] ?? oblast['icon']) as String?;
    final isSelected = selected.contains(name);
    final isExpanded = _expandedOblast == name;
    final districts = _districtsByOblast[name];
    final districtList = districts ?? const <String>[];
    final selectedDistricts = districts != null
        ? selected.intersection(districts.toSet())
        : <String>{};

    return RegionTile(
      name: name,
      emoji: emoji,
      isSelected: isSelected,
      isExpanded: isExpanded,
      districts: districts,
      selectedDistricts: selectedDistricts,
      onOblastTap: () {
        if (_expandedOblast == name) {
          HapticFeedback.selectionClick();
          notifier.toggleOblast(name, districtList);
        } else {
          setState(() => _expandedOblast = name);
        }
      },
      onDistrictTap: (d) {
        if (!ProGate.isUnlocked(ProFeature.preciseRaionPush)) {
          _showRaionProSheet(context);
          return;
        }
        HapticFeedback.selectionClick();
        notifier.toggleDistrict(d, name, districtList);
      },
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

  void _showRaionProSheet(BuildContext ctx) {
    HapticFeedback.mediumImpact();
    final cs = Theme.of(ctx).colorScheme;
    showModalBottomSheet<void>(
      context: ctx,
      backgroundColor: Colors.transparent,
      builder: (_) {
        return Container(
          margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 28),
          decoration: BoxDecoration(
            color: cs.surface,
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: NeptunStatus.premium.withValues(alpha: 0.3),
              width: 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: NeptunStatus.premium.withValues(alpha: 0.15),
                ),
                child: Icon(
                  Icons.location_on_rounded,
                  color: NeptunStatus.premium,
                  size: 26,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'PRO — точні push по районах',
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Обирайте конкретний район і отримуйте push лише тоді, коли загроза у вашому місті — а не по всій області.',
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: cs.onSurface.withValues(alpha: 0.65),
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: FilledButton(
                  onPressed: () {
                    Navigator.pop(ctx);
                    ctx.push('/premium');
                  },
                  style: FilledButton.styleFrom(
                    backgroundColor: NeptunStatus.premium,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: Text(
                    'Отримати PRO',
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
