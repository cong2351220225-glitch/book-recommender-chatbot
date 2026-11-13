class BookVisionResult {
  final bool success;
  final bool isBookCover;
  final String? title;
  final String? author;
  final double confidence;
  final String message;

  BookVisionResult({
    required this.success,
    required this.isBookCover,
    this.title,
    this.author,
    this.confidence = 0.0,
    required this.message,
  });

  factory BookVisionResult.fromJson(Map<String, dynamic> json) {
    return BookVisionResult(
      success: json['success'] == true,
      isBookCover: json['is_book_cover'] == true,
      title: json['title'] as String?,
      author: json['author'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      message: (json['message'] as String?) ?? '',
    );
  }
}
