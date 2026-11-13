class ReadingProgressModel {
  final String bookId;
  final int currentPage;
  final int totalPages;
  final double progressPercent;
  final String lastReadLocation;
  final String updatedAt;

  ReadingProgressModel({
    required this.bookId,
    required this.currentPage,
    required this.totalPages,
    required this.progressPercent,
    this.lastReadLocation = '',
    required this.updatedAt,
  });

  factory ReadingProgressModel.fromJson(Map<String, dynamic> json) {
    return ReadingProgressModel(
      bookId: json['book_id']?.toString() ?? '',
      currentPage: (json['current_page'] as num?)?.toInt() ?? 1,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 1,
      progressPercent: (json['progress_percent'] as num?)?.toDouble() ?? 0.0,
      lastReadLocation: json['last_read_location']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'book_id': bookId,
      'current_page': currentPage,
      'total_pages': totalPages,
      'progress_percent': progressPercent,
      'last_read_location': lastReadLocation,
      'updated_at': updatedAt,
    };
  }
}

class ReadingDocInfoModel {
  final String bookId;
  final String title;
  final String author;
  final bool canRead;
  final String format; // 'pdf', 'epub', 'none'
  final int fileSizeBytes;
  final String fileUrl;
  final ReadingProgressModel? savedProgress;

  ReadingDocInfoModel({
    required this.bookId,
    required this.title,
    this.author = '',
    required this.canRead,
    this.format = 'none',
    this.fileSizeBytes = 0,
    this.fileUrl = '',
    this.savedProgress,
  });

  bool get isPdf => format.toLowerCase() == 'pdf';
  bool get isEpub => format.toLowerCase() == 'epub';

  String get formattedFileSize {
    if (fileSizeBytes <= 0) return '0 KB';
    if (fileSizeBytes < 1024 * 1024) {
      return '${(fileSizeBytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(fileSizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  factory ReadingDocInfoModel.fromJson(Map<String, dynamic> json) {
    ReadingProgressModel? prog;
    if (json['saved_progress'] != null && json['saved_progress'] is Map<String, dynamic>) {
      prog = ReadingProgressModel.fromJson(json['saved_progress'] as Map<String, dynamic>);
    }

    return ReadingDocInfoModel(
      bookId: json['book_id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      author: json['author']?.toString() ?? '',
      canRead: json['can_read'] == true,
      format: json['format']?.toString() ?? 'none',
      fileSizeBytes: (json['file_size_bytes'] as num?)?.toInt() ?? 0,
      fileUrl: json['file_url']?.toString() ?? '',
      savedProgress: prog,
    );
  }
}

