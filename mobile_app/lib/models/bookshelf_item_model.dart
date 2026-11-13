import 'book_model.dart';

class BookshelfItemModel {
  final String id;
  final String bookId;
  String status; // 'favorite', 'reading', 'completed'
  int progressPage;
  int totalPages;
  int rating;
  String notes;
  final String addedAt;
  String updatedAt;
  final BookModel? book;

  BookshelfItemModel({
    required this.id,
    required this.bookId,
    required this.status,
    this.progressPage = 0,
    this.totalPages = 0,
    this.rating = 0,
    this.notes = '',
    required this.addedAt,
    required this.updatedAt,
    this.book,
  });

  bool get isFavorite => status == 'favorite';
  bool get isReading => status == 'reading';
  bool get isCompleted => status == 'completed';

  double get progressPercentage {
    if (totalPages <= 0) return 0.0;
    final pct = progressPage / totalPages;
    return pct > 1.0 ? 1.0 : (pct < 0.0 ? 0.0 : pct);
  }

  factory BookshelfItemModel.fromJson(Map<String, dynamic> json) {
    BookModel? parsedBook;
    if (json['book'] != null && json['book'] is Map<String, dynamic>) {
      try {
        parsedBook = BookModel.fromJson(json['book'] as Map<String, dynamic>);
      } catch (_) {
        parsedBook = null;
      }
    }

    return BookshelfItemModel(
      id: json['id']?.toString() ?? '',
      bookId: json['book_id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'favorite',
      progressPage: (json['progress_page'] as num?)?.toInt() ?? 0,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 0,
      rating: (json['rating'] as num?)?.toInt() ?? 0,
      notes: json['notes']?.toString() ?? '',
      addedAt: json['added_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      book: parsedBook,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'book_id': bookId,
      'status': status,
      'progress_page': progressPage,
      'total_pages': totalPages,
      'rating': rating,
      'notes': notes,
      'added_at': addedAt,
      'updated_at': updatedAt,
      if (book != null) 'book': book!.toJson(),
    };
  }
}

