import 'package:flutter/material.dart';
import '../models/book_model.dart';
import '../repositories/book_repository.dart';

class BookProvider extends ChangeNotifier {
  final BookRepository _bookRepository;

  // Catalog State
  List<BookModel> _books = [];
  int _totalBooks = 0;
  int _currentPage = 1;
  int _totalPages = 0;
  bool _isLoading = false;
  bool _isLoadingMore = false;
  String? _errorMessage;

  // Active Filters
  String _searchQuery = '';
  String _selectedGenre = 'Tất cả';
  String _selectedLanguage = 'Tất cả';
  int? _minYear;
  int? _maxYear;
  double? _minRating;
  String _sortBy = 'Phù hợp';
  bool _readingOnly = false;
  bool _featuredOnly = false;
  String? _isbnFilter;
  String? _authorFilter;
  List<String> _languages = [];

  // Detail State
  BookModel? _selectedBook;
  List<BookModel> _relatedBooks = [];
  String _readingStatus = '';
  bool _canRead = false;
  bool _isLoadingDetail = false;
  String? _detailError;

  BookProvider({BookRepository? bookRepository})
      : _bookRepository = bookRepository ?? BookRepository();

  // Getters
  List<BookModel> get books => _books;
  int get totalBooks => _totalBooks;
  int get currentPage => _currentPage;
  int get totalPages => _totalPages;
  bool get isLoading => _isLoading;
  bool get isLoadingMore => _isLoadingMore;
  bool get hasMore => _currentPage < _totalPages;
  String? get errorMessage => _errorMessage;

  String get searchQuery => _searchQuery;
  String get selectedGenre => _selectedGenre;
  String get selectedLanguage => _selectedLanguage;
  int? get minYear => _minYear;
  int? get maxYear => _maxYear;
  double? get minRating => _minRating;
  String get sortBy => _sortBy;
  bool get readingOnly => _readingOnly;
  bool get featuredOnly => _featuredOnly;
  String? get isbnFilter => _isbnFilter;
  String? get authorFilter => _authorFilter;
  List<String> get languages => _languages;

  bool get hasActiveFilters =>
      _searchQuery.isNotEmpty ||
      _selectedGenre != 'Tất cả' ||
      _selectedLanguage != 'Tất cả' ||
      _minYear != null ||
      _maxYear != null ||
      (_minRating != null && _minRating! > 0) ||
      _readingOnly ||
      _featuredOnly ||
      (_isbnFilter != null && _isbnFilter!.isNotEmpty) ||
      (_authorFilter != null && _authorFilter!.isNotEmpty);

  BookModel? get selectedBook => _selectedBook;
  List<BookModel> get relatedBooks => _relatedBooks;
  String get readingStatus => _readingStatus;
  bool get canRead => _canRead;
  bool get isLoadingDetail => _isLoadingDetail;
  String? get detailError => _detailError;

  Future<void> fetchLanguages() async {
    try {
      final langs = await _bookRepository.getLanguages();
      _languages = langs;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchBooks({bool refresh = false}) async {
    if (refresh) {
      _currentPage = 1;
    }

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await _bookRepository.getBooks(
        query: _searchQuery,
        genre: _selectedGenre,
        language: _selectedLanguage,
        minYear: _minYear,
        maxYear: _maxYear,
        minRating: _minRating,
        sortBy: _sortBy,
        readingOnly: _readingOnly,
        featuredOnly: _featuredOnly,
        isbn: _isbnFilter,
        author: _authorFilter,
        page: _currentPage,
        pageSize: 20,
      );

      _books = response.items;
      _totalBooks = response.total;
      _currentPage = response.page;
      _totalPages = response.totalPages;
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadMore() async {
    if (_isLoadingMore || !hasMore || _isLoading) return;

    _isLoadingMore = true;
    notifyListeners();

    try {
      final nextPage = _currentPage + 1;
      final response = await _bookRepository.getBooks(
        query: _searchQuery,
        genre: _selectedGenre,
        language: _selectedLanguage,
        minYear: _minYear,
        maxYear: _maxYear,
        minRating: _minRating,
        sortBy: _sortBy,
        readingOnly: _readingOnly,
        featuredOnly: _featuredOnly,
        isbn: _isbnFilter,
        author: _authorFilter,
        page: nextPage,
        pageSize: 20,
      );

      _books.addAll(response.items);
      _currentPage = response.page;
      _totalPages = response.totalPages;
      _totalBooks = response.total;
    } catch (_) {
    } finally {
      _isLoadingMore = false;
      notifyListeners();
    }
  }

  void setSearchQuery(String query) {
    if (_searchQuery == query) return;
    _searchQuery = query;
    fetchBooks(refresh: true);
  }

  void setGenre(String genre) {
    if (_selectedGenre == genre) return;
    _selectedGenre = genre;
    fetchBooks(refresh: true);
  }

  void setLanguage(String language) {
    if (_selectedLanguage == language) return;
    _selectedLanguage = language;
    fetchBooks(refresh: true);
  }

  void setYearRange(int? min, int? max) {
    if (_minYear == min && _maxYear == max) return;
    _minYear = min;
    _maxYear = max;
    fetchBooks(refresh: true);
  }

  void setMinRating(double? rating) {
    if (_minRating == rating) return;
    _minRating = rating;
    fetchBooks(refresh: true);
  }

  void setSortBy(String sort) {
    if (_sortBy == sort) return;
    _sortBy = sort;
    fetchBooks(refresh: true);
  }

  void toggleReadingOnly() {
    _readingOnly = !_readingOnly;
    fetchBooks(refresh: true);
  }

  void toggleFeaturedOnly() {
    _featuredOnly = !_featuredOnly;
    fetchBooks(refresh: true);
  }

  void applyAdvancedFilter({
    String? query,
    String? title,
    String? author,
    String? isbn,
    String? genre,
    String? language,
    int? minYear,
    int? maxYear,
    double? minRating,
    String? sortBy,
    bool? readingOnly,
    bool? featuredOnly,
  }) {
    if (query != null) _searchQuery = query;
    if (author != null) _authorFilter = author;
    if (isbn != null) _isbnFilter = isbn;
    if (genre != null) _selectedGenre = genre;
    if (language != null) _selectedLanguage = language;
    _minYear = minYear;
    _maxYear = maxYear;
    _minRating = minRating;
    if (sortBy != null) _sortBy = sortBy;
    if (readingOnly != null) _readingOnly = readingOnly;
    if (featuredOnly != null) _featuredOnly = featuredOnly;
    fetchBooks(refresh: true);
  }

  void resetFilters() {
    _searchQuery = '';
    _selectedGenre = 'Tất cả';
    _selectedLanguage = 'Tất cả';
    _minYear = null;
    _maxYear = null;
    _minRating = null;
    _sortBy = 'Phù hợp';
    _readingOnly = false;
    _featuredOnly = false;
    _isbnFilter = null;
    _authorFilter = null;
    fetchBooks(refresh: true);
  }

  Future<void> fetchBookDetail(String bookId) async {
    _isLoadingDetail = true;
    _detailError = null;
    _selectedBook = null;
    _relatedBooks = [];
    notifyListeners();

    try {
      final data = await _bookRepository.getBookDetail(bookId);
      _selectedBook = data['book'] as BookModel;
      _relatedBooks = data['related_books'] as List<BookModel>;
      _readingStatus = data['reading_status'] as String;
      _canRead = data['can_read'] as bool;
      _detailError = null;
    } catch (e) {
      _detailError = e.toString();
    } finally {
      _isLoadingDetail = false;
      notifyListeners();
    }
  }
}
