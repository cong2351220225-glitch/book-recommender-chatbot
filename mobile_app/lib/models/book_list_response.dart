import 'book_model.dart';

class BookListResponse {
  final List<BookModel> items;
  final int total;
  final int page;
  final int pageSize;
  final int totalPages;

  BookListResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  bool get hasMore => page < totalPages;

  factory BookListResponse.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    final items = rawItems
        .map((item) => BookModel.fromJson(item as Map<String, dynamic>))
        .toList();

    return BookListResponse(
      items: items,
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 0,
    );
  }
}

