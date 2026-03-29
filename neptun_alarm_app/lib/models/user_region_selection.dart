/// Вибір регіонів користувача
/// Зберігає ТІЛЬКИ ID, ніяких назв
class UserRegionSelection {
  /// Якщо користувач обрав всю область
  final Set<String> oblastIds;
  
  /// Якщо користувач обрав конкретні райони
  final Set<String> raionIds;
  
  /// Якщо користувач обрав конкретний населений пункт
  final String? settlementId;

  const UserRegionSelection({
    Set<String>? oblastIds,
    this.raionIds = const {},
    this.settlementId,
  }) : oblastIds = oblastIds ?? const {};

  factory UserRegionSelection.fromJson(Map<String, dynamic> json) {
    final legacyOblastId = json['oblastId'] as String?;
    final rawOblastIds = json['oblastIds'] as List<dynamic>?;
    final Set<String> parsedOblastIds = rawOblastIds
            ?.map((e) => e as String)
            .toSet() ??
        {};
    if (parsedOblastIds.isEmpty && legacyOblastId != null && legacyOblastId.isNotEmpty) {
      parsedOblastIds.add(legacyOblastId);
    }
    return UserRegionSelection(
      oblastIds: parsedOblastIds,
      raionIds: (json['raionIds'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toSet() ?? {},
      settlementId: json['settlementId'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'oblastIds': oblastIds.toList(),
    'raionIds': raionIds.toList(),
    'settlementId': settlementId,
  };

  bool get isEmpty => oblastIds.isEmpty && raionIds.isEmpty && settlementId == null;
  bool get isNotEmpty => !isEmpty;

  /// Перевіряє чи обрана вся область (а не окремі райони)
  bool get hasFullOblast => oblastIds.isNotEmpty && raionIds.isEmpty && settlementId == null;

  /// Перевіряє чи обрані конкретні райони
  bool get hasSpecificRaions => raionIds.isNotEmpty;

  @override
  String toString() => 'UserRegionSelection(oblasts: $oblastIds, raions: $raionIds, settlement: $settlementId)';
}
