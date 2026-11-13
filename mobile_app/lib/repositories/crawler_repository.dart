import '../models/crawler_book_model.dart';
import '../services/api_service.dart';

class CrawlerRepository {
  final ApiService _apiService;

  CrawlerRepository({ApiService? apiService}) : _apiService = apiService ?? ApiService();

  Future<List<CrawlerSourceModel>> getSources() async {
    return await _apiService.getCrawlerSources();
  }

  Future<List<CrawlerBookCandidate>> searchBooks({
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
    return await _apiService.searchCrawlerBooks(
      query: query,
      author: author,
      subject: subject,
      isbn: isbn,
      language: language,
      yearFrom: yearFrom,
      yearTo: yearTo,
      source: source,
      limit: limit,
    );
  }

  Future<CrawlerImportResult> importBook({
    required Map<String, dynamic> candidate,
    bool upsertChroma = true,
  }) async {
    return await _apiService.importCrawlerBook(
      candidate: candidate,
      upsertChroma: upsertChroma,
    );
  }

  Future<CrawlerBatchImportResponse> batchImport({
    required List<Map<String, dynamic>> candidates,
    bool upsertChroma = true,
  }) async {
    return await _apiService.batchImportCrawlerBooks(
      candidates: candidates,
      upsertChroma: upsertChroma,
    );
  }

  Future<Map<String, dynamic>> getUnindexed() async {
    return await _apiService.getUnindexedBooks();
  }

  Future<ChromaIndexStatus> getChromaIndexStatus() async {
    final data = await _apiService.getUnindexedBooks();
    return ChromaIndexStatus.fromJson(data);
  }

  Future<Map<String, dynamic>> syncUnindexed() async {
    return await _apiService.syncUnindexedVectors();
  }

  Future<SyncChromaResult> syncUnindexedVectors() async {
    final data = await _apiService.syncUnindexedVectors();
    return SyncChromaResult.fromJson(data);
  }
}

