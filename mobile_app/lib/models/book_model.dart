class BookModel {
  final String bookId;
  final String title;
  final String author;
  final String authorId;
  final String genre;
  final String description;
  final dynamic year;
  final String isbn;
  final String publisher;
  final dynamic pages;
  final String language;
  final String format;
  final String coverUrl;
  final dynamic rating;
  final bool featured;
  final String tags;
  final String targetAudience;
  final String mood;
  final String difficulty;
  final String summary;
  final bool readingAvailable;
  final String readingType;
  final String readingUrl;
  final String localFile;
  final String purchaseUrl;
  final String libraryUrl;

  BookModel({
    required this.bookId,
    required this.title,
    required this.author,
    this.authorId = '',
    this.genre = '',
    this.description = '',
    this.year,
    this.isbn = '',
    this.publisher = '',
    this.pages,
    this.language = '',
    this.format = '',
    this.coverUrl = '',
    this.rating,
    this.featured = false,
    this.tags = '',
    this.targetAudience = '',
    this.mood = '',
    this.difficulty = '',
    this.summary = '',
    this.readingAvailable = false,
    this.readingType = '',
    this.readingUrl = '',
    this.localFile = '',
    this.purchaseUrl = '',
    this.libraryUrl = '',
  });

  double get ratingValue {
    if (rating == null) return 0.0;
    if (rating is num) return (rating as num).toDouble();
    return double.tryParse(rating.toString()) ?? 0.0;
  }

  String get displayYear => year != null && year.toString().isNotEmpty ? year.toString() : 'N/A';

  factory BookModel.fromJson(Map<String, dynamic> json) {
    bool parseBool(dynamic value) {
      if (value == null) return false;
      if (value is bool) return value;
      final s = value.toString().toLowerCase().trim();
      return s == 'true' || s == '1';
    }

    return BookModel(
      bookId: json['book_id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Chưa rõ tiêu đề',
      author: json['author']?.toString() ?? 'Chưa rõ tác giả',
      authorId: json['author_id']?.toString() ?? '',
      genre: json['genre']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      year: json['year'],
      isbn: json['isbn']?.toString() ?? '',
      publisher: json['publisher']?.toString() ?? '',
      pages: json['pages'],
      language: json['language']?.toString() ?? '',
      format: json['format']?.toString() ?? '',
      coverUrl: json['cover_url']?.toString() ?? '',
      rating: json['rating'],
      featured: parseBool(json['featured']),
      tags: json['tags']?.toString() ?? '',
      targetAudience: json['target_audience']?.toString() ?? '',
      mood: json['mood']?.toString() ?? '',
      difficulty: json['difficulty']?.toString() ?? '',
      summary: json['summary']?.toString() ?? '',
      readingAvailable: parseBool(json['reading_available']),
      readingType: json['reading_type']?.toString() ?? '',
      readingUrl: json['reading_url']?.toString() ?? '',
      localFile: json['local_file']?.toString() ?? '',
      purchaseUrl: json['purchase_url']?.toString() ?? '',
      libraryUrl: json['library_url']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'book_id': bookId,
      'title': title,
      'author': author,
      'author_id': authorId,
      'genre': genre,
      'description': description,
      'year': year,
      'isbn': isbn,
      'publisher': publisher,
      'pages': pages,
      'language': language,
      'format': format,
      'cover_url': coverUrl,
      'rating': rating,
      'featured': featured,
      'tags': tags,
      'target_audience': targetAudience,
      'mood': mood,
      'difficulty': difficulty,
      'summary': summary,
      'reading_available': readingAvailable,
      'reading_type': readingType,
      'reading_url': readingUrl,
      'local_file': localFile,
      'purchase_url': purchaseUrl,
      'library_url': libraryUrl,
    };
  }
}

