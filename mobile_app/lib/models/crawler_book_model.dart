class CrawlerSourceModel {
  final String id;
  final String name;
  final String description;

  CrawlerSourceModel({
    required this.id,
    required this.name,
    required this.description,
  });

  factory CrawlerSourceModel.fromJson(Map<String, dynamic> json) {
    return CrawlerSourceModel(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }
}

class CrawlerBookCandidate {
  final String title;
  final String author;
  final String isbn;
  final String publisher;
  final dynamic year;
  final dynamic pages;
  final String language;
  final String description;
  final String coverUrl;
  final bool readingAvailable;
  final String readingType;
  final String readingUrl;
  final String purchaseUrl;
  final String libraryUrl;
  final String source;
  final String status; // 'new', 'duplicate', 'uncertain'
  final String matchReason;
  final String genre;
  final dynamic rating;
  final Map<String, dynamic> rawCandidate;

  // Trạng thái giao diện
  bool isSelected;

  CrawlerBookCandidate({
    required this.title,
    required this.author,
    this.isbn = '',
    this.publisher = '',
    this.year,
    this.pages,
    this.language = '',
    this.description = '',
    this.coverUrl = '',
    this.readingAvailable = false,
    this.readingType = '',
    this.readingUrl = '',
    this.purchaseUrl = '',
    this.libraryUrl = '',
    this.source = '',
    this.status = 'new',
    this.matchReason = '',
    this.genre = '',
    this.rating,
    required this.rawCandidate,
    this.isSelected = false,
  });

  bool get isDuplicate => status == 'duplicate';
  bool get isUncertain => status == 'uncertain';
  bool get isNew => status == 'new';
  bool get hasNoDescription => description.trim().isEmpty;

  factory CrawlerBookCandidate.fromJson(Map<String, dynamic> json) {
    final status = json['status'] as String? ?? (json['is_duplicate'] == true ? 'duplicate' : 'new');
    final matchReason = json['match_reason'] as String? ?? json['matched_by'] as String? ?? '';
    final source = json['source'] as String? ?? json['_source'] as String? ?? '';

    return CrawlerBookCandidate(
      title: json['title'] as String? ?? 'Chưa rõ tiêu đề',
      author: json['author'] as String? ?? 'Chưa rõ tác giả',
      isbn: json['isbn']?.toString() ?? '',
      publisher: json['publisher'] as String? ?? '',
      year: json['year'],
      pages: json['pages'],
      language: json['language'] as String? ?? '',
      description: json['description'] as String? ?? json['description_raw'] as String? ?? '',
      coverUrl: json['cover_url'] as String? ?? '',
      readingAvailable: json['reading_available'] == true || json['reading_available'] == 'True',
      readingType: json['reading_type'] as String? ?? '',
      readingUrl: json['reading_url'] as String? ?? '',
      purchaseUrl: json['purchase_url'] as String? ?? '',
      libraryUrl: json['library_url'] as String? ?? '',
      source: source,
      status: status,
      matchReason: matchReason,
      genre: json['genre'] as String? ?? '',
      rating: json['rating'],
      rawCandidate: json,
      isSelected: false,
    );
  }

  Map<String, dynamic> toCandidatePayload() {
    return Map<String, dynamic>.from(rawCandidate);
  }
}

class CrawlerImportResult {
  final String title;
  final String? bookId;
  final bool success;
  final String message;
  final bool vectorIndexed;

  CrawlerImportResult({
    required this.title,
    this.bookId,
    required this.success,
    required this.message,
    this.vectorIndexed = false,
  });

  factory CrawlerImportResult.fromJson(Map<String, dynamic> json) {
    return CrawlerImportResult(
      title: json['title'] as String? ?? '',
      bookId: json['book_id'] as String?,
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '',
      vectorIndexed: json['vector_indexed'] as bool? ?? false,
    );
  }
}

class CrawlerBatchImportResponse {
  final int totalRequested;
  final int importedCount;
  final int skippedCount;
  final List<CrawlerImportResult> results;

  CrawlerBatchImportResponse({
    required this.totalRequested,
    required this.importedCount,
    required this.skippedCount,
    required this.results,
  });

  factory CrawlerBatchImportResponse.fromJson(Map<String, dynamic> json) {
    final rawResults = json['results'] as List<dynamic>? ?? [];
    return CrawlerBatchImportResponse(
      totalRequested: json['total_requested'] as int? ?? 0,
      importedCount: json['imported_count'] as int? ?? 0,
      skippedCount: json['skipped_count'] as int? ?? 0,
      results: rawResults.map((e) => CrawlerImportResult.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}

class ChromaIndexStatus {
  final int totalBooks;
  final int indexedCount;
  final int unindexedCount;
  final int failedCount;
  final String? lastSyncedAt;
  final List<Map<String, dynamic>> unindexedBooks;
  final String collectionName;
  final String embeddingModel;

  ChromaIndexStatus({
    required this.totalBooks,
    required this.indexedCount,
    required this.unindexedCount,
    this.failedCount = 0,
    this.lastSyncedAt,
    this.unindexedBooks = const [],
    this.collectionName = 'books_collection',
    this.embeddingModel = 'gemini-embedding-2',
  });

  factory ChromaIndexStatus.fromJson(Map<String, dynamic> json) {
    final rawUnindexed = json['unindexed_books'] as List<dynamic>? ?? [];
    return ChromaIndexStatus(
      totalBooks: json['total_books'] as int? ?? 0,
      indexedCount: json['indexed_count'] as int? ?? 0,
      unindexedCount: json['count'] as int? ?? (json['unindexed_count'] as int? ?? rawUnindexed.length),
      failedCount: json['failed_count'] as int? ?? 0,
      lastSyncedAt: json['last_synced_at'] as String?,
      unindexedBooks: rawUnindexed.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
      collectionName: json['collection_name'] as String? ?? 'books_collection',
      embeddingModel: json['embedding_model'] as String? ?? 'gemini-embedding-2',
    );
  }
}

class SyncChromaResult {
  final bool success;
  final int syncedCount;
  final int totalUnindexed;
  final int failedCount;
  final String message;

  SyncChromaResult({
    required this.success,
    required this.syncedCount,
    required this.totalUnindexed,
    this.failedCount = 0,
    required this.message,
  });

  factory SyncChromaResult.fromJson(Map<String, dynamic> json) {
    return SyncChromaResult(
      success: json['success'] as bool? ?? false,
      syncedCount: json['synced_count'] as int? ?? 0,
      totalUnindexed: json['total_unindexed'] as int? ?? 0,
      failedCount: json['failed_count'] as int? ?? 0,
      message: json['message'] as String? ?? '',
    );
  }
}

