import 'location_item_model.dart';

class ChatSourceBook {
  final String id;
  final String title;
  final String author;
  final String genre;
  final String year;
  final String rating;
  final String coverUrl;
  final double? distance;

  ChatSourceBook({
    required this.id,
    required this.title,
    this.author = '',
    this.genre = '',
    this.year = '',
    this.rating = '',
    this.coverUrl = '',
    this.distance,
  });

  factory ChatSourceBook.fromMap(Map<String, dynamic> map) {
    final meta = map['metadata'] as Map<String, dynamic>? ?? {};
    return ChatSourceBook(
      id: map['id']?.toString() ?? meta['book_id']?.toString() ?? '',
      title: meta['title']?.toString() ?? map['title']?.toString() ?? 'Chưa rõ tiêu đề',
      author: meta['author']?.toString() ?? map['author']?.toString() ?? '',
      genre: meta['genre']?.toString() ?? map['genre']?.toString() ?? '',
      year: meta['year']?.toString() ?? map['year']?.toString() ?? '',
      rating: meta['rating']?.toString() ?? map['rating']?.toString() ?? '',
      coverUrl: meta['cover_url']?.toString() ?? map['cover_url']?.toString() ?? '',
      distance: (map['distance'] as num?)?.toDouble(),
    );
  }
}

class ChatMessageModel {
  final String id;
  final String role; // 'user' or 'assistant'
  String content;
  final String timestamp;
  List<ChatSourceBook> sources;
  List<LocationItemModel> locations;
  final String? intent;
  bool isStreaming;
  bool hasError;

  ChatMessageModel({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
    List<ChatSourceBook>? sources,
    List<LocationItemModel>? locations,
    this.intent,
    this.isStreaming = false,
    this.hasError = false,
  })  : sources = sources != null ? List<ChatSourceBook>.from(sources) : <ChatSourceBook>[],
        locations = locations != null ? List<LocationItemModel>.from(locations) : <LocationItemModel>[];

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) {
    final rawSources = json['sources'] as List<dynamic>? ?? [];
    final sources = rawSources
        .map((s) => ChatSourceBook.fromMap(s as Map<String, dynamic>))
        .toList();

    final rawLocations = json['locations'] as List<dynamic>? ?? [];
    final locations = rawLocations
        .map((l) => LocationItemModel.fromJson(l as Map<String, dynamic>))
        .toList();

    return ChatMessageModel(
      id: json['id']?.toString() ?? DateTime.now().millisecondsSinceEpoch.toString(),
      role: json['role']?.toString() ?? 'assistant',
      content: json['content']?.toString() ?? '',
      timestamp: json['timestamp']?.toString() ?? '',
      sources: sources,
      locations: locations,
      intent: json['intent']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'role': role,
      'content': content,
      'timestamp': timestamp,
      'sources': sources
          .map((s) => {
                'id': s.id,
                'metadata': {
                  'title': s.title,
                  'author': s.author,
                  'genre': s.genre,
                  'year': s.year,
                  'rating': s.rating,
                  'cover_url': s.coverUrl,
                },
                if (s.distance != null) 'distance': s.distance,
              })
          .toList(),
      'locations': locations.map((l) => l.toJson()).toList(),
      if (intent != null) 'intent': intent,
    };
  }
}
