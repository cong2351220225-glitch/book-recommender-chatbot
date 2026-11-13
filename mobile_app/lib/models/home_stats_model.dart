import 'book_model.dart';

class HomeStatsModel {
  final int totalBooks;
  final int totalAuthors;
  final int totalGenres;
  final int onlineReadingCount;
  final List<BookModel> featuredBooks;

  HomeStatsModel({
    required this.totalBooks,
    required this.totalAuthors,
    required this.totalGenres,
    required this.onlineReadingCount,
    this.featuredBooks = const [],
  });

  factory HomeStatsModel.fromJson(Map<String, dynamic> json) {
    final rawFeatured = json['featured_books'] as List<dynamic>? ?? [];
    final featured = rawFeatured
        .map((b) => BookModel.fromJson(b as Map<String, dynamic>))
        .toList();

    return HomeStatsModel(
      totalBooks: (json['total_books'] as num?)?.toInt() ?? 0,
      totalAuthors: (json['total_authors'] as num?)?.toInt() ?? 0,
      totalGenres: (json['total_genres'] as num?)?.toInt() ?? 0,
      onlineReadingCount: (json['online_reading_count'] as num?)?.toInt() ?? 0,
      featuredBooks: featured,
    );
  }
}

