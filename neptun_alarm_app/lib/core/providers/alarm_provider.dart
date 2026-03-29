import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/data_stream_service.dart';
import '../di/service_locator.dart';

final dataStreamServiceProvider =
    Provider<DataStreamService>((ref) => sl<DataStreamService>());

final alarmStreamProvider = StreamProvider<List<dynamic>>((ref) {
  final ds = ref.watch(dataStreamServiceProvider);
  return ds.alarmStream;
});
