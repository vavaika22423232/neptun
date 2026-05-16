/// Легасі-матч назв (коли в FCM немає `oblast_id`).
/// «Київ» не можна зіставляти з «Київською обл.» через `String.contains` —
/// «київ» входить у «київськ».
bool isKyivCityOnlyName(String normalizedSelected) {
  return normalizedSelected == 'м. київ' || normalizedSelected == 'київ';
}

bool isKyivOblastFcmName(String normalizedRegion) {
  return normalizedRegion.contains('київськ') &&
      normalizedRegion.contains('область');
}

/// Відповідає [notification_service] легасі-циклам для фонового/foreground-фільтрів
bool legacyNameRegionMatches(
  String selectedRegion,
  String fcmRegion,
  String fcmLocation,
) {
  final normalizedSelected = selectedRegion.toLowerCase().trim();
  final normalizedRegion = fcmRegion.toLowerCase().trim();
  final normalizedLocation = fcmLocation.toLowerCase().trim();

  if (normalizedRegion.contains(normalizedSelected)) {
    if (isKyivCityOnlyName(normalizedSelected) &&
        isKyivOblastFcmName(normalizedRegion)) {
      return false;
    }
    return true;
  }
  if (normalizedSelected.contains(normalizedRegion) && normalizedRegion.isNotEmpty) {
    return true;
  }
  if (normalizedLocation.contains(normalizedSelected)) {
    return true;
  }
  return false;
}
