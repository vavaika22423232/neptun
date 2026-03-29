/// Тип адміністративної одиниці
enum RegionType {
  oblast,     // Область
  raion,      // Район
  settlement, // Населений пункт
}

/// Модель адміністративної одиниці України
class RegionNode {
  final String id;
  final RegionType type;
  final String nameUk;
  final String? parentId;

  const RegionNode({
    required this.id,
    required this.type,
    required this.nameUk,
    this.parentId,
  });

  factory RegionNode.fromJson(Map<String, dynamic> json) {
    return RegionNode(
      id: json['id'] as String,
      type: RegionType.values.firstWhere(
        (t) => t.name == json['type'],
        orElse: () => RegionType.settlement,
      ),
      nameUk: json['nameUk'] as String,
      parentId: json['parentId'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type.name,
    'nameUk': nameUk,
    'parentId': parentId,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RegionNode && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'RegionNode(id: $id, type: $type, name: $nameUk)';
}
