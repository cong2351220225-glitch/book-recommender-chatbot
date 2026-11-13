import '../models/bookshelf_item_model.dart';
import '../services/api_service.dart';

class BookshelfRepository {
  final ApiService _apiService;

  BookshelfRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<List<BookshelfItemModel>> getBookshelf({String? status}) async {
    return await _apiService.getBookshelf(status: status);
  }

  Future<Map<String, dynamic>> checkBook(String bookId) async {
    return await _apiService.checkBookInBookshelf(bookId);
  }

  Future<BookshelfItemModel> addItem({
    required String bookId,
    required String status,
    int progressPage = 0,
    int totalPages = 0,
    int rating = 0,
    String notes = '',
  }) async {
    return await _apiService.addBookshelfItem(
      bookId: bookId,
      status: status,
      progressPage: progressPage,
      totalPages: totalPages,
      rating: rating,
      notes: notes,
    );
  }

  Future<BookshelfItemModel> updateItem(
    String itemId, {
    String? status,
    int? progressPage,
    int? totalPages,
    int? rating,
    String? notes,
  }) async {
    return await _apiService.updateBookshelfItem(
      itemId,
      status: status,
      progressPage: progressPage,
      totalPages: totalPages,
      rating: rating,
      notes: notes,
    );
  }

  Future<bool> deleteItem(String itemId) async {
    return await _apiService.deleteBookshelfItem(itemId);
  }

  Future<bool> deleteBook(String bookId, {String? status}) async {
    return await _apiService.deleteBookFromBookshelf(bookId, status: status);
  }
}

