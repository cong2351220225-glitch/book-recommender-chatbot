import 'package:flutter/material.dart';
import '../models/bookshelf_item_model.dart';
import '../repositories/bookshelf_repository.dart';

class BookshelfProvider extends ChangeNotifier {
  final BookshelfRepository _repository;

  List<BookshelfItemModel> _items = [];
  bool _isLoading = false;
  String? _errorMessage;
  int _selectedTabIndex = 0; // 0: Yêu thích, 1: Đang đọc, 2: Đã đọc

  BookshelfProvider({BookshelfRepository? repository})
      : _repository = repository ?? BookshelfRepository();

  List<BookshelfItemModel> get items => _items;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  int get selectedTabIndex => _selectedTabIndex;

  List<BookshelfItemModel> get favoriteItems =>
      _items.where((it) => it.isFavorite).toList();

  List<BookshelfItemModel> get readingItems =>
      _items.where((it) => it.isReading).toList();

  List<BookshelfItemModel> get completedItems =>
      _items.where((it) => it.isCompleted).toList();

  int get totalCount => _items.length;
  int get favoriteCount => favoriteItems.length;
  int get readingCount => readingItems.length;
  int get completedCount => completedItems.length;

  void setSelectedTab(int index) {
    if (_selectedTabIndex != index) {
      _selectedTabIndex = index;
      notifyListeners();
    }
  }

  Future<void> loadBookshelf({bool silent = false}) async {
    if (!silent) {
      _isLoading = true;
      _errorMessage = null;
      notifyListeners();
    }

    try {
      _items = await _repository.getBookshelf();
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  bool isFavorite(String bookId) {
    return _items.any((it) => it.bookId == bookId && it.isFavorite);
  }

  String? getReadingStatus(String bookId) {
    for (final it in _items) {
      if (it.bookId == bookId && (it.isReading || it.isCompleted)) {
        return it.status;
      }
    }
    return null;
  }

  BookshelfItemModel? findItem(String bookId, String status) {
    try {
      return _items.firstWhere(
        (it) => it.bookId == bookId && it.status == status,
      );
    } catch (_) {
      return null;
    }
  }

  Future<bool> toggleFavorite(String bookId) async {
    final existing = findItem(bookId, 'favorite');
    if (existing != null) {
      return await removeItem(existing.id);
    } else {
      return await addItem(bookId: bookId, status: 'favorite');
    }
  }

  Future<bool> addItem({
    required String bookId,
    required String status,
    int progressPage = 0,
    int totalPages = 0,
    int rating = 0,
    String notes = '',
  }) async {
    try {
      final newItem = await _repository.addItem(
        bookId: bookId,
        status: status,
        progressPage: progressPage,
        totalPages: totalPages,
        rating: rating,
        notes: notes,
      );
      // Remove any duplicate if present locally
      _items.removeWhere((it) => it.id == newItem.id);
      _items.insert(0, newItem);
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateStatus(String itemId, String newStatus) async {
    try {
      final updated = await _repository.updateItem(itemId, status: newStatus);
      final idx = _items.indexWhere((it) => it.id == itemId);
      if (idx != -1) {
        _items[idx] = updated;
        notifyListeners();
      }
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateProgress(String itemId, int progressPage, {int? totalPages}) async {
    try {
      final updated = await _repository.updateItem(
        itemId,
        progressPage: progressPage,
        totalPages: totalPages,
      );
      final idx = _items.indexWhere((it) => it.id == itemId);
      if (idx != -1) {
        _items[idx] = updated;
        notifyListeners();
      }
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> removeItem(String itemId) async {
    try {
      final ok = await _repository.deleteItem(itemId);
      if (ok) {
        _items.removeWhere((it) => it.id == itemId);
        notifyListeners();
      }
      return ok;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> removeBook(String bookId, {String? status}) async {
    try {
      final ok = await _repository.deleteBook(bookId, status: status);
      if (ok) {
        _items.removeWhere(
          (it) => it.bookId == bookId && (status == null || it.status == status),
        );
        notifyListeners();
      }
      return ok;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  void clear() {
    _items.clear();
    _errorMessage = null;
    notifyListeners();
  }
}

