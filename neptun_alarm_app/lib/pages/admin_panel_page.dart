import 'dart:convert';
import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import '../config/config.dart';
import '../services/moderator_service.dart';

/// Admin panel — WebView loading neptun.in.ua/admin with auto-login via moderator secret.
/// Visible only when moderator is authenticated.
class AdminPanelPage extends StatefulWidget {
  const AdminPanelPage({super.key});

  @override
  State<AdminPanelPage> createState() => _AdminPanelPageState();
}

class _AdminPanelPageState extends State<AdminPanelPage> {
  WebViewController? _controller;
  bool _isLoading = true;
  bool _hasError = false;
  String? _errorMessage;
  bool _loginAttempted = false;
  bool _webViewInitialized = false;

  static final _baseUrl = ApiConfig.baseUrl;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_webViewInitialized) {
      _webViewInitialized = true;
      _initWebView();
    }
  }

  Future<void> _initWebView() async {
    final surfaceColor = Theme.of(context).colorScheme.surface;
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _hasError = true;
          _errorMessage = 'Спочатку увійдіть як модератор';
        });
      }
      return;
    }

    try {
      final ctrl = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(surfaceColor);

      if (Platform.isAndroid) {
        final androidCtrl = ctrl.platform as AndroidWebViewController;
        androidCtrl.setMediaPlaybackRequiresUserGesture(false);
      }

      ctrl.setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) setState(() => _isLoading = true);
          },
          onPageFinished: (url) => _onPageFinished(ctrl, url, secret),
          onWebResourceError: (error) {
            if (error.isForMainFrame == true && mounted) {
              setState(() {
                _isLoading = false;
                _hasError = true;
                _errorMessage = 'Помилка завантаження';
              });
            }
          },
          onNavigationRequest: (request) {
            if (request.url.startsWith(_baseUrl) ||
                request.url.startsWith('https://neptun.in.ua')) {
              return NavigationDecision.navigate;
            }
            return NavigationDecision.prevent;
          },
          onSslAuthError: (error) => error.cancel(),
        ),
      );

      await ctrl.loadRequest(Uri.parse('$_baseUrl/admin'));
      if (mounted) {
        setState(() {
          _controller = ctrl;
          _webViewInitialized = true;
        });
      }
    } catch (e) {
      debugPrint('AdminPanel WebView init error: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
          _hasError = true;
          _errorMessage = e.toString();
        });
      }
    }
  }

  Future<void> _onPageFinished(
    WebViewController ctrl,
    String url,
    String secret,
  ) async {
    if (!mounted || _loginAttempted) {
      if (mounted) setState(() => _isLoading = false);
      return;
    }

    final uri = Uri.tryParse(url);
    final isNeptunAdmin =
        uri != null &&
        uri.host.contains('neptun.in.ua') &&
        (uri.path == '/admin' || uri.path.startsWith('/admin'));

    if (!isNeptunAdmin) {
      if (mounted) setState(() => _isLoading = false);
      return;
    }

    _loginAttempted = true;
    final escaped = jsonEncode(secret);
    await ctrl.runJavaScript('''
      (function() {
        fetch('/api/admin/auth/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({password: $escaped}),
          credentials: 'include'
        }).then(function(r) {
          if (r.ok) {
            window.location.href = '/admin';
          }
        }).catch(function() {});
      })();
    ''');
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    if (_hasError) {
      return Scaffold(
        appBar: AppBar(title: const Text('Адмін панель')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.admin_panel_settings_rounded,
                  size: 48,
                  color: cs.error,
                ),
                const SizedBox(height: 16),
                Text(
                  _errorMessage ?? 'Помилка',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: cs.onSurface, fontSize: 16),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () {
                    setState(() {
                      _hasError = false;
                      _loginAttempted = false;
                      _webViewInitialized = false;
                    });
                    _initWebView();
                  },
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Спробувати знову'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Адмін панель')),
      body: Stack(
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
              color: cs.surface,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: cs.primary),
                    const SizedBox(height: 16),
                    Text(
                      'Завантаження...',
                      style: TextStyle(
                        color: cs.onSurfaceVariant,
                        fontSize: 14,
                      ),
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
