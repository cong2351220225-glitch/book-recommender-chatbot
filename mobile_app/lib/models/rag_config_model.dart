class RagConfigModel {
  final int vectorCount;
  final int defaultTopK;
  final int maxTopK;
  final int minTopK;
  final String collectionName;

  RagConfigModel({
    required this.vectorCount,
    this.defaultTopK = 3,
    this.maxTopK = 10,
    this.minTopK = 1,
    this.collectionName = 'books_collection',
  });

  factory RagConfigModel.fromJson(Map<String, dynamic> json) {
    return RagConfigModel(
      vectorCount: json['vector_count'] as int? ?? 0,
      defaultTopK: json['default_top_k'] as int? ?? 3,
      maxTopK: json['max_top_k'] as int? ?? 10,
      minTopK: json['min_top_k'] as int? ?? 1,
      collectionName: json['collection_name']?.toString() ?? 'books_collection',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'vector_count': vectorCount,
      'default_top_k': defaultTopK,
      'max_top_k': maxTopK,
      'min_top_k': minTopK,
      'collection_name': collectionName,
    };
  }
}

