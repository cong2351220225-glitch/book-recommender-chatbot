import '../models/recommendation_model.dart';
import '../services/api_service.dart';

class RecommendationRepository {
  final ApiService _apiService;

  RecommendationRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<RecommendationListModel> getForYouRecommendations({int limit = 10}) async {
    return await _apiService.getForYouRecommendations(limit: limit);
  }

  Future<RecommendationListModel> getContinueReadingRecommendations({int limit = 6}) async {
    return await _apiService.getContinueReadingRecommendations(limit: limit);
  }

  Future<RecommendationListModel> getSimilarRecommendations(String bookId, {int limit = 6}) async {
    return await _apiService.getSimilarRecommendations(bookId, limit: limit);
  }

  Future<RecommendationPreferencesModel> getPreferences() async {
    return await _apiService.getRecommendationPreferences();
  }

  Future<RecommendationPreferencesModel> updatePreferences({
    List<String> preferredGenres = const [],
    List<String> preferredAuthors = const [],
    String readingGoal = '',
  }) async {
    return await _apiService.updateRecommendationPreferences(
      preferredGenres: preferredGenres,
      preferredAuthors: preferredAuthors,
      readingGoal: readingGoal,
    );
  }

  Future<RecommendationFeedbackResponseModel> sendFeedback({
    required String bookId,
    bool? liked,
    String reason = '',
  }) async {
    return await _apiService.sendRecommendationFeedback(
      bookId: bookId,
      liked: liked,
      reason: reason,
    );
  }

  Future<RecommendationListModel> refreshRecommendations({int limit = 10}) async {
    return await _apiService.refreshRecommendations(limit: limit);
  }
}

