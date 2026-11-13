import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../models/reading_progress_model.dart';
import '../repositories/reading_repository.dart';

class ReadingProvider extends ChangeNotifier {
  final ReadingRepository _repository;

  ReadingDocInfoModel? _docInfo;
  Uint8List? _documentBytes;
  int _currentPage = 1;
  int _totalPages = 1;
  double _zoomLevel = 1.0;
  bool _isLoading = false;
  String? _errorMessage;

  bool _hasResumePosition = false;
  int _resumePage = 1;

  ReadingProvider({ReadingRepository? repository})
      : _repository = repository ?? ReadingRepository();

  ReadingDocInfoModel? get docInfo => _docInfo;
  Uint8List? get documentBytes => _documentBytes;
  int get currentPage => _currentPage;
  int get totalPages => _totalPages;
  double get zoomLevel => _zoomLevel;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get hasResumePosition => _hasResumePosition;
  int get resumePage => _resumePage;

  double get progressPercentage {
    if (_totalPages <= 0) return 0.0;
    final pct = _currentPage / _totalPages;
    return pct > 1.0 ? 1.0 : (pct < 0.0 ? 0.0 : pct);
  }

  Future<void> loadDocument(String bookId) async {
    _isLoading = true;
    _errorMessage = null;
    _documentBytes = null;
    _docInfo = null;
    _hasResumePosition = false;
    _currentPage = 1;
    _totalPages = 1;
    _zoomLevel = 1.0;
    notifyListeners();

    try {
      // 1. Fetch document metadata info
      _docInfo = await _repository.getReadingDocInfo(bookId);

      if (!_docInfo!.canRead) {
        _errorMessage = 'Tác phẩm này hiện chưa có bản số hóa khả dụng để đọc.';
        _isLoading = false;
        notifyListeners();
        return;
      }

      // 2. Fetch document binary bytes
      _documentBytes = await _repository.getDocumentBytes(bookId);

      // Check saved progress
      if (_docInfo?.savedProgress != null && _docInfo!.savedProgress!.currentPage > 1) {
        _resumePage = _docInfo!.savedProgress!.currentPage;
        _hasResumePosition = true;
      }

      // Set initial page from resume or 1
      _currentPage = _hasResumePosition ? _resumePage : 1;
      _totalPages = _docInfo?.savedProgress?.totalPages ?? 5;
      if (_totalPages < _currentPage) _totalPages = _currentPage;
    } catch (e) {
      _errorMessage = 'Không thể tải tài liệu số: ${e.toString()}';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setTotalPages(int total) {
    if (total > 0 && _totalPages != total) {
      _totalPages = total;
      notifyListeners();
    }
  }

  void jumpToPage(int page) {
    final clamped = page.clamp(1, _totalPages);
    if (_currentPage != clamped) {
      _currentPage = clamped;
      notifyListeners();
      saveProgress();
    }
  }

  void nextPage() {
    if (_currentPage < _totalPages) {
      jumpToPage(_currentPage + 1);
    }
  }

  void prevPage() {
    if (_currentPage > 1) {
      jumpToPage(_currentPage - 1);
    }
  }

  void resumeFromSavedPage() {
    if (_hasResumePosition) {
      jumpToPage(_resumePage);
      _hasResumePosition = false;
      notifyListeners();
    }
  }

  void dismissResumePrompt() {
    _hasResumePosition = false;
    notifyListeners();
  }

  void zoomIn() {
    if (_zoomLevel < 3.0) {
      _zoomLevel = (_zoomLevel + 0.25).clamp(0.5, 3.0);
      notifyListeners();
    }
  }

  void zoomOut() {
    if (_zoomLevel > 0.5) {
      _zoomLevel = (_zoomLevel - 0.25).clamp(0.5, 3.0);
      notifyListeners();
    }
  }

  void resetZoom() {
    _zoomLevel = 1.0;
    notifyListeners();
  }

  Future<void> saveProgress() async {
    if (_docInfo == null) return;
    try {
      await _repository.saveProgress(
        bookId: _docInfo!.bookId,
        currentPage: _currentPage,
        totalPages: _totalPages,
        location: 'Trang $_currentPage',
      );
    } catch (_) {}
  }

  void reset() {
    _docInfo = null;
    _documentBytes = null;
    _currentPage = 1;
    _totalPages = 1;
    _zoomLevel = 1.0;
    _isLoading = false;
    _errorMessage = null;
    _hasResumePosition = false;
    notifyListeners();
  }
}

