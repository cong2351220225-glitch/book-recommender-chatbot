import '../models/home_stats_model.dart';
import '../services/api_service.dart';

class HomeRepository {
  final ApiService _apiService;

  HomeRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<HomeStatsModel> getHomeStats() async {
    return await _apiService.getHomeStats();
  }
}

