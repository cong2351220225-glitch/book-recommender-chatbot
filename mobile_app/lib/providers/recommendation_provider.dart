import 'package:flutter/foundation.dart';
import '../models/recommendation_model.dart';
import '../repositories/recommendation_repository.dart';

class RecommendationProvider extends ChangeNotifier {
  final RecommendationRepository _repository;

  RecommendationProvider({RecommendationRepository? repository})
      : _repository = repository ?? RecommendationRepository();

  // State
  List<RecommendedBookItemModel> _forYouList = [];
  List<RecommendedBookItemModel> _continueReadingList = [];
  final Map<String, List<RecommendedBookItemModel>> _similarCache = {};
  RecommendationPreferencesModel? _preferences;

  bool _isLoadingForYou = false;
  bool _isLoadingContinueReading = false;
  bool _isLoadingPreferences = false;
  bool _isSubmittingFeedback = false;
  String? _errorMessage;

  String _forYouSourceBasis = '';
  bool _isForYouPersonalized = false;
  bool _isForYouLoaded = false;
  bool _isPreferencesLoaded = false;
  String? _currentUsername;

  // Getters
  List<RecommendedBookItemModel> get forYouList => _forYouList;
  List<RecommendedBookItemModel> get continueReadingList => _continueReadingList;
  RecommendationPreferencesModel? get preferences => _preferences;
  bool get isLoadingForYou => _isLoadingForYou;
  bool get isLoadingContinueReading => _isLoadingContinueReading;
  bool get isLoadingPreferences => _isLoadingPreferences;
  bool get isSubmittingFeedback => _isSubmittingFeedback;
  String? get errorMessage => _errorMessage;
  String get forYouSourceBasis => _forYouSourceBasis;
  bool get isForYouPersonalized => _isForYouPersonalized;
  bool get hasForYouData => _forYouList.isNotEmpty;

  List<RecommendedBookItemModel> getSimilarForBook(String bookId) {
    return _similarCache[bookId] ?? [];
  }

  /// Xóa sạch dữ liệu khi logout hoặc đổi user để tránh rò rỉ dữ liệu giữa tài khoản A và B.
  void clearData() {
    _forYouList = [];
    _continueReadingList = [];
    _similarCache.clear();
    _preferences = null;
    _isLoadingForYou = false;
    _isLoadingContinueReading = false;
    _isLoadingPreferences = false;
    _isSubmittingFeedback = false;
    _errorMessage = null;
    _forYouSourceBasis = '';
    _isForYouPersonalized = false;
    _isForYouLoaded = false;
    _isPreferencesLoaded = false;
    _currentUsername = null;
    notifyListeners();
  }

  /// Kiểm tra nếu user thay đổi (đăng nhập tài khoản khác), tự động reset state.
  void checkUserSession(String? username) {
    if (_currentUsername != username) {
      clearData();
      _currentUsername = username;
    }
  }

  /// Tải danh sách sách gợi ý cho bạn (hỗ trợ cả Guest và User).
  Future<void> loadForYou({
    bool force = false,
    int limit = 10,
    String? currentUsername,
  }) async {
    checkUserSession(currentUsername);

    // Tránh gọi API liên tục nếu đã có dữ liệu và không yêu cầu force
    if (_isForYouLoaded && !force) return;

    _isLoadingForYou = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _repository.getForYouRecommendations(limit: limit);
      _forYouList = res.recommendations;
      _forYouSourceBasis = res.sourceBasis;
      _isForYouPersonalized = res.isPersonalized;
      _isForYouLoaded = true;
    } catch (e) {
      _errorMessage = 'Không thể tải danh sách gợi ý: ${e.toString()}';
    } finally {
      _isLoadingForYou = false;
      notifyListeners();
    }
  }

  /// Tải danh sách sách tiếp tục mạch đọc (yêu cầu đăng nhập).
  Future<void> loadContinueReading({
    bool force = false,
    int limit = 6,
    String? currentUsername,
  }) async {
    checkUserSession(currentUsername);
    if (currentUsername == null || currentUsername.isEmpty) {
      _continueReadingList = [];
      return;
    }

    if (_continueReadingList.isNotEmpty && !force) return;

    _isLoadingContinueReading = true;
    notifyListeners();

    try {
      final res = await _repository.getContinueReadingRecommendations(limit: limit);
      _continueReadingList = res.recommendations;
    } catch (e) {
      // Tiếp tục mạch đọc là phụ trợ, không làm crash màn hình chính
      _continueReadingList = [];
    } finally {
      _isLoadingContinueReading = false;
      notifyListeners();
    }
  }

  /// Tải danh sách sách tương tự cho 1 cuốn sách cụ thể (có cache).
  Future<List<RecommendedBookItemModel>> loadSimilar(
    String bookId, {
    bool force = false,
    int limit = 6,
  }) async {
    if (!force && _similarCache.containsKey(bookId)) {
      return _similarCache[bookId]!;
    }

    try {
      final res = await _repository.getSimilarRecommendations(bookId, limit: limit);
      _similarCache[bookId] = res.recommendations;
      notifyListeners();
      return res.recommendations;
    } catch (e) {
      return [];
    }
  }

  /// Tải sở thích đọc sách của user.
  Future<void> loadPreferences({
    bool force = false,
    String? currentUsername,
  }) async {
    checkUserSession(currentUsername);
    if (currentUsername == null || currentUsername.isEmpty) {
      _preferences = null;
      return;
    }

    if (_isPreferencesLoaded && !force) return;

    _isLoadingPreferences = true;
    notifyListeners();

    try {
      final prefs = await _repository.getPreferences();
      _preferences = prefs;
      _isPreferencesLoaded = true;
    } catch (e) {
      // Preferences có thể rỗng nếu user mới
    } finally {
      _isLoadingPreferences = false;
      notifyListeners();
    }
  }

  /// Cập nhật sở thích đọc sách.
  Future<bool> updatePreferences({
    required List<String> preferredGenres,
    List<String> preferredAuthors = const [],
    String readingGoal = '',
  }) async {
    _isLoadingPreferences = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final updated = await _repository.updatePreferences(
        preferredGenres: preferredGenres,
        preferredAuthors: preferredAuthors,
        readingGoal: readingGoal,
      );
      _preferences = updated;
      _isPreferencesLoaded = true;

      // Tự động làm mới danh sách gợi ý theo sở thích mới
      await refresh(limit: _forYouList.length > 0 ? _forYouList.length : 10);
      return true;
    } catch (e) {
      _errorMessage = 'Cập nhật sở thích thất bại: ${e.toString()}';
      return false;
    } finally {
      _isLoadingPreferences = false;
      notifyListeners();
    }
  }

  /// Thích (Like) một cuốn sách.
  Future<bool> likeBook(String bookId, {String reason = ''}) async {
    _isSubmittingFeedback = true;
    notifyListeners();

    try {
      final res = await _repository.sendFeedback(
        bookId: bookId,
        liked: true,
        reason: reason,
      );

      if (res.success) {
        // Cập nhật trạng thái trong list For You
        for (final item in _forYouList) {
          if (item.bookId == bookId) {
            item.userFeedback = 'liked';
          }
        }
      }
      return res.success;
    } catch (e) {
      return false;
    } finally {
      _isSubmittingFeedback = false;
      notifyListeners();
    }
  }

  /// Không thích (Dislike) một cuốn sách -> Loại bỏ ngay khỏi danh sách gợi ý.
  Future<bool> dislikeBook(String bookId, {String reason = ''}) async {
    _isSubmittingFeedback = true;
    notifyListeners();

    try {
      final res = await _repository.sendFeedback(
        bookId: bookId,
        liked: false,
        reason: reason,
      );

      if (res.success) {
        // Loại bỏ ngay cuốn sách bị dislike khỏi danh sách hiển thị
        _forYouList.removeWhere((item) => item.bookId == bookId);
        _continueReadingList.removeWhere((item) => item.bookId == bookId);
      }
      return res.success;
    } catch (e) {
      return false;
    } finally {
      _isSubmittingFeedback = false;
      notifyListeners();
    }
  }

  /// Hủy bỏ phản hồi (Restore / Reset).
  Future<bool> restoreBook(String bookId) async {
    _isSubmittingFeedback = true;
    notifyListeners();

    try {
      final res = await _repository.sendFeedback(
        bookId: bookId,
        liked: null,
      );

      if (res.success) {
        for (final item in _forYouList) {
          if (item.bookId == bookId) {
            item.userFeedback = null;
          }
        }
      }
      return res.success;
    } catch (e) {
      return false;
    } finally {
      _isSubmittingFeedback = false;
      notifyListeners();
    }
  }

  /// Làm mới gợi ý.
  Future<void> refresh({int limit = 10}) async {
    _isLoadingForYou = true;
    notifyListeners();

    try {
      final res = await _repository.refreshRecommendations(limit: limit);
      _forYouList = res.recommendations;
      _forYouSourceBasis = res.sourceBasis;
      _isForYouPersonalized = res.isPersonalized;
      _isForYouLoaded = true;
    } catch (e) {
      // Fallback về getForYou nếu refresh token/post gặp vấn đề
      await loadForYou(force: true, limit: limit, currentUsername: _currentUsername);
    } finally {
      _isLoadingForYou = false;
      notifyListeners();
    }
  }
}

