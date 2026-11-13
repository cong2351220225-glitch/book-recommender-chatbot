class RecommendedBookItemModel {
  final String bookId;
  final String title;
  final String author;
  final String genre;
  final String coverUrl;
  final double rating;
  final dynamic year;
  final dynamic pages;
  final bool readingAvailable;
  final String readingType;
  final String format;
  final double score;
  final String reason;
  final String reasonType;
  String? userFeedback; // 'liked', 'disliked', null

  RecommendedBookItemModel({
    required this.bookId,
    required this.title,
    required this.author,
    this.genre = 'Tổng hợp',
    this.coverUrl = '',
    this.rating = 4.0,
    this.year,
    this.pages = 0,
    this.readingAvailable = false,
    this.readingType = '',
    this.format = 'Bìa mềm',
    this.score = 0.0,
    this.reason = '',
    this.reasonType = 'featured',
    this.userFeedback,
  });

  bool get isLiked => userFeedback == 'liked';
  bool get isDisliked => userFeedback == 'disliked';

  factory RecommendedBookItemModel.fromJson(Map<String, dynamic> json) {
    return RecommendedBookItemModel(
      bookId: json['book_id']?.toString() ?? '',
      title: json['title'] as String? ?? 'Chưa rõ tiêu đề',
      author: json['author'] as String? ?? 'Chưa rõ tác giả',
      genre: json['genre'] as String? ?? 'Tổng hợp',
      coverUrl: json['cover_url'] as String? ?? '',
      rating: (json['rating'] is num) ? (json['rating'] as num).toDouble() : 4.0,
      year: json['year'],
      pages: json['pages'] ?? 0,
      readingAvailable: json['reading_available'] == true || json['reading_available'] == 'True',
      readingType: json['reading_type'] as String? ?? '',
      format: json['format'] as String? ?? 'Bìa mềm',
      score: (json['score'] is num) ? (json['score'] as num).toDouble() : 0.0,
      reason: json['reason'] as String? ?? '',
      reasonType: json['reason_type'] as String? ?? 'featured',
      userFeedback: json['user_feedback'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'book_id': bookId,
      'title': title,
      'author': author,
      'genre': genre,
      'cover_url': coverUrl,
      'rating': rating,
      'year': year,
      'pages': pages,
      'reading_available': readingAvailable,
      'reading_type': readingType,
      'format': format,
      'score': score,
      'reason': reason,
      'reason_type': reasonType,
      'user_feedback': userFeedback,
    };
  }
}

class RecommendationListModel {
  final int total;
  final List<RecommendedBookItemModel> recommendations;
  final String algorithm;
  final bool isPersonalized;
  final String sourceBasis;

  RecommendationListModel({
    required this.total,
    required this.recommendations,
    this.algorithm = 'hybrid_content_semantic',
    this.isPersonalized = true,
    this.sourceBasis = '',
  });

  factory RecommendationListModel.fromJson(Map<String, dynamic> json) {
    final rawList = json['recommendations'] as List<dynamic>? ?? [];
    return RecommendationListModel(
      total: json['total'] as int? ?? rawList.length,
      recommendations: rawList
          .map((e) => RecommendedBookItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      algorithm: json['algorithm'] as String? ?? 'hybrid_content_semantic',
      isPersonalized: json['is_personalized'] as bool? ?? false,
      sourceBasis: json['source_basis'] as String? ?? '',
    );
  }
}

class RecommendationPreferencesModel {
  final String username;
  final List<String> preferredGenres;
  final List<String> preferredAuthors;
  final String readingGoal;
  final String updatedAt;

  RecommendationPreferencesModel({
    required this.username,
    required this.preferredGenres,
    required this.preferredAuthors,
    this.readingGoal = '',
    this.updatedAt = '',
  });

  factory RecommendationPreferencesModel.fromJson(Map<String, dynamic> json) {
    final genres = (json['preferred_genres'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList() ??
        [];
    final authors = (json['preferred_authors'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList() ??
        [];

    return RecommendationPreferencesModel(
      username: json['username'] as String? ?? '',
      preferredGenres: genres,
      preferredAuthors: authors,
      readingGoal: json['reading_goal'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'preferred_genres': preferredGenres,
      'preferred_authors': preferredAuthors,
      'reading_goal': readingGoal,
    };
  }
}

class RecommendationFeedbackResponseModel {
  final bool success;
  final String bookId;
  final bool? liked;
  final String message;

  RecommendationFeedbackResponseModel({
    required this.success,
    required this.bookId,
    this.liked,
    required this.message,
  });

  factory RecommendationFeedbackResponseModel.fromJson(Map<String, dynamic> json) {
    return RecommendationFeedbackResponseModel(
      success: json['success'] as bool? ?? false,
      bookId: json['book_id'] as String? ?? '',
      liked: json['liked'] as bool?,
      message: json['message'] as String? ?? '',
    );
  }
}

