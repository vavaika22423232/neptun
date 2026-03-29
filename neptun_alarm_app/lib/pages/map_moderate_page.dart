import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'native_map_page.dart';

/// Wrapper for moderator map deletion: Scaffold + AppBar with back button.
class MapModeratePage extends StatelessWidget {
  const MapModeratePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Модерація міток'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: const NativeMapPage(),
    );
  }
}
