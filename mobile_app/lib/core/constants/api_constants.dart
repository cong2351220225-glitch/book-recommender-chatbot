import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiConstants {
  // Configurable base URL
  static String _customBaseUrl = '';

  static void setCustomBaseUrl(String url) {
    var trimmed = url.trim();
    while (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    _customBaseUrl = trimmed;
  }

  static String get baseUrl {
    if (_customBaseUrl.isNotEmpty) {
      return _customBaseUrl;
    }
    // Check runtime environment
    if (kIsWeb) {
      return 'http://localhost:8000';
    }
    try {
      if (Platform.isAndroid) {
        // Android Emulator uses 10.0.2.2 to access host machine
        return 'http://10.0.2.2:8000';
      }
    } catch (_) {}
    // Default for Windows, macOS, Linux, iOS Simulator
    return 'http://127.0.0.1:8000';
  }

  // Auth endpoints
  static const String register = '/api/v1/auth/register';
  static const String login = '/api/v1/auth/login';
  static const String me = '/api/v1/auth/me';

  // Home & Stats
  static const String homeStats = '/api/v1/home/stats';

  // Books
  static const String books = '/api/v1/books';
  static const String bookLanguages = '/api/v1/books/languages';
  static String bookDetail(String id) => '/api/v1/books/$id';
  static String bookRelated(String id) => '/api/v1/books/$id/related';

  // Authors
  static const String authors = '/api/v1/authors';
  static String authorDetail(String id) => '/api/v1/authors/$id';

  // Genres
  static const String genres = '/api/v1/genres';

  // Locations & Google Maps
  static const String locationsSearch = '/api/v1/locations/search';

  // Chatbot AI RAG Endpoints
  static const String chatMessage = '/api/v1/chat/message';
  static const String chatStream = '/api/v1/chat/stream';
  static String chatHistory(String sessionId) => '/api/v1/chat/history/$sessionId';
  static const String chatSessions = '/api/v1/chat/sessions';
  static String chatSession(String sessionId) => '/api/v1/chat/sessions/$sessionId';
  static const String chatConfig = '/api/v1/chat/config';
  static const String chatTts = '/api/v1/chat/tts';
  static const String transcribeAudio = '/api/v1/chat/transcribe-audio';

  // AI Book Vision
  static const String recognizeCover = '/api/v1/books/recognize-cover';

  // Personal Bookshelf Endpoints
  static const String bookshelf = '/api/v1/bookshelf';
  static String bookshelfCheck(String bookId) => '/api/v1/bookshelf/check/$bookId';
  static String bookshelfItem(String itemId) => '/api/v1/bookshelf/$itemId';
  static String bookshelfBook(String bookId) => '/api/v1/bookshelf/book/$bookId';

  // Digital Book Reader Endpoints
  static String readingStatus(String bookId) => '/api/v1/reading/status/$bookId';
  static String readingFile(String bookId) => '/api/v1/reading/file/$bookId';
  static String readingInfo(String bookId) => '/api/v1/reading/info/$bookId';
  static String readingProgress(String bookId) => '/api/v1/reading/progress/$bookId';
  static const String saveReadingProgress = '/api/v1/reading/progress';

  // AI Book Crawler Endpoints (Admin)
  static const String crawlerSources = '/api/v1/crawler/sources';
  static const String crawlerSearch = '/api/v1/crawler/search';
  static const String crawlerImport = '/api/v1/crawler/import';
  static const String crawlerBatchImport = '/api/v1/crawler/batch-import';
  static const String crawlerUnindexed = '/api/v1/crawler/unindexed';
  static const String crawlerSyncUnindexed = '/api/v1/crawler/sync-unindexed';

  // AI Book Recommendation Endpoints
  static const String recommendationsForYou = '/api/v1/recommendations/for-you';
  static const String recommendationsContinueReading = '/api/v1/recommendations/continue-reading';
  static String recommendationsSimilar(String bookId) => '/api/v1/recommendations/similar/$bookId';
  static const String recommendationPreferences = '/api/v1/recommendations/preferences';
  static const String recommendationFeedback = '/api/v1/recommendations/feedback';
  static const String recommendationRefresh = '/api/v1/recommendations/refresh';

  // Health
  static const String health = '/health';

  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);
}

