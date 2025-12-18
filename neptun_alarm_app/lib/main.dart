import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const NeptunAlarmApp());
}

class NeptunAlarmApp extends StatelessWidget {
  const NeptunAlarmApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Neptun Alarm Map',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const MainPage(),
    );
  }
}

class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => _MainPageState();
}

class _MainPageState extends State<MainPage> {
  int _selectedIndex = 0;
  
  final List<Widget> _pages = [
    const MapPage(),
    const MessagesPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.map),
            label: 'Карта',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.list),
            label: 'Повідомлення',
          ),
        ],
      ),
    );
  }
}

class MapPage extends StatefulWidget {
  const MapPage({super.key});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.white)
      ..enableZoom(true)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {},
          onPageStarted: (String url) {
            print('Page started loading: $url');
          },
          onPageFinished: (String url) {
            print('Page finished loading: $url');
          },
          onWebResourceError: (WebResourceError error) {
            print('WebView error: ${error.description}');
          },
          onNavigationRequest: (NavigationRequest request) {
            return NavigationDecision.navigate;
          },
        ),
      )
      ..clearCache()
      ..loadRequest(
        Uri.parse('https://neptun.in.ua/map-only'),
        headers: {
          'Cache-Control': 'no-cache',
        },
      );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: WebViewWidget(controller: _controller),
    );
  }
}

class MessagesPage extends StatefulWidget {
  const MessagesPage({super.key});

  @override
  State<MessagesPage> createState() => _MessagesPageState();
}

class _MessagesPageState extends State<MessagesPage> {
  List<AlarmMessage> _messages = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    try {
      final response = await http.get(Uri.parse('https://neptun.in.ua/api/messages'));
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        setState(() {
          _messages = (data['messages'] as List)
              .map((m) => AlarmMessage.fromJson(m))
              .toList();
          _isLoading = false;
        });
      }
    } catch (e) {
      print('Error loading messages: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Повідомлення (${_messages.length})'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _loadMessages();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  child: ListTile(
                    leading: Icon(
                      message.type.contains('БпЛА') || message.type.contains('дрон')
                          ? Icons.airplanemode_active
                          : Icons.rocket_launch,
                      color: message.type.contains('БпЛА') || message.type.contains('дрон')
                          ? Colors.orange
                          : Colors.red,
                    ),
                    title: Text(message.location),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(message.type),
                        Text(
                          message.timestamp,
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                    isThreeLine: true,
                  ),
                );
              },
            ),
    );
  }
}

class AlarmMessage {
  final String type;
  final String location;
  final String timestamp;
  final double? latitude;
  final double? longitude;
  final String text;

  AlarmMessage({
    required this.type,
    required this.location,
    required this.timestamp,
    this.latitude,
    this.longitude,
    required this.text,
  });

  factory AlarmMessage.fromJson(Map<String, dynamic> json) {
    return AlarmMessage(
      type: json['type'] ?? 'Невідомо',
      location: json['location'] ?? 'Невідоме місце',
      timestamp: json['timestamp'] ?? '',
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      text: json['text'] ?? '',
    );
  }
}
