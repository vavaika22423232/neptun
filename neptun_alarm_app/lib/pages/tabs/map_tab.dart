import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import '../../services/map_ready_notifier.dart';
import '../../services/moderator_service.dart';
import '../../design/design_exports.dart';

/// Map tab — loads the Next.js map in a WebView with ?embed=1
class MapTab extends StatefulWidget {
  const MapTab({super.key});

  @override
  State<MapTab> createState() => _MapTabState();
}

class _MapTabState extends State<MapTab> with AutomaticKeepAliveClientMixin {
  WebViewController? _controller;
  bool _isLoading = true;
  bool _hasError = false;
  bool _platformError = false;
  bool? _lastTheme; // true = dark, false = light

  String _buildMapUrl() {
    final brightness = Theme.of(context).brightness;
    final theme = brightness == Brightness.light ? 'light' : 'dark';
    return 'https://neptun.in.ua/?embed=1&theme=$theme';
  }

  Future<void> _injectAdminCredentials(WebViewController ctrl) async {
    if (!ModeratorService.instance.isModerator) return;
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) return;
    final escaped = Uri.encodeComponent(secret);
    await ctrl.runJavaScript(
      'window.__ADMIN_SECRET = decodeURIComponent("$escaped");',
    );
  }

  @override
  bool get wantKeepAlive => true;

  bool _webViewInitialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_webViewInitialized) {
      _webViewInitialized = true;
      _initWebView();
    } else {
      _checkThemeAndReload();
    }
  }

  Future<void> _initWebView() async {
    // Safety net: dismiss splash even if WebView crashes at platform level
    Future.delayed(const Duration(seconds: 4), () {
      MapReadyNotifier.instance.markReady();
    });

    try {
      final isDark = Theme.of(context).brightness == Brightness.dark;
      _lastTheme = isDark;
      final bgColor = Theme.of(context).colorScheme.surface;
      final ctrl = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(bgColor);

      // Android-specific: enable DOM storage, set cache mode; hardware-accelerated WebGL/Canvas
      if (Platform.isAndroid) {
        final androidCtrl = ctrl.platform as AndroidWebViewController;
        androidCtrl.setMediaPlaybackRequiresUserGesture(false);
        // Force hardware-accelerated rendering of WebGL/Canvas content
        androidCtrl.setTextZoom(100);
      }

      ctrl.setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) {
              setState(() {
                _isLoading = true;
                _hasError = false;
              });
            }
          },
          onProgress: (progress) {
            // Dismiss splash early at 60% — HTML/CSS loaded, JS hydrating
            if (progress >= 60) {
              MapReadyNotifier.instance.markReady();
            }
          },
          onPageFinished: (_) {
            _injectAdminCredentials(ctrl);
            if (mounted) setState(() => _isLoading = false);
            MapReadyNotifier.instance.markReady();
          },
          onWebResourceError: (error) {
            // Only show error screen for main frame failures (page itself).
            // Sub-resource errors (tile 404, CDN script timeout, analytics
            // beacon) are non-critical and should NOT trigger the overlay.
            if (error.isForMainFrame == true && mounted) {
              debugPrint(
                'Map load error: type=${error.errorType} code=${error.errorCode} '
                'desc="${error.description}" url=${error.url}',
              );
              setState(() {
                _isLoading = false;
                _hasError = true;
              });
            }
            // Even on error, dismiss splash so user can see the retry UI
            MapReadyNotifier.instance.markReady();
          },
          onNavigationRequest: (request) {
            if (request.url.startsWith('https://neptun.in.ua')) {
              return NavigationDecision.navigate;
            }
            return NavigationDecision.prevent;
          },
          onSslAuthError: (error) {
            error.cancel();
          },
        ),
      );
      await ctrl.loadRequest(Uri.parse(_buildMapUrl()));
      if (mounted) setState(() => _controller = ctrl);
    } catch (e) {
      debugPrint('WebView init error: $e');
      if (mounted) {
        setState(() {
          _platformError = true;
          _isLoading = false;
        });
      }
      MapReadyNotifier.instance.markReady();
    }
  }

  void _checkThemeAndReload() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (_lastTheme != null && _lastTheme != isDark && _controller != null) {
      _lastTheme = isDark;
      final themeStr = isDark ? 'dark' : 'light';
      _controller!.setBackgroundColor(Theme.of(context).colorScheme.surface);
      // Seamlessly toggle theme without reloading the entire WebView
      _controller!.runJavaScript('if(window.setTheme) window.setTheme("$themeStr");');
    }
  }

  @override
  void dispose() {
    _controller = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;

    if (_platformError) {
      return Container(
        color: NeptunSurfaces.s0,
        padding: NeptunSpacing.pagePadding,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TacticalSurface(
                style: TacticalSurfaceStyle.raised,
                padding: const EdgeInsets.all(NeptunSpacing.xxl),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: NeptunSurfaces.s2,
                        borderRadius: BorderRadius.circular(NeptunRadius.md),
                        border: Border.all(color: NeptunSurfaces.border),
                      ),
                      child: Icon(
                        Icons.map_outlined,
                        size: 28,
                        color: cs.onSurface.withValues(alpha: 0.4),
                      ),
                    ),
                    const SizedBox(height: NeptunSpacing.xl),
                    Text(
                      'Карта недоступна',
                      style: GoogleFonts.plusJakartaSans(
                        color: cs.onSurface,
                        fontSize: NeptunTypography.h2,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: NeptunSpacing.sm),
                    Text(
                      'Перезапустіть додаток',
                      style: GoogleFonts.plusJakartaSans(
                        color: cs.onSurface.withValues(alpha: 0.5),
                        fontSize: NeptunTypography.body,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: NeptunSpacing.xxl),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: () {
                          HapticFeedback.mediumImpact();
                          setState(() {
                            _platformError = false;
                            _isLoading = true;
                          });
                          _initWebView();
                        },
                        icon: const Icon(Icons.refresh_rounded, size: 20),
                        label: const Text('Спробувати знову'),
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(NeptunRadius.md),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Stack(
      children: [
        if (_controller != null)
          Platform.isAndroid
              ? WebViewWidget.fromPlatformCreationParams(
                  params: AndroidWebViewWidgetCreationParams(
                    controller:
                        _controller!.platform as AndroidWebViewController,
                    displayWithHybridComposition: true,
                  ),
                )
              : WebViewWidget(controller: _controller!),
        if (_isLoading)
          Container(
            color: NeptunSurfaces.s0,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 36,
                    height: 36,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: cs.primary,
                    ),
                  ),
                  const SizedBox(height: NeptunSpacing.lg),
                  Text(
                    'Завантаження карти...',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: NeptunTypography.body,
                      fontWeight: FontWeight.w500,
                      color: cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (_hasError && !_isLoading)
          Container(
            color: NeptunSurfaces.s0,
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: NeptunSpacing.xxl),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(NeptunSpacing.xxl),
                      decoration: BoxDecoration(
                        color: NeptunSurfaces.s1,
                        borderRadius: BorderRadius.circular(NeptunRadius.xl),
                        border: Border.all(color: NeptunStatus.alarm.withValues(alpha: 0.3)),
                      ),
                      child: Icon(
                        Icons.cloud_off_rounded,
                        size: 56,
                        color: NeptunStatus.alarm.withValues(alpha: 0.6),
                      ),
                    ),
                    const SizedBox(height: NeptunSpacing.xxl),
                    Text(
                      'Не вдалося завантажити карту',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: NeptunTypography.h2,
                        fontWeight: FontWeight.w700,
                        color: cs.onSurface,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: NeptunSpacing.sm),
                    Text(
                      'Перевірте з\'єднання або спробуйте пізніше',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: NeptunTypography.body,
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: NeptunSpacing.xxl),
                    _TacticalPrimaryButton(
                      label: 'Спробувати знову',
                      icon: Icons.refresh_rounded,
                      onPressed: () async {
                        HapticFeedback.mediumImpact();
                        setState(() {
                          _hasError = false;
                          _isLoading = true;
                        });
                        final url = _buildMapUrl();
                        _controller?.loadRequest(Uri.parse(url));
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _TacticalPrimaryButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onPressed;

  const _TacticalPrimaryButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 20),
        label: Text(label),
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(
            vertical: NeptunSpacing.lg,
            horizontal: NeptunSpacing.xl,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(NeptunRadius.md),
          ),
        ),
      ),
    );
  }
}
