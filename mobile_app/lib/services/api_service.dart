import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/dio_client.dart';
import '../core/network/api_exceptions.dart';
import '../models/user_model.dart';
import '../models/book_model.dart';
import '../models/book_list_response.dart';
import '../models/author_model.dart';
import '../models/genre_model.dart';
import '../models/home_stats_model.dart';
import '../models/chat_message_model.dart';
import '../models/chat_session_model.dart';
import '../models/rag_config_model.dart';
import '../models/bookshelf_item_model.dart';
import '../models/reading_progress_model.dart';
import '../models/crawler_book_model.dart';
import '../models/recommendation_model.dart';
import '../models/location_item_model.dart';

class ApiService {
  final DioClient _dioClient;

  ApiService({DioClient? dioClient}) : _dioClient = dioClient ?? DioClient();

  // ---------------- AUTH ----------------
  Future<UserModel> register(String username, String password) async {
    final response = await _dioClient.post(
      ApiConstants.register,
      data: {'username': username, 'password': password},
    );
    return UserModel.fromJson(response.data);
  }

  Future<UserModel> login(String username, String password) async {
    final response = await _dioClient.post(
      ApiConstants.login,
      data: {'username': username, 'password': password},
    );
    return UserModel.fromJson(response.data);
  }

  Future<UserModel> getMe() async {
    final response = await _dioClient.get(ApiConstants.me);
    return UserModel.fromJson(response.data);
  }

  // ---------------- HOME ----------------
  Future<HomeStatsModel> getHomeStats() async {
    final response = await _dioClient.get(ApiConstants.homeStats);
    return HomeStatsModel.fromJson(response.data);
  }

  // ---------------- BOOKS ----------------
  Future<BookListResponse> getBooks({
    String? query,
    String? title,
    String? author,
    String? isbn,
    String? genre,
    String? language,
    int? minYear,
    int? maxYear,
    double? minRating,
    bool? featuredOnly,
    bool? readingOnly,
    int page = 1,
    int pageSize = 20,
    String sortBy = 'Phù hợp',
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      'sort_by': sortBy,
    };

    if (query != null && query.isNotEmpty) queryParams['q'] = query;
    if (title != null && title.isNotEmpty) queryParams['title'] = title;
    if (author != null && author.isNotEmpty && author != 'Tất cả') {
      queryParams['author'] = author;
    }
    if (isbn != null && isbn.isNotEmpty) queryParams['isbn'] = isbn;
    if (genre != null && genre.isNotEmpty && genre != 'Tất cả') {
      queryParams['genre'] = genre;
    }
    if (language != null && language.isNotEmpty && language != 'Tất cả') {
      queryParams['language'] = language;
    }
    if (minYear != null) queryParams['min_year'] = minYear;
    if (maxYear != null) queryParams['max_year'] = maxYear;
    if (minRating != null && minRating > 0) queryParams['min_rating'] = minRating;
    if (featuredOnly == true) queryParams['featured_only'] = true;
    if (readingOnly == true) queryParams['reading_only'] = true;

    final response = await _dioClient.get(
      ApiConstants.books,
      queryParameters: queryParams,
    );
    return BookListResponse.fromJson(response.data);
  }

  Future<List<String>> getBookLanguages() async {
    final response = await _dioClient.get(ApiConstants.bookLanguages);
    final list = response.data as List<dynamic>? ?? [];
    return list.map((e) => e.toString()).toList();
  }

  Future<Map<String, dynamic>> getBookDetail(String bookId) async {
    final response = await _dioClient.get(ApiConstants.bookDetail(bookId));
    final data = response.data as Map<String, dynamic>;
    final book = BookModel.fromJson(data['book'] as Map<String, dynamic>);
    final rawRelated = data['related_books'] as List<dynamic>? ?? [];
    final relatedBooks = rawRelated
        .map((b) => BookModel.fromJson(b as Map<String, dynamic>))
        .toList();

    return {
      'book': book,
      'related_books': relatedBooks,
      'reading_status': data['reading_status']?.toString() ?? '',
      'can_read': data['can_read'] == true,
    };
  }

  Future<List<BookModel>> getRelatedBooks(String bookId, {int limit = 5}) async {
    final response = await _dioClient.get(
      ApiConstants.bookRelated(bookId),
      queryParameters: {'limit': limit},
    );
    final list = response.data as List<dynamic>? ?? [];
    return list.map((b) => BookModel.fromJson(b as Map<String, dynamic>)).toList();
  }

  // ---------------- AUTHORS ----------------
  Future<List<AuthorModel>> getAuthors({String? query}) async {
    final queryParams = <String, dynamic>{};
    if (query != null && query.isNotEmpty) queryParams['q'] = query;

    final response = await _dioClient.get(
      ApiConstants.authors,
      queryParameters: queryParams,
    );
    final list = response.data as List<dynamic>? ?? [];
    return list.map((a) => AuthorModel.fromJson(a as Map<String, dynamic>)).toList();
  }

  Future<AuthorModel> getAuthorDetail(String authorId) async {
    final response = await _dioClient.get(ApiConstants.authorDetail(authorId));
    final data = response.data as Map<String, dynamic>;
    final authorData = data['author'] as Map<String, dynamic>;
    final booksData = data['books'] as List<dynamic>? ?? [];

    final merged = Map<String, dynamic>.from(authorData);
    merged['books'] = booksData;
    return AuthorModel.fromJson(merged);
  }

  // ---------------- GENRES ----------------
  Future<List<GenreModel>> getGenres() async {
    final response = await _dioClient.get(ApiConstants.genres);
    final list = response.data as List<dynamic>? ?? [];
    return list.map((g) => GenreModel.fromJson(g as Map<String, dynamic>)).toList();
  }

  // ---------------- CHATBOT AI RAG ----------------
  Future<Map<String, dynamic>> sendChatMessage({
    required String message,
    String? sessionId,
    int topK = 3,
    Map<String, dynamic>? readerProfile,
  }) async {
    final response = await _dioClient.post(
      ApiConstants.chatMessage,
      data: {
        'message': message,
        if (sessionId != null) 'session_id': sessionId,
        'top_k': topK,
        if (readerProfile != null) 'reader_profile': readerProfile,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  Future<void> sendChatMessageStream({
    required String message,
    String? sessionId,
    int topK = 3,
    Map<String, dynamic>? readerProfile,
    required Function(String chunk) onChunk,
    required Function(
      String fullAnswer,
      List<ChatSourceBook> sources,
      List<LocationItemModel> locations,
      String intent,
      String sessionId,
    ) onDone,
    required Function(String error) onError,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dioClient.dio.post<ResponseBody>(
        ApiConstants.chatStream,
        data: {
          'message': message,
          if (sessionId != null) 'session_id': sessionId,
          'top_k': topK,
          if (readerProfile != null) 'reader_profile': readerProfile,
        },
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
          receiveTimeout: const Duration(minutes: 2),
        ),
        cancelToken: cancelToken,
      );

      final stream = response.data?.stream;
      if (stream == null) {
        onError('Không nhận được luồng dữ liệu phản hồi từ máy chủ.');
        return;
      }

      final lines = utf8.decoder.bind(stream).transform(const LineSplitter());

      await for (final line in lines) {
        final trimmed = line.trim();
        if (trimmed.isEmpty || !trimmed.startsWith('data: ')) continue;

        final jsonString = trimmed.substring(6).trim();
        if (jsonString.isEmpty) continue;

        try {
          final data = jsonDecode(jsonString) as Map<String, dynamic>;

          if (data.containsKey('chunk')) {
            onChunk(data['chunk'].toString());
          }

          if (data.containsKey('done') && data['done'] == true) {
            final rawBooks = data['books'] as List<dynamic>? ?? [];
            final sources = rawBooks
                .map((b) => ChatSourceBook.fromMap(b as Map<String, dynamic>))
                .toList();

            final rawLocations = data['locations'] as List<dynamic>? ?? [];
            final locations = rawLocations
                .map((l) => LocationItemModel.fromJson(l as Map<String, dynamic>))
                .toList();

            onDone(
              data['answer']?.toString() ?? '',
              sources,
              locations,
              data['intent']?.toString() ?? 'book_query',
              data['session_id']?.toString() ?? sessionId ?? '',
            );
            return;
          }

          if (data.containsKey('error')) {
            onError(data['error'].toString());
            return;
          }
        } catch (_) {}
      }
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) {
        onError('Đã dừng phản hồi theo yêu cầu.');
      } else {
        final apiEx = ApiException.fromDioException(e);
        onError(apiEx.message);
      }
    } catch (e) {
      onError('Lỗi kết nối streaming: ${e.toString()}');
    }
  }

  Future<List<ChatMessageModel>> getChatHistory(String sessionId) async {
    final response = await _dioClient.get(ApiConstants.chatHistory(sessionId));
    final data = response.data as Map<String, dynamic>;
    final rawMessages = data['messages'] as List<dynamic>? ?? [];
    return rawMessages
        .map((m) => ChatMessageModel.fromJson(m as Map<String, dynamic>))
        .toList();
  }

  Future<List<ChatSessionModel>> getChatSessions() async {
    final response = await _dioClient.get(ApiConstants.chatSessions);
    final data = response.data as Map<String, dynamic>;
    final rawSessions = data['sessions'] as List<dynamic>? ?? [];
    return rawSessions
        .map((s) => ChatSessionModel.fromJson(s as Map<String, dynamic>))
        .toList();
  }

  Future<bool> deleteChatSession(String sessionId) async {
    final response = await _dioClient.delete(ApiConstants.chatSession(sessionId));
    return response.statusCode == 200;
  }

  Future<RagConfigModel> getRagConfig() async {
    final response = await _dioClient.get(ApiConstants.chatConfig);
    final data = response.data as Map<String, dynamic>;
    return RagConfigModel.fromJson(data);
  }

  // ---------------- BOOKSHELF ----------------
  Future<List<BookshelfItemModel>> getBookshelf({String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    final response = await _dioClient.get(
      ApiConstants.bookshelf,
      queryParameters: queryParams,
    );
    final data = response.data as Map<String, dynamic>;
    final rawItems = data['items'] as List<dynamic>? ?? [];
    return rawItems
        .map((it) => BookshelfItemModel.fromJson(it as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> checkBookInBookshelf(String bookId) async {
    final response = await _dioClient.get(ApiConstants.bookshelfCheck(bookId));
    return response.data as Map<String, dynamic>;
  }

  Future<BookshelfItemModel> addBookshelfItem({
    required String bookId,
    required String status,
    int progressPage = 0,
    int totalPages = 0,
    int rating = 0,
    String notes = '',
  }) async {
    final response = await _dioClient.post(
      ApiConstants.bookshelf,
      data: {
        'book_id': bookId,
        'status': status,
        'progress_page': progressPage,
        'total_pages': totalPages,
        'rating': rating,
        'notes': notes,
      },
    );
    return BookshelfItemModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<BookshelfItemModel> updateBookshelfItem(
    String itemId, {
    String? status,
    int? progressPage,
    int? totalPages,
    int? rating,
    String? notes,
  }) async {
    final body = <String, dynamic>{};
    if (status != null) body['status'] = status;
    if (progressPage != null) body['progress_page'] = progressPage;
    if (totalPages != null) body['total_pages'] = totalPages;
    if (rating != null) body['rating'] = rating;
    if (notes != null) body['notes'] = notes;

    final response = await _dioClient.put(
      ApiConstants.bookshelfItem(itemId),
      data: body,
    );
    return BookshelfItemModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<bool> deleteBookshelfItem(String itemId) async {
    final response = await _dioClient.delete(ApiConstants.bookshelfItem(itemId));
    final data = response.data as Map<String, dynamic>;
    return data['success'] == true;
  }

  Future<bool> deleteBookFromBookshelf(String bookId, {String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    final response = await _dioClient.delete(
      ApiConstants.bookshelfBook(bookId),
      queryParameters: queryParams,
    );
    final data = response.data as Map<String, dynamic>;
    return data['success'] == true;
  }

  // ---------------- DIGITAL READING ----------------
  Future<Map<String, dynamic>> getReadingStatus(String bookId) async {
    final response = await _dioClient.get(ApiConstants.readingStatus(bookId));
    return response.data as Map<String, dynamic>;
  }

  Future<ReadingDocInfoModel> getReadingDocInfo(String bookId) async {
    final response = await _dioClient.get(ApiConstants.readingInfo(bookId));
    return ReadingDocInfoModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ReadingProgressModel> getReadingProgress(String bookId) async {
    final response = await _dioClient.get(ApiConstants.readingProgress(bookId));
    return ReadingProgressModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ReadingProgressModel> saveReadingProgress({
    required String bookId,
    required int currentPage,
    required int totalPages,
    String? location,
  }) async {
    final response = await _dioClient.post(
      ApiConstants.saveReadingProgress,
      data: {
        'book_id': bookId,
        'current_page': currentPage,
        'total_pages': totalPages,
        'last_read_location': location ?? 'Trang $currentPage',
      },
    );
    return ReadingProgressModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Uint8List> downloadReadingFile(String bookId) async {
    final response = await _dioClient.get(
      ApiConstants.readingFile(bookId),
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data as List<int>);
  }

  // ---------------- AI CRAWLER (ADMIN) ----------------
  Future<List<CrawlerSourceModel>> getCrawlerSources() async {
    final response = await _dioClient.get(ApiConstants.crawlerSources);
    final data = response.data as Map<String, dynamic>;
    final list = data['sources'] as List<dynamic>? ?? [];
    return list.map((e) => CrawlerSourceModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<CrawlerBookCandidate>> searchCrawlerBooks({
    String query = '',
    String author = '',
    String subject = '',
    String isbn = '',
    String language = '',
    int yearFrom = 0,
    int yearTo = 0,
    String source = 'all',
    int limit = 15,
  }) async {
    final response = await _dioClient.post(
      ApiConstants.crawlerSearch,
      data: {
        'query': query,
        'author': author,
        'subject': subject,
        'isbn': isbn,
        'language': language,
        'year_from': yearFrom,
        'year_to': yearTo,
        'source': source,
        'limit': limit,
      },
    );
    final data = response.data as Map<String, dynamic>;
    final list = data['results'] as List<dynamic>? ?? [];
    return list.map((e) => CrawlerBookCandidate.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<CrawlerImportResult> importCrawlerBook({
    required Map<String, dynamic> candidate,
    bool upsertChroma = true,
  }) async {
    final response = await _dioClient.post(
      ApiConstants.crawlerImport,
      data: {
        'candidate': candidate,
        'upsert_chroma': upsertChroma,
      },
    );
    return CrawlerImportResult.fromJson(response.data as Map<String, dynamic>);
  }

  Future<CrawlerBatchImportResponse> batchImportCrawlerBooks({
    required List<Map<String, dynamic>> candidates,
    bool upsertChroma = true,
  }) async {
    final response = await _dioClient.post(
      ApiConstants.crawlerBatchImport,
      data: {
        'candidates': candidates,
        'upsert_chroma': upsertChroma,
      },
    );
    return CrawlerBatchImportResponse.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> getUnindexedBooks() async {
    final response = await _dioClient.get(ApiConstants.crawlerUnindexed);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncUnindexedVectors() async {
    final response = await _dioClient.post(ApiConstants.crawlerSyncUnindexed);
    return response.data as Map<String, dynamic>;
  }

  // ---------------- AI RECOMMENDATIONS ----------------
  Future<RecommendationListModel> getForYouRecommendations({int limit = 10}) async {
    final response = await _dioClient.get(
      ApiConstants.recommendationsForYou,
      queryParameters: {'limit': limit},
    );
    return RecommendationListModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationListModel> getContinueReadingRecommendations({int limit = 6}) async {
    final response = await _dioClient.get(
      ApiConstants.recommendationsContinueReading,
      queryParameters: {'limit': limit},
    );
    return RecommendationListModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationListModel> getSimilarRecommendations(String bookId, {int limit = 6}) async {
    final response = await _dioClient.get(
      ApiConstants.recommendationsSimilar(bookId),
      queryParameters: {'limit': limit},
    );
    return RecommendationListModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationPreferencesModel> getRecommendationPreferences() async {
    final response = await _dioClient.get(ApiConstants.recommendationPreferences);
    return RecommendationPreferencesModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationPreferencesModel> updateRecommendationPreferences({
    List<String> preferredGenres = const [],
    List<String> preferredAuthors = const [],
    String readingGoal = '',
  }) async {
    final response = await _dioClient.post(
      ApiConstants.recommendationPreferences,
      data: {
        'preferred_genres': preferredGenres,
        'preferred_authors': preferredAuthors,
        'reading_goal': readingGoal,
      },
    );
    return RecommendationPreferencesModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationFeedbackResponseModel> sendRecommendationFeedback({
    required String bookId,
    bool? liked,
    String reason = '',
  }) async {
    final response = await _dioClient.post(
      ApiConstants.recommendationFeedback,
      data: {
        'book_id': bookId,
        'liked': liked,
        'reason': reason,
      },
    );
    return RecommendationFeedbackResponseModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<RecommendationListModel> refreshRecommendations({int limit = 10}) async {
    final response = await _dioClient.post(
      ApiConstants.recommendationRefresh,
      queryParameters: {'limit': limit},
    );
    return RecommendationListModel.fromJson(response.data as Map<String, dynamic>);
  }

  // ---------------- HEALTH ----------------
  Future<Map<String, dynamic>> checkHealth() async {
    final response = await _dioClient.get(ApiConstants.health);
    return response.data as Map<String, dynamic>;
  }

  // ---------------- LOCATIONS & GOOGLE MAPS ----------------
  Future<LocationSearchResponseModel> searchLocations({
    String location = 'Hồ Chí Minh',
    String kind = 'all',
    int limit = 10,
  }) async {
    final response = await _dioClient.get(
      ApiConstants.locationsSearch,
      queryParameters: {
        'location': location,
        'kind': kind,
        'limit': limit,
      },
    );
    return LocationSearchResponseModel.fromJson(response.data as Map<String, dynamic>);
  }
}

