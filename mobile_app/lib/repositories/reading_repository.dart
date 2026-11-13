import 'dart:typed_data';
import '../models/reading_progress_model.dart';
import '../services/api_service.dart';

class ReadingRepository {
  final ApiService _apiService;

  ReadingRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<Map<String, dynamic>> getReadingStatus(String bookId) async {
    return await _apiService.getReadingStatus(bookId);
  }

  Future<ReadingDocInfoModel> getReadingDocInfo(String bookId) async {
    return await _apiService.getReadingDocInfo(bookId);
  }

  Future<ReadingProgressModel> getReadingProgress(String bookId) async {
    return await _apiService.getReadingProgress(bookId);
  }

  Future<ReadingProgressModel> saveProgress({
    required String bookId,
    required int currentPage,
    required int totalPages,
    String? location,
  }) async {
    return await _apiService.saveReadingProgress(
      bookId: bookId,
      currentPage: currentPage,
      totalPages: totalPages,
      location: location,
    );
  }

  Future<Uint8List> getDocumentBytes(String bookId) async {
    return await _apiService.downloadReadingFile(bookId);
  }
}

