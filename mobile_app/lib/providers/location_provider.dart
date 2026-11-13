import 'package:flutter/material.dart';
import '../models/location_item_model.dart';
import '../repositories/location_repository.dart';

class LocationProvider extends ChangeNotifier {
  final LocationRepository _repository;

  List<LocationItemModel> _locations = [];
  Map<String, String> _fallbackUrls = {};
  bool _isLoading = false;
  String? _errorMessage;
  String _selectedKind = 'bookstore'; // 'bookstore', 'library', 'all'
  String _currentQuery = '';
  int _limit = 10;

  LocationProvider({LocationRepository? repository})
      : _repository = repository ?? LocationRepository();

  List<LocationItemModel> get locations => _locations;
  Map<String, String> get fallbackUrls => _fallbackUrls;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String get selectedKind => _selectedKind;
  String get currentQuery => _currentQuery;
  int get limit => _limit;

  void setKind(String kind) {
    if (_selectedKind != kind) {
      _selectedKind = kind;
      notifyListeners();
    }
  }

  void setLimit(int limit) {
    if (_limit != limit) {
      _limit = limit;
      notifyListeners();
    }
  }

  Future<void> searchLocations({
    String? query,
    String? kind,
    int? limit,
  }) async {
    final loc = query?.trim() ?? _currentQuery.trim();
    if (loc.isEmpty) {
      _errorMessage = 'Vui lòng nhập khu vực, quận/huyện hoặc tỉnh/thành phố.';
      notifyListeners();
      return;
    }

    _currentQuery = loc;
    if (kind != null) _selectedKind = kind;
    if (limit != null) _limit = limit;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await _repository.searchLocations(
        location: _currentQuery,
        kind: _selectedKind,
        limit: _limit,
      );
      _locations = response.results;
      _fallbackUrls = response.fallbackUrls;
      _errorMessage = null;
    } catch (e) {
      _locations = [];
      _errorMessage = e.toString().replaceAll('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void retryLastSearch() {
    if (_currentQuery.isNotEmpty) {
      searchLocations(query: _currentQuery, kind: _selectedKind, limit: _limit);
    }
  }

  void clearResults() {
    _locations.clear();
    _errorMessage = null;
    _currentQuery = '';
    notifyListeners();
  }
}

