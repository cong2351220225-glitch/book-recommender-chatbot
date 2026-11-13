import '../models/author_model.dart';
import '../services/api_service.dart';

class AuthorRepository {
  final ApiService _apiService;

  AuthorRepository({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Future<List<AuthorModel>> getAuthors({String? query}) async {
    return await _apiService.getAuthors(query: query);
  }

  Future<AuthorModel> getAuthorDetail(String authorId) async {
    return await _apiService.getAuthorDetail(authorId);
  }
}

