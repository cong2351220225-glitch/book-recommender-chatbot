import 'package:flutter/foundation.dart';
import '../models/crawler_book_model.dart';
import '../repositories/crawler_repository.dart';

class CrawlerProvider extends ChangeNotifier {
  final CrawlerRepository _repository;

  CrawlerProvider({CrawlerRepository? repository})
      : _repository = repository ?? CrawlerRepository();

  List<CrawlerSourceModel> _sources = [];
  String _selectedSource = 'all';
  List<CrawlerBookCandidate> _results = [];
  bool _isLoading = false;
  bool _isImporting = false;
  String? _errorMessage;
  CrawlerBatchImportResponse? _lastBatchResult;

  // ChromaDB Vector Sync State
  ChromaIndexStatus? _chromaStatus;
  bool _isLoadingChromaStatus = false;
  bool _isSyncingChroma = false;
  SyncChromaResult? _lastSyncResult;
  String? _chromaErrorMessage;

  // Getters
  List<CrawlerSourceModel> get sources => _sources;
  String get selectedSource => _selectedSource;
  List<CrawlerBookCandidate> get results => _results;
  bool get isLoading => _isLoading;
  bool get isImporting => _isImporting;
  String? get errorMessage => _errorMessage;
  CrawlerBatchImportResponse? get lastBatchResult => _lastBatchResult;

  // Statistics Getters
  int get totalCount => _results.length;
  int get newCount => _results.where((b) => b.isNew).length;
  int get duplicateCount => _results.where((b) => b.isDuplicate).length;
  int get uncertainCount => _results.where((b) => b.isUncertain).length;
  int get noDescCount => _results.where((b) => b.hasNoDescription).length;

  List<CrawlerBookCandidate> get selectedBooks =>
      _results.where((b) => b.isSelected).toList();

  int get selectedCount => selectedBooks.length;

  bool get isAllSelected =>
      _results.isNotEmpty && _results.every((b) => b.isSelected);

  // ChromaDB Vector Getters
  ChromaIndexStatus? get chromaStatus => _chromaStatus;
  bool get isLoadingChromaStatus => _isLoadingChromaStatus;
  bool get isSyncingChroma => _isSyncingChroma;
  SyncChromaResult? get lastSyncResult => _lastSyncResult;
  String? get chromaErrorMessage => _chromaErrorMessage;

  void setSelectedSource(String sourceId) {
    _selectedSource = sourceId;
    notifyListeners();
  }

  void toggleSelectBook(int index, bool? value) {
    if (index >= 0 && index < _results.length) {
      _results[index].isSelected = value ?? false;
      notifyListeners();
    }
  }

  void toggleSelectAll(bool? value) {
    final select = value ?? false;
    for (final book in _results) {
      book.isSelected = select;
    }
    notifyListeners();
  }

  void selectAllNew() {
    for (final book in _results) {
      book.isSelected = book.isNew;
    }
    notifyListeners();
  }

  void deselectAll() {
    for (final book in _results) {
      book.isSelected = false;
    }
    notifyListeners();
  }

  void clearResults() {
    _results.clear();
    _errorMessage = null;
    _lastBatchResult = null;
    notifyListeners();
  }

  Future<void> fetchSources() async {
    try {
      _sources = await _repository.getSources();
      notifyListeners();
    } catch (e) {
      _sources = [
        CrawlerSourceModel(id: 'all', name: 'Tất cả các nguồn', description: 'Đồng thời 6 nguồn'),
        CrawlerSourceModel(id: 'openlibrary', name: 'Open Library', description: 'Kho mở'),
        CrawlerSourceModel(id: 'google_books', name: 'Google Books', description: 'Google'),
        CrawlerSourceModel(id: 'gutenberg', name: 'Project Gutenberg', description: 'Sách tự do'),
        CrawlerSourceModel(id: 'internet_archive', name: 'Internet Archive', description: 'Lưu trữ'),
        CrawlerSourceModel(id: 'europeana', name: 'Europeana', description: 'Di sản châu Âu'),
        CrawlerSourceModel(id: 'itunes', name: 'Apple Books', description: 'Apple'),
      ];
      notifyListeners();
    }
  }

  Future<void> search({
    String query = '',
    String author = '',
    String subject = '',
    String isbn = '',
    String language = '',
    int yearFrom = 0,
    int yearTo = 0,
    int limit = 20,
  }) async {
    final q = query.trim();
    final a = author.trim();
    final s = subject.trim();
    final i = isbn.trim();

    if (q.isEmpty && a.isEmpty && s.isEmpty && i.isEmpty) {
      _errorMessage = 'Vui lòng nhập ít nhất một từ khóa, tên tác giả, chủ đề hoặc mã ISBN.';
      notifyListeners();
      return;
    }

    _isLoading = true;
    _errorMessage = null;
    _lastBatchResult = null;
    notifyListeners();

    try {
      _results = await _repository.searchBooks(
        query: q,
        author: a,
        subject: s,
        isbn: i,
        language: language,
        yearFrom: yearFrom,
        yearTo: yearTo,
        source: _selectedSource,
        limit: limit,
      );
    } catch (e) {
      _errorMessage = 'Tìm kiếm thất bại: ${e.toString()}';
      _results = [];
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<CrawlerImportResult> importSingleBook(
    CrawlerBookCandidate candidate, {
    bool upsertChroma = true,
  }) async {
    _isImporting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final result = await _repository.importBook(
        candidate: candidate.toCandidatePayload(),
        upsertChroma: upsertChroma,
      );
      if (result.success) {
        candidate.isSelected = false;
      }
      return result;
    } catch (e) {
      return CrawlerImportResult(
        title: candidate.title,
        success: false,
        message: 'Lỗi khi nhập sách: ${e.toString()}',
      );
    } finally {
      _isImporting = false;
      notifyListeners();
    }
  }

  Future<CrawlerBatchImportResponse> importSelectedBooks({
    bool upsertChroma = true,
  }) async {
    final targets = selectedBooks;
    if (targets.isEmpty) {
      return CrawlerBatchImportResponse(
        totalRequested: 0,
        importedCount: 0,
        skippedCount: 0,
        results: [],
      );
    }

    _isImporting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final payloads = targets.map((b) => b.toCandidatePayload()).toList();
      final response = await _repository.batchImport(
        candidates: payloads,
        upsertChroma: upsertChroma,
      );
      _lastBatchResult = response;

      // Cập nhật trạng thái sách trong danh sách kết quả sau khi nhập
      for (final res in response.results) {
        for (final book in _results) {
          if (book.title == res.title && res.success) {
            book.isSelected = false;
          }
        }
      }

      return response;
    } catch (e) {
      _errorMessage = 'Lỗi nhập danh sách: ${e.toString()}';
      return CrawlerBatchImportResponse(
        totalRequested: targets.length,
        importedCount: 0,
        skippedCount: targets.length,
        results: targets
            .map((t) => CrawlerImportResult(
                  title: t.title,
                  success: false,
                  message: e.toString(),
                ))
            .toList(),
      );
    } finally {
      _isImporting = false;
      notifyListeners();
    }
  }

  // ---------------- CHROMADB VECTOR SYNC ----------------

  Future<void> fetchChromaStatus() async {
    _isLoadingChromaStatus = true;
    _chromaErrorMessage = null;
    notifyListeners();

    try {
      _chromaStatus = await _repository.getChromaIndexStatus();
    } catch (e) {
      _chromaErrorMessage = 'Không thể tải trạng thái ChromaDB: ${e.toString()}';
    } finally {
      _isLoadingChromaStatus = false;
      notifyListeners();
    }
  }

  Future<SyncChromaResult> syncChroma() async {
    _isSyncingChroma = true;
    _chromaErrorMessage = null;
    notifyListeners();

    try {
      final result = await _repository.syncUnindexedVectors();
      _lastSyncResult = result;
      // Reload stats after sync completes
      try {
        _chromaStatus = await _repository.getChromaIndexStatus();
      } catch (_) {}
      return result;
    } catch (e) {
      final failResult = SyncChromaResult(
        success: false,
        syncedCount: 0,
        totalUnindexed: _chromaStatus?.unindexedCount ?? 0,
        message: 'Lỗi đồng bộ vector: ${e.toString()}',
      );
      _lastSyncResult = failResult;
      _chromaErrorMessage = failResult.message;
      return failResult;
    } finally {
      _isSyncingChroma = false;
      notifyListeners();
    }
  }
}
