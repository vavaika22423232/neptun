import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../config/prefs_keys.dart';
import '../../pages/app_shell.dart';
import '../../pages/tabs/map_tab.dart';
import '../../pages/tabs/radar_tab.dart';
import '../../pages/tabs/chat_tab.dart';
import '../../pages/tabs/profile_tab.dart';
import '../../pages/onboarding_page.dart';
import '../../pages/premium_page.dart';
import '../../pages/feedback_page.dart';
import '../../pages/feedback_moderation_page.dart';
import '../../pages/admin_panel_page.dart';
import '../../pages/chat_admin_page.dart';
import '../../pages/complaints_page.dart';
import '../../pages/shelters_page.dart';
import '../../pages/messages_page.dart';
import '../../pages/profile_page.dart';
import '../../features/trust/presentation/trust_center_page.dart';
import '../../features/radar/presentation/threat_dashboard_page.dart';
import '../../features/history/presentation/alarm_history_page.dart';
import '../../features/analytics/presentation/personal_analytics_page.dart';
import '../../features/heatmap/presentation/heatmap_page.dart';
import '../../features/briefing/presentation/briefing_page.dart';

class AppRouter {
  final SharedPreferences prefs;
  late final GoRouter router;

  AppRouter({required this.prefs}) {
    router = GoRouter(
      initialLocation: '/',
      redirect: (context, state) {
        final isFirstLaunch = prefs.getBool(PrefsKeys.firstLaunch) ?? true;
        final location = state.matchedLocation;

        if (isFirstLaunch && location != '/onboarding') return '/onboarding';
        if (!isFirstLaunch && location == '/onboarding') return '/';

        return null;
      },
      routes: [
        GoRoute(
          path: '/onboarding',
          builder: (context, state) => const OnboardingPage(),
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) =>
              AppShell(navigationShell: navigationShell),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/',
                  pageBuilder: (context, state) =>
                      const NoTransitionPage(child: MapTab()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/radar',
                  pageBuilder: (context, state) =>
                      _shellTabPage(context, state, const RadarTab()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/chat',
                  pageBuilder: (context, state) =>
                      _shellTabPage(context, state, const ChatTab()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/profile',
                  pageBuilder: (context, state) =>
                      _shellTabPage(context, state, const ProfileTab()),
                ),
              ],
            ),
          ],
        ),
        GoRoute(
          path: '/premium',
          pageBuilder: (context, state) =>
              _fadeThroughPage(context, state, const PremiumPage()),
        ),
        GoRoute(
          path: '/feedback',
          pageBuilder: (context, state) =>
              _fadeThroughPage(context, state, const FeedbackPage()),
        ),
        GoRoute(
          path: '/feedback-moderation',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const FeedbackModerationPage()),
        ),
        GoRoute(
          path: '/admin',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const AdminPanelPage()),
        ),
        GoRoute(
          path: '/chat-admin',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const ChatAdminPage()),
        ),
        GoRoute(
          path: '/complaints',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const ComplaintsPage()),
        ),
        GoRoute(
          path: '/shelters',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const SheltersPage()),
        ),
        GoRoute(
          path: '/alerts',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const AlertsPage()),
        ),
        GoRoute(
          path: '/profile-page',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const ProfilePage()),
        ),
        GoRoute(
          path: '/trust',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const TrustCenterPage()),
        ),
        GoRoute(
          path: '/history',
          pageBuilder: (context, state) =>
              _sharedAxisPage(context, state, const AlarmHistoryPage()),
        ),
        GoRoute(
          path: '/analytics',
          pageBuilder: (context, state) =>
              _sharedAxisPage(context, state, const PersonalAnalyticsPage()),
        ),
        GoRoute(
          path: '/heatmap',
          pageBuilder: (context, state) =>
              _sharedAxisPage(context, state, const HeatmapPage()),
        ),
        GoRoute(
          path: '/radar-full',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const ThreatDashboardPage()),
        ),
        GoRoute(
          path: '/briefing',
          pageBuilder: (context, state) =>
              _slideUpPage(context, state, const BriefingPage()),
        ),
      ],
    );
  }

  /// Bottom tabs: light fade + micro-slide (IndexedStack still keeps state;
  /// this runs when the shell shows the branch and improves perceived motion on mobile).
  static CustomTransitionPage<void> _shellTabPage(
    BuildContext context,
    GoRouterState state,
    Widget child,
  ) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 260),
      reverseTransitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 200),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        if (reduceMotion) return child;
        final curved = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
        );
        return FadeTransition(
          opacity: Tween<double>(begin: 0.88, end: 1.0).animate(curved),
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.02),
              end: Offset.zero,
            ).animate(curved),
            child: child,
          ),
        );
      },
    );
  }

  static CustomTransitionPage _slideUpPage(
    BuildContext context,
    GoRouterState state,
    Widget child,
  ) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return CustomTransitionPage(
      key: state.pageKey,
      child: child,
      transitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 320),
      reverseTransitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 260),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        if (reduceMotion) return child;
        return SlideTransition(
          position: Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero)
              .animate(
                CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
              ),
          child: FadeTransition(opacity: animation, child: child),
        );
      },
    );
  }

  /// Fade-through: opacity crossfade (for overlay-style pages).
  static CustomTransitionPage _fadeThroughPage(
    BuildContext context,
    GoRouterState state,
    Widget child,
  ) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return CustomTransitionPage(
      key: state.pageKey,
      child: child,
      transitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 280),
      reverseTransitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 220),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        if (reduceMotion) return child;
        return FadeTransition(
          opacity: CurvedAnimation(parent: animation, curve: Curves.easeInOut),
          child: child,
        );
      },
    );
  }

  /// Shared-axis: slide horizontally for drill-down feel.
  static CustomTransitionPage _sharedAxisPage(
    BuildContext context,
    GoRouterState state,
    Widget child,
  ) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return CustomTransitionPage(
      key: state.pageKey,
      child: child,
      transitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 300),
      reverseTransitionDuration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 240),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        if (reduceMotion) return child;
        return SlideTransition(
          position:
              Tween<Offset>(
                begin: const Offset(0.05, 0),
                end: Offset.zero,
              ).animate(
                CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
              ),
          child: FadeTransition(
            opacity: CurvedAnimation(
              parent: animation,
              curve: const Interval(0.0, 0.5, curve: Curves.easeIn),
            ),
            child: child,
          ),
        );
      },
    );
  }
}
