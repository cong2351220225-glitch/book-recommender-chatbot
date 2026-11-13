import '../models/genre_model.dart';
import '../services/api_service.dart';

class GenreRepository {
  final ApiService _apiService;

  GenreRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<List<GenreModel>> getGenres() async {
    return await _apiService.getGenres();
  }
}

