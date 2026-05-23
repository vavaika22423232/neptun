// Fails CI if lib/ contains macOS-style duplicate files (* 2.dart, * 3.dart).
import 'dart:io';

void main() {
  final libDir = Directory('lib');
  if (!libDir.existsSync()) {
    stderr.writeln('lib/ not found — run from neptun_alarm_app root');
    exit(1);
  }

  final duplicates = <String>[];
  for (final entity in libDir.listSync(recursive: true)) {
    if (entity is! File) continue;
    final name = entity.uri.pathSegments.last;
    if (RegExp(r' \d+\.dart$').hasMatch(name)) {
      duplicates.add(entity.path);
    }
  }

  if (duplicates.isEmpty) {
    stdout.writeln('OK: no duplicate dart filenames in lib/');
    exit(0);
  }

  stderr.writeln('Duplicate dart files found (${duplicates.length}):');
  for (final path in duplicates..sort()) {
    stderr.writeln('  $path');
  }
  exit(1);
}
