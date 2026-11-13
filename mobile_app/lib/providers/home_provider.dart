import 'package:flutter/material.dart';
import '../models/home_stats_model.dart';
import '../repositories/home_repository.dart';

class HomeProvider extends ChangeNotifier {
  final HomeRepository _homeRepository;

  HomeStatsModel? _stats;
  bool _isLoading = false;
  String? _errorMessage;

  HomeProvider({HomeRepository? homeRepository})
      : _homeRepository = homeRepository ?? HomeRepository();

  HomeStatsModel? get stats => _stats;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadHomeStats({bool forceRefresh = false}) async {
    if (_stats != null && !forceRefresh) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _stats = await _homeRepository.getHomeStats();
      _errorMessage = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

