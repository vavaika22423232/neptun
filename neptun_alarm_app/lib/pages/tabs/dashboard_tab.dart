import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';


/// Dashboard tab — loads the Next.js dashboard in a WebView with ?embed=1&theme=...
class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab>
    with AutomaticKeepAliveClientMixin {
  WebViewController? _controller;
  bool _isLoading = true;
  bool _hasError = false;
  bool _platformError = false;
  bool? _lastTheme;

  @override
  bool get wantKeepAlive => true;

  bool _webViewInitialized = false;

  String _buildDashUrl(bool isDark) =>
      'https://neptun.in.ua/dashboard?embed=1&theme=${isDark ? "dark" : "light"}';

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
    try {
      final isDark = Theme.of(context).brightness == Brightness.dark;
      _lastTheme = isDark;
      final dashUrl = _buildDashUrl(isDark);
      final bgColor = Theme.of(context).colorScheme.surface;
      final ctrl = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(bgColor);

      // Android-specific optimizations
      if (Platform.isAndroid) {
        final androidCtrl = ctrl.platform as AndroidWebViewController;
        androidCtrl.setMediaPlaybackRequiresUserGesture(false);
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
          onPageFinished: (_) {
            if (mounted) setState(() => _isLoading = false);
          },
          onWebResourceError: (error) {
            // Only show error screen for main frame failures.
            // Sub-resource errors (tiles, scripts, fonts) are non-critical.
            if (error.isForMainFrame == true && mounted) {
              debugPrint(
                'Dashboard load error: type=${error.errorType} '
                'code=${error.errorCode} desc="${error.description}"',
              );
              setState(() {
                _isLoading = false;
                _hasError = true;
              });
            }
          },
          onNavigationRequest: (request) {
            if (request.url.startsWith('https://neptun.in.ua')) {
              return NavigationDecision.navigate;
            }
            return NavigationDecision.prevent;
          },
        ),
      );
      await ctrl.loadRequest(Uri.parse(dashUrl));
      if (mounted) setState(() => _controller = ctrl);
    } catch (e) {
      debugPrint('Dashboard WebView init error: $e');
      if (mounted) {
        setState(() {
          _platformError = true;
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller = null;
    super.dispose();
  }

  void _checkThemeAndReload() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (_lastTheme != null && _lastTheme != isDark && _controller != null) {
      _lastTheme = isDark;
      final bgColor = Theme.of(context).colorScheme.surface;
      _controller!.setBackgroundColor(bgColor);
      _controller!.loadRequest(Uri.parse(_buildDashUrl(isDark)));
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;

    if (_platformError) {
      return Container(
        color: cs.surface,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.grid_view_outlined,
                size: 48,
                color: cs.onSurface.withValues(alpha: 0.3),
              ),
              const SizedBox(height: 16),
              Text(
                'Дашборд недоступний',
                style: TextStyle(
                  color: cs.onSurface,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Перезапустіть додаток',
                style: TextStyle(color: cs.onSurfaceVariant, fontSize: 14),
              ),
              const SizedBox(height: 24),
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    _platformError = false;
                    _isLoading = true;
                  });
                  _initWebView();
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Спробувати знову'),
              ),
            ],
          ),
        ),
      );
    }

    // Account for AppBar + status bar since AppShell uses extendBodyBehindAppBar
    final topInset = MediaQuery.of(context).padding.top + 52;

    return Stack(
      children: [
        if (_controller != null)
          Padding(
            padding: EdgeInsets.only(top: topInset),
            child: SizedBox.expand(
              child: Platform.isAndroid
                  ? WebViewWidget.fromPlatformCreationParams(
                      params: AndroidWebViewWidgetCreationParams(
                        controller:
                            _controller!.platform as AndroidWebViewController,
                        displayWithHybridComposition: true,
                      ),
                    )
                  : WebViewWidget(controller: _controller!),
            ),
          ),
        if (_isLoading)
          Container(
            color: cs.surface,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 32,
                    height: 32,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: cs.primary,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Завантаження дашборду...',
                    style: TextStyle(color: cs.onSurfaceVariant, fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
        if (_hasError && !_isLoading)
          Container(
            color: cs.surface,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.cloud_off_rounded,
                    size: 48,
                    color: cs.onSurface.withValues(alpha: 0.3),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Не вдалося завантажити дашборд',
                    style: TextStyle(
                      color: cs.onSurface,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Перевірте з\'єднання або спробуйте пізніше',
                    style: TextStyle(color: cs.onSurfaceVariant, fontSize: 14),
                  ),
                  const SizedBox(height: 24),
                  TextButton.icon(
                    onPressed: () {
                      final isDark =
                          Theme.of(context).brightness == Brightness.dark;
                      _controller?.loadRequest(
                        Uri.parse(_buildDashUrl(isDark)),
                      );
                    },
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('Спробувати знову'),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
